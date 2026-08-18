"""Governed Grade-D composition for one exact free-slot Backpack move.

The client request, response structure, destination slot, and quantity have
each been accepted separately.  Their use together after the persisted V111
merge, plus the reconnect collection order, is explicitly HYP-PF-008.  This
module is opt-in, test-only, and never authorizes an occupied destination.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .item_move_capture import (
    ITEM_MOVE_CAPTURE_FIELDS,
    ITEM_MOVE_CAPTURE_REQUEST_PC,
    ITEM_MOVE_CAPTURE_REQUEST_SHA256,
    classify_item_move_attempt,
)


HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256 = (
    "DF40B49DC179DB07A006FC4989273D6F97529DAE6FF7D0DE692815435A1CD2F9"
)
HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256 = (
    "45C38CB7331EAF0EA8A06191DEFBD039733FB3EAD88E6142C08AEB1F6ACFE10E"
)
HYPOTHESIZED_SLOT2_BACKPACK_SHA256 = (
    "5B2FECF979CD5B9E65586E6AD0DE834598028C7B1A1B7502B40C94F32281ADDC"
)


@dataclass(frozen=True)
class ItemMoveHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    request_sha256: str
    response_pc_sha256: str
    response_frame_sha256: str
    backpack_sha256: str
    # The swap profile is a strict superset of the free-slot profile: the
    # HYP-PF-010 free-slot lane keeps its exact behavior, and an occupied
    # destination additionally swaps with the different occupying identity
    # instead of failing closed.  Under the default profile this field is
    # False and occupied destinations stay fail-closed exactly as pinned.
    occupied_swap: bool = False


_PROFILE = ItemMoveHypothesisScenario(
    "item_move_hypothesis_v111_merged_id1_slot0_to_free_slot2",
    "HYP-PF-008",
    ITEM_MOVE_CAPTURE_REQUEST_SHA256,
    HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256,
    HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256,
    HYPOTHESIZED_SLOT2_BACKPACK_SHA256,
)

_EXPECTED = {
    "schema": 1,
    "id": _PROFILE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_backpack": "merged_v111_exact",
        "required_sequence": "selected_and_runtime_ready",
        "destination_policy": "slot2_must_be_free",
    },
    "request": {
        "operation": ITEM_MOVE_CAPTURE_FIELDS[0],
        "value32": ITEM_MOVE_CAPTURE_FIELDS[1],
        "item_identity": ITEM_MOVE_CAPTURE_FIELDS[2],
        "pc_size": len(ITEM_MOVE_CAPTURE_REQUEST_PC),
        "pc_sha256": ITEM_MOVE_CAPTURE_REQUEST_SHA256,
    },
    "composed_response": {
        "pc_size": 71,
        "pc_sha256": HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256,
        "frame_size": 82,
        "frame_sha256": HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256,
        "quantity": 2,
        "slot": 2,
    },
    "persisted_post_state": {
        "identity_order": [1, 2, 4],
        "identity1_quantity": 2,
        "identity1_slot": 2,
        "backpack_size": 124,
        "backpack_sha256": HYPOTHESIZED_SLOT2_BACKPACK_SHA256,
    },
    "capabilities": [
        "emit_one_tracked_free_slot_move_after_commit",
        "project_tracked_post_state_only_in_same_opt_in_mode",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "occupied_slot_swap_or_displacement",
        "generalized_item_move",
        "equipment_or_item_ownership",
        "production_baseline_behavior",
    ],
}

# PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
_SWAP_PROFILE = ItemMoveHypothesisScenario(
    "item_move_hypothesis_v111_occupied_swap",
    "HYP-PF-017",
    "", "", "", "",
    True,
)

_EXPECTED_SWAP = {
    "schema": 1,
    "id": _SWAP_PROFILE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _SWAP_PROFILE.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_backpack": "governed_v111_allowlist",
        "required_sequence": "selected_and_runtime_ready",
        "destination_policy": "occupied_by_different_identity_swaps",
        "free_slot_policy": "unchanged_hyp_pf_010",
    },
    "request": {
        "operation": ITEM_MOVE_CAPTURE_FIELDS[0],
        "shape": "generic_item_operate_move_tuple",
        "pc_size": len(ITEM_MOVE_CAPTURE_REQUEST_PC),
    },
    "composed_response": {
        "shape": "item_operate_res_two_item_delta",
        "item_count": 2,
        "entry_order": ["moved_item", "displaced_item"],
    },
    "capabilities": [
        "emit_generalized_free_slot_move_after_commit_as_hyp_pf_010",
        "swap_occupied_destination_with_different_identity_after_commit",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "client_display_acceptance",
        "stack_merge_or_split_on_swap",
        "cross_container_or_equipment_movement",
        "production_baseline_behavior",
    ],
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


def load_item_move_hypothesis_scenario(
    path: str | Path,
) -> ItemMoveHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid item-move hypothesis scenario") from exc
    if type(data) is dict and _exact_equal(data, _EXPECTED):
        return require_item_move_hypothesis_scenario(ItemMoveHypothesisScenario(
            data["id"], data["hypothesis_id"], data["request"]["pc_sha256"],
            data["composed_response"]["pc_sha256"],
            data["composed_response"]["frame_sha256"],
            data["persisted_post_state"]["backpack_sha256"],
        ))
    if type(data) is dict and _exact_equal(data, _EXPECTED_SWAP):
        return require_item_move_hypothesis_scenario(ItemMoveHypothesisScenario(
            data["id"], data["hypothesis_id"], "", "", "", "", True,
        ))
    raise ValueError("item-move hypothesis scenario exceeds the exact allowlist")


def require_item_move_hypothesis_scenario(
    value: Any,
) -> ItemMoveHypothesisScenario:
    if type(value) is not ItemMoveHypothesisScenario or value not in (
        _PROFILE, _SWAP_PROFILE,
    ):
        raise ValueError("item-move hypothesis scenario object exceeds the allowlist")
    if value.request_sha256 and hashlib.sha256(
        ITEM_MOVE_CAPTURE_REQUEST_PC
    ).hexdigest().upper() != value.request_sha256:
        raise RuntimeError("item-move hypothesis request fixture drift")
    return value


def classify_item_move_hypothesis_attempt(legacy: Any, parsed: Any) -> str:
    """Own every ItemOperateReq and reuse the exact capture classification."""
    return classify_item_move_attempt(legacy, parsed)


# PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
def make_hypothesized_move_response(legacy: Any) -> tuple[bytes, bytes]:
    """Build and independently pin the tracked quantity-2/slot-2 composition."""
    pc, frame = legacy.make_item_operate_move_delta_success(2, 2)
    if len(pc) != 71 or hashlib.sha256(pc).hexdigest().upper() != HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256:
        raise RuntimeError("HYP-PF-008 response PC drift")
    if len(frame) != 82 or hashlib.sha256(frame).hexdigest().upper() != HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256:
        raise RuntimeError("HYP-PF-008 response frame drift")
    return pc, frame
