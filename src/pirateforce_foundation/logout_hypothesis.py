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

# HYP-PF-028 (LOGOUT-RETURN-SELECT-001): the return-select-server response.
# Round-100 static RE (agent D, pf_bridge/FACTPACK_R100_LOGOUT_TRANSITION_
# STATIC.md) proved with a mechanism that an ECHO cannot transition the client:
# every vital echoed inside GSCN_RunTimeProtocolRes is consumed by the inbound
# actor-vital RECONCILE pass 0x446F30, which only adds/updates/removes actor
# vitals and never switches scene/state/connection.  The real transition is
# driven by a session/connection orchestrator (vtable 0xf45030) that waits on a
# mode+timer and then tears down the game connection.  ReturnSelectServerVital
# (0x709E) is the strongest-NAMED candidate for the "return to character
# select" direction, but agent D found NO client code path that consumes 0x709E
# to drive cStateSelectServer, so static cannot decide whether sending it
# transitions the client -- that is exactly the queued attended A/B (GT-033).
# This scenario answers a captured LogoutVital with a well-formed 0x709E vital
# (then the pinned ack, then the proven clean close), so an attended run can
# observe whether the real client acts on it.  The 0x709E body is composed from
# the client's OWN serializer field layout (below); the original server's
# actual return-select response is unrecoverable and this is our design.
LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST = "return_select_server_first"

# HYP-PF-031 (LOGOUT-CHAT-PUSH-001): the unsolicited chat-triggered push.
# GT-033 is BLOCKED at the trigger, not at the response: the attended tester
# cannot click the client's HOME menu item, so the client never emits
# LogoutVital 0x1B40 and neither GT-033 variant (the PF-013 close nor the
# PF-028 response-first shape) can ever fire -- both REPLY to a request that
# never arrives.  The tester CAN reliably type into chat (Return focuses the
# chat box), and the chat-input trigger path is already proven end to end:
# HYP-PF-027 answers one accepted 34-byte ascii12 chat-input frame with a
# composed spawn frame a headless replay reads back from the bytes.  This
# policy therefore decouples the frozen PF-028 response from its request
# pairing: ONE accepted ascii12 chat-input frame makes the server push the
# already-pinned ReturnSelectServerVital (0x709E) response UNSOLICITED --
# no LogoutVital needed, exactly once per session -- so an attended run can
# observe whether the response ALONE causes the client screen transition.
# No new byte is composed: the pushed frame is the byte-identical hash-pinned
# HYP-PF-028 composition (38-byte PC / 48-byte frame, pins above).  Nothing
# in the chat request is read, no store is touched, no session lease is
# closed and no socket action is taken; and if the client DOES later send a
# LogoutVital while this scenario is active, the lane deliberately does NOT
# answer it (named no-reply event), so the session asks exactly one question.
LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT = "chat_push_return_select"

# HYP_PF_040 (LOGOUT-DIALOG-OPEN-001, branch 6 of RE-189's Job 2): the
# unsolicited return-select push AT DIALOG-OPEN TIME instead of in reply to
# LogoutVital.  RE-189 (pf_bridge/notes_to_chief/consumed/20260901_1008_
# RE-189-RESULT-PLUS18-LOCAL-UI-AND-SERVER-BRANCH-MATRIX.md) found that
# every existing logout response profile above answers the LogoutVital
# REQUEST itself, which per R40 only ever arrives AFTER the client has
# already built its local logout-confirmation dialog -- too late to
# influence the one client-side field (SystemSetting_LogoutConfirm+0x18)
# every profile above is trying to flip. This policy instead keys off the
# full-form GetWorldInfoVital (0x3D4B) that HYP-PF-016 already correlated
# 7/7 with dialog-open across two captured sessions, and pushes the same
# byte-identical pinned HYP-PF-028 ReturnSelectServerVital (0x709E) at that
# moment, unsolicited, ahead of any LogoutVital -- see
# logout_dialog_open_hypothesis.py for the dispatch function this policy
# routes to and the full nonclaim list it inherits from RE-189.
# PF-HYPOTHESIS-LEDGER: HYP-PF-040 active
# LOGOUT-DIALOG-OPEN-001.  Registered in docs/HYPOTHESIS_LEDGER.json; this
# annotation and that entry's source_refs bind each other both ways.
LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH = "worldinfo_dialog_open_push"

