"""Strict test-only profile for proactive Second Password success.

The response bytes are the already accepted V110 result=OK packet.  Sending
that packet after runtime readiness, before a client request, is deliberately
tracked as HYP-PF-009 and is never enabled by the normal server baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


SECOND_PASSWORD_OK_PC_SHA256 = (
    "5C29ED7BCBA475B8B3E71570622E6E0BAD98C7790153BBDA2560289505C99B36"
)
SECOND_PASSWORD_OK_FRAME_SHA256 = (
    "7AEE68CCB80484793EB45471EE13ED197D352AFF6ED3AF03CC9C7A2CB8ACEE05"
)


@dataclass(frozen=True)
class SecondPasswordBypassScenario:
    scenario_id: str
    response_pc_sha256: str
    response_frame_sha256: str


_PROFILE = SecondPasswordBypassScenario(
    "second_password_bypass_v110_after_runtime_ready",
    SECOND_PASSWORD_OK_PC_SHA256,
    SECOND_PASSWORD_OK_FRAME_SHA256,
)

_EXPECTED = {
    "schema": 1,
    "id": "second_password_bypass_v110_after_runtime_ready",
    "hypothesis_id": "HYP-PF-009",
    "test_only": True,
    "production_allowed": False,
    "requires": "item_move_capture_v111_merged_id1_slot0_to_free_slot2",
    "trigger": "first_runtime_ready_after_selected_start_game",
    "response": {
        "vital": "CheckSecondPwdVital",
        "nested_id": 0x4B98,
        "nested_version": 0,
        "result": 1,
        "u32": 0,
        "ansi": "",
        "pc_size": 34,
        "pc_sha256": SECOND_PASSWORD_OK_PC_SHA256,
        "frame_size": 44,
        "frame_sha256": SECOND_PASSWORD_OK_FRAME_SHA256,
    },
    "capabilities": ["proactive_second_password_ok_once"],
    "nonclaims": [
        "original_server_timing",
        "credential_validation",
        "production_authentication_policy",
        "general_authentication_bypass",
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


def load_second_password_bypass_scenario(
    path: str | Path,
) -> SecondPasswordBypassScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid second-password bypass scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _EXPECTED):
        raise ValueError("second-password bypass scenario exceeds the exact allowlist")
    response = data["response"]
    return require_second_password_bypass_scenario(SecondPasswordBypassScenario(
        data["id"], response["pc_sha256"], response["frame_sha256"],
    ))


def require_second_password_bypass_scenario(
    value: Any,
) -> SecondPasswordBypassScenario:
    if type(value) is not SecondPasswordBypassScenario or value != _PROFILE:
        raise ValueError("second-password bypass scenario object exceeds the exact allowlist")
    return value


def make_proactive_second_password_ok(
    legacy: Any, scenario: SecondPasswordBypassScenario,
) -> tuple[bytes, bytes]:
    """Build and hash-pin the accepted packet at the hypothesized timing."""
    # PF-HYPOTHESIS-LEDGER: HYP-PF-009 active
    require_second_password_bypass_scenario(scenario)
    pc, frame = legacy.make_check_second_password_success()
    if len(pc) != 34 or hashlib.sha256(pc).hexdigest().upper() != scenario.response_pc_sha256:
        raise RuntimeError("HYP-PF-009 response PC drift")
    if (
        len(frame) != 44
        or hashlib.sha256(frame).hexdigest().upper()
        != scenario.response_frame_sha256
    ):
        raise RuntimeError("HYP-PF-009 response frame drift")
    return pc, frame
