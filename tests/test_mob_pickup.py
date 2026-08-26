"""LANE-B: the drop a monster left becomes a row in somebody's bag.

The load-bearing tests in this file are the four below; the rest are guards.

``test_a_full_bag_does_not_eat_the_drop`` is the one that matters most.  A
pickup is the only operation in this lane that can DESTROY something a player
owns, and it destroys it by refusing AFTER the row has left the ground.  The
module's whole ordering argument exists for this test.

``test_only_one_of_two_claims_on_one_key_wins`` pins the race.  The lane
resolves against a snapshot and takes through the cell, which is a
check-then-act shape -- it is safe only because mob_loot never reuses a key,
and this test is what says so out loud.

``test_the_delta_is_byte_equal_to_the_item_lanes_composer`` is the only reason
to believe these bytes are the right bytes: the item lane pinned that shape
against frozen V141, and this lane re-derives rather than importing a probe.

``test_the_governed_allowlist_is_the_wall_this_lane_stops_at`` pins the
BLOCKER as a test.  BUILD-006 asks for "relog and it is still there"; the
persisted bag is content-allowlisted by a lane this one does not own, and a
round that only wrote that in prose would be a round whose prose rots.
"""

import ast
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import inventory, mob_loot, mob_pickup
from pirateforce_foundation.inventory import (
    BACKPACK_BASE_IDENTITY,
    BACKPACK_BASE_MASK,
    INITIAL_BACKPACK,
    BackpackState,
    ItemAttrState,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_loot import DropLedger, DropLedgerCell, GroundDrop
from pirateforce_foundation.mob_pickup import (
    BAG_SLOT_COUNT,
    MAX_ITEM_IDENTITY,
    MOB_PICKUP_NONCLAIMS,
    MOB_PICKUP_REFUSAL_REASONS,
    NEW_ROW_DETAIL_PRESENT,
    NEW_ROW_RAW_U8_38,
    NEW_ROW_RAW_U8_39,
    PICKUP_RADIUS,
    BagRowWrite,
    MobPickupContractError,
    PickupClaim,
    PickupOutcome,
    bag_delta_pc,
    commit_pickup,
    first_free_slot,
    next_item_identity,
    pickup_report,
    pin_document,
    place_in_bag,
    production_allowed,
    require_bag_shape,
    resolve_claim,
    test_only,
    within_pickup_radius,
)


MODULE_PATH = ROOT / "src" / "pirateforce_foundation" / "mob_pickup.py"
PIN_PATH = ROOT / "scenarios" / "combat_pickup_001.json"

# The identities the sibling lanes' tests use, so one kill reads the same in
# three files: a roster monster, and a session-shaped player identity.
MOB = 0x201F
KILLER = 0x750059
STRANGER = 0x750060
ITEM = 2400046            # the roster's most common drop
KEY = mob_loot.DROP_KEY_BASE
EMPTY_BAG = BackpackState(BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())


def a_drop(key=KEY, item=ITEM, quantity=1, at=(10.0, 20.0, 30.0),
           mob=MOB, killer=KILLER):
    return GroundDrop(
        key, item, quantity,
        mob_loot.as_wire_float(at[0]), mob_loot.as_wire_float(at[1]),
        mob_loot.as_wire_float(at[2]), mob, killer,
    )


def a_cell(*drops):
    """A cell holding exactly these rows, with the keys marked as issued."""
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(DropLedger(tuple(drops), 1, issued, ()))


def a_claim(key=KEY, identity=KILLER, at=(10.0, 20.0, 30.0)):
    return PickupClaim(identity, at[0], at[1], at[2], key)


class MobPickupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.source = MODULE_PATH.read_text(encoding="utf-8")

    def _refusal(self, call, *args, **kwargs):
        with self.assertRaises(MobPickupContractError) as caught:
            call(*args, **kwargs)
        return caught.exception.args[0]

    # -- what kind of lane this is -----------------------------------------
    def test_the_lane_is_production_and_has_no_flag(self):
        """No flag machinery in the CODE.  Prose may name one; code may not."""
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        tree = ast.parse(self.source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        forbidden = ("scenario_id", "hypothesis_id", "unlock", "allowlisted")
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                for word in forbidden:
                    self.assertNotIn(
                        word, node.value,
                        "a production lane may not carry %r in a value" % word)
            if isinstance(node, ast.Name):
                for word in forbidden:
                    self.assertNotIn(word, node.id)
            if isinstance(node, ast.Attribute):
                for word in forbidden:
                    self.assertNotIn(word, node.attr)

    @staticmethod
    def _imported_names(source):
        """Collect import names, including the ``from . import X`` form.

        Inherited whole from tests/test_mob_loot.py, which learned each part
        of it from an adversarial pass that defeated the previous part: the
        relative-import blindness, and then string arithmetic through
        import_module.
        """
        names = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                    names.update(node.module.split("."))
                for alias in node.names:
                    names.add(alias.name)
                    if alias.asname:
                        names.add(alias.asname)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
                    names.update(alias.name.split("."))
                    if alias.asname:
                        names.add(alias.asname)
            elif isinstance(node, ast.Call):
                func = node.func
                target = getattr(func, "attr", getattr(func, "id", ""))
                if target in ("import_module", "__import__"):
                    for argument in node.args:
                        if isinstance(argument, ast.Constant):
                            names.add(str(argument.value))
                            names.update(str(argument.value).split("."))
        return names

    def test_the_module_imports_no_probe_lane(self):
        imported = self._imported_names(self.source)
        self.assertIn(
            "mob_loot", imported,
            "the tripwire cannot see this module's own relative import")
        for name in imported:
            self.assertNotIn(
                "hypothesis", name,
                "a production lane may not import a scenario-gated probe")
        # Structural, not by name: a name check cannot see through string
        # arithmetic, so the MACHINERY for a dynamic import is what is banned.
        for node in ast.walk(ast.parse(self.source)):
            if isinstance(node, ast.Call):
                func = node.func
                target = getattr(func, "attr", getattr(func, "id", ""))
                self.assertNotIn(
                    target, ("import_module", "__import__"),
                    "a production lane may not import dynamically")
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, "import_module")
        self.assertNotIn("importlib", imported)

    def test_the_import_tripwire_catches_the_forms_that_defeated_it_before(self):
        for attack in (
            "from . import pickup_listener_hypothesis\n",
            "from .ground_loot_hypothesis import GROUND_LIST_BIT\n",
            "import pirateforce_foundation.pickup_listener_hypothesis\n",
            "import importlib\n"
            "p = importlib.import_module('pirateforce_foundation.x_hypothesis')\n",
        ):
            imported = self._imported_names(attack)
            self.assertTrue(
                any("hypothesis" in name for name in imported),
                "the tripwire is blind to %r" % attack)

    def test_the_lane_takes_only_shapes_from_the_item_lane_never_its_policy(self):
        """inventory.py is another lane's file.  This one borrows its RECORDS.

        The two dataclasses and the two base constants are the SHIPPED SHAPE
        of a persisted bag.  Every FUNCTION in that module is governed by
        HYP-PF-008 / HYP-PF-010 item-move hypotheses, and a lane that called
        one would be inheriting a hypothesis it never states.
        """
        allowed = {
            "BackpackState", "ItemAttrState",
            "BACKPACK_BASE_MASK", "BACKPACK_BASE_IDENTITY",
        }
        for node in ast.walk(ast.parse(self.source)):
            if isinstance(node, ast.ImportFrom) and node.module == "inventory":
                for alias in node.names:
                    self.assertIn(
                        alias.name, allowed,
                        "%s is the item lane's policy, not its shape"
                        % alias.name)

    def test_the_lane_has_no_clock_no_socket_and_no_file(self):
        banned = {
            "time", "monotonic", "sleep", "now", "utcnow", "open", "socket",
            "connect", "execute", "executemany", "commit", "cursor",
        }
        for node in ast.walk(ast.parse(self.source)):
            if isinstance(node, ast.Call):
                func = node.func
                target = getattr(func, "attr", getattr(func, "id", ""))
                self.assertNotIn(
                    target, banned,
                    "a pure transaction may not call %r" % target)

    def test_the_module_is_pure_ascii(self):
        MODULE_PATH.read_text(encoding="ascii")

    # -- the claim ---------------------------------------------------------
    def test_a_claim_refuses_a_bad_identity_and_a_bad_position(self):
        self.assertEqual(
            self._refusal(PickupClaim, 0, 1.0, 2.0, 3.0, KEY),
            "identity_not_positive")
        self.assertEqual(
            self._refusal(PickupClaim, KILLER, float("nan"), 2.0, 3.0, KEY),
            "position_not_finite")
        self.assertEqual(
            self._refusal(PickupClaim, KILLER, 1.0, 2.0, 3.0, -1),
            "value_out_of_range")
        self.assertEqual(
            self._refusal(PickupClaim, KILLER, 1.0, 2.0, 3.0, "1"),
            "value_not_int")
        self.assertEqual(
            self._refusal(PickupClaim, True, 1.0, 2.0, 3.0, KEY),
            "value_not_int",
            "a bool is not an identity, and bool is a subclass of int")

    def test_a_reference_that_is_not_on_the_ground_is_refused_by_name(self):
        cell = a_cell(a_drop())
        self.assertEqual(
            self._refusal(resolve_claim, cell.ledger, a_claim(key=KEY + 5)),
            "object_ref_not_on_the_ground")

    def test_only_the_killer_may_claim_the_drop(self):
        cell = a_cell(a_drop())
        self.assertEqual(
            self._refusal(
                resolve_claim, cell.ledger, a_claim(identity=STRANGER)),
            "not_the_killer")

    def test_a_claimant_too_far_away_is_refused_by_name(self):
        cell = a_cell(a_drop(at=(0.0, 0.0, 0.0)))
        far = (PICKUP_RADIUS + 1.0, 0.0, 0.0)
        self.assertEqual(
            self._refusal(resolve_claim, cell.ledger, a_claim(at=far)),
            "claimant_out_of_range")

    def test_the_radius_boundary_is_inclusive_and_is_measured_in_3d(self):
        self.assertTrue(within_pickup_radius((0.0, 0.0, 0.0),
                                             (PICKUP_RADIUS, 0.0, 0.0)))
        self.assertFalse(within_pickup_radius((0.0, 0.0, 0.0),
                                              (PICKUP_RADIUS + 0.5, 0.0, 0.0)))
        # A drop directly above the claimant is as far away as one beside it:
        # the aggro lane compares full 3D and so does this one.
        self.assertFalse(within_pickup_radius(
            (0.0, 0.0, 0.0), (0.0, 0.0, PICKUP_RADIUS + 0.5)))

    def test_the_radius_covers_one_kills_own_scatter(self):
        """The arithmetic the constant claims, checked rather than asserted."""
        furthest = mob_loot.DROP_SCATTER_STEP * (mob_loot.MAX_DROPS_PER_KILL - 1)
        self.assertTrue(within_pickup_radius(
            (0.0, 0.0, 0.0), (furthest, 0.0, 0.0)),
            "a player standing where the monster fell cannot reach the last "
            "object that kill produced")

    def test_resolving_a_claim_takes_nothing(self):
        cell = a_cell(a_drop())
        before = cell.ledger
        resolve_claim(cell.ledger, a_claim())
        self.assertEqual(cell.ledger, before)

    # -- the bag -----------------------------------------------------------
    def test_the_lowest_free_slot_is_the_one_taken(self):
        self.assertEqual(first_free_slot(EMPTY_BAG), 0)
        self.assertEqual(first_free_slot(INITIAL_BACKPACK), 4)
        gapped = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            tuple(item for item in INITIAL_BACKPACK.items if item.slot != 1))
        self.assertEqual(first_free_slot(gapped), 1)

    def test_a_full_bag_refuses_by_name(self):
        full = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            tuple(ItemAttrState(slot + 1, ITEM, 1, slot)
                  for slot in range(BAG_SLOT_COUNT)))
        self.assertEqual(self._refusal(first_free_slot, full), "bag_is_full")

    def test_the_next_identity_follows_the_highest_not_the_count(self):
        self.assertEqual(next_item_identity(EMPTY_BAG), 1)
        self.assertEqual(next_item_identity(INITIAL_BACKPACK), 5)
        # A bag whose middle row was deleted: a count would hand out 4, which
        # a surviving row already holds and the primary key would reject.
        gapped = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            tuple(item for item in INITIAL_BACKPACK.items
                  if item.identity != 2))
        self.assertEqual(len(gapped.items), 3)
        self.assertEqual(next_item_identity(gapped), 5)

    def test_an_identity_at_the_column_ceiling_is_refused_by_name(self):
        at_the_top = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(MAX_ITEM_IDENTITY, ITEM, 1, 0),))
        self.assertEqual(
            self._refusal(next_item_identity, at_the_top),
            "identity_block_spent")

    def test_a_bag_with_two_rows_in_one_slot_is_refused_by_name(self):
        collided = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(1, ITEM, 1, 0), ItemAttrState(2, ITEM, 1, 0)))
        self.assertEqual(
            self._refusal(require_bag_shape, collided), "bag_row_collides")

    def test_the_new_rows_raw_columns_are_the_shipped_ones(self):
        """Copied from what exists, not chosen: every baseline row carries these."""
        for item in INITIAL_BACKPACK.items:
            self.assertEqual(item.raw_u8_38, NEW_ROW_RAW_U8_38)
            self.assertEqual(item.raw_u8_39, NEW_ROW_RAW_U8_39)
            self.assertEqual(item.detail_present, NEW_ROW_DETAIL_PRESENT)

    def test_placing_keeps_the_bag_in_identity_order(self):
        bag, item = place_in_bag(INITIAL_BACKPACK, a_drop())
        self.assertEqual(item.identity, 5)
        self.assertEqual(item.slot, 4)
        self.assertEqual(item.template_id, ITEM)
        self.assertEqual(
            [row.identity for row in bag.items], [1, 2, 3, 4, 5],
            "store._load_backpack reads rows ORDER BY item_identity")
        self.assertEqual(len(INITIAL_BACKPACK.items), 4, "the input is a value")

    def test_nothing_stacks_even_when_the_template_is_already_there(self):
        bag, first = place_in_bag(EMPTY_BAG, a_drop())
        bag, second = place_in_bag(bag, a_drop(key=KEY + 1))
        self.assertEqual(first.template_id, second.template_id)
        self.assertNotEqual(first.slot, second.slot)
        self.assertEqual(first.quantity, 1)
        self.assertEqual(second.quantity, 1)

    def test_a_quantity_the_slot_cannot_carry_is_refused(self):
        oversized = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(1, ITEM, 0x10000, 0),))
        self.assertEqual(
            self._refusal(require_bag_shape, oversized), "value_out_of_range")

    # -- the transaction ---------------------------------------------------
    def test_one_claim_moves_one_row_from_the_ground_to_the_bag(self):
        cell = a_cell(a_drop())
        outcome = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        self.assertEqual(type(outcome), PickupOutcome)
        self.assertEqual(cell.ledger.drops, ())
        self.assertEqual(len(outcome.bag_after.items), 5)
        self.assertEqual(outcome.item.template_id, ITEM)
        self.assertEqual(outcome.drop.drop_key, KEY)
        self.assertEqual(outcome.bag_before, INITIAL_BACKPACK)

    def test_the_row_write_names_the_exact_insert(self):
        cell = a_cell(a_drop(quantity=3))
        outcome = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        self.assertEqual(
            BagRowWrite.COLUMNS,
            ("character_id", "item_identity", "template_id", "quantity",
             "slot", "raw_u8_38", "raw_u8_39", "detail_present"))
        self.assertEqual(
            outcome.row_write.values(77),
            (77, 5, ITEM, 3, 4, NEW_ROW_RAW_U8_38, NEW_ROW_RAW_U8_39,
             NEW_ROW_DETAIL_PRESENT))
        self.assertEqual(
            self._refusal(outcome.row_write.values, 0), "value_out_of_range")

    def test_the_row_write_matches_the_shipped_column_list(self):
        """The columns are migration 003's, read from the file, not remembered."""
        migration = (ROOT / "migrations" / "003_character_inventory.sql").read_text(
            encoding="utf-8")
        body = migration.split("CREATE TABLE character_backpack_items", 1)[1]
        body = body.split(");", 1)[0]
        for column in BagRowWrite.COLUMNS:
            self.assertIn(column, body, "%s is not a column of the table" % column)

    def test_a_stale_bag_is_caught_at_the_write_and_not_by_the_primary_key(self):
        """Two pickups, one stale bag: the slot collides and the PK is blind.

        The database keys (character_id, item_identity), so a stale IDENTITY
        is rejected for free.  The SLOT is not in that key, so two rows land
        in one slot and nothing complains until the next login cannot parse
        the bag.  require_fits is what the writer runs to see it in time.
        """
        cell = a_cell(a_drop(), a_drop(key=KEY + 1))
        first = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        second = commit_pickup(cell, INITIAL_BACKPACK, a_claim(key=KEY + 1))
        self.assertEqual(first.item.slot, second.item.slot)
        self.assertEqual(first.item.identity, second.item.identity)
        # Against the bag the FIRST pickup produced, the second row does not
        # fit -- and it says so before anything is written.
        self.assertTrue(first.row_write.fits(INITIAL_BACKPACK))
        self.assertFalse(second.row_write.fits(first.bag_after))
        self.assertEqual(
            self._refusal(second.row_write.require_fits, first.bag_after),
            "bag_row_collides")
        # A slot collision alone is enough, with no identity collision at all.
        slot_only = BagRowWrite(KILLER, 99, ITEM, 1, first.item.slot)
        self.assertFalse(slot_only.fits(first.bag_after))
        self.assertFalse(slot_only.fits(object()))

    def test_a_full_bag_does_not_eat_the_drop(self):
        """THE ORDERING TEST.  Everything that refuses, refuses before the take.

        A lane that took the row off the ground and then discovered the bag
        was full would answer "your bag is full" by DESTROYING the object the
        player was reaching for.
        """
        full = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            tuple(ItemAttrState(slot + 1, ITEM, 1, slot)
                  for slot in range(BAG_SLOT_COUNT)))
        cell = a_cell(a_drop())
        before = cell.ledger
        self.assertEqual(
            self._refusal(commit_pickup, cell, full, a_claim()), "bag_is_full")
        self.assertEqual(cell.ledger, before, "the drop left the ground anyway")

    def test_every_refusal_of_a_claim_leaves_the_drop_on_the_ground(self):
        for claim in (a_claim(key=KEY + 5), a_claim(identity=STRANGER),
                      a_claim(at=(PICKUP_RADIUS + 10.0, 0.0, 0.0))):
            cell = a_cell(a_drop(at=(0.0, 0.0, 0.0)))
            before = cell.ledger
            with self.assertRaises(MobPickupContractError):
                commit_pickup(cell, INITIAL_BACKPACK, claim)
            self.assertEqual(cell.ledger, before)

    def test_only_one_of_two_claims_on_one_key_wins(self):
        """THE RACE.  The loser is refused by name and changes nothing.

        Safe only because mob_loot never reuses a key: a key still in the
        ledger at take time names the same object it named at resolve time.
        """
        cell = a_cell(a_drop())
        first = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        self.assertEqual(first.item.identity, 5)
        self.assertEqual(
            self._refusal(commit_pickup, cell, INITIAL_BACKPACK, a_claim()),
            "object_ref_not_on_the_ground")

    def test_a_key_taken_by_a_pickup_is_never_handed_out_again(self):
        cell = a_cell(a_drop())
        commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        self.assertEqual(cell.ledger.drops, ())
        self.assertGreater(
            cell.ledger.next_key, KEY,
            "a reused key would let a client hold a stale object under it")

    def test_losing_the_row_at_take_time_is_reported_as_taken_not_missing(self):
        """The window the snapshot cannot close, forced open on purpose.

        Between resolve and take, another claimant can win.  The loser must
        learn that the row is GONE -- not that its own reference was wrong --
        because the two answers imply different next moves: one says retry
        never, the other says the derived object reference may be wrong.
        """
        cell = a_cell(a_drop())

        def vanish(drop_key):
            raise mob_loot.MobLootContractError(
                mob_loot.REFUSE_DROP_NOT_IN_LEDGER, "another claim took it")

        cell.take = vanish
        self.assertEqual(
            self._refusal(commit_pickup, cell, INITIAL_BACKPACK, a_claim()),
            "drop_taken_by_another_claim")

    def test_a_cell_subclass_is_not_the_scenes_cell(self):
        class OtherCell(DropLedgerCell):
            pass

        cell = OtherCell(DropLedger((a_drop(),), 1, KEY + 1, ()))
        self.assertEqual(
            self._refusal(commit_pickup, cell, INITIAL_BACKPACK, a_claim()),
            "type_not_typed_record")

    def test_the_transaction_refuses_untyped_arguments(self):
        cell = a_cell(a_drop())
        self.assertEqual(
            self._refusal(commit_pickup, object(), INITIAL_BACKPACK, a_claim()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(commit_pickup, cell, INITIAL_BACKPACK, object()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(commit_pickup, cell, object(), a_claim()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(resolve_claim, object(), a_claim()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(place_in_bag, EMPTY_BAG, object()),
            "type_not_typed_record")

    # -- the bytes ---------------------------------------------------------
    def test_the_delta_is_byte_equal_to_the_item_lanes_composer(self):
        """One shape, two lanes, byte for byte.

        The item lane pinned this shape against frozen V141 for a MOVE.  If
        the two ever stop agreeing, this lane is guessing at a shape it did
        not measure -- which is exactly what NONCLAIM 3 says it must not do
        quietly.
        """
        governed = inventory.HYPOTHESIZED_V111_SLOT2_BACKPACK.items[0]
        self.assertEqual(
            bag_delta_pc(self.legacy, governed),
            inventory.make_item_move_delta_response(self.legacy, governed))

    def test_the_delta_carries_the_new_row_a_pickup_made(self):
        _bag, item = place_in_bag(INITIAL_BACKPACK, a_drop())
        pc, frame = bag_delta_pc(self.legacy, item)
        self.assertIn(self.legacy.qwordtag(0x32, item.identity), pc)
        self.assertIn(self.legacy.u32tag(0x14, ITEM), pc)
        self.assertGreater(len(frame), len(pc))

    def test_the_composer_refuses_when_the_two_derivations_disagree(self):
        class DriftingLegacy:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            @staticmethod
            def u16tag(tag, value):
                return bytes((tag,)) + b"\x00\x00"

        _bag, item = place_in_bag(EMPTY_BAG, a_drop(quantity=2))
        self.assertEqual(
            self._refusal(bag_delta_pc, DriftingLegacy(self.legacy), item),
            "composed_bytes_off_pin")

    def test_the_delta_refuses_an_untyped_row_and_an_id_of_zero(self):
        self.assertEqual(
            self._refusal(bag_delta_pc, self.legacy, object()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(
                bag_delta_pc, self.legacy, ItemAttrState(1, 0, 1, 0)),
            "value_out_of_range")

    def test_a_name_a_person_would_read_is_required_where_one_is_read_out(self):
        """Money and a nameless id refuse at the READING edge, not the wire.

        A bag delta serializes any row a bag holds -- including the four a
        character ships with, which are not in this lane's drop tables.  What
        may never happen is a REPORT that puts a blank where an item name goes.
        """
        cell = a_cell(a_drop())
        good = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        money = PickupOutcome(
            good.drop, ItemAttrState(9, mob_pickup.MONEY_ITEM_ID, 1, 9),
            good.bag_before, good.bag_after, good.row_write)
        self.assertEqual(
            self._refusal(pickup_report, money), "money_has_no_ground_object")
        nameless = PickupOutcome(
            good.drop, ItemAttrState(9, 999999, 1, 9),
            good.bag_before, good.bag_after, good.row_write)
        self.assertEqual(
            self._refusal(pickup_report, nameless), "item_has_no_name")

    # -- the wall ----------------------------------------------------------
    def test_the_governed_allowlist_is_the_wall_this_lane_stops_at(self):
        """BUILD-006's relog row, pinned as the blocker it actually is.

        A bag holding a picked-up item is outside the item lane's CONTENT
        allowlist, and both the login load and the world-entry attr build run
        that allowlist.  Persisting the row before that lane widens it does
        not fail softly -- the character cannot enter the world.  The day it
        is widened, this test goes red and this lane's prose must be rewritten
        in the same round.
        """
        bag, item = place_in_bag(INITIAL_BACKPACK, a_drop())
        # Gate 1: the login load.  A ValueError here is not caught by
        # runtime.py's (KeyError, PermissionError) handler at all.
        with self.assertRaises(ValueError):
            inventory.require_known_backpack(bag)
        # Gate 2: the character-select stage, which answers with no reply.
        self.assertFalse(inventory.is_unmoved_baseline(bag))
        # Gate 3: the world-entry attr build.
        with self.assertRaises(ValueError):
            inventory.make_backpack_attr(self.legacy, bag)
        self.assertTrue(mob_pickup.GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE)
        self.assertEqual(item.identity, 5)
        # And the shape itself is fine -- it is the CONTENTS that are governed.
        require_bag_shape(bag)

    def test_the_lane_never_says_a_pickup_survives_a_relog(self):
        cell = a_cell(a_drop())
        outcome = commit_pickup(cell, INITIAL_BACKPACK, a_claim())
        self.assertFalse(outcome.persisted)
        report = pickup_report(outcome)
        self.assertFalse(report["persisted"])
        self.assertFalse(report["survives_a_relog"])
        self.assertEqual(report["item_name"], outcome.display_name)
        self.assertEqual(report["claimed_by"], KILLER)
        self.assertEqual(report["from_the_kill_of"], MOB)
        self.assertEqual(
            self._refusal(pickup_report, object()), "type_not_typed_record")

    # -- the declarations --------------------------------------------------
    def test_every_named_refusal_reason_can_actually_happen(self):
        """SET EQUALITY over the names actually RAISED, not a source count.

        The declaration tuple is excluded from the collector: it is itself a
        tuple whose first element is a refusal constant, and a collector that
        whitelisted its head would let a name placed first there need no code
        path at all.
        """
        constants = {}
        for line in self.source.splitlines():
            if line.startswith("REFUSE_") and " = " in line:
                name, value = line.split(" = ", 1)
                constants[name.strip()] = value.strip().strip('"')
        tree = ast.parse(self.source)
        raised = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            call = node.exc
            if not isinstance(call, ast.Call):
                continue
            if getattr(call.func, "id", "") != "MobPickupContractError":
                continue
            if not call.args:
                continue
            first = call.args[0]
            if isinstance(first, ast.Name) and first.id in constants:
                raised.add(constants[first.id])
            elif isinstance(first, ast.Constant):
                raised.add(str(first.value))
        self.assertEqual(
            set(MOB_PICKUP_REFUSAL_REASONS) - raised, set(),
            "declared refusal names that no code path produces")
        self.assertEqual(
            raised - set(MOB_PICKUP_REFUSAL_REASONS), set(),
            "refusal names produced but not declared")

    def test_the_refusal_names_are_unique(self):
        self.assertEqual(
            len(set(MOB_PICKUP_REFUSAL_REASONS)),
            len(MOB_PICKUP_REFUSAL_REASONS))

    def test_the_assumptions_are_labelled_as_assumptions(self):
        """Three things this lane decided for itself, each tagged in the file."""
        for subject in ("object reference", "killer-only", "PICKUP_RADIUS"):
            self.assertTrue(
                any(subject in claim for claim in MOB_PICKUP_NONCLAIMS),
                "%s is a decision this lane made and must carry a nonclaim"
                % subject)
        self.assertGreaterEqual(
            self.source.count("[LANE-B ASSUMPTION"), 3,
            "every decision this lane made for itself carries the tag COO reads")

    def test_the_pin_document_says_what_the_lane_is_and_is_not(self):
        document = pin_document(self.legacy)
        self.assertTrue(document["production_allowed"])
        self.assertFalse(document["test_only"])
        self.assertIsNone(document["scenario"])
        self.assertFalse(document["wire"]["ever_observed_for_a_new_item"])
        self.assertTrue(document["blocked"]["relog_persistence"])
        self.assertFalse(document["transaction"]["stacks"])
        self.assertTrue(
            document["transaction"]["everything_that_refuses_refuses_before_the_take"])
        self.assertEqual(document["refusals"], list(MOB_PICKUP_REFUSAL_REASONS))

    def test_the_shipped_pin_file_is_what_the_code_computes(self):
        self.assertEqual(
            json.loads(PIN_PATH.read_text(encoding="utf-8")),
            json.loads(json.dumps(pin_document(self.legacy), sort_keys=True)))


if __name__ == "__main__":
    unittest.main()