# RE-189 Job 2, branch 3 (CORE-REQUEST: pf_bridge/notes_to_chief/
# 20260901_1844_LANE-A-CORE-REQUEST-re189-branch2-built-branch3-needs-
# runtime-py-hyp041-ledger.md, section 3).  Branch 3 of the RE-189 matrix
# is the ack-first reorder: swap the wire order of HYP-PF-028's two
# already-pinned frames so the pinned LogoutVital ack
# (``make_logout_ack_response``) goes out FIRST and the pinned
# ReturnSelectServerVital (``make_return_select_server_response``) goes
# out SECOND -- the reverse of ``LOGOUT_RESPONSE_POLICY_RETURN_SELECT_
# FIRST`` above.  Lane A checked the real code before asking (the
# "no-guessing" rule) and found ``runtime.py``'s existing dispatch
# hardcodes the 0x709E-before-ack order inline with no parameter to
# swap, so a new ``response_policy`` value with its own routing branch
# is the only way to reach the reversed order without touching either
# pinned composer -- neither composer changes, no new byte is invented,
# only the calling order and which frame is sent first.  This round
# (chief, option (a) of the CORE-REQUEST) adds ONLY this constant and
# the sibling routing branch in ``runtime.py`` that reads it: no
# scenario JSON, no allowlist profile, and no hypothesis_id are assigned
# yet -- that is lane A's next-round work, the same two-step pattern
# HYP-PF-040 used (chief wired an unreachable branch first; lane A added
# the allowlisted profile + scenario file the following round, see the
# module comment above HYP-PF-040 and ``test_logout_dialog_open_scenario
# _wired.py``'s own docstring for that precedent).  Until a profile
# exists in ``require_logout_hypothesis_scenario``'s allowlist, no real
# boot can ever construct a scenario carrying this value, so the new
# routing branch is provably unreachable from any default path, exactly
# like that precedent was before its allowlist profile landed.
LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER = "ack_first_reorder"

# The trigger vital id, copied from the proven GT-006 chat-input decode --
# never imported: an encoder does not import a neighbouring lane (the
# HYP-PF-027 rule).  The tests pin this copy against the chat module's own
# constant so the two cannot drift apart silently.
CHAT_PUSH_TRIGGER_VITAL_ID = 0xAC52
CHAT_PUSH_TRIGGER_PAYLOAD_SIZE = 34
CHAT_PUSH_TRIGGER_CLASSIFICATION = "ascii12"

