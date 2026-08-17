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


# HYP-PF-016 (LOGOUT-RESP-001): response-first logout.  Attended GT-008
# falsified the client-observable layer of the ack+close shape -- the real
# client never notices a bare server FIN -- so a screen transition needs a
# protocol response frame the client recognizes.  R40 decoded the one
# candidate the client itself produces: GetWorldInfoVital (0x3D4B), fired on
# every logout-dialog open (correlation 7/7 across two sessions, always
# followed by LogoutVital within 2-14 s) as a deterministic 268-byte PC:
# GSCN_RunTimeProtocolReq envelope with vital count 3 and a 248-byte payload
# whose skeleton is byte-stable across sessions -- two byte-identical full
# 123-byte records plus the empty record 0B 00, with exactly six float32
# value slots per record free (semantics not claimed).  No golden response
# exists in the corpus, so the designed response invents no content byte: it
# echoes the full payload the client itself sent last on the same connection,
# inside the accepted GSCN_RunTimeProtocolRes v4 collection envelope,
# mirroring the client's own collection count (3) and nested id/version and
# closing with the proven trailing derived-class change mask 0B 00 (the
# DELETE-SOFT-002 lesson: a RuntimeRes collection without that mask is
# over-read by the client and rejected with ErrorData=28317).
LOGOUT_RESPONSE_POLICY_ACK_ONLY = "ack_only"
LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST = "worldinfo_response_first"

WORLDINFO_VITAL_ID = 0x3D4B
WORLDINFO_FULL_VITAL_COUNT = 3
WORLDINFO_RECORD_SIZE = 123
WORLDINFO_EMPTY_RECORD = bytes.fromhex("0B00")
WORLDINFO_FULL_PAYLOAD_SIZE = (
    2 * WORLDINFO_RECORD_SIZE + len(WORLDINFO_EMPTY_RECORD)
)
# R40 float32 value slots (each preceded by its 0x2A tag byte): the only
# payload bytes that ever differed between the two full-form capture
# sessions.  Their meaning is an explicit nonclaim; they are echoed verbatim.
WORLDINFO_RECORD_FLOAT_SLICES = (
    (58, 62), (63, 67), (98, 102), (103, 107), (112, 116), (117, 121),
)
# Full-form record skeleton: the capture_gt002 record with the six float
# value slots zeroed.  capture_item_move_hyp001 yields the identical
# skeleton (verified byte-for-byte); any full form outside this skeleton
# fails closed and is never stored or echoed.
WORLDINFO_RECORD_SKELETON = bytes.fromhex(
    "0B0012010F0B000B010BFF32000000000000000026FFFFFFFF0B190B000B0005"
    "0132000000000000000026010000000B0C0B0C0B0C0B0308012A000000002A00"
    "0000000B020B040B00326F000000000000000B040B01326E0000000000000008"
    "022A000000002A000000000B0008032A000000002A000000000B00"
)

WORLDINFO_RESPONSE_PC_SIZE = 270
WORLDINFO_RESPONSE_FRAME_SIZE = 283

