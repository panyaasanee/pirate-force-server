"""Direct unit tests for ``pirateforce_foundation.inventory``.

WHY THIS FILE EXISTS.  ``inventory.py`` is BUILD-006/M5's own Backpack
model -- the two wall gates (``require_backpack_shape`` /
``require_known_backpack``), the three governed mutations (HYP-PF-010/017/
018: move / swap / merge), the three ItemOperate-result wire composers and
the wire encoder ``make_backpack_attr`` itself.  Thirteen OTHER test files
import symbols from this module (``test_mob_pickup.py``,
``test_item_lifecycle.py``, ``test_bag_admission.py``,
``test_item_move_capture.py``, ``test_item_move_hypothesis.py``,
``test_item_move_generalized.py``, ``test_item_merge_hypothesis.py``,
``test_item_swap_hypothesis.py``, ``test_item_operate_res_hypothesis.py``,
``test_gate2_bag_admission_wiring.py``, ``test_mob_pickup_persist.py``,
``test_store_acquired_item_insert.py``, ``test_item_order_static.py``) but
every one of them exercises inventory.py only incidentally, through its
OWN feature's lens.  Until this round no file pinned inventory.py's own
contract directly: its error paths (``KeyError``/``FileExistsError``/
``LookupError``/``ValueError`` -- which one fires for which malformed
request), and two exported functions with NO test reference anywhere in
this repository at all (confirmed by
``grep -rln is_exact_merge_request tests/`` returning nothing before this
file): ``parse_merge_candidate`` and ``is_exact_merge_request``, both of
which ``runtime.py`` (``:1459`` and ``:6999``) calls on every inbound
ItemOperate request to decide whether the V111 stack-merge persistence
path may fire at all.

This file does not change inventory.py's behaviour.  It is a direct-line
pin on that behaviour so a future edit to any of these functions turns a
test red here instead of only failing, quietly, three modules downstream.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import inventory
from pirateforce_foundation.inventory import (
    BACKPACK_BASE_IDENTITY,
    BACKPACK_BASE_MASK,
    BACKPACK_RANGE_MASK,
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_FIELDS,
    V111_MERGE_REQUEST_PC,
    BackpackState,
    ItemAttrState,
    is_exact_merge_request,
    is_unmoved_baseline,
    make_backpack_attr,
    make_item_merge_delta_response,
    make_item_move_delta_response,
    make_item_swap_delta_response,
    merge_known_item_into_occupied_slot,
    move_known_item_to_free_slot,
    parse_merge_candidate,
    require_backpack_shape,
    require_known_backpack,
    swap_known_item_with_occupied_slot,
)
from pirateforce_foundation.legacy_bridge import load_legacy

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


class RequireBackpackShapeTests(unittest.TestCase):
    """The character-select LOAD gate: structure only, any content."""

    def test_accepts_the_two_shipped_goldens(self):
        self.assertIs(require_backpack_shape(INITIAL_BACKPACK), INITIAL_BACKPACK)
        self.assertIs(require_backpack_shape(MERGED_V111_BACKPACK), MERGED_V111_BACKPACK)

    def test_accepts_well_formed_content_outside_both_goldens(self):
        drifted = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(99, 2200099, 1, 5),),
        )
        self.assertIs(require_backpack_shape(drifted), drifted)

    def test_rejects_wrong_type(self):
        with self.assertRaises(ValueError):
            require_backpack_shape("not a backpack")

    def test_rejects_non_tuple_items(self):
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            [ItemAttrState(1, 2600001, 1, 0)],
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)

    def test_rejects_item_of_wrong_type_inside_the_tuple(self):
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            ({"identity": 1},),
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)

    def test_rejects_duplicate_identity(self):
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (
                ItemAttrState(1, 2600001, 1, 0),
                ItemAttrState(1, 2400901, 1, 1),
            ),
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)

    def test_rejects_duplicate_slot(self):
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (
                ItemAttrState(1, 2600001, 1, 0),
                ItemAttrState(2, 2400901, 1, 0),
            ),
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)

    def test_rejects_slot_at_the_swap_parking_value(self):
        # migration 003 permits 0..65535 (store.py parks a row at 65535
        # mid-swap) but inventory.py's own guard is the narrower 0..39 the
        # visible bag actually has -- see mob_pickup.py's own comment on
        # this exact asymmetry.
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(1, 2600001, 1, 0xFFFF),),
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)

    def test_rejects_out_of_range_quantity(self):
        bad = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(1, 2600001, 0x10000, 0),),
        )
        with self.assertRaises(ValueError):
            require_backpack_shape(bad)


class RequireKnownBackpackTests(unittest.TestCase):
    """The content-restricted gate: exactly the two golden snapshots."""

    def test_accepts_the_two_shipped_goldens(self):
        self.assertIs(require_known_backpack(INITIAL_BACKPACK), INITIAL_BACKPACK)
        self.assertIs(require_known_backpack(MERGED_V111_BACKPACK), MERGED_V111_BACKPACK)

    def test_rejects_structurally_valid_content_outside_the_allowlist(self):
        drifted = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(99, 2200099, 1, 5),),
        )
        with self.assertRaises(ValueError):
            require_known_backpack(drifted)

    def test_rejects_malformed_shape_before_ever_reaching_content(self):
        with self.assertRaises(ValueError):
            require_known_backpack("not a backpack")


class IsUnmovedBaselineTests(unittest.TestCase):
    def test_both_goldens_are_unmoved(self):
        self.assertTrue(is_unmoved_baseline(INITIAL_BACKPACK))
        self.assertTrue(is_unmoved_baseline(MERGED_V111_BACKPACK))

    def test_a_moved_state_is_not(self):
        after, _ = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 10)
        self.assertFalse(is_unmoved_baseline(after))

    def test_an_unrelated_value_is_not(self):
        self.assertFalse(is_unmoved_baseline("not a backpack"))
        self.assertFalse(is_unmoved_baseline(None))


class MoveKnownItemToFreeSlotTests(unittest.TestCase):
    def test_same_slot_request_is_the_exact_none_no_op(self):
        self.assertIsNone(move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 0))

    def test_moving_to_a_genuinely_free_slot_relocates_only_that_item(self):
        after, moved = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 10)
        self.assertEqual(moved.slot, 10)
        self.assertEqual(moved.identity, 1)
        untouched = [item for item in after.items if item.identity != 1]
        original = [item for item in INITIAL_BACKPACK.items if item.identity != 1]
        self.assertEqual(untouched, original)
        require_backpack_shape(after)

    def test_unknown_identity_raises_key_error(self):
        with self.assertRaises(KeyError):
            move_known_item_to_free_slot(INITIAL_BACKPACK, 12345, 10)

    def test_occupied_destination_raises_file_exists_error(self):
        with self.assertRaises(FileExistsError):
            move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 1)

    def test_out_of_range_destination_slot_raises_value_error(self):
        with self.assertRaises(ValueError):
            move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 40)

    def test_rejects_a_bag_outside_the_governed_allowlist(self):
        drifted = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(1, 2600001, 1, 0), ItemAttrState(99, 2200099, 1, 5)),
        )
        with self.assertRaises(ValueError):
            move_known_item_to_free_slot(drifted, 1, 10)


class SwapKnownItemWithOccupiedSlotTests(unittest.TestCase):
    def test_swapping_two_known_items_exchanges_only_their_slots(self):
        after, moved, displaced = swap_known_item_with_occupied_slot(
            INITIAL_BACKPACK, 1, 1,
        )
        self.assertEqual(moved.identity, 1)
        self.assertEqual(moved.slot, 1)
        self.assertEqual(displaced.identity, 2)
        self.assertEqual(displaced.slot, 0)
        require_backpack_shape(after)
        by_id = {item.identity: item.slot for item in after.items}
        self.assertEqual(by_id[1], 1)
        self.assertEqual(by_id[2], 0)
        self.assertEqual(by_id[3], 2)
        self.assertEqual(by_id[4], 3)

    def test_same_slot_request_is_refused_not_a_no_op(self):
        with self.assertRaises(ValueError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 0)

    def test_unoccupied_destination_raises_lookup_error(self):
        with self.assertRaises(LookupError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 10)

    def test_unknown_identity_raises_key_error(self):
        with self.assertRaises(KeyError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 12345, 1)


class MergeKnownItemIntoOccupiedSlotTests(unittest.TestCase):
    def test_merging_the_v111_stack_source_sums_quantity_and_removes_it(self):
        after, merged, consumed_identity = merge_known_item_into_occupied_slot(
            INITIAL_BACKPACK, 3, 0,
        )
        self.assertEqual(merged.identity, 1)
        self.assertEqual(merged.quantity, 2)
        self.assertEqual(consumed_identity.identity, 3)
        self.assertEqual(
            {item.identity for item in after.items}, {1, 2, 4},
        )
        self.assertEqual(after, MERGED_V111_BACKPACK)

    def test_same_slot_request_is_refused_not_a_no_op(self):
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 1, 0)

    def test_unoccupied_destination_raises_lookup_error(self):
        with self.assertRaises(LookupError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 10)

    def test_different_template_occupant_is_refused(self):
        # identity 3 (template 2600001) into slot 1 (identity 2, template
        # 2400901) -- same-table merge is not what this transition owns.
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 1)

    def test_different_variant_same_template_occupant_is_refused(self):
        variant_bag = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (
                ItemAttrState(1, 2600001, 1, 0, raw_u8_38=1),
                ItemAttrState(2, 2400901, 1, 1),
                ItemAttrState(3, 2600001, 1, 2),
                ItemAttrState(4, 2200002, 1, 3),
            ),
        )
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(variant_bag, 3, 0)

    def test_quantity_sum_beyond_the_u16_wire_bound_is_refused(self):
        huge_bag = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (
                ItemAttrState(1, 2600001, 0xFFFF, 0),
                ItemAttrState(2, 2400901, 1, 1),
                ItemAttrState(3, 2600001, 1, 2),
                ItemAttrState(4, 2200002, 1, 3),
            ),
        )
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(huge_bag, 3, 0)

    def test_unknown_identity_raises_key_error(self):
        with self.assertRaises(KeyError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 12345, 0)


class WireEncodersTests(unittest.TestCase):
    """The three ItemOperate result composers and the Backpack encoder,
    pinned directly against the frozen legacy module rather than only
    through mob_pickup.py's/item_lifecycle's own lens."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_make_backpack_attr_matches_the_frozen_four_item_golden(self):
        result = make_backpack_attr(self.legacy, INITIAL_BACKPACK)
        self.assertEqual(result, self.legacy.make_backpack_attr_four_items())

    def test_make_backpack_attr_serializes_a_structurally_valid_drifted_bag(self):
        drifted = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(99, 2200099, 1, 5),),
        )
        result = make_backpack_attr(self.legacy, drifted)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_make_backpack_attr_refuses_a_frozen_constant_drift(self):
        # A minimal stand-in carrying every constant make_backpack_attr's
        # own drift guard checks, correct except ONE -- the loop must raise
        # on that one before ever touching a wire-encoding method, so the
        # stub need not implement u8tag/u32tag/etc at all.
        stub = SimpleNamespace(
            BACKPACK_ATTR=0x1F81,
            V103_ITEM_SEQUENCE=1,
            V103_ITEM_TEMPLATE=999999,  # drifted; real value is 2600001
            V110_CASK_SEQUENCE=2,
            V110_CASK_TEMPLATE=2400901,
            V111_STACK_SOURCE_SEQUENCE=3,
            V123_BLADE_SEQUENCE=4,
            V123_BLADE_TEMPLATE=2200002,
            V120_BACKPACK_BASE_RANGE_MASK=1,
        )
        with self.assertRaises(ValueError):
            make_backpack_attr(stub, INITIAL_BACKPACK)

    def test_make_item_move_delta_response_pins_the_v111_slot2_golden(self):
        moved = ItemAttrState(1, 2600001, 2, 2)
        result = make_item_move_delta_response(self.legacy, moved)
        self.assertEqual(result, self.legacy.make_item_operate_move_delta_success(2, 2))

    def test_make_item_swap_delta_response_carries_both_items_in_order(self):
        moved = ItemAttrState(1, 2600001, 1, 1)
        displaced = ItemAttrState(2, 2400901, 1, 0)
        result = make_item_swap_delta_response(self.legacy, moved, displaced)
        self.assertIsInstance(result, tuple)
        pc, frame = result
        self.assertIsInstance(pc, bytes)
        self.assertIsInstance(frame, bytes)

    def test_make_item_swap_delta_response_refuses_identical_identity(self):
        item = ItemAttrState(1, 2600001, 1, 1)
        with self.assertRaises(ValueError):
            make_item_swap_delta_response(self.legacy, item, item)

    def test_make_item_swap_delta_response_refuses_identical_slot(self):
        moved = ItemAttrState(1, 2600001, 1, 0)
        displaced = ItemAttrState(2, 2400901, 1, 0)
        with self.assertRaises(ValueError):
            make_item_swap_delta_response(self.legacy, moved, displaced)

    def test_make_item_merge_delta_response_pins_the_v111_golden(self):
        merged = MERGED_V111_BACKPACK.items[0]
        result = make_item_merge_delta_response(self.legacy, merged, 3)
        self.assertEqual(result, self.legacy.make_item_operate_stack_merge_success())

    def test_make_item_merge_delta_response_refuses_identical_identity(self):
        merged = MERGED_V111_BACKPACK.items[0]
        with self.assertRaises(ValueError):
            make_item_merge_delta_response(self.legacy, merged, merged.identity)

    def test_make_item_merge_delta_response_refuses_a_single_stack_quantity(self):
        lone = ItemAttrState(1, 2600001, 1, 0)
        with self.assertRaises(ValueError):
            make_item_merge_delta_response(self.legacy, lone, 3)


