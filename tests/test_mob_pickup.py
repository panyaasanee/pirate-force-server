"""LANE-B: the drop a monster left becomes a row in somebody's bag.

The load-bearing tests in this file are the five below; the rest are guards.

``test_a_full_bag_does_not_eat_the_drop`` is the one that matters most.  A
pickup is the only operation in this lane that can DESTROY something a player
owns, and it destroys it by refusing AFTER the row has left the ground.  The
module's whole ordering argument exists for this test.

``test_two_pickups_in_one_session_do_not_collide`` is the second.  The first
draft of this lane took the bag as a value, and an adversarial pass showed two
pickups in one session allocating one slot and one identity with nothing
raised -- both drops off the ground, the second row then refused by the
database.  BagCell is the answer and this test is what holds it.

``test_only_one_of_two_claims_on_one_key_wins`` pins the race on the ground.
The lane resolves against a snapshot and takes through mob_loot's cell, which
is a check-then-act shape -- safe only because that lane never reuses a key.

``test_the_delta_is_byte_equal_to_the_item_lanes_composer`` plus
``test_the_envelope_is_pinned_at_run_time_not_only_in_a_test`` are the reason
to believe these bytes are the right bytes.  The first alone was not enough:
it compares ONE governed row, and a shim that moved a constant OUTSIDE the
seven ItemAttr fields sailed through it.

``test_the_governed_allowlist_is_the_wall_this_lane_stops_at`` pins the
BLOCKER as a test.  BUILD-006 asks for "relog and it is still there";
COO-DECISION 20260826_0950 (a) moved the character-SELECT LOAD off the
content gate, and COO-DECISION 20260828_0844 moved the WORLD-ENTRY WIRE
BUILD off it too (a narrow scope grant to this lane, since no separate item
lane exists to do it) -- but the HYP-PF-008 opt-in gate
(``is_unmoved_baseline``) is unchanged and deliberately out of that grant, so
the wall still stands there.  And a round that only wrote that in prose would
be a round whose prose rots.
"""

import ast
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import bag_admission, inventory, mob_loot, mob_pickup
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
    DELTA_FRAME_MAGIC,
    DELTA_PC_PREFIX_PIN,
    DELTA_PC_SUFFIX_PIN,
    MAX_ITEM_IDENTITY,
    MOB_PICKUP_NONCLAIMS,
    MOB_PICKUP_REFUSAL_REASONS,
    NEW_ROW_DETAIL_PRESENT,
    NEW_ROW_RAW_U8_38,
    NEW_ROW_RAW_U8_39,
    PICKUP_RADIUS,
    REFUSALS_THAT_LEAVE_THE_DROP_ON_THE_GROUND,
    BagCell,
    BagCellRegistry,
    BagCellTaken,
    BagRowWrite,
    MobPickupContractError,
    PickupClaim,
    PickupOutcome,
    bag_delta_pc,
    bag_row_write_console_line,
    dispatch_pickup_request,
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
MIGRATION_PATH = ROOT / "migrations" / "003_character_inventory.sql"