# Deterministic captured probe payloads (one full form per session; within a
# session every shot was byte-identical -- R40).  Pinned end to end for the
# tests and the headless probe; every other lawful full form differs only in
# the float slots and is covered by the structural checks above.
WORLDINFO_PROBE_PAYLOADS = {
    "capture_gt002": bytes.fromhex(
        "0B0012010F0B000B010BFF32000000000000000026FFFFFFFF0B190B000B0005"
        "0132000000000000000026010000000B0C0B0C0B0C0B0308012A8B35403F2A33"
        "33733F0B020B040B00326F000000000000000B040B01326E0000000000000008"
        "022A8B35403F2A1B246C3F0B0008032A8B35403F2ADDF95C3F0B00"
        "0B0012010F0B000B010BFF32000000000000000026FFFFFFFF0B190B000B0005"
        "0132000000000000000026010000000B0C0B0C0B0C0B0308012A8B35403F2A33"
        "33733F0B020B040B00326F000000000000000B040B01326E0000000000000008"
        "022A8B35403F2A1B246C3F0B0008032A8B35403F2ADDF95C3F0B00"
        "0B00"
    ),
    "capture_item_move_hyp001": bytes.fromhex(
        "0B0012010F0B000B010BFF32000000000000000026FFFFFFFF0B190B000B0005"
        "0132000000000000000026010000000B0C0B0C0B0C0B0308012ABD9D313F2AAA"
        "89653F0B020B040B00326F000000000000000B040B01326E0000000000000008"
        "022ABD9D313F2AC90C593F0B0008032ABD9D313F2AE88F4C3F0B00"
        "0B0012010F0B000B010BFF32000000000000000026FFFFFFFF0B190B000B0005"
        "0132000000000000000026010000000B0C0B0C0B0C0B0308012ABD9D313F2AAA"
        "89653F0B020B040B00326F000000000000000B040B01326E0000000000000008"
        "022ABD9D313F2AC90C593F0B0008032ABD9D313F2AE88F4C3F0B00"
        "0B00"
    ),
}
WORLDINFO_PROBE_PAYLOAD_SHA256 = {
    "capture_gt002": (
        "5959EC6BF3F9C9AD34E5CFB8D444C8664659087065425C15CF1D876F95FAF324"
    ),
    "capture_item_move_hyp001": (
        "9D4D11E13ADF4ADE1AF639C9BDB925FD9395404BEDC4E683DF43127E1CD0BCF1"
    ),
}
WORLDINFO_PROBE_REQUEST_PC_SHA256 = {
    "capture_gt002": (
        "F185DE9AAD4563940978C2467D2CEA5092270914AA16954A6547A8F842F6DF99"
    ),
    "capture_item_move_hyp001": (
        "D33E068BDEC59A3C16D29DB640B1A3B8625E36795477CAB31282C6B30FBAA559"
    ),
}
WORLDINFO_PROBE_RESPONSE_PC_SHA256 = {
    "capture_gt002": (
        "7879485AB11BB6F1F1123EC33FA0468ECA00AD62DC5E29619F1DB61394143EFF"
    ),
    "capture_item_move_hyp001": (
        "3E7C2A20738DCEC2BC03C8DB6B00590082187B78E62980499B9C17CCF61F98C9"
    ),
}
WORLDINFO_PROBE_RESPONSE_FRAME_SHA256 = {
    "capture_gt002": (
        "21D7971DAFEC09404844447C80A0F25E1E24F7ED44E6B86A45E462FBBE2298A8"
    ),
    "capture_item_move_hyp001": (
        "8AEB397340082F85BC6EF2C52A0E3852CBB2DD75985507A9EE951F730B33114C"
    ),
}


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
    response_policy: str


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
    LOGOUT_RESPONSE_POLICY_ACK_ONLY,
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
    LOGOUT_RESPONSE_POLICY_ACK_ONLY,
)

