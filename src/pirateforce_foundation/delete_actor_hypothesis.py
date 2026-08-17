"""Governed designed soft-delete lane for DeleteActorVital (0x36DB).

The nested request record, its id, version, and both producer op values are
the accepted DELETE-003 grade-A static decode
(reports/PF_DELETE003_PRODUCER_OUTER_FRAMING_NEGATIVE_20260816.md): UI path
``0x4E6190 -> 0x4B2990`` submits op 1 with the selector and an opaque
UI-derived wstring; path ``0x4B47A0`` submits op 2 with an empty wstring.
No natural 0x36DB wire was ever captured (bounded corpus negative), so both
the outer request envelope accepted here and the response composed here are
*designed hypotheses*, opened 2026-08-18 under the project owner's explicit
Lane-1 Option-B decision of 2026-08-18 00:52 (which supersedes the DELETE-003
stop rule's approval requirement while keeping its nonclaims):

- accepted request envelope: the exact one-vital ``GSCN_LoginProtocol``
  (0x453A) shape every captured character-select-stage request uses
  (login_verify, create_actor): outer version 0, mask 0x02, vital_count 1,
  nested id 0x36DB, nested version 1, nested payload parsed by the strict
  DELETE-003 parser.  Op 1 only; op 2 has no proven UI provenance and fails
  closed.
- designed response (v2, DELETE-SOFT-002): echo the exact request vital back
  inside the accepted ``GSCN_RunTimeProtocolRes`` v4 single-vital collection
  envelope **with the trailing derived-class change mask ``0B 00``**
  (``make_runtime_vitals``, the composition every live-accepted RuntimeRes
  collection response uses).  The v1 composition (``make_runtime_vital``,
  no trailing mask) was falsified live by attended GT-010 on 2026-08-18:
  the real client parsed the whole stream, over-read past the echoed record
  looking for the derived-class mask, and raised the RuntimeRes stream error
  ``GSCN_RunTimeProtocolRes ErrorData=28317`` (28317 = 0x6E9D = the protocol
  class id of GSCN_RUNTIME_PROTOCOL_RES itself) while the request-side
  envelope was confirmed byte-compatible -- the server parsed the natural
  0x36DB and committed the soft delete.  Decode + candidate ranking:
  reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md.
  DELETE-003 proved the client owns an inbound DeleteActorVital consumer
  (``0x5EFDC0 -> 0x4BAEB0``) with the same codec; whether the *fixed* echo
  now drives the UI (list refresh, freed slot) is the re-queued attended
  claim (GT-011).

The repository commit (``deleted_at`` set under the migration-004 partial
unique indexes) happens before any ack byte is queued.  Wrong envelopes,
wrong ops, unparseable records, wrong stages, and repository refusals all
fail closed with no reply and no write.  This module is opt-in, test-only
(``production_allowed`` false), and never hard-deletes: child position and
backpack rows survive as history.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from .delete_actor import (
    DELETE_ACTOR_VITAL_ID,
    DELETE_ACTOR_VITAL_VERSION,
    parse_delete_actor_vital_request,
)


# Designed probe requests (no captured 0x36DB wire exists anywhere in the
# corpus): op 1, selector 0, with the empty wstring and with the DELETE-003
# disposable character name as the opaque UI string.  Deterministic, pinned
# end to end for tests and replay tooling.
DELETE_ACTOR_PROBE_NESTED_PAYLOADS = {
    "op1_selector0_empty": bytes.fromhex(
        "0801080014000000004400000000"
    ),
    "op1_selector0_deltst01": bytes.fromhex(
        "0801080014000000004410000000"
        "440065006C0054007300740030003100"
    ),
}


def _login_protocol_request_pc(legacy: Any, nested_payload: bytes) -> bytes:
    """Compose the designed one-vital GSCN_LoginProtocol delete request."""
    return bytes(
        legacy.u16tag(0x12, legacy.GSCN_LOGIN_PROTOCOL)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, DELETE_ACTOR_VITAL_ID)
        + legacy.u8tag(0x0B, DELETE_ACTOR_VITAL_VERSION)
        + nested_payload
    )


# Deterministic designed-probe pins (34/50-byte request PCs, echo ack
# 36/52-byte PCs inside 46/62-byte frames), verified end to end by the tests.
# v2 (DELETE-SOFT-002): the ack PC/frame pins moved +2 bytes when the trailing
# derived-class change mask 0B 00 joined the composition after attended GT-010
# falsified the tail-less v1 ack live (ErrorData=28317; see the module
# docstring and reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md).
# The request pins are unchanged: the natural GT-010 capture confirmed the
# request envelope byte-compatible, so only the response side moved.
DELETE_ACTOR_PROBE_REQUEST_PC_SHA256 = {
    "op1_selector0_empty": (
        "F5DDA13FA9DEB964B70C0E2614C664C722CF2A7D411A88532E77BFE869DB6DC9"
    ),
    "op1_selector0_deltst01": (
        "7C386621653189CD6CD72B2EE170CD89C4E24ED690EBBE0A3F03391164791ABE"
    ),
}
DELETE_ACTOR_PROBE_ACK_PC_SHA256 = {
    "op1_selector0_empty": (
        "481A8939FD84D2DDC1A81645F10856A5C666D2387776704355A62E8FA36D4581"
    ),
    "op1_selector0_deltst01": (
        "D2F82525658EDB80D0232F037ADFCE8AE476F01B7BDB44C46BAAEE780E2BD7EF"
    ),
}
DELETE_ACTOR_PROBE_ACK_FRAME_SHA256 = {
    "op1_selector0_empty": (
        "055ACBB0B690891DFB3799FD6760BA102288593675454D243873AB03F0B3223E"
    ),
    "op1_selector0_deltst01": (
        "679EBAF9B3A1F202CAF0F13248C704DF9B8B993C8802FF7248B9FA9F2213FD21"
    ),
}


@dataclass(frozen=True)
class DeleteActorHypothesisScenario:
    scenario_id: str
    hypothesis_id: str


_PROFILE = DeleteActorHypothesisScenario(
    "delete_actor_hypothesis_soft_delete_op1",
    "HYP-PF-015",
)

_EXPECTED = {
    "schema": 1,
    "id": _PROFILE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE.hypothesis_id,
    "entry": {
        "flow": "character_select_stage",
        "required_sequence": "character_list_sent_and_nothing_selected",
        "request_envelope": "gscn_login_protocol_one_vital_designed",
        "response_policy": "echo_exact_request_vital_after_committed_soft_delete",
    },
    "persisted_post_state": {
        "characters_deleted_at": "written_before_ack_bytes_are_queued",
        "child_rows": "positions_and_backpack_rows_survive_as_history",
        "slot_reuse": "migration_004_partial_unique_indexes_allow_recreate",
    },
    "capabilities": [
        "soft_delete_one_owned_unselected_character_by_selector",
        "acknowledge_committed_soft_delete_with_designed_echo",
        "recreate_into_the_freed_slot_through_the_existing_create_path",
    ],
    "nonclaims": [
        "original_server_request_envelope",
        "original_server_response_policy",
        "client_observable_list_refresh_or_slot_reuse",
        "semantic_names_for_op_values_1_and_2",
        "op2_handling",
        "hard_delete_or_history_removal",
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


def load_delete_actor_hypothesis_scenario(
    path: str | Path,
) -> DeleteActorHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid delete actor hypothesis scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _EXPECTED):
        raise ValueError(
            "delete actor hypothesis scenario exceeds the exact allowlist"
        )
    return require_delete_actor_hypothesis_scenario(_PROFILE)


def require_delete_actor_hypothesis_scenario(
    value: Any,
) -> DeleteActorHypothesisScenario:
    if type(value) is not DeleteActorHypothesisScenario or value != _PROFILE:
        raise ValueError(
            "delete actor hypothesis scenario object exceeds the allowlist"
        )
    for name, payload in DELETE_ACTOR_PROBE_NESTED_PAYLOADS.items():
        record = (
            b"\x12" + struct.pack("<H", DELETE_ACTOR_VITAL_ID)
            + b"\x0b" + bytes((DELETE_ACTOR_VITAL_VERSION,))
            + payload
        )
        parsed = parse_delete_actor_vital_request(record)
        if parsed.op != 1 or parsed.selector != 0:
            raise RuntimeError("delete actor hypothesis probe fixture drift")
    return value


def classify_delete_actor_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one 0x36DB-bearing parse against the designed accepted shape."""
    if not (
        parsed.outer_id == legacy.GSCN_LOGIN_PROTOCOL
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_id == DELETE_ACTOR_VITAL_ID
        and parsed.nested_version == DELETE_ACTOR_VITAL_VERSION
    ):
        return "wrong_envelope"
    record = (
        b"\x12" + struct.pack("<H", DELETE_ACTOR_VITAL_ID)
        + b"\x0b" + bytes((DELETE_ACTOR_VITAL_VERSION,))
        + parsed.nested_payload
    )
    try:
        request = parse_delete_actor_vital_request(record)
    except (TypeError, ValueError):
        return "unparsed"
    if request.op != 1:
        return "op2_unproven"
    return "exact_op1"


