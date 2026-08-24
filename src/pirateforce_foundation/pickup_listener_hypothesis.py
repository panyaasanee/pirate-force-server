"""PICKUP-LISTENER-001 -- server-side strict decoder for the
PickupTerrainThing pickup request body, vital id DERIVED 0x4543
(HYP-PF-036).

Where the project stops without this module
-------------------------------------------
GT-046 (2026-08-23) proved the client-outbound pickup producer: a left mouse
click on an in-range ground object (WM_LBUTTONDOWN 0x201 path of the
DropThingModule_Client callback) builds a PickupTerrainThing at 0x006B0639,
copies one dword from the selected live runtime drop-object into object+0x14,
and hands the object to the outbound protocol queue at 0x006B0653.  Until
this module nothing in src/ could read one byte of that request: a real
client that clicked a ground object would have its frame fall through to the
frozen v141 default path, unread and unlogged.  This lane builds the
server-side strict decoder of exactly the proven body shape and nothing
more: it decodes, counts and records; it never replies and never writes.
The server side is listen-only -- this message is never sent by us.  The
ONLY PROVEN PRODUCER is client-outbound: GT-046 proved that a producer
exists, not that the message never travels server-to-client (the class
carries a full R codec and sits in the inbound CreateById prototype tree
per RE-056), which is one more reason this side only listens.

What is proven, and by whom (do not re-prove)
---------------------------------------------
All facts below come from committed artifacts; no client image was read on
this round and none exists where this was written:

  * pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv line 52 registers the class:
    name_va 0x00F3093C, registration site 0x00BEE5E0, serializer 0x005E5E30,
    handler 0x005EF640, vtable 0x00F3005C.
  * pf_bridge/external/PF_SERIALIZER_FIELDS.tsv rows 859-862 carry four
    byte-symmetric W/R rows (the codec is statically CLOSED) against
    serializer span [0x005E5E30,0x005E5E83), len 83, span SHA-256
    8e439d4f3ff1479e723b220d8dd78a262b41df3b74839da9d4cb728f69773066:

        u32 tag 0x14  object+0x14   gate ALWAYS
        u8  tag 0x08  object+0x18   gate ALWAYS

  * GT-046 job 5 pinned the +0x14 source: the producer reads pointer
    [esi+0x7C], then dword [pointer+0x10], and copies that dword into the
    object -- the id of a live runtime drop-object instance selected by the
    module.  (letter pf_bridge/notes_to_chief/20260823_1435_GT046-PASS-
    outbound-mouseclick-runtime-drop-object.md)

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * THE OPCODE IS DERIVED, NEVER OBSERVED ON ANY WIRE.  The runtime vital id
    lives in a .data slot (0x0108202C) that is ZERO on disk; 0x4543 (17731)
    comes from the validated project name-hash only
    (pf_bridge/FACTPACK_L2_CLASSCENSUS001_20260820.tsv row 1003).  The
    capture corpus contains ZERO PickupTerrainThing frames in either
    direction (pf_bridge/external/PF_FIELD_VALIDATION.tsv rows 102-103,
    status NOT_OBSERVED).  If the real runtime id differs, this lane simply
    never fires and the frame keeps the pre-existing unknown-opcode
    behavior recorded below -- an attended run under a WRONG derived opcode
    is still interpretable.
  * The MEANING of the u32 at object+0x14 is deliberately given the neutral
    name ``object_ref_u32``: GT-046 proves only that the client copies it
    from a selected live runtime drop-object ([ptr+0x10]).  It is NOT
    claimed to be an element_key, a template id, or any scene-table row id;
    whether that runtime object was originally instantiated from scene data
    or from a network record is unproven.
  * The MEANING of the u8 at object+0x18 is unknown; it is decoded as
    ``opaque_u8`` and nothing here or anywhere may interpret it.
  * This lane is NOT claimed to explain monster-drop pickup: the separate
    FightingDropModule_Client / FightingDropNotify family (GT-046 job 6)
    remains undecoded and may carry that behavior instead.
  * The request ENVELOPE for this vital has never been captured.  The
    accepted envelope here is the one-vital GSCN_RunTimeProtocolReq shape
    every captured client request of other vitals uses -- OUR acceptance
    design, fail closed, not a claim about what a real client would wrap
    this message in.  The per-vital version byte 0 is likewise our design.
  * No pickup rule exists and none is invented: an accepted request removes
    nothing from any scene, grants no item, answers nothing and writes no
    row.
  * Nothing is claimed about the ORIGINAL server, which is gone forever.

Pre-existing behavior for unknown opcodes (recorded, not changed)
-----------------------------------------------------------------
With no scenario handed in, and for every other opcode with or without it,
an inbound GSCN_RunTimeProtocolReq frame whose nested vital id matches no
dispatch branch falls through runtime.py to the frozen v141
``GameSessionState.dispatch`` runtime branch: the FIRST runtime request of a
session triggers the one-time empty RuntimeRes ack (plus the one-time
welcome message and music-control frames), and every later frame whose
nested id matches no per-vital handler returns an empty action list -- no
reply, no error, no per-vital event (the only recorder on that path is the
v129 post-action1 observer, active only after quest3020_accept_success_sent).
This lane hooks its DERIVED id 0x4543 exactly the way HYP-PF-034 hooked
0x36AA: a scenario-gated branch keyed on its own vital id, ahead of that
fall-through, byte-identical to the baseline when the scenario is absent.

Fail-closed contract
--------------------
The decoder refuses, by named reason and with no partial result: a payload
that is not bytes, any truncation, a wrong tag at either position, and any
byte left over after the trailing u8.  The encoder (test-side, used to build
probe frames) refuses non-int members and members outside their wire width,
and every composed payload is re-decoded and compared with the request
before the bytes are returned.  In dispatch every refusal is a named
no-reply event recorded on the session; no path in this file or its
dispatch branch touches the database.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in
the dispatch branch does not exist: in default mode a 0x4543 frame falls
through to the frozen v141 path exactly as before this module existed.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


PICKUP_LISTENER_CHECKPOINT = "PICKUP-LISTENER-001"
PICKUP_LISTENER_HYPOTHESIS_ID = "HYP-PF-036"
production_allowed = False

# ---------------------------------------------------------------- static pins
# Committed-artifact provenance (PF_PROTOCOL_REGISTRY.tsv line 52 and
# PF_SERIALIZER_FIELDS.tsv rows 859-862); carried as documentation-grade
# constants and never dereferenced.
#
# DERIVED, NEVER OBSERVED: the runtime id slot 0x0108202C is zero on disk
# and no capture holds this vital in either direction; 0x4543 is the
# validated name-hash derivation only (FACTPACK_L2_CLASSCENSUS001 row 1003).
PICKUP_LISTENER_VITAL_ID = 0x4543
PICKUP_LISTENER_VITAL_ID_PROVENANCE = (
    "derived_from_name_hash_never_observed_on_wire"
)
PICKUP_LISTENER_RUNTIME_ID_SLOT_VA = 0x0108202C     # zero on disk
PICKUP_LISTENER_NAME_VA = 0xF3093C
PICKUP_LISTENER_REGISTRATION_VA = 0xBEE5E0
PICKUP_LISTENER_HANDLER_VA = 0x5EF640
PICKUP_LISTENER_VTABLE_VA = 0xF3005C
PICKUP_LISTENER_SERIALIZER_VA = 0x5E5E30
PICKUP_LISTENER_SERIALIZER_LEN = 83
PICKUP_LISTENER_SERIALIZER_SHA256 = (
    "8e439d4f3ff1479e723b220d8dd78a262b41df3b74839da9d4cb728f69773066"
)

# The per-vital u8 version byte accepted in the request envelope.  OUR
# DESIGN, not a pin: every captured client request of other vitals carries 0
# and no capture exists for this vital.  Stated in the docstring nonclaims.
PICKUP_LISTENER_VITAL_VERSION = 0

# The statically closed body geometry, exactly as the symmetric W/R rows
# state it.  Note the u8 tag is 0x08 here, NOT the 0x0B of the HYP-PF-034
# template lane -- the delivery table says 0x08 and the delivery table wins.
PICKUP_LISTENER_OBJECT_REF_TAG = 0x14        # u32 at object+0x14
PICKUP_LISTENER_OPAQUE_U8_TAG = 0x08         # u8 at object+0x18
PICKUP_LISTENER_OBJECT_REF_OBJECT_OFFSET = 0x14
PICKUP_LISTENER_OPAQUE_U8_OBJECT_OFFSET = 0x18
# On the wire: tag+4 then tag+1 = 7 bytes, always (both gates are ALWAYS).
PICKUP_LISTENER_PAYLOAD_SIZE = 7

# Rejection reasons; every one of them means "no fields, no reply, no write".
# The first two are ENCODER-side only (test/probe composition refusing bad
# declared values) and can never be raised by decode/classify/dispatch, so
# their dispatch event names can never occur; the last four are the wire
# families a real frame can trip.
PICKUP_LISTENER_REJECTIONS = (
    "pickup_value_type_not_integer",
    "pickup_value_outside_field_width",
    "truncated_payload",
    "wrong_object_ref_tag",
    "wrong_opaque_u8_tag",
    "trailing_bytes_after_object",
)


@dataclass(frozen=True)
class PickupListenerFields:
    """The two decoded values, named by proven source and width ONLY.

    ``object_ref_u32`` records only what GT-046 job 5 proved: the client
    copies this dword from the selected live runtime drop-object
    ([ptr+0x10]).  It is NOT an element_key and must not be renamed to
    claim any table semantics.  ``opaque_u8`` has no known meaning and is
    never interpreted (see the module docstring nonclaims).
    """

    object_ref_u32: int
    opaque_u8: int


@dataclass(frozen=True)
class PickupListenerHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    response_policy: str


# ------------------------------------------------------------ the probe plan
PICKUP_LISTENER_SCENARIO_ID = "pickup_listener_hypothesis_decode_probe"
PICKUP_LISTENER_RESPONSE_POLICY = (
    "decode_count_and_record_no_reply_no_write"
)

# The probe field pairs the tests drive through the real dispatcher.  The
# VALUES are OUR DESIGN and are chosen only to be tellable-apart and to
# exercise the statically closed wire widths: an all-zero pair, the width
# maxima, and a mid-range pair with two distinct member values.  None of
# them is claimed to be a real drop-object id or anything else.
PICKUP_LISTENER_PROBE_ORDER = ("ZERO", "MID", "MAX")
PICKUP_LISTENER_PROBE_FIELDS = {
    "ZERO": PickupListenerFields(0, 0),
    "MID": PickupListenerFields(305419896, 42),
    "MAX": PickupListenerFields(0xFFFFFFFF, 0xFF),
}

# ----------------------------------------------------------------- the pins
# Computed by running THIS encoder deterministically (the probe plan takes no
# per-session input, so the pins are absolute); every value below is a sha256
# of bytes this module composed, never a value copied in.
PICKUP_LISTENER_PROBE_PAYLOAD_SHA256 = {
    "ZERO": (
        "B2398619DB817C08B9CA007A8A85D88B28630FC0A6332D7C0096CFCB47BC9083"
    ),
    "MID": (
        "33DBDBF7B68DCD2DDD15791104B3BE5174C2B1235AFFED11619CBD78460BC971"
    ),
    "MAX": (
        "7F29F214B667DEFD573881FD22EC9B0B6D93A26D7ABB13631AC8D4DAD8630890"
    ),
}
PICKUP_LISTENER_PROBE_REQUEST_PC_SHA256 = {
    "ZERO": (
        "76BC9F9264A9342D5ADE0D84EA3832925641FA2612E453FB9D8B6B5F4BE8249F"
    ),
    "MID": (
        "850177F9BFA1157F51488768458373D19881281930365759CDEF3EFFF26F5923"
    ),
    "MAX": (
        "D643151C90FF47365C5286746FC7EB6D2E084C3023D2905AB264B12A104182AB"
    ),
}
PICKUP_LISTENER_PROBE_PAYLOAD_SIZE = {
    "ZERO": 7, "MID": 7, "MAX": 7,
}
PICKUP_LISTENER_PROBE_REQUEST_PC_SIZE = {
    "ZERO": 27, "MID": 27, "MAX": 27,
}


# ---------------------------------------------------------------- self-guards
def _require_probe_plan() -> None:
    """The pinned plan must keep asking the questions it was built to ask."""
    if len(set(PICKUP_LISTENER_PROBE_ORDER)) != len(
        PICKUP_LISTENER_PROBE_ORDER
    ):
        raise RuntimeError("HYP-PF-036 duplicate probe label")
    if set(PICKUP_LISTENER_PROBE_FIELDS) != set(
        PICKUP_LISTENER_PROBE_ORDER
    ):
        raise RuntimeError("HYP-PF-036 probe plan label drift")
    fields = PICKUP_LISTENER_PROBE_FIELDS
    if fields["ZERO"] != PickupListenerFields(0, 0):
        raise RuntimeError(
            "HYP-PF-036 the probe plan must keep the all-zero pair"
        )
    if fields["MAX"] != PickupListenerFields(0xFFFFFFFF, 0xFF):
        raise RuntimeError(
            "HYP-PF-036 the probe plan must keep the width maxima"
        )
    for label in PICKUP_LISTENER_PROBE_ORDER:
        if type(fields[label]) is not PickupListenerFields:
            raise RuntimeError("HYP-PF-036 probe plan field type drift")


def _require_int(value: Any, width_bits: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise ValueError(
            "pickup listener rejected: pickup_value_type_not_integer"
        )
    if value < 0 or value >= (1 << width_bits):
        raise ValueError(
            "pickup listener rejected: pickup_value_outside_field_width"
        )
    return value


# ---------------------------------------------------------------- encoder
# PF-HYPOTHESIS-LEDGER: HYP-PF-036 active
def encode_pickup_listener_payload(
    legacy: Any,
    fields: PickupListenerFields,
) -> bytes:
    """Compose one PickupTerrainThing body from the declared pair.

    Test-side and probe-side only: the server never emits this message (the
    only proven producer is client-outbound; we are listen-only).  The
    wire order is the delivery-table one and nothing else: u32 tag 0x14 at
    object+0x14, then u8 tag 0x08 at object+0x18.  The member semantics
    beyond the GT-046 source proof are unknown; the values pass through as
    declared or the composition refuses with a named reason and no bytes.
    The composed payload is re-decoded before it is returned, so the
    encoder can never emit something its own decoder would refuse.
    """
    if type(fields) is not PickupListenerFields:
        raise ValueError(
            "pickup listener rejected: pickup_value_type_not_integer"
        )
    payload = bytearray()
    payload += legacy.u32tag(
        PICKUP_LISTENER_OBJECT_REF_TAG,
        _require_int(fields.object_ref_u32, 32),
    )
    payload += legacy.u8tag(
        PICKUP_LISTENER_OPAQUE_U8_TAG,
        _require_int(fields.opaque_u8, 8),
    )
    payload = bytes(payload)
    if len(payload) != PICKUP_LISTENER_PAYLOAD_SIZE:
        raise RuntimeError("HYP-PF-036 composed payload size drift")
    if decode_pickup_listener_payload(payload) != fields:
        raise RuntimeError("HYP-PF-036 encoder is not decoder-inverse")
    return payload


# ---------------------------------------------------------------- decoder
def decode_pickup_listener_payload(
    payload: Any,
) -> PickupListenerFields:
    """Read one PickupTerrainThing body into the declared pair.

    Written strictly from the symmetric delivery-table wire order: every tag
    byte is verified at its position, every truncation refuses, and a byte
    left over after the trailing u8 refuses.  No partial result is ever
    returned.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise ValueError("pickup listener rejected: truncated_payload")
    payload = bytes(payload)
    if len(payload) < 5:
        raise ValueError("pickup listener rejected: truncated_payload")
    if payload[0] != PICKUP_LISTENER_OBJECT_REF_TAG:
        raise ValueError("pickup listener rejected: wrong_object_ref_tag")
    first = int.from_bytes(payload[1:5], "little")
    cursor = 5
    if len(payload) - cursor < 2:
        raise ValueError("pickup listener rejected: truncated_payload")
    if payload[cursor] != PICKUP_LISTENER_OPAQUE_U8_TAG:
        raise ValueError("pickup listener rejected: wrong_opaque_u8_tag")
    second = payload[cursor + 1]
    cursor += 2
    if cursor != len(payload):
        raise ValueError(
            "pickup listener rejected: trailing_bytes_after_object"
        )
    return PickupListenerFields(first, second)