# PF-HYPOTHESIS-LEDGER: HYP-PF-016 active
_PROFILE_WORLDINFO_FIRST = LogoutHypothesisScenario(
    "logout_hypothesis_worldinfo_first_subcode01_03",
    "HYP-PF-016",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST,
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

# HYP-PF-016 exact allowlist: the unchanged PF-012 request/ack pins and the
# unchanged PF-013 close lever, plus the single new pre-ack action -- echo the
# stored client-sent GetWorldInfoVital payload first.  No response byte is
# invented under this scenario either; a session that never produced a full
# 0x3D4B payload gets silence (no reply, no write).
_EXPECTED_WORLDINFO_FIRST = {
    "schema": 1,
    "id": _PROFILE_WORLDINFO_FIRST.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_WORLDINFO_FIRST.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST,
        "worldinfo_source": (
            "echo_last_full_248b_getworldinfo_payload_stored_in_memory_"
            "from_this_connection"
        ),
        "worldinfo_missing_policy": "fail_closed_silent_no_reply_no_write",
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
        "worldinfo_full": {
            "pc_size": 268,
            "payload_size": WORLDINFO_FULL_PAYLOAD_SIZE,
            "vital_count": WORLDINFO_FULL_VITAL_COUNT,
            "probe_payload_sha256": {
                "capture_gt002": WORLDINFO_PROBE_PAYLOAD_SHA256[
                    "capture_gt002"
                ],
                "capture_item_move_hyp001": WORLDINFO_PROBE_PAYLOAD_SHA256[
                    "capture_item_move_hyp001"
                ],
            },
            "probe_pc_sha256": {
                "capture_gt002": WORLDINFO_PROBE_REQUEST_PC_SHA256[
                    "capture_gt002"
                ],
                "capture_item_move_hyp001": WORLDINFO_PROBE_REQUEST_PC_SHA256[
                    "capture_item_move_hyp001"
                ],
            },
        },
    },
    "composed_responses": {
        "worldinfo_first": {
            "pc_size": WORLDINFO_RESPONSE_PC_SIZE,
            "frame_size": WORLDINFO_RESPONSE_FRAME_SIZE,
            "probe_pc_sha256": {
                "capture_gt002": WORLDINFO_PROBE_RESPONSE_PC_SHA256[
                    "capture_gt002"
                ],
                "capture_item_move_hyp001": (
                    WORLDINFO_PROBE_RESPONSE_PC_SHA256[
                        "capture_item_move_hyp001"
                    ]
                ),
            },
            "probe_frame_sha256": {
                "capture_gt002": WORLDINFO_PROBE_RESPONSE_FRAME_SHA256[
                    "capture_gt002"
                ],
                "capture_item_move_hyp001": (
                    WORLDINFO_PROBE_RESPONSE_FRAME_SHA256[
                        "capture_item_move_hyp001"
                    ]
                ),
            },
        },
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
        "sessions_closed_at": (
            "written_before_worldinfo_response_bytes_are_queued"
        ),
        "position_rewrite": "none",
        "worldinfo_storage": "connection_memory_only_no_table_no_write_path",
    },
    "capabilities": [
        "store_last_full_getworldinfo_payload_per_connection_in_memory",
        "echo_stored_getworldinfo_payload_before_the_pinned_logout_ack",
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "silence_connection_after_acknowledged_logout",
        "server_initiated_clean_socket_close_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "getworldinfo_float_and_constant_semantics",
        "client_observable_exit_or_character_select_return",
        "logout_outside_runtime_ready_sequence",
        "subcodes_other_than_01_and_03",
        "production_baseline_behavior",
    ],
}

_EXPECTED_BY_ID = {
    _PROFILE_ECHO.scenario_id: (_EXPECTED_ECHO, _PROFILE_ECHO),
    _PROFILE_ACK_CLOSE.scenario_id: (_EXPECTED_ACK_CLOSE, _PROFILE_ACK_CLOSE),
    _PROFILE_WORLDINFO_FIRST.scenario_id: (
        _EXPECTED_WORLDINFO_FIRST, _PROFILE_WORLDINFO_FIRST,
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
        _PROFILE_ECHO, _PROFILE_ACK_CLOSE, _PROFILE_WORLDINFO_FIRST,
    ):
        raise ValueError("logout hypothesis scenario object exceeds the allowlist")
    for subcode in LOGOUT_SUBCODES:
        digest = hashlib.sha256(LOGOUT_REQUEST_PCS[subcode]).hexdigest().upper()
        if digest != LOGOUT_REQUEST_PC_SHA256[subcode]:
            raise RuntimeError("logout hypothesis request fixture drift")
    for probe, payload in WORLDINFO_PROBE_PAYLOADS.items():
        digest = hashlib.sha256(payload).hexdigest().upper()
        if (
            digest != WORLDINFO_PROBE_PAYLOAD_SHA256[probe]
            or not is_full_worldinfo_payload(payload)
        ):
            raise RuntimeError("logout hypothesis worldinfo fixture drift")
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


def is_full_worldinfo_payload(payload: Any) -> bool:
    """Accept exactly the R40 full 248-byte GetWorldInfoVital form.

    Two byte-identical 123-byte records followed by the empty record
    ``0B 00``; outside the six float32 value slots every record byte must
    equal the pinned cross-session skeleton.  Everything else -- the empty
    2-byte form, truncated or extended payloads, diverging duplicate
    records, and skeleton drift -- is rejected so it is never stored and
    never echoed.
    """
    if type(payload) is not bytes or len(payload) != WORLDINFO_FULL_PAYLOAD_SIZE:
        return False
    first = payload[:WORLDINFO_RECORD_SIZE]
    second = payload[WORLDINFO_RECORD_SIZE:2 * WORLDINFO_RECORD_SIZE]
    if first != second:
        return False
    if payload[2 * WORLDINFO_RECORD_SIZE:] != WORLDINFO_EMPTY_RECORD:
        return False
    masked = bytearray(first)
    for start, stop in WORLDINFO_RECORD_FLOAT_SLICES:
        masked[start:stop] = b"\x00" * (stop - start)
    return bytes(masked) == WORLDINFO_RECORD_SKELETON


def classify_worldinfo_frame(legacy: Any, parsed: Any) -> str:
    """Classify one 0x3D4B-bearing parse against the R40 captured forms."""
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.nested_id == WORLDINFO_VITAL_ID
        and parsed.nested_version == 0
    ):
        return "wrong_envelope"
    if (
        parsed.vital_count == 1
        and parsed.nested_payload == WORLDINFO_EMPTY_RECORD
    ):
        # R40: the 2-byte empty form fires mid-gameplay without any logout
        # correlation; it is acknowledged as known but never stored.
        return "empty_form"
    if parsed.vital_count != WORLDINFO_FULL_VITAL_COUNT:
        return "wrong_envelope"
    if not is_full_worldinfo_payload(parsed.nested_payload):
        return "wrong_payload"
    return "full_form"