# ReturnSelectServerVital wire body, decoded from the client serializer
# 0x5e69f0 (descriptor table 0xf304ec slot2) by the round-101 static pass, the
# same method agent D used on LogoutVital's 0x5e6820.  The serializer writes,
# in order:
#   field1  object +0x14  wire tag 0x08  u8            -> 08 <v>
#   field2  object +0x18  wire tag 0x32  8-byte scalar  -> 32 <8 bytes>
#   field3  object +0x20  wire tag 0x44  std::string    -> 44 <u32 len><data>
# [STALE][MEASURED] round 292 (2026-09-01, corrected same round after
# pf-adversary re-review of the first draft): field3's tag byte 0x44 is
# UNCONFIRMED against ReturnSelectServerVital's own serializer -- NOT
# confirmed false either way. pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
# records field 3 of ReturnSelectServerVital (rows 1125/1128) as
# UNTAGGED_STRING8_LEN32LE, which looks like "no tag byte" -- but the same
# TSV gives the IDENTICAL label to DeleteActorVital's own string field
# (rows 462/466), whose 0x44 tag GT-018 independently confirmed is real.
# GT-055 already established why: this label describes the scope of the
# string-writing HELPER call only: a tag byte can be written by a separate
# instruction just before the helper is called, outside the span the label
# covers (exactly the DeleteActorVital case). So the TSV proves neither
# "field3 has no tag" nor "field3's tag is 0x44" -- both are open until
# someone finds (or fails to find) a tag-write instruction immediately
# before `string_wire_call@0x005E6A2B`, the way rows 1123/1124 show for
# field1/field2's STACK@+0x14/+0x18 writes. The ORIGINAL sentence below
# ("EVERY TAG BYTE ... IS READ FROM THE CLIENT'S OWN SERIALIZER") overclaims
# field3 was measured the same way field1/field2 were -- it was not. See
# RE-196 (CLIENT_RE_QUEUE.md) for the open question, and
# notes_to_chief/20260901_1737_LANE-A-CORE-REQUEST-logout-tag-byte-overclaim-found-by-real-adversary.md
# for how this was first caught.
# FIELD1/FIELD2's TAG BYTES (0x08 / 0x32) ARE READ FROM THE CLIENT'S OWN
# SERIALIZER; FIELD3's TAG BYTE (0x44) IS NOT -- SEE [STALE][MEASURED] ABOVE.
# nothing structural is invented.  No producer in the client sets these fields
# to any non-zero content, so the field VALUES default to zero and the string
# is empty -- an explicit nonclaim, the same honest default agent D applied.
# The all-zero form is therefore the minimal well-formed body: 16 bytes.
#
# ---------------------------------------------------------------------------
# RE-070 ERRATUM, round 168 (2026-08-25).  Two corrections, one of them against
# a premise this module used to state as settled.  Neither changes one byte of
# this lane; both change what may be claimed from it.
#
# (1) THE BROAD PHRASE "0x709E has no client producer" IS RETIRED.  It used to
# appear twice further down this module and once in the lane's test.  What the
# wire evidence actually says is narrower AND points the other way:
#
#   Codex's frozen capture accounting -- pf_bridge/external/PF_FIELD_VALIDATION
#   .tsv rows 144-145, table sha256 080a5f32580df575632fee69d3f8faa6e2e745ad17
#   75d05daf3e272e4e0941c3, pinned at tools/pf_external_registry.py -- records
#   ReturnSelectServerVital as W observed 2 / parsed 2 / files 2 / VALIDATED,
#   and R observed 0 / NOT_OBSERVED.  W is the client->server direction.  The
#   two frames sit in the bridge-only files inventoried as PF_INPUT_INVENTORY
#   .tsv rows 693 and 927 (sha256 2a43616bac2370cd68297ff533c9ef0c84498d1ea35e
#   6d81957af81391efa3ab, block ordinal 6; and b79b22f9c69519a7baf560470af2e22
#   48985ed648c8d3a2c7c1bf81053d53ee3, block ordinal 7).
#
#   PROVENANCE, stated plainly: this round did NOT hash those capture files.
#   They do not exist on a cloud clone.  What is verifiable here is that two
#   second-party tables written by Codex record these digests against those
#   paths, and that both tables still match their registry pins.  That is a
#   weaker claim than "measured", and it is the only one available.
#
#   Both sessions are character-select-stage sessions, and the outer envelope
#   is GSCN_LoginProtocol 0x453A -- the one-vital request shape every captured
#   character-select-stage request uses.  So the accurate statement is:
#
#     every observation of 0x709E anywhere in the corpus is the CLIENT SENDING
#     IT AS A REQUEST at character select.  Not one frame has ever been seen
#     travelling server -> client, which is the direction THIS LANE USES.
#
#   Read that as evidence about direction, never as support for the lane: it
#   runs the other way from the only traffic anyone has measured.  The payload
#   VALUES were not measured by that pass, so the zero default above stands.
#   Caveat that travels with the word VALIDATED: GT-047 showed the validator
#   accepts a mutated field_offset, so one validator pass is not on its own a
#   reason to promote any schema claim.
#
# (2) A PREMISE THIS MODULE USED TO STATE IS NOW IN TENSION WITH THE REGISTRY.
# The old wording asserted "the id-getter 0x5e6960 has zero callers and no
# consumer keys on 0x709E".  But pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv
# row 73 carries, for ReturnSelectServerVital: getter_va 0x005E6960 installed
# at reg_site_va 0x00BEE880, and handler_va 0x005F1190 -- an address that is
# UNIQUE to this row across all 519 rows, so it is not one of the shared stubs
# that table reuses elsewhere (contrast serializer_va 0x0043BB80, shared by the
# whole Attr cohort).  "Zero direct rel32 callers" is therefore not evidence of
# "no producer": indirect dispatch through the descriptor table is exactly what
# the registry describes.
#
#   NOT RESOLVED HERE, and deliberately not asserted either way: whether
#   0x005F1190 is a semantic handler for 0x709E or an artefact of how that
#   table was built.  Deciding it needs the client image, which a cloud clone
#   does not have.  Until someone measures it, this module claims only that the
#   old premise is no longer load-bearing.
# ---------------------------------------------------------------------------
RETURN_SELECT_SERVER_VITAL_ID = 0x709E
RETURN_SELECT_SERVER_BODY = bytes.fromhex(
    "0800" "32" "0000000000000000" "44" "00000000"
)
RETURN_SELECT_SERVER_BODY_SIZE = 16
# Composed GSCN_RunTimeProtocolRes v4 (one vital, version 0, the 16-byte body),
# deterministic: 38-byte PC / 48-byte frame.  Pinned so the module, verifier,
# replay and scenario all agree byte-for-byte.
RETURN_SELECT_SERVER_RESPONSE_PC_SIZE = 38
RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE = 48
RETURN_SELECT_SERVER_RESPONSE_PC_SHA256 = (
    "A4C8DF4299EA7C3A5EE5554D1D29D7F8C1A2B51031CA210CBEB9AF2AD9D4CA9E"
)
RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256 = (
    "08C2A925BD67CD3D0AFA7992F98D472ED8FD22787756521A5DF8CBF174E5CB8E"
)

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

# PF-HYPOTHESIS-LEDGER: HYP-PF-028 retired
_PROFILE_RETURN_SELECT = LogoutHypothesisScenario(
    "logout_hypothesis_return_select_server_subcode01_03",
    "HYP-PF-028",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
)

# HYP-PF-028 exact allowlist: the unchanged PF-012 request/ack pins and the
# unchanged PF-013 close lever, plus the single new pre-ack action -- compose
# and send one well-formed ReturnSelectServerVital (0x709E) whose body is the
# client serializer's own field layout with all fields zero.  No response byte
# is invented under this scenario either: the 0x709E tags come from the client
# serializer and the values are the honest zero default (no client producer was
# found for the field VALUES -- see the RE-070 erratum at the body pin above),
# fully pinned below.
_EXPECTED_RETURN_SELECT = {
    "schema": 1,
    "id": _PROFILE_RETURN_SELECT.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_RETURN_SELECT.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
        "return_select_source": (
            "client_serializer_0x5e69f0_field_layout_all_zero_no_client_"
            "producer_values_default_zero"
        ),
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
        "return_select_first": {
            "vital_id": RETURN_SELECT_SERVER_VITAL_ID,
            "body_size": RETURN_SELECT_SERVER_BODY_SIZE,
            "pc_size": RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
            "pc_sha256": RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
            "frame_size": RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
            "frame_sha256": RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
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
            "written_before_return_select_response_bytes_are_queued"
        ),
        "position_rewrite": "none",
    },
    "capabilities": [
        "compose_well_formed_return_select_server_vital_from_client_"
        "serializer_field_layout",
        "send_return_select_server_vital_before_the_pinned_logout_ack",
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "silence_connection_after_acknowledged_logout",
        "server_initiated_clean_socket_close_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "return_select_server_field_values_and_string_semantics",
        "client_consumes_0x709e_or_transitions_to_character_select",
        "client_observable_exit_or_character_select_return",
        "logout_outside_runtime_ready_sequence",
        "subcodes_other_than_01_and_03",
        "production_baseline_behavior",
    ],
}