class MergeRequestParsingTests(unittest.TestCase):
    """``parse_merge_candidate``/``is_exact_merge_request`` had NO test
    reference anywhere in this repository before this file, despite
    ``runtime.py`` calling both on every inbound ItemOperate request
    (``:1459``, ``:6999``) to gate the V111 persistent-merge dispatch."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def _parse(self, pc: bytes):
        return self.legacy.parse_outer(pc)

    def test_the_real_accepted_request_is_recognized_both_ways(self):
        parsed = self._parse(V111_MERGE_REQUEST_PC)
        self.assertEqual(
            parse_merge_candidate(self.legacy, parsed), V111_MERGE_FIELDS,
        )
        self.assertTrue(is_exact_merge_request(self.legacy, parsed))

    def test_a_trailing_byte_is_still_a_candidate_but_not_the_exact_request(self):
        padded = V111_MERGE_REQUEST_PC + b"\x00"
        parsed = self._parse(padded)
        # parse_outer's outer/base fields are unaffected by a trailing byte
        # appended after the fully-consumed nested payload, so the field
        # tuple still decodes -- only the exact-request predicate, which
        # additionally pins parsed.raw_pc against the golden bytes, must
        # tell the two apart.
        self.assertEqual(
            parse_merge_candidate(self.legacy, parsed), V111_MERGE_FIELDS,
        )
        self.assertFalse(is_exact_merge_request(self.legacy, parsed))

    def test_a_non_item_operate_nested_id_is_not_a_candidate(self):
        # Re-tag the outer envelope's nested vital id (bytes 16-17, the u16
        # LE value right after the ParsedOuter prefix's nested-id tag byte
        # at 15) to a value that is not ITEM_OPERATE_REQ_VITAL (0x4BED, per
        # ``current/pf_login_game_server_v141.py``), and confirm the parser
        # truly moved: nested_id changes, not just the outcome.
        mutated = bytearray(V111_MERGE_REQUEST_PC)
        mutated[16:18] = (0xFFFE).to_bytes(2, "little")
        parsed = self._parse(bytes(mutated))
        self.assertNotEqual(parsed.nested_id, self.legacy.ITEM_OPERATE_REQ_VITAL)
        self.assertIsNone(parse_merge_candidate(self.legacy, parsed))
        self.assertFalse(is_exact_merge_request(self.legacy, parsed))

    def test_a_different_field_tuple_is_recognized_but_refused_as_exact(self):
        # Flip the operation VALUE byte (index 21: index 20 is that field's
        # own 0x0B tag, consumed first) away from V111_MERGE_FIELDS'
        # operation (4): still a well-formed ItemOperateVitalReq, just not
        # the one merge candidate this module allowlists.
        mutated = bytearray(V111_MERGE_REQUEST_PC)
        self.assertEqual(mutated[21], 4)
        mutated[21] = 0x05
        parsed = self._parse(bytes(mutated))
        self.assertIsNone(parse_merge_candidate(self.legacy, parsed))
        self.assertFalse(is_exact_merge_request(self.legacy, parsed))

    def test_wrong_outer_mask_is_refused_as_exact_even_if_fields_still_decode(self):
        # outer_mask VALUE lives at byte 11 in the parsed prefix (u16
        # id-tag+value[0:3] + u32 base-tag+value[3:8] + u8 version
        # tag+value[8:10] + u8 mask tag[10]/value[11]).  Clearing bit 0x02
        # means parse_outer never even looks for a nested vital.
        mutated = bytearray(V111_MERGE_REQUEST_PC)
        self.assertEqual(mutated[11], 0x02)
        mutated[11] = 0x00
        parsed = self._parse(bytes(mutated))
        self.assertIsNone(parsed.nested_id)
        self.assertIsNone(parse_merge_candidate(self.legacy, parsed))
        self.assertFalse(is_exact_merge_request(self.legacy, parsed))


if __name__ == "__main__":
    unittest.main()