# ---------------------------------------------------------------- classifier
def classify_pickup_listener_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one 0x4543-bearing parse against the acceptance design.

    The accepted envelope is the same one-vital client request envelope the
    chat, logout and learn-skill-request lanes accept: GSCN_RunTimeProtocolReq,
    outer version 0, outer mask 0x02, vital_count 1, nested version 0.  For
    this vital that envelope is OUR acceptance design (never captured -- see
    the module docstring nonclaims).  Everything else fails closed.
    """
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_id == PICKUP_LISTENER_VITAL_ID
        and parsed.nested_version == PICKUP_LISTENER_VITAL_VERSION
    ):
        return "wrong_envelope"
    try:
        decode_pickup_listener_payload(parsed.nested_payload)
    except ValueError as exc:
        reason = str(exc).rsplit(": ", 1)[-1]
        if reason not in PICKUP_LISTENER_REJECTIONS:
            raise RuntimeError(
                "HYP-PF-036 decoder raised an unregistered reason"
            ) from exc
        return reason
    return "exact_pickup"


# ---------------------------------------------------------------- probe frames
def compose_pickup_listener_probe_pc(
    legacy: Any, fields: PickupListenerFields,
) -> bytes:
    """Build one full client-request PC carrying the pickup body.

    Test-side and probe-side only.  The 20-byte envelope is the one-vital
    GSCN_RunTimeProtocolReq header every captured client request of other
    vitals uses (the same bytes the chat-lane probe PCs pin); wrapping the
    DERIVED vital id 0x4543 in it is OUR DESIGN, stated in the module
    docstring nonclaims.
    """
    payload = encode_pickup_listener_payload(legacy, fields)
    return bytes(
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, PICKUP_LISTENER_VITAL_ID)
        + legacy.u8tag(0x0B, PICKUP_LISTENER_VITAL_VERSION)
        + payload
    )


# ---------------------------------------------------------------- scenario gate
_PROFILE_DECODE_PROBE = PickupListenerHypothesisScenario(
    PICKUP_LISTENER_SCENARIO_ID,
    PICKUP_LISTENER_HYPOTHESIS_ID,
    PICKUP_LISTENER_RESPONSE_POLICY,
)


def _fields_schema(fields: PickupListenerFields) -> dict[str, int]:
    return {
        "object_ref_u32": fields.object_ref_u32,
        "opaque_u8": fields.opaque_u8,
    }


def _expected_probe() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": PICKUP_LISTENER_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": PICKUP_LISTENER_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": PICKUP_LISTENER_RESPONSE_POLICY,
        },
        "dispatch": {
            "trigger": "inbound_one_vital_0x4543_pickup_frame",
            "trigger_classifier": "classify_pickup_listener_attempt",
            "frames_emitted_per_accepted_request": 0,
            "accepted_event": "pickup_listener_hypothesis_decoded_no_reply",
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": PICKUP_LISTENER_VITAL_ID,
            "vital_id_provenance": PICKUP_LISTENER_VITAL_ID_PROVENANCE,
            "vital_version": PICKUP_LISTENER_VITAL_VERSION,
            "vital_version_provenance": (
                "our_design_no_capture_or_static_pin_fixes_it"
            ),
            "envelope": (
                "gscn_runtime_protocol_req_one_vital_client_request_"
                "our_acceptance_design_for_this_vital"
            ),
            "body_order": [
                "u32_tag_0x14_at_object_0x14",
                "u8_tag_0x08_at_object_0x18",
            ],
            "payload_wire_size": PICKUP_LISTENER_PAYLOAD_SIZE,
            "provenance": {
                "ticket": "GT-046",
                "letter": (
                    "pf_bridge/notes_to_chief/20260823_1435_GT046-PASS-"
                    "outbound-mouseclick-runtime-drop-object.md"
                ),
                "registry": "pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv",
                "delivery_table": (
                    "pf_bridge/external/PF_SERIALIZER_FIELDS.tsv"
                ),
                "delivery_rows": "W_and_R_byte_symmetric_gate_ALWAYS",
                "derived_id_source": (
                    "pf_bridge/FACTPACK_L2_CLASSCENSUS001_20260820.tsv"
                ),
                "capture_status": (
                    "not_observed_in_either_direction_"
                    "pf_field_validation_rows_102_103"
                ),
                "serializer_va": "0x005E5E30",
                "serializer_len": PICKUP_LISTENER_SERIALIZER_LEN,
                "serializer_sha256": PICKUP_LISTENER_SERIALIZER_SHA256,
            },
        },
        "probe": {
            "per_probe": {
                label: {
                    "fields": _fields_schema(
                        PICKUP_LISTENER_PROBE_FIELDS[label]
                    ),
                    "payload_size": (
                        PICKUP_LISTENER_PROBE_PAYLOAD_SIZE[label]
                    ),
                    "payload_sha256": (
                        PICKUP_LISTENER_PROBE_PAYLOAD_SHA256[label]
                    ),
                    "request_pc_size": (
                        PICKUP_LISTENER_PROBE_REQUEST_PC_SIZE[label]
                    ),
                    "request_pc_sha256": (
                        PICKUP_LISTENER_PROBE_REQUEST_PC_SHA256[label]
                    ),
                }
                for label in PICKUP_LISTENER_PROBE_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "decode_the_delivery_table_pickup_body_shape",
            "refuse_malformed_bodies_by_named_reason",
            "count_and_record_accepted_pickups_per_session",
            "repeatable_per_session_no_reply_no_persisted_state_change",
        ],
        "nonclaims": [
            "the_runtime_vital_id_which_is_hash_derived_never_observed",
            "any_wire_observation_of_this_vital_in_either_direction",
            "any_meaning_for_object_ref_u32_beyond_the_gt046_source_proof",
            "any_meaning_for_opaque_u8",
            "any_pickup_rule_or_any_response_frame",
            "monster_drop_pickup_which_may_ride_the_fightingdrop_family",
            "the_request_envelope_which_was_never_captured",
            "the_vital_version_byte_which_is_our_design",
            "original_server_pickup_behavior",
            "item_grant_or_database_write",
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


def load_pickup_listener_hypothesis_scenario(
    path: str | Path,
) -> PickupListenerHypothesisScenario:
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
            "invalid pickup listener hypothesis scenario"
        ) from exc
    if type(data) is not dict or data.get("id") != (
        PICKUP_LISTENER_SCENARIO_ID
    ):
        raise ValueError(
            "pickup listener hypothesis scenario exceeds the exact "
            "allowlist"
        )
    if not _exact_equal(data, _expected_probe()):
        raise ValueError(
            "pickup listener hypothesis scenario exceeds the exact "
            "allowlist"
        )
    return require_pickup_listener_hypothesis_scenario(
        _PROFILE_DECODE_PROBE
    )


def require_pickup_listener_hypothesis_scenario(
    value: Any,
) -> PickupListenerHypothesisScenario:
    if (
        type(value) is not PickupListenerHypothesisScenario
        or value != _PROFILE_DECODE_PROBE
    ):
        raise ValueError(
            "pickup listener hypothesis scenario object exceeds the "
            "allowlist"
        )
    _require_probe_plan()
    return value
