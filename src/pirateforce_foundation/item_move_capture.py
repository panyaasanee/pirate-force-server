"""Strict opt-in capture boundary for one exact ItemOperate move request.

This capability records an original-client request only.  It deliberately
contains no response builder, persistence operation, or generalized move
policy.  A future response/reconnect composition remains Grade D and requires
its own governed milestone.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


ITEM_MOVE_CAPTURE_REQUEST_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
    "ED 4B 0B 00 0B 04 14 02 00 00 00 32 01 00 00 00 "
    "00 00 00 00"
)
ITEM_MOVE_CAPTURE_REQUEST_SHA256 = (
    "7A59F83060CFEC50D087BF991695852BA27C00B27B7B46B3D72F3340830436EE"
)
ITEM_MOVE_CAPTURE_FIELDS = (4, 2, 1)


@dataclass(frozen=True)
class ItemMoveCaptureScenario:
    scenario_id: str
    operation: int
    value32: int
    item_identity: int
    request_sha256: str


_PROFILE = ItemMoveCaptureScenario(
    "item_move_capture_v111_merged_id1_slot0_to_free_slot2",
    *ITEM_MOVE_CAPTURE_FIELDS,
    ITEM_MOVE_CAPTURE_REQUEST_SHA256,
)

_EXPECTED = {
    "schema": 1,
    "id": "item_move_capture_v111_merged_id1_slot0_to_free_slot2",
    "test_only": True,
    "entry": {
        "flow": "full_writable_character",
        "required_backpack": "merged_v111_exact",
        "required_sequence": "selected_and_runtime_ready",
    },
    "candidate": {
        "outer_id": 0x6E6F,
        "outer_version": 0,
        "outer_mask": 2,
        "vital_count": 1,
        "nested_id": 0x4BED,
        "nested_version": 0,
        "operation": 4,
        "value32": 2,
        "item_identity": 1,
        "pc_size": 36,
        "pc_sha256": ITEM_MOVE_CAPTURE_REQUEST_SHA256,
    },
    "capabilities": ["capture_exact_item_move_request_no_reply"],
    "nonclaims": [
        "item_move_response",
        "item_move_persistence",
        "reconnect_collection_order",
        "occupied_slot_policy",
        "generalized_item_move",
    ],
}


def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return (
            set(actual) == set(expected)
            and all(_exact_equal(actual[key], value) for key, value in expected.items())
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_item_move_capture_scenario(path: str | Path) -> ItemMoveCaptureScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid item-move capture scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _EXPECTED):
        raise ValueError("item-move capture scenario exceeds the exact allowlist")
    candidate = data["candidate"]
    return require_item_move_capture_scenario(ItemMoveCaptureScenario(
        data["id"], candidate["operation"], candidate["value32"],
        candidate["item_identity"], candidate["pc_sha256"],
    ))


def require_item_move_capture_scenario(value: Any) -> ItemMoveCaptureScenario:
    if (
        type(value) is not ItemMoveCaptureScenario
        or type(value.scenario_id) is not str
        or type(value.operation) is not int
        or type(value.value32) is not int
        or type(value.item_identity) is not int
        or type(value.request_sha256) is not str
        or value != _PROFILE
    ):
        raise ValueError("item-move capture scenario object exceeds the exact allowlist")
    if len(ITEM_MOVE_CAPTURE_REQUEST_PC) != 36:
        raise RuntimeError("item-move request fixture size drift")
    actual_hash = hashlib.sha256(ITEM_MOVE_CAPTURE_REQUEST_PC).hexdigest().upper()
    if actual_hash != value.request_sha256:
        raise RuntimeError("item-move request fixture hash drift")
    return value


def classify_item_move_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one already-identified ItemOperateReq without authorizing it."""
    try:
        fields = legacy.parse_item_operate_req(parsed)
    except (ValueError, TypeError, AttributeError):
        return "malformed_or_trailing"
    if fields != ITEM_MOVE_CAPTURE_FIELDS:
        return "wrong_tuple"
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_version == 0
        and parsed.raw_pc == ITEM_MOVE_CAPTURE_REQUEST_PC
    ):
        return "wrong_envelope"
    return "exact"
