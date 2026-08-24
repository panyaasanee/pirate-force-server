"""ITEMOP-RES-GREENLINE-001 -- pinned ItemOperateVitalRes 0x4C13 sweep for
the GT-063 attended question: which shape puts the green chat line
``received [item] * count`` (client message id 131) on the real screen
(HYP-PF-037).

Where the project stops without this module
-------------------------------------------
GT-049 (letter pf_bridge/notes_to_chief/20260824_0923_GT049-RESULT-ID131-
INBOUND-ITEMOPERATE.md) proved statically that message id 131 -- template
``received [ $V1 ] * $V2``, the green pickup line -- is emitted from the
INBOUND ``ItemOperateVitalRes`` handler chain 0x005EF5E0 -> 0x005CC309: the
server decides that a pickup succeeded, not the client.  RE-059 (letter
pf_bridge/notes_to_chief/20260824_1413_RE-059-RESULT-EXTRACTED-5-OF-5.md)
extracted all five real captured 0x4C13 frames byte-exactly, and RE-060
(letter pf_bridge/notes_to_chief/20260824_1422_RE-060-RESULT-PINNED-5-
CODES.md) pinned the item-table id scheme (full_id / 100000 -> table,
full_id % 100000 -> n_ID; 24 = ITEM_CONSUMABLES).  What nobody recorded is
WHAT THE SCREEN SHOWED when any of those five frames travelled: we hold the
envelopes but not the letters' effects.  This lane composes the sweep the
attended GT-063 ticket fires so a person can finally watch the chat area
while known bytes leave the server.

What the three sweep frames are, and why these shapes
-----------------------------------------------------
Every frame reuses the ONE ItemOperate result codec this project has
already proven end to end: ``inventory.make_item_move_delta_response``,
whose exact output the real client accepted live at V111 and whose exact
output equals captured frame 1 of RE-059 BYTE FOR BYTE at the message
layer (re-verified at every composition below).  No frame carries a byte
whose shape was guessed.

  1. ``ITEMOP_RES_CTRL_CAPTURE_REPLAY`` -- the control: byte-exact replay
     of RE-059 captured frame 1 (message layer, 54 bytes, committed hex).
     The composition is DUAL-DERIVED and both derivations are compared on
     every call: the committed capture hex on one side, our golden codec
     over ``ItemAttrState(1, 2600001, 2, 2)`` on the other.  If a shape
     that demonstrably travelled produces nothing on screen, that is a
     valuable result, not a wasted frame.
  2. ``ITEMOP_RES_BAGUPD_ID2400901_QTY1`` -- the same proven shape whose
     ItemBagAttr update element carries the real consumable item id
     2400901 (RE-060: table 24 ITEM_CONSUMABLES, n_ID 901; the same item
     the canonical smoke backpack holds at identity 2, slot 1) with
     quantity 1 -- the shape expected to raise the green line.
  3. ``ITEMOP_RES_BAGUPD_ID2400901_QTY5`` -- identical except quantity 5,
     probing the ``* <count>`` channel of template id 131.

Why there is NO affected_identity_count > 0 frame in this sweep
---------------------------------------------------------------
The GT-063 ticket draft proposed count=1 frames.  The static record
(PF_SERIALIZER_FIELDS.tsv rows 769-794, PF_TAG_CENSUS.tsv) yields only a
CANDIDATE per-element shape (u64 tag 0x32 then u8 tag 0x08), it has never
been walked against a real record (all five captured frames carry count 0),
and whether the unclassified direct call R13 (0x005ED2F0) participates per
element is OPEN -- a composed count=1 frame could be short or long without
any way to know.  Composing from a guessed shape is exactly what this
project's fail-closed rule forbids, so the count>0 dimension goes back to
the bridge as its own static ticket (RE-064) instead of onto a live socket.
Every frame this module emits keeps affected_identity_count = 0, the only
value ever captured.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * NOTHING IS CLAIMED ABOUT WHAT THE SCREEN SHOWS.  Whether any of the
    three frames raises the green line, another message, or nothing is
    exactly the attended GT-063 question; this module only guarantees the
    bytes that leave.
  * NO FIELD SEMANTICS beyond what the golden codec already carries are
    claimed: R4, the bag mask, the two raw u8 item fields and the
    affected-identity tail keep the values the accepted capture shape
    carries, and no new meaning is assigned to any of them.
  * The item id 2400901 rests on RE-060's id scheme, which is pinned by
    candidate 100%-hit evidence, NOT by wire confirmation; if the screen
    shows a different item name than the table predicts, that is a new
    finding, not a defect of this lane.
  * NOT CLAIMED that the original server -- closed, unpublished and
    unrecoverable -- ever sent a quantity-5 variant or ever answered a
    pickup with this exact shape.  Frames 2 and 3 are this project's own
    probe design over the proven codec.
  * NOT CLAIMED that any item enters the bag or the database: the lane
    writes no row, and what the client's local bag view does with these
    frames is part of the attended observation, not of this module.
  * The 15-byte envelope prefix of the captured PC block is NOT committed
    anywhere this clone can read; the replay is byte-exact at the message
    layer (wrapper tag through the affected-identity tail, 54 bytes) and
    rides the same frozen v141 envelope the client already accepts, whose
    PC length 71 equals the captured PC length.  Byte-exactness of the
    envelope prefix itself is deliberately not claimed.

Fail-closed contract
--------------------
Refused with ``ValueError`` and no bytes: a step index outside the pinned
plan (no other input exists -- the plan is module-frozen).  The message
decoder refuses, by named reason, a wrong tag at every position, a bag
whose base is not the one accepted base (mask 0xFF, identity 0), an
affected_identity_count other than 0 (the only captured value; composing
past it is forbidden above), any truncation, and any trailing byte.  Every
composed step is re-decoded and compared with its declared plan row, the
control step is compared against the committed capture hex, and every
composition is hash-pinned in the module AND in the scenario file from the
same live computation.  No database call exists on any path in this file.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in
the dispatch branch does not exist: nothing in default mode composes one
byte of this.  ``database_write`` is ``none`` -- the lane opens no table.
That claim is about the DISPATCH path: the boot that carries the lane
still runs the shared foundation startup (migrate and expire-open-sessions
on the explicit ``--db``) before any trigger arrives, the same boundary
every scenario lane in this tree shares.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .inventory import ItemAttrState, make_item_move_delta_response


ITEM_OPERATE_RES_CHECKPOINT = "ITEMOP-RES-GREENLINE-001"
ITEM_OPERATE_RES_HYPOTHESIS_ID = "HYP-PF-037"
production_allowed = False

# ---------------------------------------------------------------- static pins
# Capture and static provenance closed by GT-049 / RE-059 / RE-060; carried
# as documentation-grade constants and never dereferenced.
ITEM_OPERATE_RES_VITAL_ID = 0x4C13          # ItemOperateVitalRes
# The version byte is CAPTURE-PINNED: all five RE-059 frames carry 2, and
# the golden codec already emits 2 -- unlike the sweep lanes whose version
# byte is our design, this one is not a choice.
ITEM_OPERATE_RES_VITAL_VERSION = 2
GREENLINE_HANDLER_VA = 0x005EF5E0           # GT-049 inbound 0x4C13 handler
GREENLINE_EMITTER_VA = 0x005CC309           # GT-049 chat emitter call site
GREENLINE_MESSAGE_ID = 131                  # template "received [ $V1 ] * $V2"

# RE-059 captured frame 1, message layer: wrapper tag 0x12 + opcode 0x4C13
# + version + R4 + bag_present + ItemBagAttr (43 bytes) + affected count 0.
# Committed verbatim at pf_bridge/notes_to_chief/
# 20260824_1413_RE-059-RESULT-EXTRACTED-5-OF-5.md line 44; source capture
# file sha256 2e43b7066130cf3c2ac43493aebd7bc9662085ce4fb6276809e6baf52a2a
# 581e, PC block index 101, PC len 71, wrapper offset 15.  The outer tail
# 0B 00 and the 15-byte PC prefix are the envelope's, not the message's.
CAPTURE_FRAME1_MESSAGE_HEX = (
    "12134C0B0208000B010BFF3200000000000000000F0100320100000000000000"
    "1441AC27000F02000F0200080008FF0B000F00000800"
)
CAPTURE_FRAME1_MESSAGE_SIZE = 54
CAPTURE_FRAME1_MESSAGE_SHA256 = (
    "60756925E095A507ACFFD49ECF013DAF50C706429A0FA4DA9B73CC66B6E27496"
)
CAPTURE_PC_WRAPPER_OFFSET = 15              # RE-059: wrapper off 15
CAPTURE_PC_LEN = 71                         # RE-059: PC len 71

# Message-layer geometry over the frozen envelope: the per-vital region
# starts at the wrapper offset and ends two bytes before the PC does (the
# envelope's collection tail u8 tag 0x0B, value 0).
ITEM_OPERATE_RES_PC_MESSAGE_OFFSET = CAPTURE_PC_WRAPPER_OFFSET
ITEM_OPERATE_RES_PC_TAIL_SIZE = 2
ITEM_OPERATE_RES_PC_VITAL_ID_SLICE = slice(16, 18)
ITEM_OPERATE_RES_PC_VERSION_OFFSET = 19

ITEM_OPERATE_RES_REJECTIONS = (
    "unknown_step_label",
    "truncated_message",
    "wrong_wrapper_tag",
    "wrong_vital_id",
    "wrong_version_tag",
    "unimplemented_version",
    "wrong_r4_tag",
    "unimplemented_r4",
    "wrong_bag_present_tag",
    "unimplemented_bag_present",
    "wrong_bag_mask_tag",
    "unimplemented_bag_base",
    "wrong_bag_identity_tag",
    "wrong_update_count_tag",
    "wrong_item_identity_tag",
    "wrong_item_template_tag",
    "wrong_item_quantity_tag",
    "wrong_item_slot_tag",
    "wrong_item_raw38_tag",
    "wrong_item_raw39_tag",
    "wrong_item_detail_tag",
    "wrong_removal_count_tag",
    "unimplemented_removal_count",
    "wrong_affected_count_tag",
    "unimplemented_affected_count",
    "trailing_bytes_after_affected_count",
)


@dataclass(frozen=True)
class ItemOperateResMessage:
    """One decoded 0x4C13 message of exactly the shapes this lane emits."""
    version: int
    r4: int
    bag_base_mask: int
    bag_base_identity: int
    items: tuple[ItemAttrState, ...]
    removal_count: int
    affected_identity_count: int


@dataclass(frozen=True)
class ItemOperateResHypothesisScenario:
    id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float


ITEM_OPERATE_RES_SCENARIO_ID = "item_operate_res_greenline_sweep"

# ------------------------------------------------------------- the step plan
# One ItemAttrState per step; every step goes through the SAME golden codec.
# Step 1 is the capture replay: its item IS the item captured frame 1
# carries (identity 1, template 2600001, quantity 2, slot 2 -- the accepted
# V111 move-delta golden), which is how the dual derivation below can hold.
# Steps 2 and 3 carry the RE-060-decoded consumable the canonical smoke
# backpack holds at identity 2 / slot 1, quantity 1 then 5.
ITEM_OPERATE_RES_STEPS = (
    ("ITEMOP_RES_CTRL_CAPTURE_REPLAY", ItemAttrState(1, 2600001, 2, 2)),
    ("ITEMOP_RES_BAGUPD_ID2400901_QTY1", ItemAttrState(2, 2400901, 1, 1)),
    ("ITEMOP_RES_BAGUPD_ID2400901_QTY5", ItemAttrState(2, 2400901, 5, 1)),
)
ITEM_OPERATE_RES_STEP_ORDER = tuple(
    label for label, _item in ITEM_OPERATE_RES_STEPS
)
ITEM_OPERATE_RES_STEP_ITEMS = {
    label: item for label, item in ITEM_OPERATE_RES_STEPS
}
ITEM_OPERATE_RES_PROBE_ITEM_ID = 2400901    # RE-060: 24=ITEM_CONSUMABLES, 901

# The identity guard value, the HYP-PF-026 lesson carried by every sweep
# lane since: the canonical smoke character.  The sweep refuses to fire for
# any other selected identity, so the bytes a tester sees are the pinned
# bytes or nothing.
ITEM_OPERATE_RES_PROBE_IDENTITY_LO = 0x10010001
ITEM_OPERATE_RES_PROBE_IDENTITY_HI = 0

ITEM_OPERATE_RES_SPACING_SECONDS = 3.0
ITEM_OPERATE_RES_FIRST_DELAY_SECONDS = 0.0
ITEM_OPERATE_RES_ACTION_LABEL_PREFIX = "HYP_PF_037_"

# ------------------------------------------------------ absolute output pins
# Every step is pinned at three layers -- message (wrapper tag through the
# affected-identity tail), PC and frame -- by sha256 and exact size, all
# frozen from one live computation.  The control step's message pin IS the
# committed capture hex digest.
ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256 = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": CAPTURE_FRAME1_MESSAGE_SHA256,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": (
        "A6B59308BE17181B88EF796127CDD4E33E1C3420D7BDF7ABA5C2B74060E12BBC"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": (
        "6D09CFF552F3F88B362EDE354AD6D743B5F8E348C20FF718457A7AB01A4F83F1"
    ),
}
ITEM_OPERATE_RES_PROBE_MESSAGE_SIZE = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": CAPTURE_FRAME1_MESSAGE_SIZE,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": 54,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": 54,
}
ITEM_OPERATE_RES_PROBE_PC_SHA256 = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": (
        "DF40B49DC179DB07A006FC4989273D6F97529DAE6FF7D0DE692815435A1CD2F9"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": (
        "CA0367388B08FEFAC085035C63C06FB3FC8B9209A6B7DC6A125E585373F9797C"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": (
        "2D6928A8503F3CFC6BB0A300709BEAD52F532541A1117EE21E36FD5C7FA80529"
    ),
}
ITEM_OPERATE_RES_PROBE_PC_SIZE = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": CAPTURE_PC_LEN,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": 71,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": 71,
}
ITEM_OPERATE_RES_PROBE_FRAME_SHA256 = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": (
        "45C38CB7331EAF0EA8A06191DEFBD039733FB3EAD88E6142C08AEB1F6ACFE10E"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": (
        "7369D96011D362B641FCB91E3A16B407C4E5EE80976A9482E835396D11CC6DCE"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": (
        "7DB4971018AA00E120919D561ED4E20ED305619E7B439A685AD2B1E6C9840FFB"
    ),
}
ITEM_OPERATE_RES_PROBE_FRAME_SIZE = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": 82,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": 82,
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": 82,
}


# ---------------------------------------------------------------- self-guards
def _require_step_plan() -> None:
    """The pinned plan must keep asking the questions it was built to ask."""
    if len(set(ITEM_OPERATE_RES_STEP_ORDER)) != len(ITEM_OPERATE_RES_STEP_ORDER):
        raise RuntimeError("HYP-PF-037 duplicate step label")
    if len(ITEM_OPERATE_RES_STEP_ORDER) != 3:
        raise RuntimeError(
            "HYP-PF-037 the sweep must keep exactly the three designed steps"
        )
    for label in ITEM_OPERATE_RES_STEP_ORDER:
        if type(ITEM_OPERATE_RES_STEP_ITEMS[label]) is not ItemAttrState:
            raise RuntimeError("HYP-PF-037 step plan item type drift")
    if ITEM_OPERATE_RES_STEP_ITEMS["ITEMOP_RES_CTRL_CAPTURE_REPLAY"] != (
        ItemAttrState(1, 2600001, 2, 2)
    ):
        raise RuntimeError(
            "HYP-PF-037 the control step must stay the captured V111 golden "
            "item"
        )
    for label, quantity in (
        ("ITEMOP_RES_BAGUPD_ID2400901_QTY1", 1),
        ("ITEMOP_RES_BAGUPD_ID2400901_QTY5", 5),
    ):
        if ITEM_OPERATE_RES_STEP_ITEMS[label] != ItemAttrState(
            2, ITEM_OPERATE_RES_PROBE_ITEM_ID, quantity, 1,
        ):
            raise RuntimeError(
                "HYP-PF-037 the probe steps must stay the RE-060 consumable "
                "at quantity 1 and 5"
            )


# ---------------------------------------------------------------- decoder
def decode_item_operate_res_message(message: Any) -> ItemOperateResMessage:
    """Read one 0x4C13 message layer back, strictly, or refuse by name.

    The accepted grammar is EXACTLY the capture-validated read order RE-059
    walked (wrapper tag, opcode, u8-tagged version, u8 R4, u8 bag_present,
    the ItemBagAttr with base mask 0xFF / identity 0, tagged update items,
    tagged removal identities, then the u8 affected_identity_count) --
    narrowed on every fixed field to the values this lane emits: version 2,
    R4 0, bag present, the accepted bag base, removal count 0 and affected
    count 0.  The update-item collection is decoded as tagged, so a
    multi-item bag decodes structurally; the composer separately re-checks
    that each composed message carries exactly its one declared plan item.
    Anything else refuses with a named reason and no partial result.
    """
    if type(message) is not bytes and type(message) is not bytearray:
        raise ValueError("item operate res rejected: truncated_message")
    message = bytes(message)

    def _need(count: int) -> None:
        if len(message) - cursor[0] < count:
            raise ValueError("item operate res rejected: truncated_message")

    cursor = [0]

    def _u8(tag: int, wrong: str) -> int:
        _need(2)
        if message[cursor[0]] != tag:
            raise ValueError("item operate res rejected: " + wrong)
        value = message[cursor[0] + 1]
        cursor[0] += 2
        return value

    def _u16(tag: int, wrong: str) -> int:
        _need(3)
        if message[cursor[0]] != tag:
            raise ValueError("item operate res rejected: " + wrong)
        value = int.from_bytes(message[cursor[0] + 1:cursor[0] + 3], "little")
        cursor[0] += 3
        return value

    def _u32(tag: int, wrong: str) -> int:
        _need(5)
        if message[cursor[0]] != tag:
            raise ValueError("item operate res rejected: " + wrong)
        value = int.from_bytes(message[cursor[0] + 1:cursor[0] + 5], "little")
        cursor[0] += 5
        return value

    def _u64(tag: int, wrong: str) -> int:
        _need(9)
        if message[cursor[0]] != tag:
            raise ValueError("item operate res rejected: " + wrong)
        value = int.from_bytes(message[cursor[0] + 1:cursor[0] + 9], "little")
        cursor[0] += 9
        return value

    _need(3)
    if message[0] != 0x12:
        raise ValueError("item operate res rejected: wrong_wrapper_tag")
    if int.from_bytes(message[1:3], "little") != ITEM_OPERATE_RES_VITAL_ID:
        raise ValueError("item operate res rejected: wrong_vital_id")
    cursor[0] = 3
    version = _u8(0x0B, "wrong_version_tag")
    if version != ITEM_OPERATE_RES_VITAL_VERSION:
        raise ValueError("item operate res rejected: unimplemented_version")
    r4 = _u8(0x08, "wrong_r4_tag")
    if r4 != 0:
        raise ValueError("item operate res rejected: unimplemented_r4")
    bag_present = _u8(0x0B, "wrong_bag_present_tag")
    if bag_present != 1:
        raise ValueError("item operate res rejected: unimplemented_bag_present")
    bag_mask = _u8(0x0B, "wrong_bag_mask_tag")
    bag_identity = _u64(0x32, "wrong_bag_identity_tag")
    if bag_mask != 0xFF or bag_identity != 0:
        raise ValueError("item operate res rejected: unimplemented_bag_base")
    update_count = _u16(0x0F, "wrong_update_count_tag")
    items = []
    for _index in range(update_count):
        identity = _u64(0x32, "wrong_item_identity_tag")
        template_id = _u32(0x14, "wrong_item_template_tag")
        quantity = _u16(0x0F, "wrong_item_quantity_tag")
        slot = _u16(0x0F, "wrong_item_slot_tag")
        raw38 = _u8(0x08, "wrong_item_raw38_tag")
        raw39 = _u8(0x08, "wrong_item_raw39_tag")
        detail = _u8(0x0B, "wrong_item_detail_tag")
        items.append(ItemAttrState(
            identity, template_id, quantity, slot, raw38, raw39, detail,
        ))
    removal_count = _u16(0x0F, "wrong_removal_count_tag")
    if removal_count != 0:
        # The golden move-delta shape this lane emits never removes; the
        # merge shape that does is not part of this sweep.
        raise ValueError("item operate res rejected: unimplemented_removal_count")
    affected = _u8(0x08, "wrong_affected_count_tag")
    if affected != 0:
        # DELIBERATE: count>0 element shape is statically OPEN (R13
        # membership unresolved) -- see the module docstring and RE-064.
        raise ValueError("item operate res rejected: unimplemented_affected_count")
    if cursor[0] != len(message):
        raise ValueError(
            "item operate res rejected: trailing_bytes_after_affected_count"
        )
    return ItemOperateResMessage(
        version, r4, bag_mask, bag_identity, tuple(items), removal_count,
        affected,
    )


# ---------------------------------------------------------------- composition
# PF-HYPOTHESIS-LEDGER: HYP-PF-037 active
def make_item_operate_res_step_response(
    legacy: Any, step_index: int,
) -> tuple[bytes, bytes]:
    """Compose one numbered frame of the pinned sweep, then drift-check pins.

    The composition takes NO per-session input -- the step plan is entirely
    module-frozen -- so every sweep frame is pinned absolutely: message, pc
    and frame hash and size must all match the committed values or the
    composition refuses rather than letting drift reach a socket.  The
    control step is additionally compared byte for byte against the
    committed RE-059 capture hex, which simultaneously re-proves the dual
    derivation (capture bytes == golden codec output) on every call.
    """
    _require_step_plan()
    if type(step_index) is not int or type(step_index) is bool:
        raise ValueError("item operate res rejected: unknown_step_label")
    if step_index < 0 or step_index >= len(ITEM_OPERATE_RES_STEP_ORDER):
        raise ValueError("item operate res rejected: unknown_step_label")
    label = ITEM_OPERATE_RES_STEP_ORDER[step_index]
    item = ITEM_OPERATE_RES_STEP_ITEMS[label]
    pc, frame = make_item_move_delta_response(legacy, item)
    offset = ITEM_OPERATE_RES_PC_MESSAGE_OFFSET
    message = pc[offset:len(pc) - ITEM_OPERATE_RES_PC_TAIL_SIZE]
    if pc[ITEM_OPERATE_RES_PC_VITAL_ID_SLICE] != (
        ITEM_OPERATE_RES_VITAL_ID.to_bytes(2, "little")
    ):
        raise RuntimeError("HYP-PF-037 composed PC vital id drift")
    if pc[ITEM_OPERATE_RES_PC_VERSION_OFFSET] != (
        ITEM_OPERATE_RES_VITAL_VERSION
    ):
        raise RuntimeError("HYP-PF-037 composed PC version drift")
    if label == "ITEMOP_RES_CTRL_CAPTURE_REPLAY":
        if message != bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX):
            raise RuntimeError(
                "HYP-PF-037 control step drifted from the committed RE-059 "
                "capture bytes"
            )
    decoded = decode_item_operate_res_message(message)
    if decoded.items != (item,):
        raise RuntimeError("HYP-PF-037 composed message does not re-decode")
    if len(message) != ITEM_OPERATE_RES_PROBE_MESSAGE_SIZE[label]:
        raise RuntimeError("HYP-PF-037 composed message size pin drift")
    if hashlib.sha256(message).hexdigest().upper() != (
        ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-037 composed message drift")
    if len(pc) != ITEM_OPERATE_RES_PROBE_PC_SIZE[label]:
        raise RuntimeError("HYP-PF-037 composed PC size pin drift")
    if hashlib.sha256(pc).hexdigest().upper() != (
        ITEM_OPERATE_RES_PROBE_PC_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-037 composed PC drift")
    if len(frame) != ITEM_OPERATE_RES_PROBE_FRAME_SIZE[label]:
        raise RuntimeError("HYP-PF-037 composed frame size pin drift")
    if hashlib.sha256(frame).hexdigest().upper() != (
        ITEM_OPERATE_RES_PROBE_FRAME_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-037 composed frame drift")
    return pc, frame


# ---------------------------------------------------------------- scenario gate
_PROFILE_GREENLINE_SWEEP = ItemOperateResHypothesisScenario(
    ITEM_OPERATE_RES_SCENARIO_ID,
    ITEM_OPERATE_RES_HYPOTHESIS_ID,
    ITEM_OPERATE_RES_STEP_ORDER,
    ITEM_OPERATE_RES_SPACING_SECONDS,
)


def _item_schema(item: ItemAttrState) -> dict[str, int]:
    return {
        "identity": item.identity,
        "template_id": item.template_id,
        "quantity": item.quantity,
        "slot": item.slot,
        "raw_u8_38": item.raw_u8_38,
        "raw_u8_39": item.raw_u8_39,
        "detail_present": item.detail_present,
    }


def _expected_sweep() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": ITEM_OPERATE_RES_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": ITEM_OPERATE_RES_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_pinned_item_operate_res_greenline_sweep_"
                "no_write_no_close"
            ),
        },
        "dispatch": {
            "trigger": "accepted_chat_input_frame_exact_ascii12_shape",
            "trigger_classifier": "classify_chat_input_attempt",
            "frames_per_accepted_request": len(ITEM_OPERATE_RES_STEP_ORDER),
            "step_order": list(ITEM_OPERATE_RES_STEP_ORDER),
            "step_items": {
                label: _item_schema(ITEM_OPERATE_RES_STEP_ITEMS[label])
                for label in ITEM_OPERATE_RES_STEP_ORDER
            },
            "identity_policy": "refuse_unless_selected_is_the_pinned_probe",
            "probe_identity_lo": ITEM_OPERATE_RES_PROBE_IDENTITY_LO,
            "probe_identity_hi": ITEM_OPERATE_RES_PROBE_IDENTITY_HI,
            "spacing_seconds": ITEM_OPERATE_RES_SPACING_SECONDS,
            "first_frame_delay_seconds": ITEM_OPERATE_RES_FIRST_DELAY_SECONDS,
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": ITEM_OPERATE_RES_ACTION_LABEL_PREFIX,
            "action_labels": [
                ITEM_OPERATE_RES_ACTION_LABEL_PREFIX + label
                for label in ITEM_OPERATE_RES_STEP_ORDER
            ],
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": ITEM_OPERATE_RES_VITAL_ID,
            "vital_version": ITEM_OPERATE_RES_VITAL_VERSION,
            "vital_version_provenance": (
                "capture_pinned_all_five_re059_frames_carry_2"
            ),
            "envelope": "gscn_runtime_protocol_res_v4_one_vital_collection",
            "codec": (
                "inventory_make_item_move_delta_response_the_v111_accepted_"
                "golden"
            ),
            "affected_identity_count_policy": (
                "always_zero_the_only_captured_value_count_gt_zero_is_"
                "statically_open_re064"
            ),
            "provenance": {
                "greenline_ticket": "GT-049",
                "greenline_letter": (
                    "pf_bridge/notes_to_chief/20260824_0923_GT049-RESULT-"
                    "ID131-INBOUND-ITEMOPERATE.md"
                ),
                "handler_va": "0x005EF5E0",
                "emitter_va": "0x005CC309",
                "message_id": GREENLINE_MESSAGE_ID,
                "frames_ticket": "RE-059",
                "frames_letter": (
                    "pf_bridge/notes_to_chief/20260824_1413_RE-059-RESULT-"
                    "EXTRACTED-5-OF-5.md"
                ),
                "capture_frame1_message_sha256": (
                    CAPTURE_FRAME1_MESSAGE_SHA256
                ),
                "item_scheme_ticket": "RE-060",
                "item_scheme_letter": (
                    "pf_bridge/notes_to_chief/20260824_1422_RE-060-RESULT-"
                    "PINNED-5-CODES.md"
                ),
            },
        },
        "probe": {
            "per_step": {
                label: {
                    "message_size": ITEM_OPERATE_RES_PROBE_MESSAGE_SIZE[label],
                    "message_sha256": (
                        ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256[label]
                    ),
                    "pc_size": ITEM_OPERATE_RES_PROBE_PC_SIZE[label],
                    "pc_sha256": ITEM_OPERATE_RES_PROBE_PC_SHA256[label],
                    "frame_size": ITEM_OPERATE_RES_PROBE_FRAME_SIZE[label],
                    "frame_sha256": ITEM_OPERATE_RES_PROBE_FRAME_SHA256[label],
                }
                for label in ITEM_OPERATE_RES_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "replay_the_re059_captured_frame_1_byte_exact_at_message_layer",
            "emit_the_proven_bag_update_shape_for_the_re060_consumable",
            "probe_the_quantity_channel_of_message_id_131",
            "decode_every_composed_message_back_to_its_declared_item",
            "repeatable_sweep_per_session_no_state_change",
        ],
        "nonclaims": [
            "anything_about_what_the_screen_shows",
            "any_new_field_semantics_beyond_the_golden_codec",
            "the_re060_item_scheme_which_is_candidate_not_wire_confirmed",
            "original_server_pickup_response_behavior_which_is_unrecoverable",
            "any_item_entering_the_bag_or_the_database",
            "byte_exactness_of_the_15_byte_envelope_prefix_not_committed",
            "any_affected_identity_count_gt_zero_shape_open_as_re064",
            "client_acceptance_or_rendering_pending_the_attended_gt_ticket",
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


def load_item_operate_res_hypothesis_scenario(
    path: str | Path,
) -> ItemOperateResHypothesisScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the frames
    the dispatcher emits come from the module's own frozen step plan.  A
    file that differs from the allowlisted body anywhere -- one extra key,
    one missing key, one int where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "invalid item operate res hypothesis scenario"
        ) from exc
    if type(data) is not dict or data.get("id") != ITEM_OPERATE_RES_SCENARIO_ID:
        raise ValueError(
            "item operate res hypothesis scenario exceeds the exact allowlist"
        )
    if not _exact_equal(data, _expected_sweep()):
        raise ValueError(
            "item operate res hypothesis scenario exceeds the exact allowlist"
        )
    return require_item_operate_res_hypothesis_scenario(
        _PROFILE_GREENLINE_SWEEP
    )


def require_item_operate_res_hypothesis_scenario(
    value: Any,
) -> ItemOperateResHypothesisScenario:
    if (
        type(value) is not ItemOperateResHypothesisScenario
        or value != _PROFILE_GREENLINE_SWEEP
    ):
        raise ValueError(
            "item operate res hypothesis scenario object exceeds the allowlist"
        )
    _require_step_plan()
    return value