def _executed_sql(module_name):
    """(enclosing function, sql) for every string handed to a DB call.

    Imported in spirit from ``tests/test_bag_admission_expiry.py``, which
    wrote it after pf-adversary defeated two weaker versions.  The two
    lessons it carries, both of which apply here: SQL split across adjacent
    literals or hoisted to a module constant is invisible to a line scanner,
    and a module that DESCRIBES an INSERT in prose (this lane does, at
    length) is the opposite of one that performs it, so only strings that
    actually reach ``execute``/``executemany`` count.

    It lives in both files rather than being shared because a test that
    imports its own oracle from the file it is cross-checking would fail
    together with it.
    """
    source = (
        ROOT / "src" / "pirateforce_foundation" / f"{module_name}.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                owner[id(child)] = node.name
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name not in ("execute", "executemany", "executescript"):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            text = first.value
        elif isinstance(first, ast.Name) and first.id in constants:
            text = constants[first.id]
        else:
            continue
        out.append((owner.get(id(node), "<module>"), " ".join(text.split())))
    return out

# The identities the sibling lanes' tests use, so one kill reads the same in
# three files: a roster monster, and a session-shaped player identity.
MOB = 0x201F
KILLER = 0x750059
STRANGER = 0x750060
ITEM = 2400046            # the roster's most common drop
KEY = mob_loot.DROP_KEY_BASE
CHARACTER = 77
EMPTY_BAG = BackpackState(BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())


def a_drop(key=KEY, item=ITEM, quantity=1, at=(10.0, 20.0, 30.0),
           mob=MOB, killer=KILLER):
    return GroundDrop(
        key, item, quantity,
        mob_loot.as_wire_float(at[0]), mob_loot.as_wire_float(at[1]),
        mob_loot.as_wire_float(at[2]), mob, killer,
    )


def a_cell(*drops):
    """A ground cell holding exactly these rows, with the keys marked issued."""
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(DropLedger(tuple(drops), 1, issued, ()))


def a_claim(key=KEY, identity=KILLER, at=(10.0, 20.0, 30.0), opaque=0):
    return PickupClaim(identity, at[0], at[1], at[2], key, opaque)


def a_full_bag():
    return BackpackState(
        BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
        tuple(ItemAttrState(slot + 1, ITEM, 1, slot)
              for slot in range(BAG_SLOT_COUNT)))


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

    @staticmethod
    def _names_taken_from(source, module):
        """Every name imported FROM one sibling module, in ANY import form.

        BLIND TWICE, each time proved by an adversarial pass.  First it
        filtered on ``node.module == "inventory"``, which skips
        ``from . import inventory`` entirely (that node's module is None and
        the name lives in the alias).  The repair for that was still blind to
        every DOTTED form -- ``from pirateforce_foundation.inventory import
        require_known_backpack``, ``import pirateforce_foundation.inventory``,
        ``from pirateforce_foundation import inventory`` -- and worse, the
        legitimate relative import kept the ``assertTrue(taken)`` safety net
        satisfied, so the attacked source passed.  The rule is now: normalise
        every module path by its LAST component, the way the sibling collector
        in this file already did.
        """
        taken = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                parts = (node.module or "").split(".")
                if parts[-1] == module:
                    taken.update(alias.name for alias in node.names)
                else:
                    # `from . import inventory` / `from pkg import inventory`
                    # take the WHOLE module, so every name in it is reachable
                    # and an allowlist of names means nothing.
                    taken.update(
                        alias.name for alias in node.names
                        if alias.name.split(".")[-1] == module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[-1] == module:
                        taken.add(alias.name.split(".")[-1])
        return taken

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
        taken = self._names_taken_from(self.source, "inventory")
        self.assertTrue(taken, "the tripwire found no import to check at all")
        for name in taken:
            self.assertIn(
                name, allowed,
                "%s is the item lane's policy or its whole module, not its "
                "shape" % name)

    def test_that_tripwire_catches_every_form_that_defeated_it(self):
        """Each attack below passed one earlier version of the collector."""
        legitimate = (
            "from .inventory import BackpackState, ItemAttrState\n"
            "from . import mob_loot\n"
        )
        for attack, expected in (
            ("from . import inventory\n", "inventory"),
            ("from pirateforce_foundation import inventory\n", "inventory"),
            ("import pirateforce_foundation.inventory\n", "inventory"),
            ("import pirateforce_foundation.inventory as inv\n", "inventory"),
            ("from pirateforce_foundation.inventory import "
             "require_known_backpack\n", "require_known_backpack"),
            ("from .inventory import move_known_item_to_free_slot\n",
             "move_known_item_to_free_slot"),
        ):
            with self.subTest(attack=attack.strip()):
                taken = self._names_taken_from(legitimate + attack, "inventory")
                self.assertIn(
                    expected, taken,
                    "the tripwire is blind to %r" % attack)
                # And the check built on it must actually go red, even though
                # the legitimate relative import keeps `taken` non-empty.
                allowed = {
                    "BackpackState", "ItemAttrState",
                    "BACKPACK_BASE_MASK", "BACKPACK_BASE_IDENTITY",
                }
                self.assertFalse(
                    taken <= allowed,
                    "the attacked source still satisfies the allowlist")

    def test_the_lane_has_no_clock_no_socket_and_no_file(self):
        banned = {
            "time", "monotonic", "sleep", "now", "utcnow", "open", "socket",
            "connect", "execute", "executemany", "commit", "cursor",
            "read_text", "write_text", "read_bytes", "write_bytes",
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

    def test_the_claim_carries_both_fields_of_the_proven_body(self):
        """Two fields on the wire, two fields here, and the u8 acted on nowhere.

        The proven PickupTerrainThing body is a u32 at object+0x14 and a u8 at
        object+0x18.  The first draft of this record carried only the dword,
        which is how a lane silently discards a field it has not understood.
        """
        claim = a_claim(opaque=0xAB)
        self.assertEqual(claim.opaque_u8, 0xAB)
        self.assertEqual(
            self._refusal(PickupClaim, KILLER, 1.0, 2.0, 3.0, KEY, 0x100),
            "value_out_of_range")
        # It changes nothing this lane DOES -- nobody has measured what it
        # means -- but it must reach whoever reads a log.  The first version
        # of this test asserted only the first half, which is how it certified
        # a field being discarded one step past the door.
        one = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            a_cell(a_drop()), a_claim(opaque=0))
        two = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            a_cell(a_drop()), a_claim(opaque=0xFF))
        self.assertEqual(one.row_write, two.row_write)
        self.assertEqual(two.opaque_u8, 0xFF)
        self.assertEqual(pickup_report(two)["request_u8"], 0xFF)
        self.assertEqual(pickup_report(one)["request_u8"], 0)

    def test_a_reference_this_lane_never_issued_is_told_apart_from_a_taken_one(self):
        """The distinction that keeps RE-082 from being poisoned by clicks.

        A key BELOW issued_through was handed out by this lane and has since
        left the ground -- an ordinary double-click.  A key at or above it was
        never issued, and only that shape is evidence about the object
        reference.  One refusal for both would have logged every double-click
        in the game as evidence against the assumption RE-082 exists to test.
        """
        cell = a_cell(a_drop(key=KEY + 1))
        already = self._refusal(resolve_claim, cell.ledger, a_claim(key=KEY))
        self.assertEqual(already, "drop_already_taken")
        never = self._refusal(
            resolve_claim, cell.ledger, a_claim(key=KEY + 500))
        self.assertEqual(never, "object_ref_never_issued")
        with self.assertRaises(MobPickupContractError) as caught:
            resolve_claim(cell.ledger, a_claim(key=KEY))
        self.assertNotIn("RE-082", caught.exception.args[1])
        with self.assertRaises(MobPickupContractError) as caught:
            resolve_claim(cell.ledger, a_claim(key=KEY + 500))
        self.assertIn("RE-082", caught.exception.args[1])

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

    def test_the_radius_is_exactly_the_arithmetic_it_claims_to_be(self):
        """BOUNDS THE CONSTANT, which the first version of this test did not.

        It only asked whether the furthest object of one kill was inside the
        radius, so an adversarial pass set the radius to 1e9 and the suite
        stayed green -- a gate whose stated job is "refuse an absurd claim"
        could not tell 480 from a billion.  Now the arithmetic itself is the
        assertion, and the off-by-one that shipped is named: the furthest
        object of a 16-drop kill stands at 15 steps, not 16.
        """
        furthest = mob_loot.DROP_SCATTER_STEP * (mob_loot.MAX_DROPS_PER_KILL - 1)
        self.assertEqual(PICKUP_RADIUS, furthest)
        self.assertEqual(PICKUP_RADIUS, 450.0)
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
        self.assertEqual(
            self._refusal(first_free_slot, a_full_bag()), "bag_is_full")

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

    def test_a_high_water_mark_is_accepted_and_one_that_lags_is_refused(self):
        """The shape mob_loot proved is required, and the fallback named as one.

        A bag that has SHRUNK hands the derived form an identity it has handed
        out before -- the exact bug DropLedger.next_key exists to prevent one
        lane over.  There is no column to persist a mark in today, so the
        function accepts one and falls back; the fallback is a fallback, and
        NONCLAIM 14 says so rather than the code pretending it is a policy.
        """
        shrunk = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(1, ITEM, 1, 0),))
        self.assertEqual(next_item_identity(shrunk), 2, "the derived form")
        self.assertEqual(
            next_item_identity(shrunk, 9), 10, "the high-water form")
        self.assertEqual(
            self._refusal(next_item_identity, INITIAL_BACKPACK, 2),
            "identity_high_water_below_the_bag")
        self.assertIn(
            "14. THE ITEM IDENTITY IS DERIVED",
            "".join(MOB_PICKUP_NONCLAIMS))

    def test_a_cell_carries_its_high_water_mark_forward(self):
        cell = BagCell(EMPTY_BAG, CHARACTER, issued_through=40)
        ground = a_cell(a_drop(), a_drop(key=KEY + 1))
        first = cell.commit_pickup(ground, a_claim())
        second = cell.commit_pickup(ground, a_claim(key=KEY + 1))
        self.assertEqual(first.item.identity, 41)
        self.assertEqual(second.item.identity, 42)
        self.assertEqual(
            self._refusal(BagCell, INITIAL_BACKPACK, CHARACTER, 2),
            "identity_high_water_below_the_bag")

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

    def test_a_bag_caught_mid_swap_is_refused_rather_than_misread(self):
        """store.py parks a row at slot 65535 while it swaps two items.

        The migration CHECKs slot BETWEEN 0 AND 65535 precisely so that can
        happen, which is why this lane's 40 comes from inventory.py and not
        from the migration.  A bag read in that window must be refused, never
        treated as a bag with a 41st slot.
        """
        mid_swap = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(1, ITEM, 1, mob_pickup.SWAP_PARKING_SLOT),))
        self.assertEqual(
            self._refusal(require_bag_shape, mid_swap), "value_out_of_range")

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
        ground = a_cell(a_drop())
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        outcome = cell.commit_pickup(ground, a_claim())
        self.assertEqual(type(outcome), PickupOutcome)
        self.assertEqual(ground.ledger.drops, ())
        self.assertEqual(len(outcome.bag_after.items), 5)
        self.assertEqual(outcome.item.template_id, ITEM)
        self.assertEqual(outcome.drop.drop_key, KEY)
        self.assertEqual(outcome.bag_before, INITIAL_BACKPACK)
        self.assertEqual(cell.bag, outcome.bag_after, "the cell moved with it")

    def test_two_pickups_in_one_session_do_not_collide(self):
        """THE CELL TEST.  Two claims, one session, two different rows.

        With a bag passed by VALUE this allocated slot 4 and identity 5 twice,
        raised nothing, took both drops off the ground, and left the second
        INSERT to be refused by the database's UNIQUE(character_id, slot)
        AFTER its drop was gone.
        """
        ground = a_cell(a_drop(), a_drop(key=KEY + 1))
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        first = cell.commit_pickup(ground, a_claim())
        second = cell.commit_pickup(ground, a_claim(key=KEY + 1))
        self.assertNotEqual(first.item.slot, second.item.slot)
        self.assertNotEqual(first.item.identity, second.item.identity)
        self.assertEqual(
            sorted(row.slot for row in cell.bag.items), [0, 1, 2, 3, 4, 5])
        self.assertEqual(ground.ledger.drops, ())

    def test_the_two_rows_of_one_session_survive_the_real_schema(self):
        """Run the shipped migration and INSERT both rows.  The DB is the judge.

        The claim that made the previous version of this lane add a post-take
        refusal -- "the database accepts two rows in one slot" -- was false,
        and only the schema itself could say so.  This test loads
        migrations/003 and inserts what the cell produced.
        """
        ground = a_cell(a_drop(), a_drop(key=KEY + 1))
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        rows = [
            cell.commit_pickup(ground, a_claim()).row_write,
            cell.commit_pickup(ground, a_claim(key=KEY + 1)).row_write,
        ]
        db = sqlite3.connect(":memory:")
        try:
            db.executescript(
                "CREATE TABLE characters(id INTEGER PRIMARY KEY, "
                "created_at TEXT, deleted_at TEXT);\n"
                "INSERT INTO characters VALUES(%d,'now',NULL);\n" % CHARACTER
                + MIGRATION_PATH.read_text(encoding="utf-8"))
            statement = (
                "INSERT INTO character_backpack_items(%s) VALUES(%s)"
                % (",".join(BagRowWrite.COLUMNS),
                   ",".join("?" * len(BagRowWrite.COLUMNS))))
            for row in rows:
                db.execute(statement, row.values())
            db.commit()
            self.assertEqual(
                db.execute(
                    "SELECT COUNT(*) FROM character_backpack_items "
                    "WHERE character_id=?", (CHARACTER,)).fetchone()[0],
                6, "four shipped rows plus the two this session picked up")
            # And the claim the module used to make, checked against the
            # schema that refutes it: a second row in one slot is REFUSED.
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(statement, (
                    CHARACTER, 99, ITEM, 1, rows[0].slot,
                    NEW_ROW_RAW_U8_38, NEW_ROW_RAW_U8_39,
                    NEW_ROW_DETAIL_PRESENT))
        finally:
            db.close()

    def test_the_migration_still_carries_the_constraint_this_lane_relies_on(self):
        body = MIGRATION_PATH.read_text(encoding="utf-8")
        body = body.split("CREATE TABLE character_backpack_items", 1)[1]
        body = body.split(");", 1)[0]
        for column in BagRowWrite.COLUMNS:
            self.assertIn(column, body, "%s is not a column of the table" % column)
        # Whitespace-insensitive: the constraint is the fact, not its
        # formatting, and greping the literal string would go red the day
        # somebody reformats the migration without changing anything.
        squeezed = "".join(body.split()).upper()
        self.assertIn("PRIMARYKEY(CHARACTER_ID,ITEM_IDENTITY)", squeezed)
        self.assertIn(
            "UNIQUE(CHARACTER_ID,SLOT)", squeezed,
            "the slot uniqueness this lane's nonclaims now depend on is gone")

    def test_the_row_write_names_the_exact_insert(self):
        ground = a_cell(a_drop(quantity=3))
        outcome = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            ground, a_claim())
        self.assertEqual(
            BagRowWrite.COLUMNS,
            ("character_id", "item_identity", "template_id", "quantity",
             "slot", "raw_u8_38", "raw_u8_39", "detail_present"))
        self.assertEqual(
            outcome.row_write.values(),
            (CHARACTER, 5, ITEM, 3, 4, NEW_ROW_RAW_U8_38, NEW_ROW_RAW_U8_39,
             NEW_ROW_DETAIL_PRESENT))

    def test_the_row_cannot_be_written_under_a_character_it_was_not_claimed_for(self):
        """values() takes no argument, and that is the whole fix.

        It used to take the character id from the caller, so values(999) on a
        row claimed by another player returned a row for character 999 while
        the report went on printing the claimant.  A record that the call
        reading it can contradict is not a record.
        """
        outcome = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            a_cell(a_drop()), a_claim())
        self.assertEqual(outcome.row_write.values()[0], CHARACTER)
        self.assertEqual(pickup_report(outcome)["written_for_character"],
                         CHARACTER)
        self.assertEqual(
            self._refusal(BagCell, INITIAL_BACKPACK, 0), "value_out_of_range")

    def test_a_full_bag_does_not_eat_the_drop(self):
        """THE ORDERING TEST.  Everything that refuses, refuses before the take.

        A lane that took the row off the ground and then discovered the bag
        was full would answer "your bag is full" by DESTROYING the object the
        player was reaching for.
        """
        ground = a_cell(a_drop())
        before = ground.ledger
        cell = BagCell(a_full_bag(), CHARACTER)
        self.assertEqual(
            self._refusal(cell.commit_pickup, ground, a_claim()), "bag_is_full")
        self.assertEqual(ground.ledger, before, "the drop left the ground anyway")
        self.assertEqual(cell.bag, a_full_bag(), "the bag moved on a refusal")

    def test_every_refusal_of_a_claim_leaves_the_drop_on_the_ground(self):
        for claim in (a_claim(key=KEY + 500), a_claim(identity=STRANGER),
                      a_claim(at=(PICKUP_RADIUS + 10.0, 0.0, 0.0))):
            ground = a_cell(a_drop(at=(0.0, 0.0, 0.0)))
            before = ground.ledger
            reason = self._refusal(
                BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup,
                ground, claim)
            self.assertIn(reason, REFUSALS_THAT_LEAVE_THE_DROP_ON_THE_GROUND)
            self.assertEqual(ground.ledger, before)

    def test_exactly_one_refusal_means_the_row_is_gone(self):
        self.assertEqual(
            set(MOB_PICKUP_REFUSAL_REASONS)
            - set(REFUSALS_THAT_LEAVE_THE_DROP_ON_THE_GROUND),
            {"drop_left_the_ground"})

    def test_only_one_of_two_claims_on_one_key_wins(self):
        """THE RACE.  The loser is refused by name and changes nothing.

        Safe only because mob_loot never reuses a key: a key still in the
        ledger at take time names the same object it named at resolve time.
        """
        ground = a_cell(a_drop())
        first = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            ground, a_claim())
        self.assertEqual(first.item.identity, 5)
        self.assertEqual(
            self._refusal(
                BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup,
                ground, a_claim()),
            "drop_already_taken",
            "the loser of an ordinary race must not be told its object "
            "reference looks wrong")

    def test_two_real_threads_on_one_key_produce_exactly_one_grant(self):
        for attempt in range(25):
            ground = a_cell(a_drop())
            gate = threading.Barrier(2)
            results = []

            def claim_it():
                cell = BagCell(INITIAL_BACKPACK, CHARACTER)
                gate.wait()
                try:
                    results.append(cell.commit_pickup(ground, a_claim()))
                except MobPickupContractError as exc:
                    results.append(exc.args[0])

            threads = [threading.Thread(target=claim_it) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            grants = [row for row in results if type(row) is PickupOutcome]
            with self.subTest(attempt=attempt):
                self.assertEqual(len(grants), 1, results)
                self.assertEqual(ground.ledger.drops, ())

    def test_one_shared_cell_under_two_threads_never_double_allocates(self):
        """THE SHAPE THE SUITE WAS NOT TESTING.

        The threaded test below builds a fresh BagCell inside each thread, so
        BagCell's own lock had never been contended by anything in this file
        -- the suite exercised the shape that FAILS (two cells) and not the
        shape that works.  This one shares a single cell, which is what the
        wiring line requires.
        """
        for attempt in range(20):
            ground = a_cell(a_drop(), a_drop(key=KEY + 1))
            cell = BagCell(INITIAL_BACKPACK, CHARACTER)
            gate = threading.Barrier(2)
            done = []

            def claim_it(key):
                gate.wait()
                try:
                    done.append(cell.commit_pickup(ground, a_claim(key=key)))
                except MobPickupContractError as exc:
                    done.append(exc.args[0])

            threads = [
                threading.Thread(target=claim_it, args=(key,))
                for key in (KEY, KEY + 1)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            grants = [row for row in done if type(row) is PickupOutcome]
            with self.subTest(attempt=attempt):
                self.assertEqual(len(grants), 2, done)
                self.assertNotEqual(
                    grants[0].item.slot, grants[1].item.slot)
                self.assertNotEqual(
                    grants[0].item.identity, grants[1].item.identity)

    def test_a_second_cell_for_one_character_loses_to_the_registry(self):
        """THE INVARIANT THAT WAS ONLY AN INSTRUCTION.

        BagCell answered "a caller holding a value cannot allocate against it
        safely" -- and then said "one per character" in a docstring, with
        nothing making a second one fail.  Two cells reproduce the original
        defect exactly: same slot, same identity, both drops off the ground.
        A constructor is not something a second caller can lose, so the claim
        moved to a registry.
        """
        registry = BagCellRegistry()
        first = registry.claim(CHARACTER, INITIAL_BACKPACK)
        self.assertTrue(registry.holds(CHARACTER))
        with self.assertRaises(BagCellTaken) as caught:
            registry.claim(CHARACTER, INITIAL_BACKPACK)
        self.assertEqual(caught.exception.args[0], "bag_already_claimed")
        # It is one of this lane's refusals, so a caller catching the base
        # class catches it too.
        self.assertIsInstance(caught.exception, MobPickupContractError)
        # A different character is unaffected.
        other = registry.claim(CHARACTER + 1, INITIAL_BACKPACK)
        self.assertIsNot(first, other)
        # And releasing lets the next session in.
        self.assertTrue(registry.release(CHARACTER))
        self.assertFalse(registry.release(CHARACTER))
        registry.claim(CHARACTER, INITIAL_BACKPACK)

    def test_only_one_of_two_racing_claims_gets_the_cell(self):
        for attempt in range(20):
            registry = BagCellRegistry()
            gate = threading.Barrier(2)
            results = []

            def grab():
                gate.wait()
                try:
                    results.append(registry.claim(CHARACTER, INITIAL_BACKPACK))
                except MobPickupContractError as exc:
                    results.append(exc.args[0])

            threads = [threading.Thread(target=grab) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            cells = [row for row in results if type(row) is BagCell]
            with self.subTest(attempt=attempt):
                self.assertEqual(len(cells), 1, results)
                self.assertIn("bag_already_claimed", results)

    def test_the_two_cells_the_registry_prevents_would_have_collided(self):
        """The defect the registry exists for, shown rather than asserted."""
        ground = a_cell(a_drop(), a_drop(key=KEY + 1))
        first = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            ground, a_claim())
        second = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            ground, a_claim(key=KEY + 1))
        self.assertEqual(first.item.slot, second.item.slot)
        self.assertEqual(first.item.identity, second.item.identity)
        self.assertEqual(ground.ledger.drops, (), "both drops are gone")

    def test_the_response_bytes_are_composed_before_the_row_leaves_the_ground(self):
        """THE REFUSAL FAMILY THE WIRING LINE USED TO PUT AFTER THE TAKE.

        bag_delta_pc raises four of this lane's refusals, every one of them
        listed as leaving the drop on the ground.  While the wiring said
        "step 4: call bag_delta_pc", following that recipe with a drifting
        legacy module took the row off the ground, persisted nothing and told
        the client nothing.  The bytes are composed inside the transaction now.
        """
        real = self.legacy

        class MovedVital:
            ITEM_OPERATE_RES_VITAL = 0x4C14

            def __getattr__(self, name):
                return getattr(real, name)

        ground = a_cell(a_drop())
        before = ground.ledger
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        self.assertEqual(
            self._refusal(cell.commit_pickup, ground, a_claim(), MovedVital()),
            "composed_bytes_off_pin")
        self.assertEqual(ground.ledger, before, "the drop left the ground")
        self.assertEqual(cell.bag, INITIAL_BACKPACK)
        # And with a sound legacy the bytes ride along on the outcome, so the
        # caller never has to compose anything after the take.
        outcome = cell.commit_pickup(ground, a_claim(), self.legacy)
        self.assertIsNotNone(outcome.delta)
        self.assertEqual(
            outcome.delta, bag_delta_pc(self.legacy, outcome.item))
        self.assertTrue(pickup_report(outcome)["response_bytes_composed"])

    def test_the_wiring_line_this_lane_hands_the_chief_actually_runs(self):
        """The deliverable is a paragraph of prose; prose does not typecheck.

        An adversarial pass found the wiring line calling
        commit_pickup(cell, claim, character_id) -- a TypeError, left behind
        when character_id moved into the constructor.  Nothing tested the
        string, so nothing noticed.  This walks the recipe it describes.
        """
        wiring = mob_pickup.MOB_PICKUP_WIRING
        self.assertIn("registry.claim(character_id", wiring)
        self.assertIn("commit_pickup(drop_ledger_cell, claim, legacy)", wiring)
        self.assertIn("outcome.row_write.values()", wiring)
        self.assertIn("send outcome.delta", wiring)
        self.assertNotIn("bag_delta_pc(legacy, outcome.item)", wiring)

        # Step 0, 1, 2, 4 -- exactly as written.
        registry = BagCellRegistry()
        bag_cell = registry.claim(CHARACTER, INITIAL_BACKPACK)
        ground = a_cell(a_drop())
        claim = PickupClaim(KILLER, 10.0, 20.0, 30.0, KEY, 0)
        outcome = bag_cell.commit_pickup(ground, claim, self.legacy)
        self.assertEqual(len(outcome.row_write.values()),
                         len(BagRowWrite.COLUMNS))
        pc, frame = outcome.delta
        self.assertTrue(pc and frame)
        self.assertTrue(registry.release(CHARACTER))

    def test_the_headline_dispatch_call_the_wiring_hands_the_chief_actually_runs(
            self):
        """THE ONE LINE THIS WHOLE REFACTOR EXISTS TO MAKE TRANSCRIPTION-PROOF.

        ``test_the_wiring_line_this_lane_hands_the_chief_actually_runs``
        above only ever walks the OLD four-piece recipe MOB_PICKUP_WIRING
        used to spell out by hand -- it never once calls the NEW headline
        one-call line the wiring note (and dispatch_pickup_request's own
        docstring) now actually hands the chief.  An adversarial pass proved
        that gap concretely: swapping the ``drop_ledger_cell``/``legacy``
        argument order in that exact headline string left the full 70-test
        suite green, because the older test only searches the string for
        substrings and never runs it.

        So this test does two things the older one does not.  First, it
        proves ``MOB_PICKUP_DISPATCH_HEADLINE_CALL`` -- the one place this
        exact call text is written down -- lives verbatim inside
        ``MOB_PICKUP_WIRING``, so nobody can edit the wiring's copy of the
        call without also editing the constant this test reads.  Second, it
        EXECUTES that exact text against real fixture objects, bound under
        the very names the headline text itself uses (``bag_cell``,
        ``drop_ledger_cell``, ``legacy``, ``identity``, ``x``, ``y``, ``z``,
        ``object_ref_u32``, ``opaque_u8``).  A wrong argument order sends the
        legacy module where the ledger cell belongs (or the reverse), which
        ``commit_pickup``'s own type check refuses; a wrong argument count is
        a ``TypeError``; a call to the wrong function name is an
        ``AttributeError``.  All three turn this test red instead of leaving
        it silently unable to notice.
        """
        headline = mob_pickup.MOB_PICKUP_DISPATCH_HEADLINE_CALL
        self.assertIn(headline, mob_pickup.MOB_PICKUP_WIRING)

        registry = BagCellRegistry()
        bag_cell = registry.claim(CHARACTER, INITIAL_BACKPACK)
        ground = a_cell(a_drop())
        namespace = {
            "mob_pickup": mob_pickup,
            "bag_cell": bag_cell,
            "drop_ledger_cell": ground,
            "legacy": self.legacy,
            "identity": KILLER,
            "x": 10.0,
            "y": 20.0,
            "z": 30.0,
            "object_ref_u32": KEY,
            "opaque_u8": 3,
        }
        exec("outcome = " + headline, namespace)  # noqa: S102 -- see docstring
        outcome = namespace["outcome"]
        self.assertEqual(type(outcome), PickupOutcome)
        self.assertEqual(ground.ledger.drops, (), "the drop left the ground")
        self.assertIsNotNone(outcome.delta)
        self.assertEqual(outcome.delta, bag_delta_pc(self.legacy, outcome.item))
        self.assertEqual(outcome.opaque_u8, 3)
        self.assertTrue(registry.release(CHARACTER))

    # -- dispatch_pickup_request: the one call that now replaces steps 1-4 --
    def test_dispatch_pickup_request_returns_a_usable_outcome_and_logs_the_row(
            self):
        """Success: one call, a usable delta, and the intended row on stdout.

        The row is LOGGED, not written -- this module has no cursor and no
        connection anywhere, so there is nothing for it to persist through.
        ``outcome.persisted`` stays the property's own hard-coded False, and
        the printed line names exactly the row ``outcome.row_write`` carries,
        so a human reading the console sees the same INSERT the wiring note
        promises once the item lane widens the allowlist.
        """
        registry = BagCellRegistry()
        bag_cell = registry.claim(CHARACTER, INITIAL_BACKPACK)
        ground = a_cell(a_drop())
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            outcome = dispatch_pickup_request(
                bag_cell, ground, self.legacy, KILLER, 10.0, 20.0, 30.0, KEY,
                7)
        self.assertEqual(type(outcome), PickupOutcome)
        self.assertEqual(ground.ledger.drops, (), "the drop left the ground")
        self.assertIsNotNone(outcome.delta)
        self.assertEqual(outcome.delta, bag_delta_pc(self.legacy, outcome.item))
        self.assertEqual(outcome.opaque_u8, 7)
        self.assertFalse(outcome.persisted, "this lane has never written a row")

        lines = captured.getvalue().splitlines()
        self.assertEqual(
            len(lines), 1, "exactly one console line for one accepted claim")
        line = lines[0]
        self.assertTrue(line.startswith("MOB_PICKUP_ROW_WOULD_INSERT"))
        self.assertEqual(line, bag_row_write_console_line(outcome.row_write))
        row = outcome.row_write
        self.assertIn("character_id=%d" % row.character_id, line)
        self.assertIn("item_identity=%d" % row.item_identity, line)
        self.assertIn("template_id=%d" % row.template_id, line)
        self.assertIn("slot=%d" % row.slot, line)
        self.assertTrue(registry.release(CHARACTER))

    def test_dispatch_pickup_request_never_touches_anything_db_shaped(self):
        """The module has no cursor and no connection; prove nothing reaches for one.

        A test double that fails loudly the moment anything DB-shaped is
        touched: if a future edit slipped a ``sqlite3.connect(...)`` (or any
        other use of the real module-level ``connect``) into the dispatch
        path, this turns red instead of quietly starting to persist rows the
        module's own NONCLAIM 10 and THE WALL say it must not.
        """
        def poisoned_connect(*args, **kwargs):
            raise AssertionError(
                "dispatch_pickup_request must never open a database "
                "connection -- gate 2 (is_unmoved_baseline) still refuses "
                "a relog with a picked-up item, so persistence stays a log, "
                "not an INSERT")

        bag_cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        ground = a_cell(a_drop())
        real_connect = sqlite3.connect
        sqlite3.connect = poisoned_connect
        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                outcome = dispatch_pickup_request(
                    bag_cell, ground, self.legacy, KILLER, 10.0, 20.0, 30.0,
                    KEY)
        finally:
            sqlite3.connect = real_connect
        self.assertEqual(type(outcome), PickupOutcome)
        self.assertFalse(outcome.persisted)

    def test_dispatch_pickup_request_refuses_cleanly_like_the_pieces_it_replaces(
            self):
        """A refusal through the single call is the SAME refusal by hand.

        Two shapes, both refused before any take: a reference this lane
        never issued, and one it issued but that has already left the
        ground.  Neither call site may wrap, swallow or rename the reason --
        callers of the one-call entry point need the exact same
        ``MOB_PICKUP_REFUSAL_REASONS`` name a caller assembling
        ``PickupClaim``/``commit_pickup`` by hand would see.
        """
        cell = a_cell(a_drop(key=KEY + 1))  # issued_through == KEY + 2
        bag_cell = BagCell(INITIAL_BACKPACK, CHARACTER)

        with self.assertRaises(MobPickupContractError) as caught:
            dispatch_pickup_request(
                bag_cell, cell, self.legacy, KILLER, 10.0, 20.0, 30.0,
                KEY + 500)
        self.assertEqual(caught.exception.args[0], "object_ref_never_issued")
        manual = self._refusal(
            resolve_claim, cell.ledger, a_claim(key=KEY + 500))
        self.assertEqual(manual, caught.exception.args[0])

        with self.assertRaises(MobPickupContractError) as caught:
            dispatch_pickup_request(
                bag_cell, cell, self.legacy, KILLER, 10.0, 20.0, 30.0, KEY)
        self.assertEqual(caught.exception.args[0], "drop_already_taken")
        manual = self._refusal(resolve_claim, cell.ledger, a_claim(key=KEY))
        self.assertEqual(manual, caught.exception.args[0])
        # Every refusal above leaves the one real row on the ground, and the
        # bag cell untouched -- a refusal through the one-call path costs
        # nothing more than a refusal through the pieces would have.
        self.assertEqual(len(cell.ledger.drops), 1)
        self.assertEqual(bag_cell.bag, INITIAL_BACKPACK)

    def test_dispatch_pickup_request_refuses_a_non_bagcell_type(self):
        """Not the registry, not a lookalike, not any other object type.

        This proves the TYPE check only: a ``bag_cell`` argument that is not
        an exact ``BagCell`` is refused by name instead of reaching an
        ``AttributeError`` from deep inside ``commit_pickup``.  It does NOT
        prove that the ``BagCell`` handed in belongs to the connection the
        claim's identity names -- a ``BagCell`` for a DIFFERENT character is
        the right TYPE and passes this check untouched.  See NONCLAIM 15:
        that ownership binding is not checked anywhere in this module today.
        """
        ground = a_cell(a_drop())
        self.assertEqual(
            self._refusal(
                dispatch_pickup_request, object(), ground, self.legacy,
                KILLER, 10.0, 20.0, 30.0, KEY),
            "type_not_typed_record")

    def test_a_key_taken_by_a_pickup_is_never_handed_out_again(self):
        ground = a_cell(a_drop())
        BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(ground, a_claim())
        self.assertEqual(ground.ledger.drops, ())
        self.assertGreater(
            ground.ledger.next_key, KEY,
            "a reused key would let a client hold a stale object under it")

    def test_losing_the_row_at_take_time_does_not_blame_a_rival(self):
        """The window a snapshot cannot close, and who is NOT accused in it.

        mob_loot's own wiring makes pruning mandatory and the label lives
        0.2-0.4 s, so the row is often removed by the CALLER'S OWN PRUNER in
        exactly the window a request travels.  The earlier message said
        "somebody else has it", which is false in that case -- nobody has it.
        """
        ground = a_cell(a_drop())

        def vanish(drop_key):
            raise mob_loot.MobLootContractError(
                mob_loot.REFUSE_DROP_NOT_IN_LEDGER, "pruned")

        ground.take = vanish
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        with self.assertRaises(MobPickupContractError) as caught:
            cell.commit_pickup(ground, a_claim())
        self.assertEqual(caught.exception.args[0], "drop_left_the_ground")
        self.assertNotIn("somebody else has it", caught.exception.args[1])
        self.assertEqual(
            cell.bag, INITIAL_BACKPACK,
            "a refusal at the take must not leave the bag holding the item")

    def test_a_cell_subclass_is_not_the_scenes_cell(self):
        class OtherCell(DropLedgerCell):
            pass

        ground = OtherCell(DropLedger((a_drop(),), 1, KEY + 1, ()))
        self.assertEqual(
            self._refusal(
                BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup,
                ground, a_claim()),
            "type_not_typed_record")

    def test_the_transaction_refuses_untyped_arguments(self):
        ground = a_cell(a_drop())
        cell = BagCell(INITIAL_BACKPACK, CHARACTER)
        self.assertEqual(
            self._refusal(cell.commit_pickup, object(), a_claim()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(cell.commit_pickup, ground, object()),
            "type_not_typed_record")
        self.assertEqual(
            self._refusal(BagCell, object(), CHARACTER),
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

        The item lane pinned this shape against frozen V141 for a MOVE.  It is
        ONE governed row -- identity 1 / template 2600001 / slot 2, a shape
        this lane can never produce -- so what it proves is that the two
        composers agree, not that this lane's own rows were ever seen.
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
        magic, declared = struct.unpack("<II", frame[:8])
        self.assertEqual(magic, DELTA_FRAME_MAGIC)
        self.assertEqual(declared, len(frame) - 8)
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_envelope_is_pinned_at_run_time_not_only_in_a_test(self):
        """THE LESSON mob_loot WROTE DOWN, applied here after it was ignored.

        The first version dual-derived only the seven inner ItemAttr fields
        and trusted the legacy module for everything around them.  An
        adversarial pass moved ITEM_OPERATE_RES_VITAL in a shim and this lane
        emitted the wrong bytes happily while mob_loot, given the same shim,
        refused.  A test going red does not help: tests do not run inside a
        server.
        """
        real = self.legacy

        class MovedVital:
            ITEM_OPERATE_RES_VITAL = 0x4C14

            def __getattr__(self, name):
                return getattr(real, name)

        class ExtraByte:
            def __getattr__(self, name):
                return getattr(real, name)

            @staticmethod
            def make_runtime_vitals(vitals):
                pc, _frame = real.make_runtime_vitals(vitals)
                pc = pc + b"\x00"
                return pc, real.frame_pc(pc)

        class ShortFrame:
            def __getattr__(self, name):
                return getattr(real, name)

            @staticmethod
            def make_runtime_vitals(vitals):
                pc, frame = real.make_runtime_vitals(vitals)
                return pc, frame[:-1]

        _bag, item = place_in_bag(EMPTY_BAG, a_drop())
        for shim in (MovedVital(), ExtraByte(), ShortFrame()):
            with self.subTest(shim=type(shim).__name__):
                self.assertEqual(
                    self._refusal(bag_delta_pc, shim, item),
                    "composed_bytes_off_pin")

    def test_the_envelope_pin_is_the_envelope_the_legacy_module_composes(self):
        """The literals, checked against the real thing once, here.

        Written as literals in the module on purpose -- that is what makes
        them notice a drift -- so exactly one place has to prove they are the
        right literals, and this is it.
        """
        _bag, item = place_in_bag(EMPTY_BAG, a_drop())
        pc, _frame = bag_delta_pc(self.legacy, item)
        self.assertTrue(pc.startswith(DELTA_PC_PREFIX_PIN))
        self.assertTrue(pc.endswith(DELTA_PC_SUFFIX_PIN))
        self.assertIn(
            self.legacy.u16tag(0x12, self.legacy.ITEM_OPERATE_RES_VITAL),
            DELTA_PC_PREFIX_PIN)
        self.assertIn(
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_RES),
            DELTA_PC_PREFIX_PIN)
        # 26 bytes of ItemAttr: qword 9, u32 5, u16 3, u16 3, u8 2, u8 2, u8 2.
        self.assertEqual(
            len(pc),
            len(DELTA_PC_PREFIX_PIN) + 26 + len(DELTA_PC_SUFFIX_PIN))

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

    # -- the wall ------------------------------------------------------------
    def test_the_governed_allowlist_is_the_wall_this_lane_stops_at(self):
        """BUILD-006's relog row, pinned as the blocker it actually is.

        COO-DECISION 20260826_0950 (a) tore down the first third of this:
        the character-SELECT load (``store._load_backpack``) is now
        ``inventory.require_backpack_shape``, which only checks structure, so
        that ONE layer no longer rejects a bag holding a picked-up item.
        COO-DECISION 20260828_0844 tore down the third third: the world-entry
        wire build (``inventory.make_backpack_attr``) now also calls
        ``require_backpack_shape`` instead of ``require_known_backpack``, so
        it can serialize the same bag too -- a narrow grant to this lane,
        since no separate item lane exists to have done it instead.  Gate 2
        (``session.select_and_start``'s ``is_unmoved_baseline`` opt-in check)
        is the one gate deliberately left standing: an earlier attempt to
        narrow it too was tried and reverted in the same round it was tried,
        because it turned out to be the exact gate
        ``tests/test_item_move_generalized.py::test_moved_state_reconnect_is_opt_in_and_baseline_fails_closed``
        needed at full strength to keep a HYP-PF-010/017/018 mutated state
        from reconnecting without its own opt-in flag.

        THAT DAY CAME, AND THIS TEST DID NOT GO RED -- WHICH IS WHY IT IS
        REWRITTEN.  ~~"Gate 2 alone still refuses this exact bag ... the day
        Gate 2 is also widened, THIS test goes red"~~ IS STRUCK: chief wired
        gate 2 to ``bag_admission.may_enter_world`` in PR #233 and this test
        stayed green, because the only thing it asserted about the wall was
        ``GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE``, a module constant that
        was ``True`` by assignment (chief's R222 letter, item 3).  A tripwire
        wired to a constant is not a tripwire.

        What it pins now is the wall where the wall actually is: all three
        gates admit this bag, and the relog is unclosed because ``store.py``
        never writes the row.  The INSERT itself is pinned by
        ``tests/test_bag_admission_expiry.py`` (an ast walk over the SQL
        ``store.py`` really executes, not over prose about it), so this test
        asserts the gates and the constants, and that file asserts the write.
        Together they go red the day ``STORE-INSERT-001`` lands -- and the
        round that lands it has to rewrite this lane's prose, which is what
        the original sentence was reaching for.
        """
        bag, item = place_in_bag(INITIAL_BACKPACK, a_drop())
        # Gate 1: store._load_backpack -- shape only, this bag is
        # structurally fine (unique identities, unique slots, in-range
        # fields), so it loads.
        inventory.require_backpack_shape(bag)
        with self.assertRaises(ValueError):
            inventory.require_known_backpack(bag)
        # Gate 2: session.select_and_start, which answers with no reply.
        # This is the gate that actually still stops a relog.
        self.assertFalse(inventory.is_unmoved_baseline(bag))
        # Gate 3: the world-entry attr build -- WIDENED this round
        # (COO-DECISION 20260828_0844).  It no longer raises for this bag;
        # it serializes it, structurally identical to the four-item golden's
        # own encoding, just with a fifth ItemAttr appended.
        wire = inventory.make_backpack_attr(self.legacy, bag)
        self.assertIsInstance(wire, bytes)
        # GATE 2 AS SESSION.PY ACTUALLY CALLS IT.  ``is_unmoved_baseline``
        # above is no longer the gate -- chief wired
        # ``bag_admission.may_enter_world`` in PR #233 -- so asserting only
        # the old predicate would keep this test green through the exact
        # change it exists to catch.
        self.assertTrue(bag_admission.may_enter_world(
            bag, allow_hypothesized_item_move=False,
        ))
        # The encoder writes each identity twice by design (the full ItemAttr
        # record, then the trailing identity-only index) -- see
        # inventory.make_backpack_attr's two item loops.
        self.assertEqual(wire.count(self.legacy.qwordtag(0x32, item.identity)), 2)
        # INITIAL_BACKPACK still byte-pins exactly as before -- gate 3
        # widening must not be allowed to drift the frozen encoding.
        self.assertEqual(
            inventory.make_backpack_attr(self.legacy, INITIAL_BACKPACK),
            self.legacy.make_backpack_attr_four_items())
        # THE CONSTANT IS RE-DERIVED FROM store.py, NOT READ BACK.  Asserting
        # ``assertFalse`` on a constant assigned ``False`` is the same
        # tautology as the ``assertTrue`` it replaced, with the polarity
        # flipped -- pf-adversary measured that: it simulated
        # STORE-INSERT-001 landing (a real INSERT INTO
        # character_backpack_items plus an UPDATE of next_item_identity) and
        # this file stayed green while test_bag_admission_expiry.py went red.
        # So the flag is checked against what store.py's EXECUTED SQL says,
        # by the same ast walk that file uses, and this test goes red on the
        # day the wall moves.
        pickup_inserts = [
            function for function, sql in _executed_sql("store")
            if "INSERT INTO character_backpack_items" in sql
            and function != "_insert_initial_backpack"
        ]
        advances = [
            function for function, sql in _executed_sql("store")
            if "next_item_identity" in sql and "UPDATE" in sql
        ]
        blocked = not pickup_inserts and not advances
        self.assertTrue(
            blocked,
            "store.py now writes a pickup row and/or advances the counter; "
            "the relog is no longer blocked and this lane's prose, its two "
            "GOVERNED_BAG_ALLOWLIST_* constants and "
            "scenarios/combat_pickup_001.json must be rewritten in the same "
            "round",
        )
        self.assertEqual(
            mob_pickup.GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE, not blocked,
        )
        # And the OWNER string must name the write that actually exists.
        # The first draft of this correction said "store.py has no backpack
        # INSERT", which is false -- character creation has one.
        creation_inserts = [
            function for function, sql in _executed_sql("store")
            if "INSERT INTO character_backpack_items" in sql
        ]
        self.assertEqual(creation_inserts, ["_insert_initial_backpack"])
        self.assertIn(
            "_insert_initial_backpack",
            mob_pickup.GOVERNED_BAG_ALLOWLIST_OWNER,
        )
        self.assertIn(
            "STORE-INSERT-001", mob_pickup.GOVERNED_BAG_ALLOWLIST_OWNER,
        )
        self.assertNotIn(
            "has no backpack INSERT",
            mob_pickup.GOVERNED_BAG_ALLOWLIST_OWNER,
        )
        self.assertEqual(item.identity, 5)
        # And the shape itself is fine -- it is Gate 2 that still governs.
        require_bag_shape(bag)

    def test_make_backpack_attr_still_rejects_a_structurally_invalid_bag(self):
        """Widening gate 3's CONTENT gate did not touch its SHAPE gate.

        ``make_backpack_attr`` delegates to ``require_backpack_shape``, which
        is well covered on its own (``tests/test_item_lifecycle.py``'s
        ``RequireBackpackShapeTests``) -- but nothing called the public entry
        point that actually changed this round, ``make_backpack_attr``
        itself, with a structurally malformed state.  This closes that gap
        directly: a duplicate-slot bag must still raise through the encoder,
        exactly as it did before the gate widening.
        """
        duplicate_slot = BackpackState(
            INITIAL_BACKPACK.base_mask,
            INITIAL_BACKPACK.base_identity,
            INITIAL_BACKPACK.range_mask,
            INITIAL_BACKPACK.items + (
                ItemAttrState(5, 2600001, 1, 0),  # slot 0 already taken
            ),
        )
        with self.assertRaises(ValueError):
            inventory.make_backpack_attr(self.legacy, duplicate_slot)

    def test_gate_3_widening_does_not_touch_the_content_aware_operations(self):
        """COO-DECISION 20260828_0844 widened ONE function, not the family.

        ``make_backpack_attr`` now accepts any structurally valid bag, but
        ``move_known_item_to_free_slot`` / ``swap_known_item_with_occupied_slot``
        / ``merge_known_item_into_occupied_slot`` all still call
        ``require_known_backpack`` on entry and must still refuse the exact
        same drifted bag -- the decision's scope was the encoder only.
        """
        bag, _item = place_in_bag(INITIAL_BACKPACK, a_drop())
        with self.assertRaises(ValueError):
            inventory.move_known_item_to_free_slot(bag, 1, 10)
        with self.assertRaises(ValueError):
            inventory.swap_known_item_with_occupied_slot(bag, 1, 1)
        with self.assertRaises(ValueError):
            inventory.merge_known_item_into_occupied_slot(bag, 1, 1)

    def test_the_lane_never_says_a_pickup_survives_a_relog(self):
        outcome = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            a_cell(a_drop()), a_claim())
        self.assertFalse(outcome.persisted)
        report = pickup_report(outcome)
        self.assertFalse(report["persisted"])
        self.assertFalse(report["survives_a_relog"])
        self.assertEqual(report["item_name"], outcome.display_name)
        self.assertEqual(report["claimed_by"], KILLER)
        self.assertEqual(report["from_the_kill_of"], MOB)
        self.assertEqual(
            self._refusal(pickup_report, object()), "type_not_typed_record")

    def test_a_report_never_raises_on_a_row_outside_this_lanes_tables(self):
        """display_name must be TOTAL, because it runs after the take.

        PickupOutcome deliberately has no __post_init__ -- it is built once
        the row has left the ground, so a validator there would be a refusal
        that destroys what it refuses.  The price is that everything reading
        it must be total, and display_name was not: it indexed the drop table
        directly, so an outcome naming one of the four rows a character SHIPS
        with raised a bare KeyError inside a listener thread.
        """
        shipped = INITIAL_BACKPACK.items[0]
        self.assertNotIn(shipped.template_id, mob_loot.field_drop_tables.ITEMS)
        good = BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup(
            a_cell(a_drop()), a_claim())
        outside = PickupOutcome(
            good.drop, shipped, good.bag_before, good.bag_after,
            good.row_write)
        self.assertEqual(
            outside.display_name, "item %d" % shipped.template_id)
        report = pickup_report(outside)
        self.assertEqual(report["item_name"], outside.display_name)

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
            # BagCellTaken subclasses MobPickupContractError and is raised
            # with a declared reason, so it counts as one of this lane's
            # refusals -- a collector that saw only the base name would call
            # bag_already_claimed unreachable.
            if getattr(call.func, "id", "") not in (
                    "MobPickupContractError", "BagCellTaken"):
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

    def test_every_refusal_is_reached_by_an_actual_call_in_this_file(self):
        """The AST test above proves a raise EXISTS; this proves one HAPPENS.

        An adversarial pass found two named refusals that only a hand-built
        record could reach -- constructed by stepping around the constructors
        that make them impossible.  A refusal nothing in the suite provokes
        through the public surface is a refusal nothing in the game can
        provoke either.

        TWO ENTRIES BELOW DO NOT MEET THAT STANDARD AND SAY SO.  There is no
        deterministic public-surface path to drop_left_the_ground -- the
        ordinary loser of a race gets drop_already_taken, because the window
        between resolve and take is a handful of instructions -- so it is
        provoked by patching the ledger cell's take.  composed_bytes_off_pin
        needs a legacy module that has drifted, which only a shim can be.
        Both are real runtime possibilities that a test cannot schedule; the
        rest are reached the way a player would reach them.
        """
        provoked = set()

        def note(call, *args, **kwargs):
            try:
                call(*args, **kwargs)
            except MobPickupContractError as exc:
                provoked.add(exc.args[0])

        ground = a_cell(a_drop(key=KEY + 1, at=(0.0, 0.0, 0.0)))
        note(PickupClaim, 0, 1.0, 2.0, 3.0, KEY)                # identity
        note(PickupClaim, KILLER, float("nan"), 2.0, 3.0, KEY)  # position
        note(PickupClaim, KILLER, 1.0, 2.0, 3.0, "1")           # not int
        note(PickupClaim, KILLER, 1.0, 2.0, 3.0, -1)            # out of range
        note(resolve_claim, object(), a_claim())                # not typed
        note(resolve_claim, ground.ledger, a_claim(key=KEY))    # already taken
        note(resolve_claim, ground.ledger, a_claim(key=KEY + 500))
        note(resolve_claim, ground.ledger,
             a_claim(key=KEY + 1, identity=STRANGER))
        note(resolve_claim, ground.ledger,
             a_claim(key=KEY + 1, at=(PICKUP_RADIUS + 10.0, 0.0, 0.0)))
        note(first_free_slot, a_full_bag())
        note(next_item_identity, INITIAL_BACKPACK, 2)
        note(next_item_identity, BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(MAX_ITEM_IDENTITY, ITEM, 1, 0),)))
        note(require_bag_shape, BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
            (ItemAttrState(1, ITEM, 1, 0), ItemAttrState(2, ITEM, 1, 0))))
        pruned = a_cell(a_drop())
        pruned.take = lambda key: (_ for _ in ()).throw(
            mob_loot.MobLootContractError(
                mob_loot.REFUSE_DROP_NOT_IN_LEDGER, "pruned"))
        note(BagCell(INITIAL_BACKPACK, CHARACTER).commit_pickup,
             pruned, a_claim())
        registry = BagCellRegistry()
        registry.claim(CHARACTER, INITIAL_BACKPACK)
        note(registry.claim, CHARACTER, INITIAL_BACKPACK)   # already claimed
        note(bag_delta_pc, self.legacy, object())

        class MovedVital:
            ITEM_OPERATE_RES_VITAL = 0x4C14

            def __getattr__(inner, name):
                return getattr(self.legacy, name)

        note(bag_delta_pc, MovedVital(), ItemAttrState(1, ITEM, 1, 0))
        self.assertEqual(
            set(MOB_PICKUP_REFUSAL_REASONS) - provoked, set(),
            "refusal names nothing in this suite can provoke through the "
            "module's own surface")

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

    def test_the_object_reference_nonclaim_reports_re_082_as_closed(self):
        """RE-082 answered NONCLAIM 2 PASS/DONE on 2026-08-26 -- say so.

        The stale shape ("awaiting COO/RE confirmation") is exactly the
        failure this whole project is built to avoid: a diagnosis that was
        true once, never re-derived, and left standing as if it still were.
        This pins the corrected wording so a future edit cannot silently put
        the "awaiting" framing back without turning a test red.
        """
        nonclaim_2 = next(
            claim for claim in MOB_PICKUP_NONCLAIMS
            if claim.startswith("2. ")
        )
        self.assertIn("RE-082", nonclaim_2)
        self.assertIn("CONFIRMED", nonclaim_2)
        self.assertNotIn("awaiting COO/RE confirmation", nonclaim_2)
        # the guard itself must still say it resolves rather than trusts --
        # confirmation is not a reason to relax the runtime check
        self.assertIn("RESOLVED against the", nonclaim_2)
        # and the same correction must be in the module docstring, not only
        # in the constant a test can see without reading the prose around it
        self.assertIn("RE-082 CONFIRMED IT AT THE", self.source)
        self.assertNotIn("awaiting COO/RE confirmation", self.source)

    def test_the_lane_carries_forward_the_precondition_its_own_half_measured(self):
        """mob_loot NONCLAIM 4, not left behind in the sibling module.

        GT-046's producer needs a selected live drop-object; GT-045 measured
        that this pipe draws a label with no model under it.  So no player can
        originate a claim at all today, and that is a different fact from the
        object reference being the wrong value.
        """
        joined = "".join(MOB_PICKUP_NONCLAIMS)
        self.assertIn("NO PLAYER CAN ORIGINATE A CLAIM TODAY", joined)
        self.assertIn("nothing to click", joined)

    def test_the_pin_document_reports_what_the_lane_did_not_what_it_believes(self):
        """Every boolean here is OBSERVED by pin_document running the lane.

        The first version wrote them as literals, which made this test a set
        of tautologies -- and left "everything refuses before the take"
        reading True while a refusal outside its reach destroyed drops.  To
        prove they move, the ordering flag is recomputed against a lane whose
        ordering has been broken on purpose.
        """
        document = pin_document(self.legacy)
        self.assertTrue(document["production_allowed"])
        self.assertFalse(document["test_only"])
        self.assertIsNone(document["scenario"])
        self.assertFalse(document["wire"]["ever_observed_for_a_new_item"])
        # ~~assertTrue~~ IS STRUCK, and the flip is the point: this document
        # reported "relog_persistence: True, blocked_by: gate 2" for the
        # whole day after PR #233 opened gate 2, because the value was a
        # module constant assigned True rather than anything observed.  What
        # blocks the relog is that store.py writes no row at all.
        self.assertFalse(document["blocked"]["relog_persistence"])
        self.assertIn("store.py", document["blocked"]["blocked_by"])
        self.assertIn("STORE-INSERT-001", document["blocked"]["blocked_by"])
        observed = document["transaction_observed"]
        self.assertFalse(observed["stacks"])
        self.assertTrue(observed["killer_only"])
        self.assertTrue(observed["resolves_object_ref_against_the_ledger"])
        self.assertTrue(
            observed["everything_that_refuses_refuses_before_the_take"])
        self.assertTrue(observed["a_second_bag_cell_for_one_character_loses"])
        self.assertTrue(
            observed["pickup_radius_reaches_the_furthest_object_of_one_kill"])
        # The flag above is only as good as what it walked, so the walk is
        # published beside it -- including the byte composer, which is the
        # family the wiring line used to run AFTER the take.
        self.assertIn("composer", observed["refusals_walked_for_that_flag"])
        self.assertIn("bag_is_full", observed["refusals_walked_for_that_flag"])
        declared = document["transaction_declared"]
        self.assertEqual(declared["pickup_radius"], PICKUP_RADIUS)
        self.assertTrue(declared["pickup_radius_is_arithmetic_not_measured"])
        self.assertTrue(declared["pickup_radius_derived_on_x_only"])
        self.assertEqual(document["refusals"], list(MOB_PICKUP_REFUSAL_REASONS))
        # The sample row must be READABLE: eight columns, eight values, and
        # the shipped file used to print seven values under eight names.
        sample = document["bag_row"]["sample_row"]
        self.assertEqual(list(sample), list(BagRowWrite.COLUMNS))
        self.assertEqual(sample["template_id"], ITEM)

    def test_the_pin_documents_ordering_flag_can_actually_read_false(self):
        """THE FLAG, ACTUALLY RECOMPUTED under a deliberately broken order.

        The first version of this test inverted the order, checked that the
        ground moved, and stopped -- it never called the function whose output
        it was named for, while its docstring said "recomputed".  A control
        that does not run the thing it controls is a claim, not a control.
        """
        honest = mob_pickup._observed_behaviour(self.legacy)
        self.assertTrue(
            honest["everything_that_refuses_refuses_before_the_take"])

        real_commit = BagCell.commit_pickup

        def takes_first(cell_self, ledger_cell, claim, legacy=None):
            # The careless edit this flag exists to notice: pull the row off
            # the ground before finding out whether the bag can hold it.
            try:
                ledger_cell.take(claim.object_ref_u32)
            except mob_loot.MobLootContractError:
                pass
            return real_commit(cell_self, ledger_cell, claim, legacy)

        BagCell.commit_pickup = takes_first
        try:
            broken = mob_pickup._observed_behaviour(self.legacy)
        finally:
            BagCell.commit_pickup = real_commit
        self.assertFalse(
            broken["everything_that_refuses_refuses_before_the_take"],
            "the flag cannot read False, so its True says nothing")
        self.assertIs(BagCell.commit_pickup, real_commit)
        self.assertTrue(
            mob_pickup._observed_behaviour(self.legacy)[
                "everything_that_refuses_refuses_before_the_take"],
            "the control leaked into the next reading")

    def test_the_shipped_pin_file_is_what_the_code_computes(self):
        self.assertEqual(
            json.loads(PIN_PATH.read_text(encoding="utf-8")),
            json.loads(json.dumps(pin_document(self.legacy), sort_keys=True)))


if __name__ == "__main__":
    unittest.main()
