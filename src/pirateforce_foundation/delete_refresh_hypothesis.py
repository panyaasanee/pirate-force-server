"""Governed list-rebuild lane for the delete acknowledgement (HYP-PF-021).

DELETE-REFRESH-001.  Attended GT-011 ended with the soft delete committed in
the database, no error dialog anywhere, and the character-select list not
moving by a pixel.  UI-REFRESH-001
(``reports/PF_UI_REFRESH001_CHARACTER_SELECT_STATE_MACHINE_STATIC_20260819.md``)
answered why, byte-exact, from the read-only client image:

* the whole character list lives in ONE buffer, the collection at ``+0x180``
  of the singleton cached in ``[0x1081A90]``;
* the complete set of mutators is *bulk fill* ``0x5DDD00`` (one caller in the
  entire image: ``0x5EFCAC``, inside the ``SelectActorVital`` 0x36EF apply),
  *append one* ``0x5DDE10`` (one caller: inside the ``CreateActorVital``
  0x36CF apply) and *clear* ``0x5DDF00`` / ``0x5DE540``.  **There is no
  erase-by-key path anywhere in the image**, so no shape of the
  ``DeleteActorVital`` 0x36DB acknowledgement can ever take a row out of the
  list -- its handler ``0x4BAEB0`` only repaints from that same, unchanged
  collection;
* therefore the ONLY frame in the protocol that can make a character
  disappear from the screen is a fresh ``SelectActorVital`` (0x36EF), whose
  apply ``0x5EFC40`` resets the model (``0x406C30`` -> ``0x5DDF00``), refills
  it (``0x5DDD00``), builds a brand-new ``cStateCreateActor`` (``0x4C03E0``)
  and requests the transition (``CState::RequestNext 0x4C7320``).

This module is the server half of exactly that, and nothing else: after the
HYP-PF-015 soft delete has committed and its pinned echo ack has been
composed, send the character list again.

WHAT IS INVENTED HERE: nothing.  The rebuild frame is not composed by this
module.  It is the byte-for-byte output of ``LegacyProjector.character_list``
-- the same projection the real client has accepted at every login in every
runtime pass of this project (``character_list_projection`` is the one
``runtime_pass`` row of the character_management domain) -- taken over the
post-delete character set.  This module only *verifies and pins* that
projection before the dispatcher is allowed to queue it, so a drifted
projection fails closed instead of putting a guessed frame on the wire.

THE SECOND GT-011 SYMPTOM ("other buttons stopped responding") -- new static
evidence, byte-exact, produced by this milestone and checked by
``tools/verify_delete_refresh_static.py``:

UI-REFRESH-001 enumerated the twenty *immediate* writes (``C7 05``) to the
character-select page variable ``0x107A2C0``, observed that the delete
animation at ``0x4BAE91`` sets it to ``0x0B`` and that ``OnDeleteResult``
never restores it, and left "which page was live during GT-011" as an open
runtime question.  An exhaustive scan of every reference to ``0x107A2C0`` in
``.text`` finds **26** instructions: those 20 immediate writes, 5 reads /
compares, and one writer the immediate-only scan could not see --

    0x4BD650:  89 3D C0 A2 07 01     mov dword [0x107A2C0], edi

with ``edi`` zeroed at ``0x4BD620`` (``xor edi, edi``) and no branch and no
EDI-clobbering instruction between them (EDI is callee-saved in the Win32
x86 ABI).  ``0x4BD5E0``, the function that write sits in, has **zero direct
call sites in the whole image** and is ``cStateCreateActor``'s vtable slot
**+0x10** (vtable ``0xF16520``).  Slot +0x10 is the state machine's enter
hook: the state tick ``0x4C7540`` dispatches on the state's phase word
``+0x0C`` -- phase 0 calls ``[vtable+0x10]`` and then sets the phase to 1,
phase 1 calls the per-frame ``[vtable+0x14]`` (for ``cStateCreateActor``
that is ``0x4C3C40``, the fifteen-entry page dispatch), phase 2 (the value
``CState::RequestNext`` writes) calls the exit slot ``[vtable+0x18]`` and
promotes the pending state stored at ``+0x10`` of the navigator.

So the full predicted chain of one ``SelectActorVital`` is:

    reset the model -> refill it from our frame -> construct a fresh
    cStateCreateActor -> RequestNext -> next tick promotes it -> the tick
    after that runs its enter hook 0x4BD5E0, which zeroes the page variable

i.e. the same single frame is predicted to restore BOTH the list and the
input page that GT-011 found stuck.  That is a prediction about a client, not
a proven pixel: it is the DELETE-REFRESH-001 attended claim (GT-021).

Everything here is opt-in (``scenarios/delete_refresh_hypothesis_list_rebuild.json``
reached only through ``--delete-refresh-hypothesis-scenario``), test-only,
``production_allowed`` false, and fails closed: a request that is not the
exact designed op-1 shape, a wrong stage, a repository refusal, a projection
that does not verify, or a post-delete list that still contains the deleted
selector all produce **no bytes at all** -- not even the ack.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


# The one frame that rebuilds the client's character list (UI-REFRESH-001 s.3
# and s.6).  Version 10 is the version the frozen v141 snapshot has always
# sent and the real client has always accepted.
SELECT_ACTOR_VITAL_ID = 0x36EF
SELECT_ACTOR_VITAL_VERSION = 10

# Structure of LegacyProjector.character_list's PC, all of it runtime-proven
# (this is the login-time character list every accepted session receives):
#   [0x00..0x14)  GSCN_RunTimeProtocolRes v4 envelope, mask 0x02, count 1,
#                 nested id 0x36EF, nested version 10          -> 20 bytes
#   [0x14..0x29)  payload prefix 0B 00 | 14 0 | 14 0 | 1F 0 |
#                 0B 00 | 0B <record count>                    -> 21 bytes
#   then one actor record per listed character, then 0B 00 0B 00.
# The LAST 0B 00 is exactly the RuntimeRes derived-class change mask that
# DELETE-SOFT-002 proved the client over-reads without (ErrorData=28317):
# the composed PC is byte-identical to
# make_runtime_vitals([(0x36EF, 10, payload_without_that_trailing_mask)]),
# which make_delete_actor_list_rebuild_response checks on every composition.
LIST_REBUILD_PC_HEADER_SIZE = 20
LIST_REBUILD_PAYLOAD_PREFIX_SIZE = 21
LIST_REBUILD_PAYLOAD_SUFFIX = bytes.fromhex("0B000B00")
LIST_REBUILD_RECORD_COUNT_OFFSET = LIST_REBUILD_PC_HEADER_SIZE + 20
LIST_REBUILD_MAX_RECORDS = 0xFF

# The deterministic case the GT-011 replay produces: one owned character,
# deleted, list rebuilt empty.  45-byte PC / 55-byte frame, hash-pinned end
# to end so the headless replay and the tests check the same bytes.
LIST_REBUILD_EMPTY_PC_SIZE = 45
LIST_REBUILD_EMPTY_FRAME_SIZE = 55
LIST_REBUILD_EMPTY_PC_SHA256 = (
    "E19905837B226059E4973AD26869A41CB79EF4C4FD14BACDFD18DC4B5D3CEEA4"
)
LIST_REBUILD_EMPTY_FRAME_SHA256 = (
    "735ACC96DC0742D711167258EF0CD64D2854E0A2DEAA9B63805505DE595152CB"
)

# The rebuild is queued after the ack with the same gap the dispatcher has
# always used between the login ack and the character list
# ("FOUNDATION_CHARACTER_LIST_ONCE", 0.35 s) -- the one inter-frame spacing
# at this stage a real client is known to accept.  No new timing is invented.
DELETE_REFRESH_GAP_SECONDS = 0.35
DELETE_REFRESH_ACTION_LABEL = "HYP_PF_021_DELETE_ACTOR_LIST_REBUILD_0x36EF"

# Static anchors this lane's design rests on.  They are asserted against the
# read-only client image by tools/verify_delete_refresh_static.py; they are
# repeated here so a source reader can see what the lane assumes and so the
# verifier and the module cannot drift apart silently.
CLIENT_SHA256 = (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
)
STATIC_ANCHORS = {
    "character_list_singleton_global": 0x01081A90,
    "character_list_collection_offset": 0x180,
    "character_list_fill": 0x5DDD00,
    "character_list_clear": 0x5DDF00,
    "character_list_erase_by_key_paths": 0,
    "select_actor_apply": 0x5EFC40,
    "select_actor_fill_call_site": 0x5EFCAC,
    "select_actor_request_next_call_site": 0x5EFD1E,
    "app_reset": 0x406C30,
    "state_request_next": 0x4C7320,
    "character_select_state_ctor": 0x4C03E0,
    "character_select_state_vtable": 0xF16520,
    "character_select_enter_hook": 0x4BD5E0,
    "character_select_enter_hook_vtable_slot": 0x10,
    "page_variable": 0x0107A2C0,
    "page_variable_register_write": 0x4BD650,
    "page_variable_zero_source": 0x4BD620,
    "state_tick": 0x4C7540,
    "state_tick_enter_call_site": 0x4C75D9,
    "delete_ack_handler": 0x4BAEB0,
    "delete_animation_page_write": 0x4BAE91,
    "delete_animation_page_value": 0x0B,
}


@dataclass(frozen=True)
class DeleteRefreshHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    gap_seconds: float
    empty_pc_sha256: str
    empty_frame_sha256: str


# The one accepted profile of this lane.  (The ledger emitter annotation for
# HYP-PF-021 sits on the composer below; the verifier allows exactly one per
# file, and the composer is the function that can put bytes on a wire.)
_PROFILE = DeleteRefreshHypothesisScenario(
    "delete_refresh_hypothesis_list_rebuild_after_ack",
    "HYP-PF-021",
    DELETE_REFRESH_GAP_SECONDS,
    LIST_REBUILD_EMPTY_PC_SHA256,
    LIST_REBUILD_EMPTY_FRAME_SHA256,
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
        "response_policy": (
            "echo_exact_request_vital_then_rebuild_the_whole_list_with_"
            "select_actor_vital_0x36ef"
        ),
        "rebuild_source": (
            "reproject_the_post_delete_character_set_through_the_unchanged_"
            "runtime_proven_character_list_projection"
        ),
        "rebuild_gap_seconds": DELETE_REFRESH_GAP_SECONDS,
        "rebuild_failure_policy": "fail_closed_silent_no_reply_not_even_the_ack",
    },
    "composed_responses": {
        "list_rebuild_empty": {
            "vital_id": SELECT_ACTOR_VITAL_ID,
            "vital_version": SELECT_ACTOR_VITAL_VERSION,
            "pc_size": LIST_REBUILD_EMPTY_PC_SIZE,
            "pc_sha256": LIST_REBUILD_EMPTY_PC_SHA256,
            "frame_size": LIST_REBUILD_EMPTY_FRAME_SIZE,
            "frame_sha256": LIST_REBUILD_EMPTY_FRAME_SHA256,
        },
    },
    "persisted_post_state": {
        "characters_deleted_at": "written_before_any_byte_is_queued",
        "child_rows": "positions_and_backpack_rows_survive_as_history",
        "rebuild_write_path": "none_the_rebuild_only_reads_the_character_table",
    },
    "capabilities": [
        "soft_delete_one_owned_unselected_character_by_selector",
        "acknowledge_committed_soft_delete_with_the_pinned_designed_echo",
        "rebuild_the_client_character_list_with_select_actor_vital_after_the_ack",
    ],
    "nonclaims": [
        "original_server_request_envelope",
        "original_server_response_policy",
        "client_observable_list_refresh",
        "client_observable_page_variable_reset_or_button_recovery",
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


def load_delete_refresh_hypothesis_scenario(
    path: str | Path,
) -> DeleteRefreshHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid delete refresh hypothesis scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _EXPECTED):
        raise ValueError(
            "delete refresh hypothesis scenario exceeds the exact allowlist"
        )
    return require_delete_refresh_hypothesis_scenario(_PROFILE)


def require_delete_refresh_hypothesis_scenario(
    value: Any,
) -> DeleteRefreshHypothesisScenario:
    if type(value) is not DeleteRefreshHypothesisScenario or value != _PROFILE:
        raise ValueError(
            "delete refresh hypothesis scenario object exceeds the allowlist"
        )
    return value


def list_rebuild_pc_header(legacy: Any) -> bytes:
    """The exact GSCN_RunTimeProtocolRes v4 one-vital 0x36EF PC header."""
    return bytes(
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 4)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, SELECT_ACTOR_VITAL_ID)
        + legacy.u8tag(0x0B, SELECT_ACTOR_VITAL_VERSION)
    )


def list_rebuild_payload_prefix(legacy: Any, record_count: int) -> bytes:
    """The exact character-list payload prefix for ``record_count`` rows."""
    return bytes(
        legacy.u8tag(0x0B, 0)
        + legacy.u32tag(0x14, 0)
        + legacy.u32tag(0x14, 0)
        + legacy.u32tag(0x1F, 0)
        + legacy.u8tag(0x0B, 0)
        + legacy.u8tag(0x0B, record_count)
    )


# PF-HYPOTHESIS-LEDGER: HYP-PF-021 active
def make_delete_actor_list_rebuild_response(
    legacy: Any, projection: Any, *, record_count: int,
) -> tuple[bytes, bytes]:
    """Verify and pin one post-delete character-list rebuild before it is sent.

    ``projection`` is the ``(pc, frame)`` pair the unchanged, runtime-proven
    ``LegacyProjector.character_list`` produced over the post-delete character
    set.  This function composes nothing: it proves that what it was handed is
    that projection and no other frame, so a drifted or hand-built rebuild
    never reaches the wire.

    Checked on every call:
      1. the GSCN_RunTimeProtocolRes v4 one-vital header for 0x36EF v10;
      2. the character-list payload prefix, with the record-count byte equal
         to the number of characters the caller says it projected;
      3. the ``0B 00 0B 00`` tail;
      4. byte-equality with ``make_runtime_vitals`` over the same payload
         minus its last two bytes -- i.e. the DELETE-SOFT-002 trailing
         derived-class change mask is present, in the exact position the
         client's stream reader wants it;
      5. ``frame == frame_pc(pc)``;
      6. for the empty list, the deterministic 45/55-byte hash pins.
    """
    if type(record_count) is not int or isinstance(record_count, bool):
        raise ValueError("HYP-PF-021 rebuild record count must be an int")
    if not 0 <= record_count <= LIST_REBUILD_MAX_RECORDS:
        raise ValueError("HYP-PF-021 rebuild record count exceeds the u8 field")
    if type(projection) is not tuple or len(projection) != 2:
        raise ValueError("HYP-PF-021 rebuild projection must be a (pc, frame) pair")
    pc, frame = projection
    if type(pc) is not bytes or type(frame) is not bytes:
        raise ValueError("HYP-PF-021 rebuild projection must carry bytes")

    header = list_rebuild_pc_header(legacy)
    if len(header) != LIST_REBUILD_PC_HEADER_SIZE or not pc.startswith(header):
        raise RuntimeError("HYP-PF-021 rebuild envelope drift")
    payload = pc[LIST_REBUILD_PC_HEADER_SIZE:]
    prefix = list_rebuild_payload_prefix(legacy, record_count)
    if len(prefix) != LIST_REBUILD_PAYLOAD_PREFIX_SIZE or not payload.startswith(prefix):
        raise RuntimeError("HYP-PF-021 rebuild payload prefix drift")
    if not payload.endswith(LIST_REBUILD_PAYLOAD_SUFFIX):
        raise RuntimeError("HYP-PF-021 rebuild payload tail drift")
    collection_pc, _collection_frame = legacy.make_runtime_vitals([
        (SELECT_ACTOR_VITAL_ID, SELECT_ACTOR_VITAL_VERSION, payload[:-2]),
    ])
    if collection_pc != pc:
        raise RuntimeError("HYP-PF-021 rebuild derived-class mask drift")
    if frame != legacy.frame_pc(pc):
        raise RuntimeError("HYP-PF-021 rebuild frame drift")
    if record_count == 0:
        if (
            len(pc) != LIST_REBUILD_EMPTY_PC_SIZE
            or hashlib.sha256(pc).hexdigest().upper()
            != LIST_REBUILD_EMPTY_PC_SHA256
        ):
            raise RuntimeError("HYP-PF-021 empty rebuild PC drift")
        if (
            len(frame) != LIST_REBUILD_EMPTY_FRAME_SIZE
            or hashlib.sha256(frame).hexdigest().upper()
            != LIST_REBUILD_EMPTY_FRAME_SHA256
        ):
            raise RuntimeError("HYP-PF-021 empty rebuild frame drift")
    return pc, frame


def assert_selector_absent(characters: Any, selector: int) -> int:
    """Refuse to rebuild a list that still carries the deleted selector."""
    rows = list(characters)
    if any(row.selector == selector for row in rows):
        raise RuntimeError(
            "HYP-PF-021 refuses to rebuild a list that still holds the "
            "deleted selector"
        )
    return len(rows)