# HYP-PF-040 (LOGOUT-DIALOG-OPEN-001): the second half of the entry whose
# single required emitter annotation for this file already lives on the
# ``LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH`` constant above (the
# ledger verifier allows exactly one "active" annotation per file per
# hypothesis id). This is the sixth allowlisted profile the ledger's own
# "accepted_ceiling" and runtime.py's routing branch (see
# logout_dialog_open_hypothesis.py) already named as missing; adding it
# here is what finally makes
# LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH constructible through
# load_logout_hypothesis_scenario / the existing --logout-hypothesis-scenario
# CLI flag app.py already wires generically -- no app.py/runtime.py edit is
# needed for that part; both already dispatch on whatever scenario object
# this loader returns. The LogoutVital side of this profile (post_ack_action,
# ack pins) is the unchanged HYP-PF-013 ack-then-close shape: branch 6 only
# changes WHEN the 0x709E push happens (unsolicited, on the dialog-open
# 0x3D4B full-form frame, ahead of any LogoutVital); it does not change what
# happens if/when the client still sends LogoutVital afterward.
_PROFILE_DIALOG_OPEN = LogoutHypothesisScenario(
    "logout_hypothesis_dialog_open_push_subcode01_03",
    "HYP-PF-040",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH,
)

# HYP-PF-040 exact allowlist: the unchanged PF-012 request/ack pins and the
# unchanged PF-013 close lever for the LogoutVital side, plus the unchanged
# PF-028 0x709E body for the new unsolicited push -- no byte is invented
# under this scenario either. What is new is the DELIVERY POLICY only: the
# push rides the full-form GetWorldInfoVital (0x3D4B) trigger instead of a
# LogoutVital request pairing, one-shot per session, and is handled entirely
# by dispatch_logout_dialog_open_hypothesis (logout_dialog_open_hypothesis.py)
# -- this module's own composer/classifier are reused unchanged, not
# reimplemented, per the HYP-PF-027 rule.
_EXPECTED_DIALOG_OPEN = {
    "schema": 1,
    "id": _PROFILE_DIALOG_OPEN.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_DIALOG_OPEN.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH,
        "dialog_open_trigger": (
            "full_form_getworldinfo_vital_0x3d4b_correlated_7_of_7_with_"
            "client_local_logout_dialog_open_across_two_captured_sessions"
        ),
        "dialog_open_push_source": (
            "client_serializer_0x5e69f0_field_layout_all_zero_no_client_"
            "producer_values_default_zero_unchanged_from_hyp_pf_028"
        ),
        "dialog_open_push_policy": "unsolicited_one_shot_ahead_of_any_logoutvital",
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
        },
    },
    "composed_responses": {
        "dialog_open_push": {
            "vital_id": RETURN_SELECT_SERVER_VITAL_ID,
            "body_size": RETURN_SELECT_SERVER_BODY_SIZE,
            "pc_size": RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
            "pc_sha256": RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
            "frame_size": RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
            "frame_sha256": RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
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
        "sessions_closed_at": "written_before_ack_bytes_are_queued",
        "position_rewrite": "none",
        "worldinfo_storage": "connection_memory_only_no_table_no_write_path",
    },
    "capabilities": [
        "push_the_pinned_return_select_server_vital_unsolicited_on_the_"
        "dialog_open_full_form_getworldinfo_trigger",
        "refuse_a_second_dialog_open_push_on_the_same_session_by_name",
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "silence_connection_after_acknowledged_logout",
        "server_initiated_clean_socket_close_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "return_select_server_field_values_and_string_semantics",
        "client_consumes_0x709e_or_transitions_to_character_select",
        "client_observable_exit_or_character_select_return",
        "dialog_is_open_at_the_exact_instant_the_push_is_queued",
        "logout_outside_runtime_ready_sequence",
        "subcodes_other_than_01_and_03",
        "production_baseline_behavior",
    ],
}

# PF-HYPOTHESIS-LEDGER: HYP-PF-031 active
_PROFILE_CHAT_PUSH = LogoutHypothesisScenario(
    "logout_hypothesis_chat_push_return_select",
    "HYP-PF-031",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_NONE,
    0,
    LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT,
)

