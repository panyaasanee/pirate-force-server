"""LEARN-SKILL-REQUEST-001 -- server-side strict decoder for the
CLearnSkillVital 0x36AA request body (HYP-PF-034).

Where the project stops without this module
-------------------------------------------
LEARN-SKILL-RESULT-001 (HYP-PF-033) built the outbound half of the learn-skill
lane -- the result vital 0x673C encoder -- and named the inbound direction as
its own deliberate nonclaim.  Until this module nothing in src/ could read one
byte of the request vital 0x36AA: a real client that sent one would fall
through to the frozen v141 default path, unread and unlogged, and the wire/DB
question "does the server understand the proven request shape" had nothing to
run against.  This lane builds the server-side strict decoder of exactly the
proven shape and nothing more: it decodes, counts and records; it never
replies and never writes.

What is proven, and by whom (do not re-prove)
---------------------------------------------
All facts below come from committed artifacts; no client image was read on
this round and none exists where this was written:

  * pf_bridge/external/PF_SERIALIZER_FIELDS.tsv carries four rows for this
    vital -- W and R, byte-symmetric -- against serializer span
    [0x00755AC0,0x00755B13), len 83, span SHA-256
    b99487413ffa79784deda46283aafc2f3954d98a85362d35304b745d6c062fc4:

        u32 tag 0x14  object+0x14   gate ALWAYS
        u8  tag 0x0B  object+0x18   gate ALWAYS

  * GT-050 job 1 re-verified that exact span pin against the read-only image
    and job 2 adversarially re-derived the delivery tables byte-identically
    (letter pf_bridge/notes_to_chief/20260824_0055_GT050-RESULT-CLEARNRESULT-
    CLOSED-TRIGGER-DIRECTION-UNRESOLVED.md, 2026-08-24 00:46 +07:00).

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * The NATURAL DIRECTION of 0x36AA is NOT proven.  The client image carries
    both a WRITE and a READ codec for it; no capture and no static census has
    shown a client actually sending one.  This decoder rests on "the client
    CAN write this shape", never on "the client does".  The direction proof
    is bridge work, queued, not run.
  * The SEMANTICS of the two request fields are NOT known.  They are decoded
    as opaque values named by object offset only (request_u32_0x14 /
    request_u8_0x18).  Nothing here calls either of them a skill id, a level,
    a slot or anything else, and nothing may.
  * The request ENVELOPE for 0x36AA has never been captured.  The accepted
    envelope here is the one-vital GSCN_RunTimeProtocolReq shape that every
    captured client request of other vitals uses -- OUR acceptance design,
    fail closed, not a claim about what a real client would wrap 0x36AA in.
  * No learn rule exists and none is invented: an accepted request changes no
    skill, answers nothing (not even the 0x673C result vital the sibling
    lane can compose) and writes no row.
  * Nothing is claimed about the ORIGINAL server, which is gone forever: the
    acceptance gates and the decode-only policy are this project's design.

Fail-closed contract
--------------------
The decoder refuses, by named reason and with no partial result: a payload
that is not bytes, any truncation, a wrong tag at either position, and any
byte left over after the trailing u8.  The encoder (test-side, used to build
probe frames) refuses non-int members and members outside their wire width,
and every composed payload is re-decoded and compared with the request before
the bytes are returned.  In dispatch every refusal is a named no-reply event;
no path in this file or its dispatch branch touches the database.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in the
dispatch branch does not exist: in default mode a 0x36AA frame falls through
to the frozen v141 path exactly as before this module existed.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


LEARN_SKILL_REQUEST_CHECKPOINT = "LEARN-SKILL-REQUEST-001"
LEARN_SKILL_REQUEST_HYPOTHESIS_ID = "HYP-PF-034"
production_allowed = False

# ---------------------------------------------------------------- static pins
# Committed-artifact provenance (PF_SERIALIZER_FIELDS.tsv rows re-verified by
# GT-050 jobs 1-2); carried as documentation-grade constants and never
# dereferenced.
LEARN_SKILL_REQUEST_VITAL_ID = 0x36AA
LEARN_SKILL_REQUEST_SERIALIZER_VA = 0x755AC0
LEARN_SKILL_REQUEST_SERIALIZER_LEN = 83
LEARN_SKILL_REQUEST_SERIALIZER_SHA256 = (
    "b99487413ffa79784deda46283aafc2f3954d98a85362d35304b745d6c062fc4"
)

# The per-vital u8 version byte accepted in the request envelope.  OUR
# DESIGN, not a pin: every captured client request of other vitals carries 0
# and no capture exists for 0x36AA.  Stated in the module docstring nonclaims.
LEARN_SKILL_REQUEST_VITAL_VERSION = 0

# The proven body geometry, exactly as the symmetric W/R rows state it.
LEARN_SKILL_REQUEST_U32_TAG = 0x14           # u32 at object+0x14
LEARN_SKILL_REQUEST_U8_TAG = 0x0B            # u8 at object+0x18
LEARN_SKILL_REQUEST_U32_OBJECT_OFFSET = 0x14
LEARN_SKILL_REQUEST_U8_OBJECT_OFFSET = 0x18
# On the wire: tag+4 then tag+1 = 7 bytes, always (both gates are ALWAYS).
LEARN_SKILL_REQUEST_PAYLOAD_SIZE = 7

# Rejection reasons; every one of them means "no fields, no reply, no write".
# The first two are ENCODER-side only (test/probe composition refusing bad
# declared values) and can never be raised by decode/classify/dispatch, so
# their dispatch event names can never occur; the last four are the wire
# families a real frame can trip.
LEARN_SKILL_REQUEST_REJECTIONS = (
    "request_value_type_not_integer",
    "request_value_outside_field_width",
    "truncated_payload",
    "wrong_u32_tag",
    "wrong_u8_tag",
    "trailing_bytes_after_object",
)


@dataclass(frozen=True)
class LearnSkillRequestFields:
    """The two opaque decoded values, named by object offset ONLY.

    The member names encode nothing but the proven object offset and width;
    the meanings are unknown and deliberately unnamed (see the module
    docstring nonclaims).
    """

    request_u32_0x14: int
    request_u8_0x18: int


@dataclass(frozen=True)
class LearnSkillRequestHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    response_policy: str


# ------------------------------------------------------------ the probe plan
LEARN_SKILL_REQUEST_SCENARIO_ID = "learn_skill_request_hypothesis_decode_probe"
LEARN_SKILL_REQUEST_RESPONSE_POLICY = (
    "decode_count_and_record_no_reply_no_write"
)

# The probe field pairs the tests drive through the real dispatcher.  The
# VALUES are OUR DESIGN and are chosen only to be tellable-apart and to
# exercise the proven wire widths: an all-zero pair, the width maxima, and a
# mid-range pair with two distinct member values.  None of them is claimed to
# be a skill id, a level, or anything else.
LEARN_SKILL_REQUEST_PROBE_ORDER = ("ZERO", "MID", "MAX")
LEARN_SKILL_REQUEST_PROBE_FIELDS = {
    "ZERO": LearnSkillRequestFields(0, 0),
    "MID": LearnSkillRequestFields(1000001, 11),
    "MAX": LearnSkillRequestFields(0xFFFFFFFF, 0xFF),
}

# ----------------------------------------------------------------- the pins
# Computed by running THIS encoder deterministically (the probe plan takes no
# per-session input, so the pins are absolute); every value below is a sha256
# of bytes this module composed, never a value copied in.
LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SHA256 = {
    "ZERO": (
        "7FC03DE103971ADD441303C4EDAEF1EDF2D379D5070A53B6A8481AF159F4C84B"
    ),
    "MID": (
        "B182A5CB1F0153B43B780F644D4AEC5D99142912185B760EBEC31C00D9B6EFDF"
    ),
    "MAX": (
        "0E79D47C2600DB964304F37F5F260F9A3B84DD7582A61F42F8049379C9385265"
    ),
}
LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SHA256 = {
    "ZERO": (
        "007EC69962A76EFAD7636442B392F904291BC2037B9CEACC3DED33929EAE9563"
    ),
    "MID": (
        "88EFC1A85A625FFF9ABDC7E2886051D34C24E1116165B7433D6D0B5FDC93E6F5"
    ),
    "MAX": (
        "1CFD9DAA3C1E59EE8009017E1F32A13BBCF20F8BD5108CE0287889F4805E8CAA"
    ),
}
LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SIZE = {
    "ZERO": 7, "MID": 7, "MAX": 7,
}
LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SIZE = {
    "ZERO": 27, "MID": 27, "MAX": 27,
}


# ---------------------------------------------------------------- self-guards
def _require_probe_plan() -> None:
    """The pinned plan must keep asking the questions it was built to ask."""
    if len(set(LEARN_SKILL_REQUEST_PROBE_ORDER)) != len(
        LEARN_SKILL_REQUEST_PROBE_ORDER
    ):
        raise RuntimeError("HYP-PF-034 duplicate probe label")
    if set(LEARN_SKILL_REQUEST_PROBE_FIELDS) != set(
        LEARN_SKILL_REQUEST_PROBE_ORDER
    ):
        raise RuntimeError("HYP-PF-034 probe plan label drift")
    fields = LEARN_SKILL_REQUEST_PROBE_FIELDS
    if fields["ZERO"] != LearnSkillRequestFields(0, 0):
        raise RuntimeError(
            "HYP-PF-034 the probe plan must keep the all-zero pair"
        )
    if fields["MAX"] != LearnSkillRequestFields(0xFFFFFFFF, 0xFF):
        raise RuntimeError(
            "HYP-PF-034 the probe plan must keep the width maxima"
        )
    for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
        if type(fields[label]) is not LearnSkillRequestFields:
            raise RuntimeError("HYP-PF-034 probe plan field type drift")


def _require_int(value: Any, width_bits: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise ValueError(
            "learn skill request rejected: request_value_type_not_integer"
        )
    if value < 0 or value >= (1 << width_bits):
        raise ValueError(
            "learn skill request rejected: request_value_outside_field_width"
        )
    return value


# ---------------------------------------------------------------- encoder
# PF-HYPOTHESIS-LEDGER: HYP-PF-034 active
def encode_learn_skill_request_payload(
    legacy: Any,
    fields: LearnSkillRequestFields,
) -> bytes:
    """Compose one 0x36AA body from the opaque declared pair.

    Test-side and probe-side only: the server never emits this vital.  The
    wire order is the delivery-table one and nothing else: u32 tag 0x14 at
    object+0x14, then u8 tag 0x0B at object+0x18.  The member semantics are
    unknown and unnamed; the values pass through as declared or the
    composition refuses with a named reason and no bytes.  The composed
    payload is re-decoded before it is returned, so the encoder can never
    emit something its own decoder would refuse.
    """
    if type(fields) is not LearnSkillRequestFields:
        raise ValueError(
            "learn skill request rejected: request_value_type_not_integer"
        )
    payload = bytearray()
    payload += legacy.u32tag(
        LEARN_SKILL_REQUEST_U32_TAG,
        _require_int(fields.request_u32_0x14, 32),
    )
    payload += legacy.u8tag(
        LEARN_SKILL_REQUEST_U8_TAG,
        _require_int(fields.request_u8_0x18, 8),
    )
    payload = bytes(payload)
    if len(payload) != LEARN_SKILL_REQUEST_PAYLOAD_SIZE:
        raise RuntimeError("HYP-PF-034 composed payload size drift")
    if decode_learn_skill_request_payload(payload) != fields:
        raise RuntimeError("HYP-PF-034 encoder is not decoder-inverse")
    return payload


# ---------------------------------------------------------------- decoder
def decode_learn_skill_request_payload(
    payload: Any,
) -> LearnSkillRequestFields:
    """Read one 0x36AA body into the opaque declared pair.

    Written strictly from the symmetric delivery-table wire order: every tag
    byte is verified at its position, every truncation refuses, and a byte
    left over after the trailing u8 refuses.  No partial result is ever
    returned.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise ValueError("learn skill request rejected: truncated_payload")
    payload = bytes(payload)
    if len(payload) < 5:
        raise ValueError("learn skill request rejected: truncated_payload")
    if payload[0] != LEARN_SKILL_REQUEST_U32_TAG:
        raise ValueError("learn skill request rejected: wrong_u32_tag")
    first = int.from_bytes(payload[1:5], "little")
    cursor = 5
    if len(payload) - cursor < 2:
        raise ValueError("learn skill request rejected: truncated_payload")
    if payload[cursor] != LEARN_SKILL_REQUEST_U8_TAG:
        raise ValueError("learn skill request rejected: wrong_u8_tag")
    second = payload[cursor + 1]
    cursor += 2
    if cursor != len(payload):
        raise ValueError(
            "learn skill request rejected: trailing_bytes_after_object"
        )
    return LearnSkillRequestFields(first, second)