def parse_accepted_delete_request(parsed: Any):
    """Re-parse an already-classified exact_op1 attempt into typed fields."""
    record = (
        b"\x12" + struct.pack("<H", DELETE_ACTOR_VITAL_ID)
        + b"\x0b" + bytes((DELETE_ACTOR_VITAL_VERSION,))
        + parsed.nested_payload
    )
    return parse_delete_actor_vital_request(record)


# PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
def make_delete_actor_ack_response(
    legacy: Any, nested_payload: bytes,
) -> tuple[bytes, bytes]:
    """Build and structurally pin the designed echo ack for one accepted request.

    v2 (DELETE-SOFT-002): the ack is the exact request vital echoed inside
    the accepted GSCN_RunTimeProtocolRes v4 single-vital *collection*
    envelope with the trailing derived-class change mask ``0B 00``
    (``make_runtime_vitals``).  Attended GT-010 falsified the v1 tail-less
    composition live: the client over-read the collection and raised
    ErrorData=28317 (the RuntimeRes class id itself), exactly the failure
    mode the ``make_runtime_vitals`` comment documents.  Every RuntimeRes
    collection response the client accepted live in the same session
    (character_list, create_success) carries this trailing mask.  The
    composition is checked structurally (envelope prefix + byte-exact
    payload + trailing mask); the deterministic probe forms are additionally
    hash-pinned by the tests.
    """
    record = (
        b"\x12" + struct.pack("<H", DELETE_ACTOR_VITAL_ID)
        + b"\x0b" + bytes((DELETE_ACTOR_VITAL_VERSION,))
        + nested_payload
    )
    request = parse_delete_actor_vital_request(record)
    if request.op != 1:
        raise ValueError("delete actor ack requires an accepted op-1 request")
    pc, frame = legacy.make_runtime_vitals(
        [(DELETE_ACTOR_VITAL_ID, DELETE_ACTOR_VITAL_VERSION, nested_payload)],
    )
    if len(pc) != 22 + len(nested_payload):
        raise RuntimeError("HYP-PF-015 response PC drift")
    if not pc.endswith(nested_payload + b"\x0b\x00"):
        raise RuntimeError("HYP-PF-015 response tail drift")
    if not frame.endswith(pc):
        raise RuntimeError("HYP-PF-015 response frame drift")
    return pc, frame