# HYP-PF-031 exact allowlist: no new response byte exists under this scenario
# either -- the one pushed frame is the byte-identical hash-pinned HYP-PF-028
# composition -- and no ack, no close and no write exists at all.  What is new
# is the DELIVERY POLICY only: the response rides an accepted chat-input
# trigger instead of a LogoutVital request pairing, one-shot, and a LogoutVital
# under this scenario is deliberately not answered so the session asks exactly
# one question (GT-033 variant C: does the response ALONE transition the
# client, without request pairing).
_EXPECTED_CHAT_PUSH = {
    "schema": 1,
    "id": _PROFILE_CHAT_PUSH.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_CHAT_PUSH.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT,
        "trigger": (
            "one_accepted_ascii12_chat_input_frame_request_body_never_read"
        ),
        "return_select_source": (
            "client_serializer_0x5e69f0_field_layout_all_zero_no_client_"
            "producer_values_default_zero"
        ),
        "logout_vital_policy": (
            "no_reply_named_event_the_lane_stays_one_question"
        ),
        "one_shot": True,
        "post_ack_action": LOGOUT_POST_ACK_ACTION_NONE,
        "close_delay_ms": 0,
        "socket_action": "none",
    },
    "requests": {
        "chat_trigger": {
            "vital_id": CHAT_PUSH_TRIGGER_VITAL_ID,
            "payload_size": CHAT_PUSH_TRIGGER_PAYLOAD_SIZE,
            "classification": CHAT_PUSH_TRIGGER_CLASSIFICATION,
        },
    },
    "composed_responses": {
        "chat_push_return_select": {
            "vital_id": RETURN_SELECT_SERVER_VITAL_ID,
            "body_size": RETURN_SELECT_SERVER_BODY_SIZE,
            "pc_size": RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
            "pc_sha256": RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
            "frame_size": RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
            "frame_sha256": RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        },
    },
    "persisted_post_state": {
        "database_write": "none",
        "position_rewrite": "none",
    },
    "capabilities": [
        "push_the_pinned_return_select_server_vital_unsolicited_on_one_"
        "accepted_chat_input_trigger",
        "compose_well_formed_return_select_server_vital_from_client_"
        "serializer_field_layout",
        "refuse_a_second_trigger_on_the_same_session_by_name",
        "refuse_a_logout_vital_under_this_scenario_by_name_with_no_reply",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "original_server_ever_pushed_an_unsolicited_vital",
        "return_select_server_field_values_and_string_semantics",
        "client_consumes_0x709e_or_transitions_to_character_select",
        "client_observable_exit_or_character_select_return",
        "chat_request_body_semantics_the_trigger_is_never_read",
        "logout_vital_acknowledgement_under_this_scenario",
        "production_baseline_behavior",
    ],
}

# HYP-PF-041 (LOGOUT-TEARDOWN-TIMER-VARIANT-001, RE-189 branch 2 of Job 2):
# does the post-ack close DELAY itself matter to the real client, independent
# of the ack+close shape GT-008 already falsified at the one pinned value
# (250 ms)?  GT-008's attended negative measured only that one point on the
# timeline ("the real client never detects the clean server-side socket
# close at all -- no transition, no error dialog, no disconnect handling for
# 40+ s"); it did not sweep the delay, so whether an immediate close, a much
# longer wait, or never closing at all changes that outcome is still
# unmeasured.  This entry varies exactly one lever the HYP-PF-013 shape
# already introduced (close_delay_ms) and invents no new response byte: the
# ack pins are the unchanged HYP-PF-012 composition reused verbatim (per the
# HYP-PF-027 rule -- an encoder is not reimplemented for a parameter sweep),
# reused identically to how _PROFILE_ACK_CLOSE reuses them.  Four points are
# swept: 0 ms (close scheduled the instant the ack is queued), 2000 ms and
# 10000 ms (the delay itself is the only thing that can plausibly matter,
# since GT-008 already showed the client does not react to any close it was
# given time to notice), and "never" (post_ack_action stays
# LOGOUT_POST_ACK_ACTION_NONE -- structurally identical to the unmodified
# HYP-PF-012 echo shape, kept as a distinct scenario purely so its own
# hypothesis_id and evidence trail are tracked separately from HYP-PF-012's).
# PROVENANCE NOTE: HYP-PF-041 is not yet a registered entry in
# docs/HYPOTHESIS_LEDGER.json.  Repo-wide grep at the time this profile was
# written found no prior use of "HYP-PF-041" or "HYP_PF_041" anywhere (the
# highest registered id is HYP-PF-040), so the number is claimed here the
# same way HYP-PF-040 was provisionally named in code ahead of its own
# ledger entry -- but unlike that case, ledger registration itself
# (docs/HYPOTHESIS_LEDGER.json's canonical-hash-pinned entries) is chief's
# write zone per this project's own established practice: every prior
# ledger-entry edit visible in verify_hypothesis_ledger.py's lineage comments
# was made by a chief round, with the sole exception of a LANE-A round
# amending a tracked_versions list on an entry chief had already opened
# (HYP-PF-040 / round tmizmk) -- never minting the entry itself. A
# CORE-REQUEST asking chief to register this entry accompanies this round.
# [REGISTERED, chief cloud round 5qs3y7 2026-09-01 (CORE-REQUEST reply to
# pf_bridge/notes_to_chief/20260901_1844_LANE-A-CORE-REQUEST-re189-branch2-
# built-branch3-needs-runtime-py-hyp041-ledger.md)]: the PROVENANCE NOTE
# above is now historical -- HYP-PF-041 is a registered entry in
# docs/HYPOTHESIS_LEDGER.json as of this round, and the annotation marker
# immediately below binds this module to that entry both ways, the same
# convention every other active entry in this file already uses.
# PF-HYPOTHESIS-LEDGER: HYP-PF-041 active
# LOGOUT-TEARDOWN-TIMER-VARIANT-001.  Registered in
# docs/HYPOTHESIS_LEDGER.json; this annotation and that entry's source_refs
# bind each other both ways.
LOGOUT_CLOSE_DELAY_MS_VARIANT_0MS = 0
LOGOUT_CLOSE_DELAY_MS_VARIANT_2000MS = 2000
LOGOUT_CLOSE_DELAY_MS_VARIANT_10000MS = 10000

