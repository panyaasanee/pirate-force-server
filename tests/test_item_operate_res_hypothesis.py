"""ITEMOP-RES-GREENLINE-001 (HYP-PF-037) -- the pinned ItemOperateVitalRes
0x4C13 sweep behind the one opt-in scenario.

What is being pinned here, in one paragraph: GT-049 proved the green chat
line (message id 131, ``received [ $V1 ] * $V2``) is emitted from the
client's INBOUND 0x4C13 handler, RE-059 extracted all five real captured
0x4C13 frames byte-exactly, and RE-060 pinned the item table id scheme.
This lane answers one accepted ascii12 chat trigger from the pinned smoke
identity with THREE frames through the V111-accepted golden codec: the
RE-059 frame-1 capture replay (dual-derived: committed capture hex ==
golden codec output, both compared at every composition), then the same
proven bag-update shape carrying consumable 2400901 at quantity 1 and at
quantity 5.  Which of them, if any, puts the green line on a real screen
is exactly the attended GT-063 question -- nothing here claims it.

NOT proven here, and this is the load-bearing limit: what any client shows
for any of these frames; which wire field feeds $V1/$V2; the RE-060 id
scheme beyond candidate evidence; and any affected_identity_count>0 shape,
which is statically OPEN (R13 membership, RE-064) and which the module
refuses to compose or decode on purpose.
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.inventory import (  # noqa: E402
    ItemAttrState,
    make_item_move_delta_response,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.item_operate_res_hypothesis import (  # noqa: E402
    CAPTURE_FRAME1_MESSAGE_HEX,
    CAPTURE_FRAME1_MESSAGE_SHA256,
    CAPTURE_FRAME1_MESSAGE_SIZE,
    CAPTURE_PC_LEN,
    ITEM_OPERATE_RES_ACTION_LABEL_PREFIX,
    ITEM_OPERATE_RES_FIRST_DELAY_SECONDS,
    ITEM_OPERATE_RES_HYPOTHESIS_ID,
    ITEM_OPERATE_RES_PC_MESSAGE_OFFSET,
    ITEM_OPERATE_RES_PC_TAIL_SIZE,
    ITEM_OPERATE_RES_PC_VERSION_OFFSET,
    ITEM_OPERATE_RES_PC_VITAL_ID_SLICE,
    ITEM_OPERATE_RES_PROBE_FRAME_SHA256,
    ITEM_OPERATE_RES_PROBE_FRAME_SIZE,
    ITEM_OPERATE_RES_PROBE_IDENTITY_HI,
    ITEM_OPERATE_RES_PROBE_IDENTITY_LO,
    ITEM_OPERATE_RES_PROBE_ITEM_ID,
    ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256,
    ITEM_OPERATE_RES_PROBE_MESSAGE_SIZE,
    ITEM_OPERATE_RES_PROBE_PC_SHA256,
    ITEM_OPERATE_RES_PROBE_PC_SIZE,
    ITEM_OPERATE_RES_REJECTIONS,
    ITEM_OPERATE_RES_SCENARIO_ID,
    ITEM_OPERATE_RES_SPACING_SECONDS,
    ITEM_OPERATE_RES_STEP_ITEMS,
    ITEM_OPERATE_RES_STEP_ORDER,
    ITEM_OPERATE_RES_VITAL_ID,
    ITEM_OPERATE_RES_VITAL_VERSION,
    decode_item_operate_res_message,
    load_item_operate_res_hypothesis_scenario,
    make_item_operate_res_step_response,
    require_item_operate_res_hypothesis_scenario,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "item_operate_res_greenline_sweep.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
SWEEP_EVENT = "item_operate_res_hypothesis_greenline_sweep_sent"
IDENTITY_EVENT = "item_operate_res_hypothesis_identity_not_pinned_no_reply"

# GOLDEN byte-exact pins for the three sweep steps, computed by running the
# composer once and frozen here as full hex.  The control PC's bytes 15..69
# ARE the committed RE-059 capture hex; a change to ANY byte of any frame
# must fail this file.
GOLDEN_PC_HEX = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": (
        "129D6E140000000008040B0212010012134C0B0208000B010BFF320000000000"
        "0000000F01003201000000000000001441AC27000F02000F0200080008FF0B00"
        "0F000008000B00"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": (
        "129D6E140000000008040B0212010012134C0B0208000B010BFF320000000000"
        "0000000F01003202000000000000001485A224000F01000F0100080008FF0B00"
        "0F000008000B00"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": (
        "129D6E140000000008040B0212010012134C0B0208000B010BFF320000000000"
        "0000000F01003202000000000000001485A224000F05000F0100080008FF0B00"
        "0F000008000B00"
    ),
}
GOLDEN_FRAME_HEX = {
    "ITEMOP_RES_CTRL_CAPTURE_REPLAY": (
        "AC3E255F4A00000047F046129D6E140000000008040B0212010012134C0B0208"
        "000B010BFF3200000000000000000F0100320100000000000000144"
        "1AC27000F02000F0200080008FF0B000F000008000B00"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY1": (
        "AC3E255F4A00000047F046129D6E140000000008040B0212010012134C0B0208"
        "000B010BFF3200000000000000000F0100320200000000000000148"
        "5A224000F01000F0100080008FF0B000F000008000B00"
    ),
    "ITEMOP_RES_BAGUPD_ID2400901_QTY5": (
        "AC3E255F4A00000047F046129D6E140000000008040B0212010012134C0B0208"
        "000B010BFF3200000000000000000F0100320200000000000000148"
        "5A224000F05000F0100080008FF0B000F000008000B00"
    ),
}


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)


def _message_bytes(item: ItemAttrState) -> bytes:
    """The capture-validated 0x4C13 message layer, assembled independently
    of both the composer and the inventory codec."""
    item_wire = (
        b"\x32" + item.identity.to_bytes(8, "little")
        + b"\x14" + item.template_id.to_bytes(4, "little")
        + b"\x0F" + item.quantity.to_bytes(2, "little")
        + b"\x0F" + item.slot.to_bytes(2, "little")
        + b"\x08" + bytes([item.raw_u8_38])
        + b"\x08" + bytes([item.raw_u8_39])
        + b"\x0B" + bytes([item.detail_present])
    )
    bag = (
        b"\x0B\xFF"                      # bag base mask 0xFF
        + b"\x32" + (0).to_bytes(8, "little")  # bag base identity 0
        + b"\x0F\x01\x00"                # update count 1
        + item_wire
        + b"\x0F\x00\x00"                # removal count 0
    )
    return (
        b"\x12" + ITEM_OPERATE_RES_VITAL_ID.to_bytes(2, "little")
        + b"\x0B" + bytes([ITEM_OPERATE_RES_VITAL_VERSION])
        + b"\x08\x00"                    # R4 = 0
        + b"\x0B\x01"                    # bag_present_flag = 1
        + bag
        + b"\x08\x00"                    # affected_identity_count = 0
    )


def _step_message(pc: bytes) -> bytes:
    return pc[
        ITEM_OPERATE_RES_PC_MESSAGE_OFFSET:
        len(pc) - ITEM_OPERATE_RES_PC_TAIL_SIZE
    ]


class WireShapeTests(_LegacyCase):
    """The message layer against the capture and an independent assembly."""

    def test_the_control_message_is_the_committed_capture_hex(self):
        pc, _frame = make_item_operate_res_step_response(self.legacy, 0)
        message = _step_message(pc)
        self.assertEqual(message, bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        self.assertEqual(len(message), CAPTURE_FRAME1_MESSAGE_SIZE)
        self.assertEqual(
            hashlib.sha256(message).hexdigest().upper(),
            CAPTURE_FRAME1_MESSAGE_SHA256.upper(),
        )

    def test_the_dual_derivation_capture_equals_golden_codec(self):
        # THE control-frame fact this lane rests on: the committed RE-059
        # capture bytes and our V111-accepted golden codec agree byte for
        # byte, so the replay and the codec are one shape, not two.
        pc, frame = make_item_move_delta_response(
            self.legacy, ItemAttrState(1, 2600001, 2, 2),
        )
        control_pc, control_frame = make_item_operate_res_step_response(
            self.legacy, 0,
        )
        self.assertEqual(pc, control_pc)
        self.assertEqual(frame, control_frame)
        self.assertEqual(len(pc), CAPTURE_PC_LEN)

    def test_every_message_matches_an_independent_assembly(self):
        for index, label in enumerate(ITEM_OPERATE_RES_STEP_ORDER):
            pc, _frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            self.assertEqual(
                _step_message(pc),
                _message_bytes(ITEM_OPERATE_RES_STEP_ITEMS[label]),
                label,
            )

    def test_the_version_byte_is_the_capture_pinned_two(self):
        # Unlike the sweep lanes whose version byte is our design, this one
        # is CAPTURE-PINNED: all five RE-059 frames carry 2.
        self.assertEqual(ITEM_OPERATE_RES_VITAL_VERSION, 2)
        for index in range(len(ITEM_OPERATE_RES_STEP_ORDER)):
            pc, _frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            self.assertEqual(
                pc[ITEM_OPERATE_RES_PC_VERSION_OFFSET],
                ITEM_OPERATE_RES_VITAL_VERSION,
            )

    def test_the_probe_item_id_is_the_re060_consumable(self):
        self.assertEqual(ITEM_OPERATE_RES_PROBE_ITEM_ID, 2400901)
        self.assertEqual(ITEM_OPERATE_RES_PROBE_ITEM_ID // 100000, 24)
        self.assertEqual(ITEM_OPERATE_RES_PROBE_ITEM_ID % 100000, 901)
        for label, quantity in (
            ("ITEMOP_RES_BAGUPD_ID2400901_QTY1", 1),
            ("ITEMOP_RES_BAGUPD_ID2400901_QTY5", 5),
        ):
            item = ITEM_OPERATE_RES_STEP_ITEMS[label]
            self.assertEqual(item.template_id, ITEM_OPERATE_RES_PROBE_ITEM_ID)
            self.assertEqual(item.quantity, quantity)
            self.assertEqual((item.identity, item.slot), (2, 1))

    def test_composition_is_deterministic_and_repeatable(self):
        for index in range(len(ITEM_OPERATE_RES_STEP_ORDER)):
            first = make_item_operate_res_step_response(self.legacy, index)
            second = make_item_operate_res_step_response(self.legacy, index)
            self.assertEqual(first, second)


class RoundTripTests(_LegacyCase):
    def test_every_composed_message_decodes_to_its_declared_item(self):
        for index, label in enumerate(ITEM_OPERATE_RES_STEP_ORDER):
            pc, _frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            decoded = decode_item_operate_res_message(_step_message(pc))
            self.assertEqual(
                decoded.items, (ITEM_OPERATE_RES_STEP_ITEMS[label],), label,
            )
            self.assertEqual(decoded.version, 2)
            self.assertEqual(decoded.r4, 0)
            self.assertEqual(decoded.bag_base_mask, 0xFF)
            self.assertEqual(decoded.bag_base_identity, 0)
            self.assertEqual(decoded.removal_count, 0)
            self.assertEqual(decoded.affected_identity_count, 0)

    def test_decode_accepts_bytearray_input(self):
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        decoded = decode_item_operate_res_message(message)
        self.assertEqual(decoded.items, (ItemAttrState(1, 2600001, 2, 2),))


class FailClosedTests(_LegacyCase):
    def test_an_unknown_step_index_is_refused(self):
        for bad in (-1, 3, 99, True, False, None, "0", 0.0):
            with self.assertRaises(ValueError) as raised:
                make_item_operate_res_step_response(self.legacy, bad)
            self.assertIn("unknown_step_label", str(raised.exception))

    def test_non_bytes_messages_are_refused(self):
        for bad in (None, "12", 0x12, [0x12], object()):
            with self.assertRaises(ValueError) as raised:
                decode_item_operate_res_message(bad)
            self.assertIn("truncated_message", str(raised.exception))

    def test_truncations_are_refused_at_every_boundary(self):
        message = bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX)
        for cut in range(len(message)):
            with self.assertRaises(ValueError, msg=cut):
                decode_item_operate_res_message(message[:cut])

    def test_a_wrong_tag_at_any_tag_position_is_refused(self):
        message = bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX)
        # Every tag byte position in the 54-byte control message, derived
        # from the fixed layout: wrapper 0, version 3, R4 5, bag_present 7,
        # bag mask 9, bag identity 11, update count 20, item identity 23,
        # item template 32, item quantity 37, item slot 40, raw38 43,
        # raw39 45, detail 47, removal count 49, affected count 52.
        tag_positions = (0, 3, 5, 7, 9, 11, 20, 23, 32, 37, 40, 43, 45, 47,
                        49, 52)
        for position in tag_positions:
            tampered = bytearray(message)
            tampered[position] ^= 0xFF
            with self.assertRaises(ValueError, msg=position):
                decode_item_operate_res_message(bytes(tampered))

    def test_an_unimplemented_version_is_refused(self):
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        message[4] = 3
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(bytes(message))
        self.assertIn("unimplemented_version", str(raised.exception))

    def test_a_nonzero_affected_count_is_refused_on_purpose(self):
        # DELIBERATE: the count>0 element shape is statically OPEN (R13
        # membership unresolved, RE-064), so the decoder refuses it rather
        # than guessing where the element would end.
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        message[-1] = 1
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(bytes(message))
        self.assertIn("unimplemented_affected_count", str(raised.exception))

    def test_a_nonzero_removal_count_is_refused(self):
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        message[50] = 1                  # removal count u16 low byte
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(bytes(message))
        self.assertIn("unimplemented_removal_count", str(raised.exception))

    def test_a_foreign_bag_base_is_refused(self):
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        message[10] = 0x7F               # bag base mask
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(bytes(message))
        self.assertIn("unimplemented_bag_base", str(raised.exception))
        message = bytearray(bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX))
        message[12] = 1                  # bag base identity low byte
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(bytes(message))
        self.assertIn("unimplemented_bag_base", str(raised.exception))

    def test_the_rejection_tuple_matches_the_raise_sites_exactly(self):
        # The frozen rejection tuple must stay bound to the module's actual
        # named refusal reasons in BOTH directions: a renamed reason string
        # or a reason added without its tuple row fails here rather than
        # letting the tuple rot silently.
        source = (
            SRC_ROOT / "item_operate_res_hypothesis.py"
        ).read_text(encoding="utf-8")
        body = source.split('ITEM_OPERATE_RES_REJECTIONS = (', 1)[1]
        body = body.split(')', 1)[1]
        in_code = set(re.findall(
            r'"(?:item operate res rejected: )?'
            r'((?:wrong|unimplemented|truncated|trailing|unknown)'
            r'_[a-z0-9_]+)"',
            body,
        ))
        self.assertEqual(in_code, set(ITEM_OPERATE_RES_REJECTIONS))
        self.assertEqual(
            len(set(ITEM_OPERATE_RES_REJECTIONS)),
            len(ITEM_OPERATE_RES_REJECTIONS),
        )

    def test_trailing_bytes_are_refused(self):
        message = bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX) + b"\x00"
        with self.assertRaises(ValueError) as raised:
            decode_item_operate_res_message(message)
        self.assertIn(
            "trailing_bytes_after_affected_count", str(raised.exception),
        )


class ComposedResponseTests(_LegacyCase):
    def test_the_envelope_is_the_reused_v141_helper_not_a_new_one(self):
        for index in range(len(ITEM_OPERATE_RES_STEP_ORDER)):
            pc, frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            expected_pc, expected_frame = self.legacy.make_runtime_vitals([(
                ITEM_OPERATE_RES_VITAL_ID,
                ITEM_OPERATE_RES_VITAL_VERSION,
                _step_message(pc)[5:],
            )])
            self.assertEqual(pc, expected_pc)
            self.assertEqual(frame, expected_frame)

    def test_the_pc_carries_the_vital_id_at_the_fixed_offset(self):
        for index in range(len(ITEM_OPERATE_RES_STEP_ORDER)):
            pc, _frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            self.assertEqual(
                pc[ITEM_OPERATE_RES_PC_VITAL_ID_SLICE],
                ITEM_OPERATE_RES_VITAL_ID.to_bytes(2, "little"),
            )

    def test_every_step_matches_the_golden_full_hex_pins(self):
        for index, label in enumerate(ITEM_OPERATE_RES_STEP_ORDER):
            pc, frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            self.assertEqual(pc.hex().upper(), GOLDEN_PC_HEX[label], label)
            self.assertEqual(
                frame.hex().upper(), GOLDEN_FRAME_HEX[label], label,
            )

    def test_every_step_matches_the_module_pins(self):
        for index, label in enumerate(ITEM_OPERATE_RES_STEP_ORDER):
            pc, frame = make_item_operate_res_step_response(
                self.legacy, index,
            )
            message = _step_message(pc)
            self.assertEqual(
                len(message), ITEM_OPERATE_RES_PROBE_MESSAGE_SIZE[label],
            )
            self.assertEqual(
                hashlib.sha256(message).hexdigest().upper(),
                ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256[label].upper(),
            )
            self.assertEqual(len(pc), ITEM_OPERATE_RES_PROBE_PC_SIZE[label])
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                ITEM_OPERATE_RES_PROBE_PC_SHA256[label].upper(),
            )
            self.assertEqual(
                len(frame), ITEM_OPERATE_RES_PROBE_FRAME_SIZE[label],
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                ITEM_OPERATE_RES_PROBE_FRAME_SHA256[label].upper(),
            )

    def test_the_sweep_plan_keeps_its_designed_edges(self):
        self.assertEqual(len(ITEM_OPERATE_RES_STEP_ORDER), 3)
        self.assertEqual(
            ITEM_OPERATE_RES_STEP_ORDER[0], "ITEMOP_RES_CTRL_CAPTURE_REPLAY",
        )
        quantities = [
            ITEM_OPERATE_RES_STEP_ITEMS[label].quantity
            for label in ITEM_OPERATE_RES_STEP_ORDER[1:]
        ]
        self.assertEqual(quantities, [1, 5])


class ScenarioGateTests(unittest.TestCase):
    def test_scenario_loads_and_is_opt_in_test_only(self):
        scenario = load_item_operate_res_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(scenario.id, ITEM_OPERATE_RES_SCENARIO_ID)
        self.assertEqual(
            scenario.hypothesis_id, ITEM_OPERATE_RES_HYPOTHESIS_ID,
        )
        self.assertEqual(scenario.step_order, ITEM_OPERATE_RES_STEP_ORDER)
        self.assertEqual(
            scenario.spacing_seconds, ITEM_OPERATE_RES_SPACING_SECONDS,
        )
        raw = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(raw["test_only"], True)
        self.assertIs(raw["production_allowed"], False)

    def test_the_scenario_pins_agree_with_the_module_pins(self):
        raw = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        per_step = raw["probe"]["per_step"]
        self.assertEqual(set(per_step), set(ITEM_OPERATE_RES_STEP_ORDER))
        for label in ITEM_OPERATE_RES_STEP_ORDER:
            self.assertEqual(
                per_step[label]["message_sha256"],
                ITEM_OPERATE_RES_PROBE_MESSAGE_SHA256[label],
            )
            self.assertEqual(
                per_step[label]["pc_sha256"],
                ITEM_OPERATE_RES_PROBE_PC_SHA256[label],
            )
            self.assertEqual(
                per_step[label]["frame_sha256"],
                ITEM_OPERATE_RES_PROBE_FRAME_SHA256[label],
            )
        self.assertEqual(
            raw["wire"]["provenance"]["capture_frame1_message_sha256"],
            CAPTURE_FRAME1_MESSAGE_SHA256,
        )

    def test_the_scenario_allowlist_is_exact(self):
        raw = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.update(extra_key=1),
            lambda d: d.pop("nonclaims"),
            lambda d: d.update(production_allowed=True),
            lambda d: d.update(test_only=False),
            lambda d: d["dispatch"].update(one_shot=True),
            lambda d: d["dispatch"].update(spacing_seconds=0.5),
            lambda d: d["dispatch"]["step_order"].reverse(),
            lambda d: d["wire"].update(vital_version=0),
            lambda d: d["persisted_post_state"].update(
                database_write="sessions"
            ),
        ):
            data = json.loads(json.dumps(raw))
            mutate(data)
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False,
            ) as handle:
                json.dump(data, handle)
                path = handle.name
            try:
                with self.assertRaises(ValueError):
                    load_item_operate_res_hypothesis_scenario(path)
            finally:
                Path(path).unlink()

    def test_unrelated_scenario_files_never_load_through_this_gate(self):
        for name in (
            "skill_attr_hypothesis_attr_sweep.json",
            "pickup_listener_hypothesis_decode_probe.json",
        ):
            with self.assertRaises(ValueError):
                load_item_operate_res_hypothesis_scenario(
                    ROOT / "scenarios" / name,
                )

    def test_a_lookalike_scenario_object_is_refused(self):
        scenario = load_item_operate_res_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(),
            None,
            replace(scenario, spacing_seconds=0.25),
            replace(scenario, step_order=ITEM_OPERATE_RES_STEP_ORDER[:1]),
            replace(scenario, hypothesis_id="HYP-PF-035"),
        ):
            with self.assertRaises(ValueError):
                require_item_operate_res_hypothesis_scenario(bad)

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        module = "item_operate_res_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name,
            )
        self.assertNotIn(
            module, LEGACY_PATH.read_text(encoding="utf-8"),
        )

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if item_operate_res_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "item_operate_res_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID",
            source,
        )
        # The composer is reached from exactly one call site (the import
        # line is the other mention).
        self.assertEqual(
            source.count("make_item_operate_res_step_response"), 2,
        )
        self.assertEqual(
            source.count("make_item_operate_res_step_response("), 1,
        )
        self.assertEqual(
            source.count("_dispatch_item_operate_res_hypothesis"), 2,
        )
        self.assertIn(
            "identity_lo != ITEM_OPERATE_RES_PROBE_IDENTITY_LO", source,
        )
        self.assertIn(
            "identity_hi != ITEM_OPERATE_RES_PROBE_IDENTITY_HI", source,
        )

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--item-operate-res-hypothesis-scenario", source)
        self.assertIn(
            "'--item-operate-res-hypothesis-scenario requires an explicit '\n"
            "            'existing --db'",
            source,
        )

    def test_the_lane_is_registered_in_the_hypothesis_ledger(self):
        raw = json.loads(
            (ROOT / "docs" / "HYPOTHESIS_LEDGER.json").read_text(
                encoding="utf-8",
            )
        )
        for entry in raw["entries"]:
            if entry["id"] != ITEM_OPERATE_RES_HYPOTHESIS_ID:
                continue
            self.assertEqual(entry["status"], "active")
            self.assertIs(entry["production_allowed"], False)
            self.assertEqual(
                entry["introduced_checkpoint"], "ITEMOP-RES-GREENLINE-001",
            )
            self.assertIn("GT-049", entry["provenance"])
            self.assertIn("RE-059", entry["provenance"])
            self.assertIn("RE-060", entry["provenance"])
            self.assertIn("RE-064", entry["provenance"])
            return
        self.fail(
            "HYP-PF-037 is not registered in docs/HYPOTHESIS_LEDGER.json"
        )

    def test_the_coverage_row_stays_in_progress_not_runtime_pass(self):
        raw = json.loads(
            (ROOT / "docs" / "FUNCTIONAL_COVERAGE.json").read_text(
                encoding="utf-8",
            )
        )
        for domain in raw["domains"]:
            for cap in domain["capabilities"]:
                if cap["id"] != "system_message_display":
                    continue
                self.assertEqual(cap["status"], "in_progress")
                self.assertIn(
                    "tests/test_item_operate_res_hypothesis.py",
                    cap["test_refs"],
                )
                self.assertIn(
                    "scenarios/item_operate_res_greenline_sweep.json",
                    cap["evidence_refs"],
                )
                return
        self.fail(
            "presentation/system_message_display row is missing from the "
            "coverage matrix"
        )


class DispatchTests(unittest.TestCase):
    """The runtime wire hookup, on the REAL make_state_class path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_item_operate_res_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, sweep=True, extra_lanes=None):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_operate_res_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
            **(extra_lanes or {}),
        )

    def _state(self, login, *, sweep=True, ready=True, extra_lanes=None):
        state = self._state_type(sweep=sweep, extra_lanes=extra_lanes)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _unpin_identity(self, state, *, lo=None, hi=None):
        """Swap the selected character for one whose identity is NOT the
        pinned probe; the dispatcher reads only identity_lo/identity_hi."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        replaced = dataclasses.replace(
            selected,
            identity_lo=selected.identity_lo if lo is None else lo,
            identity_hi=selected.identity_hi if hi is None else hi,
        )
        state.foundation.selected = replaced
        return selected, replaced

    def _trigger_pc(self, payload, *, outer_id=None, outer_version=0,
                    nested_version=0):
        legacy = self.legacy
        outer = legacy.GSCN_RUNTIME_PROTOCOL_REQ if outer_id is None else outer_id
        return bytes(
            legacy.u16tag(0x12, outer)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    # ----- happy path ------------------------------------------------------

    def test_the_created_smoke_character_is_the_pinned_probe_identity(self):
        state = self._state("itemopres-id")
        selected = state.foundation.selected
        self.assertEqual(
            selected.identity_lo, ITEM_OPERATE_RES_PROBE_IDENTITY_LO,
        )
        self.assertEqual(
            selected.identity_hi, ITEM_OPERATE_RES_PROBE_IDENTITY_HI,
        )

    def test_one_request_sweeps_the_three_steps_in_the_pinned_order(self):
        state = self._state("itemopres01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 3)
        self.assertEqual(
            [action[0] for action in actions],
            [
                ITEM_OPERATE_RES_ACTION_LABEL_PREFIX + label
                for label in ITEM_OPERATE_RES_STEP_ORDER
            ],
        )
        self.assertEqual(
            [action[0] for action in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "HYP_PF_037_ITEMOP_RES_CTRL_CAPTURE_REPLAY",
                "HYP_PF_037_ITEMOP_RES_BAGUPD_ID2400901_QTY1",
                "HYP_PF_037_ITEMOP_RES_BAGUPD_ID2400901_QTY5",
            ],
        )
        self.assertEqual(state.item_operate_res_sweep_count, 1)
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_every_dispatched_frame_is_a_0x4C13_vital(self):
        state = self._state("itemopres-ids")
        actions = state.dispatch(self._trigger())
        for label, action in zip(ITEM_OPERATE_RES_STEP_ORDER, actions):
            pc = action[1]
            self.assertEqual(
                pc[ITEM_OPERATE_RES_PC_VITAL_ID_SLICE],
                ITEM_OPERATE_RES_VITAL_ID.to_bytes(2, "little"), label,
            )
        self.assertEqual(
            self.pinned["wire"]["vital_id"], ITEM_OPERATE_RES_VITAL_ID,
        )

    def test_every_dispatched_frame_matches_its_golden_hex(self):
        state = self._state("itemopres-golden")
        actions = state.dispatch(self._trigger())
        for label, action in zip(ITEM_OPERATE_RES_STEP_ORDER, actions):
            self.assertEqual(
                action[1].hex().upper(), GOLDEN_PC_HEX[label], label,
            )
            self.assertEqual(
                action[2].hex().upper(), GOLDEN_FRAME_HEX[label], label,
            )

    def test_every_dispatched_frame_matches_its_scenario_pin(self):
        state = self._state("itemopres-pins")
        actions = state.dispatch(self._trigger())
        per_step = self.pinned["probe"]["per_step"]
        for label, action in zip(ITEM_OPERATE_RES_STEP_ORDER, actions):
            self.assertEqual(
                hashlib.sha256(action[1]).hexdigest().upper(),
                per_step[label]["pc_sha256"].upper(), label,
            )
            self.assertEqual(
                hashlib.sha256(action[2]).hexdigest().upper(),
                per_step[label]["frame_sha256"].upper(), label,
            )

    def test_the_dispatched_messages_decode_to_the_declared_plan(self):
        # THE claim of this milestone, checked on dispatched bytes: the
        # capture-validated 0x4C13 shape leaves the server carrying exactly
        # the declared plan item, and the control message IS the committed
        # capture hex.
        state = self._state("itemopres-decode")
        actions = state.dispatch(self._trigger())
        for label, action in zip(ITEM_OPERATE_RES_STEP_ORDER, actions):
            message = _step_message(action[1])
            decoded = decode_item_operate_res_message(message)
            self.assertEqual(
                decoded.items, (ITEM_OPERATE_RES_STEP_ITEMS[label],), label,
            )
        self.assertEqual(
            _step_message(actions[0][1]),
            bytes.fromhex(CAPTURE_FRAME1_MESSAGE_HEX),
        )

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("itemopres-spacing")
        actions = state.dispatch(self._trigger())
        delays = [action[3] for action in actions]
        self.assertEqual(
            delays,
            [
                ITEM_OPERATE_RES_FIRST_DELAY_SECONDS,
                ITEM_OPERATE_RES_SPACING_SECONDS,
                ITEM_OPERATE_RES_SPACING_SECONDS,
            ],
        )
        self.assertEqual(
            delays[0], self.pinned["dispatch"]["first_frame_delay_seconds"],
        )
        self.assertEqual(
            delays[1], self.pinned["dispatch"]["spacing_seconds"],
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two different accepted chat payloads must produce byte-identical
        # sweeps: nothing from the request reaches the wire.
        state = self._state("itemopres-trigger")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe2"))
        self.assertEqual(first, second)
        self.assertEqual(state.item_operate_res_sweep_count, 2)

    # ----- repeatability ---------------------------------------------------

    def test_two_requests_give_six_frames_with_no_accumulated_state(self):
        state = self._state("itemopres-repeat")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe1"))
        self.assertEqual([len(first), len(second)], [3, 3])
        self.assertEqual(first, second)
        self.assertEqual(state.item_operate_res_sweep_count, 2)
        self.assertEqual(state.events.count(SWEEP_EVENT), 2)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("itemopres-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._trigger("probe1"))
        state.dispatch(self._trigger("probe2"))
        state.dispatch(self._trigger("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.item_operate_res_sweep_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("itemopres-nowrite-refused")
        before = self.db_path.read_bytes()
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], bytes([base[0] ^ 0x01]) + base[1:]):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.item_operate_res_sweep_count, 0)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.item_operate_res_sweep_count, 0)

    def test_wrong_length_fails_closed(self):
        state = self._state("itemopres-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00", b"", base[:5]):
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "item_operate_res_hypothesis_wrong_length_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "item_operate_res_hypothesis_wrong_length_no_reply"
            ),
            4,
        )

    def test_wrong_prefix_fails_closed(self):
        state = self._state("itemopres-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        self._assert_silent(
            state, self.legacy.parse_outer(self._trigger_pc(tampered)),
            "item_operate_res_hypothesis_wrong_prefix_no_reply",
        )

    def test_wrong_envelope_fails_closed(self):
        state = self._state("itemopres-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._trigger_pc(payload, nested_version=1),
            self._trigger_pc(payload, outer_version=1),
            self._trigger_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self._assert_silent(
                state, self.legacy.parse_outer(pc),
                "item_operate_res_hypothesis_wrong_envelope_no_reply",
            )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("itemopres-seq", ready=False)
        self._assert_silent(
            state, self._trigger(),
            "item_operate_res_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("itemopres-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self._assert_silent(
            state, self._trigger(),
            "item_operate_res_hypothesis_no_selected_no_reply",
        )

    def test_a_non_probe_identity_low_half_fails_closed(self):
        state = self._state("itemopres-unpin-lo")
        _original, replaced = self._unpin_identity(
            state, lo=ITEM_OPERATE_RES_PROBE_IDENTITY_LO + 1,
        )
        self.assertNotEqual(
            replaced.identity_lo, ITEM_OPERATE_RES_PROBE_IDENTITY_LO,
        )
        self._assert_silent(state, self._trigger(), IDENTITY_EVENT)

    def test_a_nonzero_identity_hi_is_not_the_pinned_probe_either(self):
        state = self._state("itemopres-unpin-hi")
        self._unpin_identity(state, hi=1)
        self._assert_silent(state, self._trigger(), IDENTITY_EVENT)

    def test_the_identity_refusal_does_not_stop_a_later_pinned_sweep(self):
        state = self._state("itemopres-repin")
        original, _replaced = self._unpin_identity(
            state, lo=ITEM_OPERATE_RES_PROBE_IDENTITY_LO ^ 0x00ABCDEF,
        )
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.events.count(IDENTITY_EVENT), 1)
        self.assertEqual(state.item_operate_res_sweep_count, 0)
        state.foundation.selected = original
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 3)
        self.assertEqual(state.item_operate_res_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)

    def test_no_refusal_path_ever_emits_a_sweep_event(self):
        state = self._state("itemopres-refusals")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:-2],
            bytes([base[0] ^ 0x01]) + base[1:],
            base[:10] + b"\x1f" + base[11:],
        ):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(state.events.count(SWEEP_EVENT), 0)
        for event in state.events:
            self.assertNotIn("sweep", event)

    # ----- containment -----------------------------------------------------

    def test_without_a_scenario_the_baseline_does_not_move(self):
        state = self._state("itemopres-off", sweep=False)
        rx_before = state.rx_frames
        events_before = list(state.events)
        before = self.db_path.read_bytes()
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_037")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.item_operate_res_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(
            [e for e in state.events[len(events_before):]
             if "item_operate_res" in e],
            [],
        )
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        from pirateforce_foundation.chat_input_hypothesis import (
            load_chat_input_hypothesis_scenario,
        )
        from pirateforce_foundation.pickup_listener_hypothesis import (
            load_pickup_listener_hypothesis_scenario,
        )
        from pirateforce_foundation.skill_attr_hypothesis import (
            load_skill_attr_hypothesis_scenario,
        )
        others = {
            "chat_input_hypothesis_scenario": load_chat_input_hypothesis_scenario(
                ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
            ),
            "skill_attr_hypothesis_scenario": (
                load_skill_attr_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "skill_attr_hypothesis_attr_sweep.json"
                )
            ),
            "pickup_listener_hypothesis_scenario": (
                load_pickup_listener_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "pickup_listener_hypothesis_decode_probe.json"
                )
            ),
        }
        for name, other in others.items():
            with self.subTest(mode=name):
                with self.assertRaises(ValueError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        item_operate_res_hypothesis_scenario=self.scenario,
                        **{name: other},
                    )
                self.assertIn("mutually exclusive", str(raised.exception))

    def test_the_lane_sits_only_in_the_allow_listed_triple(self):
        # SCENARIO-COMPOSE-001 amendment (owner ruling, Panya 2026-08-24
        # ~21:1x +07:00, chief cloud round R155): this lane joined the
        # allow-list EXACTLY ONCE, as the third member of the one allowed
        # triple beside the R153 pair.  No pair containing this lane is
        # allow-listed, so membership stays exact-set: the triple being
        # allowed does not loosen anything pairwise.
        from pirateforce_foundation.runtime import (
            COMPOSABLE_SCENARIO_LANE_SETS,
        )
        containing = [
            member for member in COMPOSABLE_SCENARIO_LANE_SETS
            if "item_operate_res_hypothesis_scenario" in member
        ]
        self.assertEqual(containing, [frozenset({
            "ground_loot_hypothesis_scenario",
            "pickup_listener_hypothesis_scenario",
            "item_operate_res_hypothesis_scenario",
        })])

    def test_a_sub_pair_of_the_triple_is_still_refused(self):
        # The triple ruling does NOT admit its sub-pairs: this lane with
        # only ONE of the other two members must refuse exactly like any
        # other off-list combination (the pickup half is already covered by
        # the every-other-mode sweep above; this is the ground-loot half).
        from pirateforce_foundation.ground_loot_hypothesis import (
            load_ground_loot_hypothesis_scenario,
        )
        with self.assertRaises(ValueError) as raised:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                item_operate_res_hypothesis_scenario=self.scenario,
                ground_loot_hypothesis_scenario=(
                    load_ground_loot_hypothesis_scenario(
                        ROOT / "scenarios"
                        / "ground_loot_hypothesis_bit08_render.json"
                    )
                ),
            )
        self.assertIn("mutually exclusive", str(raised.exception))

    def test_the_allow_listed_triple_composes_and_all_three_lanes_run(self):
        # The positive half of the R155 ruling: the triple boots, and each
        # lane's own observable still fires under its own name in the
        # composed session (the attribution discipline the ruling demands).
        from pirateforce_foundation.ground_loot_hypothesis import (
            load_ground_loot_hypothesis_scenario,
        )
        from pirateforce_foundation.pickup_listener_hypothesis import (
            PICKUP_LISTENER_PROBE_FIELDS,
            compose_pickup_listener_probe_pc,
            load_pickup_listener_hypothesis_scenario,
        )
        state = self._state("triple01", extra_lanes={
            "ground_loot_hypothesis_scenario": (
                load_ground_loot_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "ground_loot_hypothesis_bit08_render.json"
                )
            ),
            "pickup_listener_hypothesis_scenario": (
                load_pickup_listener_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "pickup_listener_hypothesis_decode_probe.json"
                )
            ),
        })
        # This lane: one accepted chat trigger still sweeps the three
        # pinned frames under the HYP-PF-037 labels.
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [action[0] for action in actions],
            [
                ITEM_OPERATE_RES_ACTION_LABEL_PREFIX + label
                for label in ITEM_OPERATE_RES_STEP_ORDER
            ],
        )
        self.assertEqual(state.item_operate_res_sweep_count, 1)
        # Listener lane: an accepted probe frame is decoded and counted
        # with no reply, exactly as it is alone.
        probe = self.legacy.parse_outer(compose_pickup_listener_probe_pc(
            self.legacy, PICKUP_LISTENER_PROBE_FIELDS["MID"],
        ))
        self.assertEqual(state.dispatch(probe), [])
        self.assertEqual(state.pickup_listener_accepted_count, 1)
        # Spawner lane: the first exact TargetPos still fires the one-shot
        # bit-0x08 pair in the same composed session.
        legacy = self.legacy
        position = state.foundation.selected.position
        target_pos = legacy.parse_outer(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + legacy.f32tag(position.x) + legacy.f32tag(position.y)
            + legacy.f32tag(position.z) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 1)
            + legacy.u8tag(0x0B, 0)
        )
        self.assertIs(state.ground_loot_pair_sent, False)
        labels = [action[0] for action in state.dispatch(target_pos)]
        self.assertIn("GROUND_LOOT_BIT08_RENDER_NEAR_ONCE", labels)
        self.assertIn("GROUND_LOOT_BIT08_RENDER_FAR_ONCE", labels)
        self.assertIs(state.ground_loot_pair_sent, True)

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for bad in (
            object(),
            replace(self.scenario, spacing_seconds=0.25),
            replace(self.scenario, step_order=ITEM_OPERATE_RES_STEP_ORDER[:1]),
            replace(self.scenario, hypothesis_id="HYP-PF-035"),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    item_operate_res_hypothesis_scenario=bad,
                )


if __name__ == "__main__":
    unittest.main()