def make_worldinfo_first_response(
    legacy: Any, payload: bytes,
) -> tuple[bytes, bytes]:
    """Echo one stored full GetWorldInfoVital payload in the Res envelope.

    The composition mirrors the client's own request container -- collection
    count 3, nested id 0x3D4B version 0, then the stored 248 payload bytes
    verbatim -- inside the accepted GSCN_RunTimeProtocolRes v4 envelope with
    the proven trailing derived-class change mask ``0B 00``.  Relative to
    the client's request the only bytes that differ are the three envelope
    constants every live-accepted RuntimeRes carries (outer id 0x6E9D,
    protocol version 4, trailing mask); zero content bytes are invented.
    ``make_runtime_vitals`` is deliberately not used here: it would rewrite
    the collection count to 1 and detach it from the client's own count/
    record correspondence, which DELETE-SOFT-002 proved the client stream-
    reader rejects on any misalignment (ErrorData=28317).
    """
    if not is_full_worldinfo_payload(payload):
        raise ValueError("worldinfo response payload exceeds the R40 full form")
    pc = bytes(
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 4)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, WORLDINFO_FULL_VITAL_COUNT)
        + legacy.u16tag(0x12, WORLDINFO_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + payload
        + legacy.u8tag(0x0B, 0)
    )
    frame = legacy.frame_pc(pc)
    if (
        len(pc) != WORLDINFO_RESPONSE_PC_SIZE
        or pc[20:20 + WORLDINFO_FULL_PAYLOAD_SIZE] != payload
        or pc[-2:] != WORLDINFO_EMPTY_RECORD
    ):
        raise RuntimeError("HYP-PF-016 response PC drift")
    if len(frame) != WORLDINFO_RESPONSE_FRAME_SIZE:
        raise RuntimeError("HYP-PF-016 response frame drift")
    for probe, probe_payload in WORLDINFO_PROBE_PAYLOADS.items():
        if payload != probe_payload:
            continue
        if (
            hashlib.sha256(pc).hexdigest().upper()
            != WORLDINFO_PROBE_RESPONSE_PC_SHA256[probe]
        ):
            raise RuntimeError("HYP-PF-016 response PC drift")
        if (
            hashlib.sha256(frame).hexdigest().upper()
            != WORLDINFO_PROBE_RESPONSE_FRAME_SHA256[probe]
        ):
            raise RuntimeError("HYP-PF-016 response frame drift")
    return pc, frame