_PROFILE_TEARDOWN_TIMER_VARIANT_0MS = LogoutHypothesisScenario(
    "logout_hypothesis_teardown_timer_variant_0ms_subcode01_03",
    "HYP-PF-041",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_0MS,
    LOGOUT_RESPONSE_POLICY_ACK_ONLY,
)

_PROFILE_TEARDOWN_TIMER_VARIANT_2000MS = LogoutHypothesisScenario(
    "logout_hypothesis_teardown_timer_variant_2000ms_subcode01_03",
    "HYP-PF-041",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_2000MS,
    LOGOUT_RESPONSE_POLICY_ACK_ONLY,
)

_PROFILE_TEARDOWN_TIMER_VARIANT_10000MS = LogoutHypothesisScenario(
    "logout_hypothesis_teardown_timer_variant_10000ms_subcode01_03",
    "HYP-PF-041",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS_VARIANT_10000MS,
    LOGOUT_RESPONSE_POLICY_ACK_ONLY,
)

_PROFILE_TEARDOWN_TIMER_VARIANT_NEVER = LogoutHypothesisScenario(
    "logout_hypothesis_teardown_timer_variant_never_subcode01_03",
    "HYP-PF-041",
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


# Each allowlist below is written by hand, independently of the profile
# construction above, on purpose: the whole point of load_logout_hypothesis_
# scenario's _exact_equal check is that the expectation is a second,
# separately-authored source, not a derivation FROM the profile object it
# is supposed to be checking (round njkvcc's real pf-adversary finding on
# this same file was exactly a "verifier" that silently shared its
# assumption with the thing it verified -- this file does not repeat that
# shape here).
_EXPECTED_TEARDOWN_TIMER_VARIANT_0MS = {
    "schema": 1,
    "id": _PROFILE_TEARDOWN_TIMER_VARIANT_0MS.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_TEARDOWN_TIMER_VARIANT_0MS.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "post_ack_policy": "dispatch_silent_then_server_clean_socket_close",
        "post_ack_action": LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        "close_delay_ms": LOGOUT_CLOSE_DELAY_MS_VARIANT_0MS,
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
        "the_delay_value_itself_changes_client_behavior",
    ],
}

_EXPECTED_TEARDOWN_TIMER_VARIANT_2000MS = {
    "schema": 1,
    "id": _PROFILE_TEARDOWN_TIMER_VARIANT_2000MS.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_TEARDOWN_TIMER_VARIANT_2000MS.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "post_ack_policy": "dispatch_silent_then_server_clean_socket_close",
        "post_ack_action": LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        "close_delay_ms": LOGOUT_CLOSE_DELAY_MS_VARIANT_2000MS,
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
        "the_delay_value_itself_changes_client_behavior",
    ],
}

_EXPECTED_TEARDOWN_TIMER_VARIANT_10000MS = {
    "schema": 1,
    "id": _PROFILE_TEARDOWN_TIMER_VARIANT_10000MS.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_TEARDOWN_TIMER_VARIANT_10000MS.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "post_ack_policy": "dispatch_silent_then_server_clean_socket_close",
        "post_ack_action": LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        "close_delay_ms": LOGOUT_CLOSE_DELAY_MS_VARIANT_10000MS,
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
        "the_delay_value_itself_changes_client_behavior",
    ],
}

_EXPECTED_TEARDOWN_TIMER_VARIANT_NEVER = {
    "schema": 1,
    "id": _PROFILE_TEARDOWN_TIMER_VARIANT_NEVER.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_TEARDOWN_TIMER_VARIANT_NEVER.hypothesis_id,
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
        "the_delay_value_itself_changes_client_behavior",
    ],
}


