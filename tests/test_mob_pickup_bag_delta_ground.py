"""LANE-B round ewq4js: what the BAG DELTA does to the floor under it.

STEP 3 of COO-DECISION 2026-09-02T10:44+07:00 (carrier composer -> removal
publisher -> ``bag_delta_pc``).  The first two are on main; this is the third
and last opt-in site of the lane.

THE ONE FACT THIS FILE IS ABOUT.  A bag delta is a RuntimeRes, so v141's own
composer puts an EMPTY derived mask on it -- "there is no ground pool" -- and
a client that reads one clears the floor.  Until this round every successful
pickup sent that frame, which meant the objects a player had NOT picked up
went off the screen together with the one they had.

The answer is not "always preserve".  It is one number, known inside the
transaction and nowhere else -- how many rows the scene has left after the
take:

  * rows left > 0 -> KEEP the floor.  The removal publication that follows
    (round lh21ua) names the survivors and RE-082 turns the omission of the
    taken key into its removal.
  * rows left == 0 -> CLEAR it, on purpose.  An empty floor is what v141's
    mask truthfully describes, and it is the only thing in this project that
    takes the LAST object of a scene off the screen: an empty generation is a
    measured client no-op (RE-082), which is the hole RE-208 is open on.

Every test below reads the answer out of the COMPOSED BYTES.  Nothing here
asks the module what it meant to do.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_drop_tables,
    mob_combat,
    mob_loot,
    mob_pickup,
)
from pirateforce_foundation.inventory import (  # noqa: E402
    BACKPACK_BASE_IDENTITY,
    BACKPACK_BASE_MASK,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.mob_pickup import (  # noqa: E402
    DELTA_PC_PRESERVE_SUFFIX_PIN,
    DELTA_PC_SUFFIX_PIN,
    BagCell,
    BackpackState,
    MobPickupContractError,
    PickupClaim,
    bag_delta_pc,
    place_in_bag,
)

SCENE = field_drop_tables.SCENE
ELSEWHERE = "Bg0002"
MOB, KILLER = 0x201F, 0x750059


def a_drop(offset=0, scene=SCENE):
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + offset, 2400046, 1,
        mob_loot.as_wire_float(0.0), mob_loot.as_wire_float(0.0),
        mob_loot.as_wire_float(0.0), MOB, KILLER, scene)


def a_cell(*drops, scene=SCENE):
    return mob_loot.DropLedgerCell(
        mob_loot.DropLedger(
            tuple(drops), 1, max(d.drop_key for d in drops) + 1, ()),
        scene=scene)


def an_empty_bag():
    return BackpackState(BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())


class LegacyFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def an_item(self):
        _bag, item = place_in_bag(an_empty_bag(), a_drop())
        return item


class TheTwoEnvelopesTests(LegacyFixture):
    """Two pinned shapes, and NOTHING between or beside them."""

    def test_the_kept_floor_changes_the_last_record_and_nothing_else(self):
        item = self.an_item()
        cleared, _f1 = bag_delta_pc(self.legacy, item)
        kept, _f2 = bag_delta_pc(self.legacy, item, preserve_ground=True)
        self.assertNotEqual(cleared, kept)
        # MEASURED, not asserted from the pins: strip each pc's own trailing
        # derived-mask record and the two must be the same bytes.
        self.assertEqual(
            cleared[:-len(mob_loot.RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)],
            kept[:-len(mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)])
        self.assertTrue(cleared.endswith(DELTA_PC_SUFFIX_PIN))
        self.assertTrue(kept.endswith(DELTA_PC_PRESERVE_SUFFIX_PIN))

    def test_this_lanes_literal_and_the_ground_lanes_agree(self):
        """The pin is a literal HERE so the day mob_loot moves is a red test.

        The first draft of it wrote the list-count tag as 0x0F -- the tag the
        ItemAttr fields beside it use -- instead of 0x12, and this is the
        comparison that would have caught it.
        """
        self.assertTrue(DELTA_PC_PRESERVE_SUFFIX_PIN.endswith(
            mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN))
        self.assertEqual(
            DELTA_PC_PRESERVE_SUFFIX_PIN[:-len(
                mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)],
            DELTA_PC_SUFFIX_PIN[:-len(
                mob_loot.RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)])

    def test_a_kept_floor_is_refused_when_nobody_asked_for_one(self):
        """The permissive half of an exhaustive match, driven.

        A composer that started putting the ground list on every RuntimeRes
        would otherwise reach the wire through the DEFAULT path, where this
        lane has decided the floor must be cleared.
        """
        item = self.an_item()
        original = self.legacy.make_runtime_vitals

        def preserving(vitals):
            # v141's own bytes with the ground list turned ON, composed HERE
            # rather than by calling the preserve composer -- that composer
            # drives ``make_runtime_vitals``, which is the name being shimmed,
            # and the first draft of this test recursed until the stack ended.
            pc, _frame = original(vitals)
            pc = (pc[:-len(mob_loot.RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)]
                  + mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)
            return pc, self.legacy.frame_pc(pc)

        self.legacy.make_runtime_vitals = preserving
        self.addCleanup(
            setattr, self.legacy, "make_runtime_vitals", original)
        with self.assertRaises(MobPickupContractError) as caught:
            bag_delta_pc(self.legacy, item)
        self.assertEqual(
            caught.exception.args[0], mob_pickup.REFUSE_COMPOSED_BYTES_OFF_PIN)

    def test_a_third_envelope_is_refused_on_both_paths(self):
        item = self.an_item()
        original = self.legacy.make_runtime_vitals

        def one_byte_more(vitals):
            pc, _frame = original(vitals)
            pc = pc + b"\x00"
            return pc, self.legacy.frame_pc(pc)

        self.legacy.make_runtime_vitals = one_byte_more
        self.addCleanup(
            setattr, self.legacy, "make_runtime_vitals", original)
        for asked in (False, True):
            with self.subTest(preserve_ground=asked):
                with self.assertRaises(MobPickupContractError) as caught:
                    bag_delta_pc(self.legacy, item, preserve_ground=asked)
                self.assertEqual(caught.exception.args[0],
                                 mob_pickup.REFUSE_COMPOSED_BYTES_OFF_PIN)


class TheFallBackTests(LegacyFixture):
    """A refused preserve costs the FLOOR, never the item and never the frame."""

    def _refuse_the_preserve(self, exc):
        original = mob_loot.preserve_ground_in_runtime_res_vitals

        def boom(*_args, **_kwargs):
            raise exc

        mob_loot.preserve_ground_in_runtime_res_vitals = boom
        self.addCleanup(
            setattr, mob_loot, "preserve_ground_in_runtime_res_vitals",
            original)

    def test_a_refused_preserve_returns_v141s_own_bytes_and_says_so(self):
        item = self.an_item()
        expected, _frame = bag_delta_pc(self.legacy, item)
        self._refuse_the_preserve(
            mob_loot.MobLootContractError("composer_moved", "measured"))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            pc, frame = bag_delta_pc(self.legacy, item, preserve_ground=True)
        self.assertEqual(pc, expected)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        line = buffer.getvalue().strip()
        self.assertEqual(len(line.splitlines()), 1)
        self.assertIn(mob_combat.GROUND_VITALS_PRESERVE_REFUSED_TOKEN, line)
        self.assertIn(mob_pickup.BAG_DELTA_PRESERVE_SITE, line)
        # The other site must not be named on this line: an operator greps
        # the console to find out WHICH frame lost the floor.
        self.assertNotIn(mob_combat.GROUND_VITALS_PRESERVE_SITE, line)
        line.encode("ascii")

    def test_an_attribute_error_out_of_a_moved_serializer_falls_back_too(self):
        item = self.an_item()
        expected, _frame = bag_delta_pc(self.legacy, item)
        self._refuse_the_preserve(AttributeError("u8tag"))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            pc, _frame = bag_delta_pc(self.legacy, item, preserve_ground=True)
        self.assertEqual(pc, expected)
        self.assertIn("AttributeError", buffer.getvalue())

    def test_a_console_that_cannot_be_written_costs_the_line_not_the_frame(self):
        """cp874, errors='strict': a print is a statement that can raise."""
        item = self.an_item()
        expected, _frame = bag_delta_pc(self.legacy, item)
        self._refuse_the_preserve(
            mob_loot.MobLootContractError("composer_moved", "measured"))

        class RefusingStdout(io.StringIO):
            def write(self, _text):
                raise OSError("the bridge console is gone")

        with redirect_stdout(RefusingStdout()):
            pc, _frame = bag_delta_pc(self.legacy, item, preserve_ground=True)
        self.assertEqual(pc, expected)


class TheTransactionComposesBothTests(LegacyFixture):
    """The transaction composes both envelopes and chooses NEITHER.

    pf-adversary's correction of this round's first draft, which decided
    inside the transaction from a row count taken before the take.  Two
    measured routes to a permanent ghost with that shape: a row expiring
    between the count's sweep and the take's sweep (the bag cell's lock does
    not span the ground cell's two acquisitions), and a removal publication
    that refuses after a floor was kept for it.  The count is gone; the
    choice belongs to the layer that can see the whole reply.
    """

    def _pick_up(self, cell, key_offset=0):
        claim = PickupClaim(
            KILLER, 0.0, 0.0, 0.0, mob_loot.DROP_KEY_BASE + key_offset)
        return BagCell(an_empty_bag(), 1).commit_pickup(
            cell, claim, self.legacy)

    def test_both_envelopes_come_back_and_the_default_is_yesterdays(self):
        outcome = self._pick_up(a_cell(a_drop(0), a_drop(1)))
        self.assertTrue(outcome.delta[0].endswith(DELTA_PC_SUFFIX_PIN))
        self.assertTrue(
            outcome.delta_floor_kept[0].endswith(DELTA_PC_PRESERVE_SUFFIX_PIN))
        self.assertEqual(
            outcome.delta, bag_delta_pc(self.legacy, outcome.item))

    def test_the_floor_count_no_longer_decides_anything(self):
        """The last row of a scene and a scene with rows left compose the SAME
        pair.  A count taken before the take cannot be trusted, so nothing in
        here reads one."""
        beside_another = self._pick_up(a_cell(a_drop(0), a_drop(1)))
        the_last_one = self._pick_up(a_cell(a_drop(0)))
        self.assertEqual(beside_another.delta, the_last_one.delta)
        self.assertEqual(
            beside_another.delta_floor_kept, the_last_one.delta_floor_kept)

    def test_a_refused_preserve_makes_the_two_envelopes_equal(self):
        """The fall back is visible to the caller without being announced."""
        original = mob_loot.preserve_ground_in_runtime_res_vitals

        def boom(*_args, **_kwargs):
            raise mob_loot.MobLootContractError("composer_moved", "measured")

        mob_loot.preserve_ground_in_runtime_res_vitals = boom
        self.addCleanup(
            setattr, mob_loot, "preserve_ground_in_runtime_res_vitals",
            original)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            outcome = self._pick_up(a_cell(a_drop(0), a_drop(1)))
        self.assertEqual(outcome.delta, outcome.delta_floor_kept)
        self.assertTrue(
            outcome.delta_floor_kept[0].endswith(DELTA_PC_SUFFIX_PIN))

    def test_rows_standing_in_another_scene_are_not_this_floor(self):
        """WAY 1 (COO-DECISION 2026-09-02T02:52+07:00) still holds underneath.

        A row that fell in scene A stays in the ledger while the player is in
        scene B and is not on their screen.  The take is resolved against the
        claimant's scene either way; what this pins is that the OTHER scene's
        row survives a pickup in this one.
        """
        cell = a_cell(a_drop(0), a_drop(1, scene=ELSEWHERE))
        outcome = self._pick_up(cell)
        self.assertEqual(outcome.item.slot, 0)
        self.assertEqual(
            [row.drop_key for row in cell.ledger.drops],
            [mob_loot.DROP_KEY_BASE + 1])

    def test_the_item_still_reaches_the_bag_when_the_floor_cannot_be_kept(self):
        original = mob_loot.preserve_ground_in_runtime_res_vitals

        def boom(*_args, **_kwargs):
            raise AttributeError("u8tag")

        mob_loot.preserve_ground_in_runtime_res_vitals = boom
        self.addCleanup(
            setattr, mob_loot, "preserve_ground_in_runtime_res_vitals",
            original)
        cell = a_cell(a_drop(0), a_drop(1))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            outcome = self._pick_up(cell)
        self.assertEqual(outcome.item.slot, 0)
        self.assertEqual(
            [row.drop_key for row in cell.ledger.drops],
            [mob_loot.DROP_KEY_BASE + 1])


class ThePinDocumentSaysBothTests(LegacyFixture):
    """The document in scenarios/ carries what a round claims on the console."""

    def test_both_flags_are_observed_true_by_running_the_lane(self):
        observed = mob_pickup._observed_behaviour(self.legacy)
        self.assertIs(observed["bag_delta_default_clears_the_ground"], True)
        self.assertIs(
            observed["bag_delta_second_envelope_keeps_the_ground"], True)

    def test_no_flag_in_the_document_claims_a_rule_the_code_no_longer_has(self):
        """pf-adversary D4: a typed True beside four re-derived pins.

        The struck flag named a decision made from a row count inside the
        transaction, which D1 removed.  Nothing may bring back a claim about
        it that no code makes.
        """
        document = mob_pickup.pin_document(self.legacy)
        flat = repr(document)
        self.assertNotIn("ground_kept_when_rows_remain", flat)
        self.assertNotIn("cleared_on_the_last_row", flat)

    def test_the_two_pcs_in_the_document_are_the_two_this_lane_composes(self):
        document = mob_pickup.pin_document(self.legacy)
        _bag, item = place_in_bag(an_empty_bag(), a_drop())
        kept, _frame = bag_delta_pc(self.legacy, item, preserve_ground=True)
        cleared, _frame = bag_delta_pc(self.legacy, item)
        self.assertEqual(document["wire"]["ground_kept_pc_size"], len(kept))
        self.assertEqual(document["wire"]["pc_size"], len(cleared))
        shared = 0
        while (shared < min(len(kept), len(cleared))
               and kept[shared] == cleared[shared]):
            shared += 1
        self.assertEqual(
            document["wire"]["ground_kept_shared_prefix_size"], shared)
        # ONE BYTE MORE than "everything before the derived-mask record", and
        # the difference is worth writing down rather than rounding off: both
        # tails OPEN with the same 0x0B tag and differ on the value after it,
        # so the two pcs agree on 70 of the 71 bytes the cleared one has.
        self.assertEqual(shared, len(cleared) - 1)


if __name__ == "__main__":
    unittest.main()