# ---------------------------------------------------------------- classifier
def classify_learn_skill_request_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one 0x36AA-bearing parse against the acceptance design.

    The accepted envelope is the same one-vital client request envelope the
    chat and logout lanes accept from real captures: GSCN_RunTimeProtocolReq,
    outer version 0, outer mask 0x02, vital_count 1, nested version 0.  For
    0x36AA itself that envelope is OUR acceptance design (never captured --
    see the module docstring nonclaims).  Everything else fails closed.
    """
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_id == LEARN_SKILL_REQUEST_VITAL_ID
        and parsed.nested_version == LEARN_SKILL_REQUEST_VITAL_VERSION
    ):
        return "wrong_envelope"
    try:
        decode_learn_skill_request_payload(parsed.nested_payload)
    except ValueError as exc:
        reason = str(exc).rsplit(": ", 1)[-1]
        if reason not in LEARN_SKILL_REQUEST_REJECTIONS:
            raise RuntimeError(
                "HYP-PF-034 decoder raised an unregistered reason"
            ) from exc
        return reason
    return "exact_request"


# ---------------------------------------------------------------- probe frames
def compose_learn_skill_request_probe_pc(
    legacy: Any, fields: LearnSkillRequestFields,
) -> bytes:
    """Build one full client-request PC carrying the 0x36AA body.

    Test-side and probe-side only.  The 20-byte envelope is the one-vital
    GSCN_RunTimeProtocolReq header every captured client request of other
    vitals uses (the same bytes the chat-lane probe PCs pin); wrapping 0x36AA
    in it is OUR DESIGN, stated in the module docstring nonclaims.
    """
    payload = encode_learn_skill_request_payload(legacy, fields)
    return bytes(
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, LEARN_SKILL_REQUEST_VITAL_ID)
        + legacy.u8tag(0x0B, LEARN_SKILL_REQUEST_VITAL_VERSION)
        + payload
    )


# ---------------------------------------------------------------- scenario gate
_PROFILE_DECODE_PROBE = LearnSkillRequestHypothesisScenario(
    LEARN_SKILL_REQUEST_SCENARIO_ID,
    LEARN_SKILL_REQUEST_HYPOTHESIS_ID,
    LEARN_SKILL_REQUEST_RESPONSE_POLICY,
)


def _fields_schema(fields: LearnSkillRequestFields) -> dict[str, int]:
    return {
        "request_u32_0x14": fields.request_u32_0x14,
        "request_u8_0x18": fields.request_u8_0x18,
    }


def _expected_probe() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": LEARN_SKILL_REQUEST_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": LEARN_SKILL_REQUEST_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": LEARN_SKILL_REQUEST_RESPONSE_POLICY,
        },
        "dispatch": {
            "trigger": "inbound_one_vital_0x36AA_request_frame",
            "trigger_classifier": "classify_learn_skill_request_attempt",
            "frames_emitted_per_accepted_request": 0,
            "accepted_event": "learn_skill_request_hypothesis_decoded_no_reply",
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": LEARN_SKILL_REQUEST_VITAL_ID,
            "vital_version": LEARN_SKILL_REQUEST_VITAL_VERSION,
            "vital_version_provenance": (
                "our_design_no_capture_or_static_pin_fixes_it"
            ),
            "envelope": (
                "gscn_runtime_protocol_req_one_vital_client_request_"
                "our_acceptance_design_for_this_vital"
            ),
            "body_order": [
                "u32_tag_0x14_at_object_0x14",
                "u8_tag_0x0B_at_object_0x18",
            ],
            "payload_wire_size": LEARN_SKILL_REQUEST_PAYLOAD_SIZE,
            "provenance": {
                "ticket": "GT-050",
                "letter": (
                    "pf_bridge/notes_to_chief/20260824_0055_GT050-RESULT-"
                    "CLEARNRESULT-CLOSED-TRIGGER-DIRECTION-UNRESOLVED.md"
                ),
                "delivery_table": (
                    "pf_bridge/external/PF_SERIALIZER_FIELDS.tsv"
                ),
                "delivery_rows": "W_and_R_byte_symmetric_gate_ALWAYS",
                "serializer_va": "0x00755AC0",
                "serializer_len": LEARN_SKILL_REQUEST_SERIALIZER_LEN,
                "serializer_sha256": LEARN_SKILL_REQUEST_SERIALIZER_SHA256,
            },
        },
        "probe": {
            "per_probe": {
                label: {
                    "fields": _fields_schema(
                        LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
                    ),
                    "payload_size": (
                        LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SIZE[label]
                    ),
                    "payload_sha256": (
                        LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SHA256[label]
                    ),
                    "request_pc_size": (
                        LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SIZE[label]
                    ),
                    "request_pc_sha256": (
                        LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SHA256[label]
                    ),
                }
                for label in LEARN_SKILL_REQUEST_PROBE_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "decode_the_delivery_table_0x36AA_body_shape",
            "refuse_malformed_bodies_by_named_reason",
            "count_and_record_accepted_requests_per_session",
            "repeatable_per_session_no_reply_no_persisted_state_change",
        ],
        "nonclaims": [
            "the_natural_direction_of_0x36AA_which_static_did_not_prove",
            "any_meaning_for_the_two_request_fields",
            "any_learn_rule_or_any_result_response",
            "the_request_envelope_for_0x36AA_which_was_never_captured",
            "the_vital_version_byte_which_is_our_design",
            "client_send_behavior_pending_the_bridge_direction_proof",
            "any_wire_observation_of_0x36AA_in_either_direction",
            "original_server_learn_skill_behavior",
            "skill_persistence_or_database_write",
            "production_dispatch_wiring",
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


def load_learn_skill_request_hypothesis_scenario(
    path: str | Path,
) -> LearnSkillRequestHypothesisScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the acceptance
    gates and probe plan live in the module's own frozen constants.  A file
    that differs from the allowlisted body anywhere -- one extra key, one
    missing key, one int where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "invalid learn skill request hypothesis scenario"
        ) from exc
    if type(data) is not dict or data.get("id") != (
        LEARN_SKILL_REQUEST_SCENARIO_ID
    ):
        raise ValueError(
            "learn skill request hypothesis scenario exceeds the exact "
            "allowlist"
        )
    if not _exact_equal(data, _expected_probe()):
        raise ValueError(
            "learn skill request hypothesis scenario exceeds the exact "
            "allowlist"
        )
    return require_learn_skill_request_hypothesis_scenario(
        _PROFILE_DECODE_PROBE
    )


def require_learn_skill_request_hypothesis_scenario(
    value: Any,
) -> LearnSkillRequestHypothesisScenario:
    if (
        type(value) is not LearnSkillRequestHypothesisScenario
        or value != _PROFILE_DECODE_PROBE
    ):
        raise ValueError(
            "learn skill request hypothesis scenario object exceeds the "
            "allowlist"
        )
    _require_probe_plan()
    return value