# RE-189 Job 2, branch 3 (LOGOUT-ACK-FIRST-REORDER-001): the allowlisted
# profile + scenario file for LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER.
# runtime.py's routing branch (see that constant's own comment above, and
# the RE_189_BRANCH3_... action labels in runtime.py) was wired by chief
# LAST round per CORE-REQUEST option (a) of pf_bridge/notes_to_chief/
# 20260901_1844_LANE-A-CORE-REQUEST-re189-branch2-built-branch3-needs-
# runtime-py-hyp041-ledger.md section 3: it composes the unchanged
# HYP-PF-012 ack FIRST, then the unchanged HYP-PF-028 ReturnSelectServerVital
# response SECOND -- the exact reverse send order of
# LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST.  Neither composer changes and
# no byte is invented; only the calling order and which frame goes out first
# differ.  Until this round, no profile in require_logout_hypothesis_
# scenario's allowlist could carry this response_policy, so the branch was
# provably unreachable from any default boot
# (tests/test_logout_ack_first_reorder_routing_wired.py, chief's own file,
# proves this directly with test_scenario_carrying_the_new_policy_is_not_
# yet_allowlisted -- read alongside this profile rather than superseded by
# it, since that file also proves the wiring is CORRECT via an in-memory
# probe scenario before any real profile existed). This entry is lane A's
# next-round half of the same two-step pattern HYP-PF-040 and HYP-PF-041
# both used: chief wires an unreachable routing branch first, lane A adds
# the allowlisted profile + scenario file afterward.
#
# HYPOTHESIS ID -- THIS IS DELIBERATELY NOT HYP-PF-041.  HYP-PF-041
# (LOGOUT-TEARDOWN-TIMER-VARIANT-001, registered in docs/HYPOTHESIS_LEDGER
# .json, chief cloud round 5qs3y7) is RE-189 Job 2 BRANCH 2 -- a sibling
# opened by the SAME CORE-REQUEST letter but a DIFFERENT hypothesis: its own
# exact_value_or_transform names only the post-ack close_delay_ms sweep and
# says nothing about frame order.  Reusing its id here would silently
# misattribute this branch's frame-reorder claim to that entry's
# already-registered, already-hash-pinned ledger text -- the opposite of
# what a hypothesis id is for.  Repo-wide grep at the time this profile was
# written (grep -rn "HYP-PF-04[0-9]" .) finds HYP-PF-040 and HYP-PF-041 both
# claimed and HYP-PF-042 unused anywhere, so HYP-PF-042 is claimed here --
# the same provisional-before-ledger-registration move HYP-PF-040 and
# HYP-PF-041 both made in their own turn (see HYP-PF-041's own PROVENANCE
# NOTE above for that precedent's exact wording).
#
# PROVENANCE NOTE: HYP-PF-042 is NOT YET a registered entry in
# docs/HYPOTHESIS_LEDGER.json as of this round.  Per this project's own
# established practice (every prior ledger-entry MINT visible in
# verify_hypothesis_ledger.py's lineage comments was a chief-round action;
# the sole lane-A exception amended an already-open entry, never minted one)
# ledger registration itself is chief's write zone, so this round does not
# hand-guess CANONICAL_CONTENT_SHA256.  A CORE-REQUEST asking chief to
# register HYP-PF-042 (LOGOUT-ACK-FIRST-REORDER-001) accompanies this round.
# DELIBERATELY NO "PF-HYPOTHESIS-LEDGER: HYP-PF-042 active" ANNOTATION LINE
# HERE YET: tools/verify_hypothesis_ledger.py's verify_source_annotations
# scans every .py under src/ and every .json under scenarios/ for that exact
# marker and raises "unregistered emitter annotation" for any id absent from
# its own EXPECTED_META table -- adding the marker before chief registers
# the entry (and updates that table) would break the verifier for every lane,
# not just this one.  The same restraint HYP-PF-041's own commit exercised
# before its registration (see that entry's PROVENANCE NOTE and its later
# [REGISTERED ...] follow-up, added in place rather than replacing the
# original text, per the R166 amend-not-replace precedent).  Add the marker
# only after docs/HYPOTHESIS_LEDGER.json carries this id.
LOGOUT_ACK_FIRST_REORDER_CHECKPOINT = "LOGOUT-ACK-FIRST-REORDER-001"

_PROFILE_ACK_FIRST_REORDER = LogoutHypothesisScenario(
    "logout_hypothesis_ack_first_reorder_subcode01_03",
    "HYP-PF-042",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
)

# HYP-PF-042 exact allowlist: the unchanged PF-012 request/ack pins and the
# unchanged PF-013 close lever (identical to _EXPECTED_RETURN_SELECT), plus
# the unchanged PF-028 0x709E body -- no byte is invented under this
# scenario either.  What is new relative to _EXPECTED_RETURN_SELECT is the
# WIRE ORDER only: the ack is sent first and the 0x709E response second,
# the reverse of "return_select_first".
_EXPECTED_ACK_FIRST_REORDER = {
    "schema": 1,
    "id": _PROFILE_ACK_FIRST_REORDER.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_ACK_FIRST_REORDER.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
        "wire_order": "ack_first_then_return_select_server_response",
        "return_select_source": (
            "client_serializer_0x5e69f0_field_layout_all_zero_no_client_"
            "producer_values_default_zero"
        ),
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
        "return_select_after_ack": {
            "vital_id": RETURN_SELECT_SERVER_VITAL_ID,
            "body_size": RETURN_SELECT_SERVER_BODY_SIZE,
            "pc_size": RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
            "pc_sha256": RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
            "frame_size": RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
            "frame_sha256": RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        },
    },
    "persisted_post_state": {
        "sessions_closed_at": "written_before_ack_bytes_are_queued",
        "position_rewrite": "none",
    },
    "capabilities": [
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "send_the_pinned_ack_before_the_return_select_server_response_"
        "reverse_of_return_select_first",
        "compose_well_formed_return_select_server_vital_from_client_"
        "serializer_field_layout",
        "server_initiated_clean_socket_close_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "return_select_server_field_values_and_string_semantics",
        "client_consumes_0x709e_or_transitions_to_character_select",
        "client_observable_exit_or_character_select_return",
        "the_reordered_wire_shape_alone_changes_client_behavior_relative_"
        "to_return_select_first",
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
    _PROFILE_RETURN_SELECT.scenario_id: (
        _EXPECTED_RETURN_SELECT, _PROFILE_RETURN_SELECT,
    ),
    _PROFILE_CHAT_PUSH.scenario_id: (
        _EXPECTED_CHAT_PUSH, _PROFILE_CHAT_PUSH,
    ),
    _PROFILE_DIALOG_OPEN.scenario_id: (
        _EXPECTED_DIALOG_OPEN, _PROFILE_DIALOG_OPEN,
    ),
    _PROFILE_TEARDOWN_TIMER_VARIANT_0MS.scenario_id: (
        _EXPECTED_TEARDOWN_TIMER_VARIANT_0MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_0MS,
    ),
    _PROFILE_TEARDOWN_TIMER_VARIANT_2000MS.scenario_id: (
        _EXPECTED_TEARDOWN_TIMER_VARIANT_2000MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_2000MS,
    ),
    _PROFILE_TEARDOWN_TIMER_VARIANT_10000MS.scenario_id: (
        _EXPECTED_TEARDOWN_TIMER_VARIANT_10000MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_10000MS,
    ),
    _PROFILE_TEARDOWN_TIMER_VARIANT_NEVER.scenario_id: (
        _EXPECTED_TEARDOWN_TIMER_VARIANT_NEVER,
        _PROFILE_TEARDOWN_TIMER_VARIANT_NEVER,
    ),
    _PROFILE_ACK_FIRST_REORDER.scenario_id: (
        _EXPECTED_ACK_FIRST_REORDER, _PROFILE_ACK_FIRST_REORDER,
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
        _PROFILE_RETURN_SELECT, _PROFILE_CHAT_PUSH, _PROFILE_DIALOG_OPEN,
        _PROFILE_TEARDOWN_TIMER_VARIANT_0MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_2000MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_10000MS,
        _PROFILE_TEARDOWN_TIMER_VARIANT_NEVER,
        _PROFILE_ACK_FIRST_REORDER,
    ):
        raise ValueError("logout hypothesis scenario object exceeds the allowlist")
    for subcode in LOGOUT_SUBCODES:
        digest = hashlib.sha256(LOGOUT_REQUEST_PCS[subcode]).hexdigest().upper()
        if digest != LOGOUT_REQUEST_PC_SHA256[subcode]:
            raise RuntimeError("logout hypothesis request fixture drift")
    if (
        # [STALE][MEASURED] round 292: byte 11's 0x44 is this module's own
        # fixture value, not an independent second source -- see the field3
        # tag note above the module docstring's wire-body comment (RE-196).
        len(RETURN_SELECT_SERVER_BODY) != RETURN_SELECT_SERVER_BODY_SIZE
        or RETURN_SELECT_SERVER_BODY[0] != 0x08
        or RETURN_SELECT_SERVER_BODY[2] != 0x32
        or RETURN_SELECT_SERVER_BODY[11] != 0x44
        or RETURN_SELECT_SERVER_BODY[12:] != b"\x00\x00\x00\x00"
    ):
        raise RuntimeError("logout hypothesis return-select body fixture drift")
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


# HYP-PF-028 composer (the ledger annotation for this id lives once on the
# profile above; the required marker for this file is that active annotation).
def make_return_select_server_response(legacy: Any) -> tuple[bytes, bytes]:
    """Compose and independently pin the designed ReturnSelectServerVital.

    One GSCN_RunTimeProtocolRes v4 vital, id 0x709E, version 0, carrying the
    16-byte body the client's own serializer 0x5e69f0 produces for an all-zero
    instance.  Relative to any other RuntimeRes the only bytes that differ are
    the nested id (0x709E) and the pinned body; the envelope constants are the
    same the frozen ``make_runtime_vitals`` writes for every accepted response.
    Zero content bytes are invented: the tags are the client serializer's own,
    the field values are the honest zero default (no client producer was found
    for those VALUES -- see the RE-070 erratum at the body pin, which also
    records that every observation of 0x709E in the corpus is the client
    SENDING it at character select, never receiving it).  Deterministic
    38-byte PC / 48-byte frame, hash-pinned.
    """
    pc, frame = legacy.make_runtime_vitals([
        (RETURN_SELECT_SERVER_VITAL_ID, 0, RETURN_SELECT_SERVER_BODY),
    ])
    if (
        len(pc) != RETURN_SELECT_SERVER_RESPONSE_PC_SIZE
        or hashlib.sha256(pc).hexdigest().upper()
        != RETURN_SELECT_SERVER_RESPONSE_PC_SHA256
    ):
        raise RuntimeError("HYP-PF-028 response PC drift")
    if (
        len(frame) != RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE
        or hashlib.sha256(frame).hexdigest().upper()
        != RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256
    ):
        raise RuntimeError("HYP-PF-028 response frame drift")
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
