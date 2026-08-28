"""LANE-B: the gate-2 admission rule admits a pickup and still refuses
every governed hypothesis post-state.

WHY THIS FILE IS SHAPED AS AN ENUMERATION RATHER THAN A LIST OF CASES.  The
previous attempt at separating gate 2 was not wrong in an exotic state -- it
was wrong in an ORDINARY one, and it was caught by an existing test rather
than by its own.  A handful of hand-picked examples would have passed that
attempt too: it narrowed the predicate to "just the slot-2 case", and any
test author writing cases by hand writes the slot-2 case.

So this file does not choose the states it checks.  It generates the
post-states the governed family can reach -- both goldens x every item they
hold x all 40 slots x the three real ``inventory`` mutators, plus the ONE
shipped post-state constant (``HYPOTHESIZED_V111_SLOT2_BACKPACK``; the merged
golden is not yielded as a constant, it arrives as a merge output) -- and
requires them to be refused, with one exemption pinned by name.  If a future
edit to ``bag_admission`` admits any member of that family, this file goes red
on the member, not on a case someone remembered to write.

READ ``test_the_enumeration_counts_are_pinned_including_the_one_that_is_zero``
BEFORE QUOTING THIS FILE AS EXHAUSTIVE.  It is one mutation deep, and it
asserts nothing at all about HYP-PF-018.

The other half is grounded the same way: the admitted bag is not an
``ItemAttrState`` assembled here.  It is whatever ``mob_pickup.place_in_bag``
-- the real producer, the only INSERT this lane has -- returns for a real
``mob_loot.GroundDrop``.  A test that admits a hand-made row proves the
predicate accepts the test author's idea of a pickup; this one proves it
accepts the pickup path's.

MEASURED, the mutation that matters (``test_the_unchanged_check_is_load_
bearing``): weaken the "every golden item present AND unchanged" check to
"the golden identities are all present", which is the obvious simplification
a later reader might make, and the HYP-PF-008 shipped post-state is ADMITTED.
That is the whole failure of the previous attempt, reproduced here as an
assertion so the check cannot be simplified back into it.
"""

from __future__ import annotations

import ast
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    bag_admission, field_mobs, inventory, mob_loot, mob_pickup,
)
from pirateforce_foundation.inventory import (
    BACKPACK_BASE_IDENTITY,
    BACKPACK_BASE_MASK,
    BACKPACK_RANGE_MASK,
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    BackpackState,
    ItemAttrState,
    is_unmoved_baseline,
    merge_known_item_into_occupied_slot,
    move_known_item_to_free_slot,
    swap_known_item_with_occupied_slot,
)

GOLDENS = (INITIAL_BACKPACK, MERGED_V111_BACKPACK)
ITEM = 2400046  # the roster's most common drop, as tests/test_mob_pickup.py uses
KEY = mob_loot.DROP_KEY_BASE
MOB = 0x2068
KILLER = 0x750059


def a_drop(key=KEY, item=ITEM, quantity=1, at=(10.0, 20.0, 30.0)):
    return mob_loot.GroundDrop(
        key, item, quantity,
        mob_loot.as_wire_float(at[0]), mob_loot.as_wire_float(at[1]),
        mob_loot.as_wire_float(at[2]), MOB, KILLER,
    )


def governed_post_states():
    """Every state the HYP-PF-008/010/017/018 family can reach from a golden.

    Yields ``(label, state)``.  A mutator that refuses a particular
    (item, slot) pair contributes nothing -- a refusal is not a post-state --
    and a same-slot no-op returns ``None``, which is not one either.
    """
    for golden_index, golden in enumerate(GOLDENS):
        for item in golden.items:
            for slot in range(bag_admission.BAG_SLOT_COUNT):
                base = f"golden{golden_index}/identity{item.identity}/slot{slot}"
                try:
                    moved = move_known_item_to_free_slot(
                        golden, item.identity, slot,
                    )
                except (KeyError, FileExistsError, ValueError):
                    moved = None
                if moved is not None:
                    yield f"HYP-PF-010 {base}", moved[0]
                try:
                    swapped = swap_known_item_with_occupied_slot(
                        golden, item.identity, slot,
                    )
                except (KeyError, FileExistsError, LookupError, ValueError):
                    swapped = None
                if swapped is not None:
                    yield f"HYP-PF-017 {base}", swapped[0]
                try:
                    # No TypeError arm: the first draft named one and the
                    # mutator cannot raise it.  A named catch nothing can
                    # reach is the defect mob_pickup spends three paragraphs
                    # removing from itself.
                    merged = merge_known_item_into_occupied_slot(
                        golden, item.identity, slot,
                    )
                except (KeyError, FileExistsError, LookupError, ValueError):
                    merged = None
                if merged is not None:
                    yield f"HYP-PF-018 {base}", merged[0]
    yield "HYP-PF-008 shipped post-state", HYPOTHESIZED_V111_SLOT2_BACKPACK


class GoldenBagsTests(unittest.TestCase):
    def test_both_goldens_are_admitted_as_golden_not_as_acquired(self):
        for index, golden in enumerate(GOLDENS):
            with self.subTest(golden=index):
                admission = bag_admission.classify(golden)
                self.assertEqual(
                    admission.verdict, bag_admission.VERDICT_GOLDEN,
                )
                self.assertEqual(admission.golden_index, index)
                self.assertEqual(admission.acquired, ())
                self.assertTrue(admission.admissible)
                # The new term is deliberately False for a plain golden: it
                # is OR-ed beside is_unmoved_baseline, not over it.
                self.assertFalse(bag_admission.is_golden_plus_acquired(golden))
                self.assertTrue(bag_admission.may_enter_world(
                    golden, allow_hypothesized_item_move=False,
                ))


class GovernedFamilyStaysRefusedTests(unittest.TestCase):
    """The guard the previous attempt broke, over the whole family."""

    def test_the_enumeration_counts_are_pinned_including_the_one_that_is_zero(self):
        """What this file actually asserts about each hypothesis, by number.

        The first draft asserted ``any(label.startswith("HYP-PF-018"))`` and
        passed -- reporting coverage of a hypothesis whose ONLY state is the
        one the refusal test then skips.  A green "we cover 018" from a loop
        with zero asserted 018 iterations is worse than no claim at all, so
        the counts are pinned instead, and the zero is written down as a
        zero.

        HYP-PF-018 having exactly one state is not a gap in the generator:
        ``merge_known_item_into_occupied_slot`` refuses 24 of the 25
        (item, slot) pairs inside ``require_known_backpack``, so there is no
        other merge post-state to reach.  What this file cannot do is tell
        that apart from a generator that silently swallowed them -- which is
        why the pin exists and why the module docstring says the real
        closure came from composing the mutators to depth 3, not from here.
        """
        counted = {}
        asserted = {}
        for label, state in governed_post_states():
            key = label.split(" ", 1)[0]
            counted[key] = counted.get(key, 0) + 1
            if state not in GOLDENS:
                asserted[key] = asserted.get(key, 0) + 1

        self.assertEqual(
            counted,
            {"HYP-PF-010": 255, "HYP-PF-017": 18, "HYP-PF-018": 1,
             "HYP-PF-008": 1},
        )
        self.assertEqual(
            asserted,
            {"HYP-PF-010": 255, "HYP-PF-017": 18, "HYP-PF-008": 1},
            "HYP-PF-018 is absent from this mapping on purpose: its only "
            "state is the exempted V111 merge, so this file asserts nothing "
            "about merges.  If a number appears for it, the exemption "
            "changed and the docstring must change with it.",
        )

    def test_exactly_one_governed_post_state_is_a_golden_and_it_is_the_v111_merge(self):
        """The one exemption below, pinned so it cannot quietly become two.

        The enumeration reaches a state that IS a golden: merging identity 3
        into slot 0 of the initial bag produces ``MERGED_V111_BACKPACK``
        exactly -- that merge is where the merged golden comes from.  Today's
        gate admits it (``is_unmoved_baseline`` is True for it) and so must
        any replacement.  It is the only such state, and this test is what
        says so; if a second one ever appears, the exemption in
        ``test_every_governed_post_state_is_refused`` stops being a statement
        about one known transition.
        """
        goldens = sorted(
            label for label, state in governed_post_states()
            if state in GOLDENS
        )
        self.assertEqual(goldens, ["HYP-PF-018 golden0/identity3/slot0"])

    def test_every_governed_post_state_is_refused(self):
        """Every one, except the V111 merge, whose post-state is a golden.

        See the test above for that single exemption.  ``is_unmoved_baseline``
        admits it today, so refusing it here would be a REGRESSION, not a
        tightening.
        """
        exempt = 0
        for label, state in governed_post_states():
            if state in GOLDENS:
                exempt += 1
                continue
            with self.subTest(state=label):
                self.assertFalse(
                    bag_admission.is_golden_plus_acquired(state), label,
                )
                self.assertFalse(
                    bag_admission.may_enter_world(
                        state, allow_hypothesized_item_move=False,
                    ),
                    label,
                )
        self.assertEqual(exempt, 1)

    def test_the_opt_in_still_admits_the_whole_family(self):
        """Widening must not cost the hypotheses their own way in."""
        for label, state in governed_post_states():
            with self.subTest(state=label):
                self.assertTrue(
                    bag_admission.may_enter_world(
                        state, allow_hypothesized_item_move=True,
                    ),
                    label,
                )

    def test_is_unmoved_baseline_agrees_on_every_generated_state(self):
        """This module adds a term; it does not disagree with the old one.

        Every governed post-state that ``is_unmoved_baseline`` refuses is
        refused here too.  If this ever fails, the two predicates have
        diverged on the family, which is exactly the divergence that broke
        the last attempt.
        """
        for label, state in governed_post_states():
            with self.subTest(state=label):
                if not is_unmoved_baseline(state):
                    self.assertFalse(
                        bag_admission.may_enter_world(
                            state, allow_hypothesized_item_move=False,
                        ),
                        label,
                    )

    def test_the_unchanged_check_is_load_bearing(self):
        """Weaken it the obvious way and HYP-PF-008 walks in.

        This is the previous attempt's failure, written as an assertion.  The
        weaker rule below -- "all golden identities are present" -- is what a
        later reader simplifying ``_classify_against`` would most plausibly
        write, and it admits the shipped HYP-PF-008 post-state.
        """
        state = HYPOTHESIZED_V111_SLOT2_BACKPACK
        golden = MERGED_V111_BACKPACK
        present = {item.identity for item in state.items}
        weaker_rule_admits = {
            item.identity for item in golden.items
        } <= present
        self.assertTrue(
            weaker_rule_admits,
            "the weakened rule must admit this state, or this test is not "
            "demonstrating the risk it claims to",
        )
        self.assertFalse(
            bag_admission.may_enter_world(
                state, allow_hypothesized_item_move=False,
            ),
            "the shipped rule must refuse what the weakened rule admits",
        )
        admission = bag_admission.classify(state)
        self.assertEqual(
            admission.reason,
            bag_admission.REASON_GOLDEN_ITEM_MOVED_OR_ALTERED,
        )


class AcquiredBagsTests(unittest.TestCase):
    """The bags come from ``mob_pickup.place_in_bag``, not from this file."""

    def test_one_real_pickup_onto_each_golden_is_admitted(self):
        for index, golden in enumerate(GOLDENS):
            with self.subTest(golden=index):
                after, item = mob_pickup.place_in_bag(golden, a_drop())
                admission = bag_admission.classify(after)
                self.assertEqual(
                    admission.verdict,
                    bag_admission.VERDICT_GOLDEN_PLUS_ACQUIRED,
                    admission,
                )
                self.assertEqual(admission.golden_index, index)
                self.assertEqual(admission.acquired, (item,))
                self.assertTrue(bag_admission.may_enter_world(
                    after, allow_hypothesized_item_move=False,
                ))

    def test_several_real_pickups_in_a_row_stay_admitted(self):
        bag = INITIAL_BACKPACK
        for step in range(6):
            bag, _ = mob_pickup.place_in_bag(bag, a_drop(key=KEY + step))
            with self.subTest(pickups=step + 1):
                admission = bag_admission.classify(bag)
                self.assertEqual(
                    admission.verdict,
                    bag_admission.VERDICT_GOLDEN_PLUS_ACQUIRED,
                    admission,
                )
                self.assertEqual(len(admission.acquired), step + 1)
                self.assertTrue(bag_admission.may_enter_world(
                    bag, allow_hypothesized_item_move=False,
                ))

    def test_a_pickup_onto_a_moved_bag_is_still_refused(self):
        """Acquisition does not launder a governed mutation.

        A HYP-PF-010 post-state that then picks something up is still a
        HYP-PF-010 post-state, and admitting it because the newest row looks
        innocent is the exact hole this predicate must not have.
        """
        moved = move_known_item_to_free_slot(INITIAL_BACKPACK, 2, 7)
        self.assertIsNotNone(moved)
        after, _ = mob_pickup.place_in_bag(moved[0], a_drop())
        self.assertFalse(bag_admission.may_enter_world(
            after, allow_hypothesized_item_move=False,
        ))
        self.assertEqual(
            bag_admission.classify(after).reason,
            bag_admission.REASON_GOLDEN_ITEM_MOVED_OR_ALTERED,
        )


class WholeM5ChainTests(unittest.TestCase):
    """The one test that says what this module is worth, end to end.

    Everything else here is about a predicate.  This walks the actual M5
    chain on a real shipped monster -- kill, roll, ground, pickup, bag -- and
    pins the single fact the round is asking COO to rule on: today's gate 2
    refuses the resulting bag, and the proposed rule admits it.

    The subject is a Bg0002 (Prison Exile) monster deliberately, and that is
    itself a finding this round measured: every bg0001 (Port Royal) row
    carries n_DROPS_* = 0 in all three columns, so a kill there rolls nothing
    and M5 has nothing to pick up at the only scene a player can stand in
    today.  See ``test_port_royal_still_drops_nothing`` below.
    """

    def test_a_real_bg0002_kill_becomes_a_bag_only_the_new_rule_admits(self):
        roster = field_mobs.load_roster(field_mobs.BG0002_SCENE)
        mob = roster[0]
        rng = random.Random(20260829)
        roll = None
        for _attempt in range(200):
            candidate = mob_loot.roll_drops(mob, rng)
            if candidate.items:
                roll = candidate
                break
        self.assertIsNotNone(
            roll, "200 rolls on a monster with three non-zero drop sets "
            "produced no item; the drop tables, not this test, changed",
        )

        dropped = roll.items[0]
        drop = mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE, dropped.item_id, dropped.quantity,
            mob_loot.as_wire_float(mob.x), mob_loot.as_wire_float(mob.y),
            mob_loot.as_wire_float(mob.z), mob.actor_identity, KILLER,
        )
        after, item = mob_pickup.place_in_bag(INITIAL_BACKPACK, drop)

        # The bag now holds something a monster really dropped.
        self.assertEqual(len(after.items), len(INITIAL_BACKPACK.items) + 1)
        self.assertEqual(item.template_id, dropped.item_id)

        # This is the whole argument, in two assertions.
        self.assertFalse(
            is_unmoved_baseline(after),
            "today's gate 2 must refuse this bag, or there is nothing to fix",
        )
        self.assertTrue(
            bag_admission.may_enter_world(
                after, allow_hypothesized_item_move=False,
            ),
            "the proposed rule must admit it, or the round delivers nothing",
        )

    def test_port_royal_still_drops_nothing(self):
        """Measured, and the reason M5 cannot be shown at Port Royal.

        Not an assertion about what SHOULD be: n_ID 916 carries zero in all
        three drop columns per the game's own tables, and COO ruled those
        four placements practice dummies rather than monsters.  This test
        exists so that if Port Royal ever starts dropping, somebody is told.
        """
        rng = random.Random(20260829)
        for mob in field_mobs.load_roster():
            with self.subTest(placement=mob.placement_index):
                self.assertEqual(
                    (mob.drops_normal, mob.drops_equipment,
                     mob.drops_specially), (0, 0, 0),
                )
                roll = mob_loot.roll_drops(mob, rng)
                self.assertEqual(roll.items, ())
                self.assertEqual(roll.money, ())
                self.assertEqual(roll.draws, 0)


class ForgedAndDegenerateBagsTests(unittest.TestCase):
    def _initial_plus(self, item: ItemAttrState) -> BackpackState:
        return BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            tuple(sorted(
                INITIAL_BACKPACK.items + (item,),
                key=lambda row: row.identity,
            )),
        )

    def test_an_identity_at_or_below_the_golden_high_water_is_refused(self):
        """The pickup path only ever mints above the highest identity."""
        highest = max(item.identity for item in INITIAL_BACKPACK.items)
        forged = ItemAttrState(
            0, ITEM, 1, 9,
            bag_admission.NEW_ROW_RAW_U8_38,
            bag_admission.NEW_ROW_RAW_U8_39,
            bag_admission.NEW_ROW_DETAIL_PRESENT,
        )
        bag = self._initial_plus(forged)
        admission = bag_admission.classify(bag)
        self.assertEqual(
            admission.reason,
            bag_admission.REASON_ACQUIRED_IDENTITY_NOT_ABOVE_GOLDEN,
        )
        self.assertFalse(bag_admission.may_enter_world(
            bag, allow_hypothesized_item_move=False,
        ))
        self.assertEqual(highest, 4)

    def test_a_row_without_the_pickup_constants_is_refused(self):
        for label, item in (
            ("raw_u8_38", ItemAttrState(5, ITEM, 1, 9, 1, 0xFF, 0)),
            ("raw_u8_39", ItemAttrState(5, ITEM, 1, 9, 0, 0x00, 0)),
            ("detail_present", ItemAttrState(5, ITEM, 1, 9, 0, 0xFF, 1)),
        ):
            with self.subTest(field=label):
                bag = self._initial_plus(item)
                self.assertEqual(
                    bag_admission.classify(bag).reason,
                    bag_admission.REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED,
                )
                self.assertFalse(bag_admission.may_enter_world(
                    bag, allow_hypothesized_item_move=False,
                ))

    def test_a_zero_quantity_row_is_refused(self):
        bag = self._initial_plus(ItemAttrState(
            5, ITEM, 0, 9,
            bag_admission.NEW_ROW_RAW_U8_38,
            bag_admission.NEW_ROW_RAW_U8_39,
            bag_admission.NEW_ROW_DETAIL_PRESENT,
        ))
        self.assertEqual(
            bag_admission.classify(bag).reason,
            bag_admission.REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED,
        )

    def test_a_shrunken_bag_is_refused_and_says_so(self):
        """NONCLAIM 2: consumption is out of scope, and refused, not ignored."""
        short = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            INITIAL_BACKPACK.items[:-1],
        )
        admission = bag_admission.classify(short)
        self.assertFalse(admission.admissible)
        self.assertEqual(
            admission.reason, bag_admission.REASON_GOLDEN_ITEM_MISSING,
        )

    def test_a_bag_on_neither_golden_is_refused(self):
        """Score 0 against both goldens gets its own reason, not a row-level one.

        A bag that shares no row with either snapshot is not "missing item 4";
        it is not built on a golden at all, and saying so is the difference
        between a reader chasing one row and a reader seeing the real shape.
        """
        stranger = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            (ItemAttrState(9, ITEM, 1, 0),),
        )
        admission = bag_admission.classify(stranger)
        self.assertFalse(admission.admissible)
        self.assertEqual(
            admission.reason, bag_admission.REASON_NO_GOLDEN_MATCHES,
        )
        self.assertIsNone(admission.golden_index)

    def test_a_bag_keeping_one_golden_row_is_explained_by_that_golden(self):
        """The score picks the golden, and the reason comes from it."""
        short = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            INITIAL_BACKPACK.items[:2],
        )
        admission = bag_admission.classify(short)
        self.assertFalse(admission.admissible)
        self.assertEqual(admission.golden_index, 0)
        self.assertEqual(
            admission.reason, bag_admission.REASON_GOLDEN_ITEM_MISSING,
        )

    def test_a_drifted_header_is_refused_even_when_a_row_was_acquired(self):
        """pf-adversary's counterexample, pinned.

        The first draft checked the three bag-level fields ONLY on the branch
        where nothing had been acquired.  So a bag carrying INITIAL's four
        rows byte-identical, plus exactly what ``place_in_bag`` mints, plus
        one drifted header field, was admitted by the new path -- while gate 2
        refuses it today.  Every drift below is one field, and each was
        admitted before the fix.

        ``place_in_bag`` copies all three fields from the bag it is given
        (``mob_pickup.py``), so no golden-rooted pickup can produce any of
        these.
        """
        acquired = ItemAttrState(
            5, ITEM, 1, 4,
            bag_admission.NEW_ROW_RAW_U8_38,
            bag_admission.NEW_ROW_RAW_U8_39,
            bag_admission.NEW_ROW_DETAIL_PRESENT,
        )
        rows = tuple(sorted(
            INITIAL_BACKPACK.items + (acquired,),
            key=lambda row: row.identity,
        ))
        for label, mask, identity, span in (
            ("base_mask", BACKPACK_BASE_MASK - 1, BACKPACK_BASE_IDENTITY,
             BACKPACK_RANGE_MASK),
            ("base_identity", BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY + 999,
             BACKPACK_RANGE_MASK),
            ("range_mask", BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY,
             BACKPACK_RANGE_MASK - 1),
        ):
            with self.subTest(field=label):
                drifted = BackpackState(mask, identity, span, rows)
                self.assertFalse(
                    is_unmoved_baseline(drifted),
                    "today's gate must refuse this, or it is not a widening",
                )
                self.assertFalse(
                    bag_admission.may_enter_world(
                        drifted, allow_hypothesized_item_move=False,
                    ),
                    f"a drifted {label} was admitted because a row was "
                    "acquired; that is the hole the header check closes",
                )
                self.assertEqual(
                    bag_admission.classify(drifted).reason,
                    bag_admission.REASON_BAG_HEADER_DIFFERS,
                )

        # The same bag with a clean header is admitted, so the test above is
        # isolating the header and nothing else.
        clean = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            rows,
        )
        self.assertTrue(bag_admission.may_enter_world(
            clean, allow_hypothesized_item_move=False,
        ))

    def test_a_changed_bag_header_is_refused_and_names_the_header(self):
        """Not "an item moved": every row here is byte-identical."""
        drifted = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY,
            BACKPACK_RANGE_MASK + 1, INITIAL_BACKPACK.items,
        )
        admission = bag_admission.classify(drifted)
        self.assertFalse(admission.admissible)
        self.assertEqual(
            admission.reason, bag_admission.REASON_BAG_HEADER_DIFFERS,
        )

    def test_the_same_rows_in_a_different_order_are_refused_and_say_so(self):
        """Refused today too (tuple equality), and it gets its own reason.

        ``place_in_bag`` sorts by identity because ``store._load_backpack``
        reads back ORDER BY item_identity, so a bag in another order came
        from neither -- and telling a reader "an item was altered" would send
        them hunting a row that is in fact unchanged.
        """
        reordered = BackpackState(
            BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, BACKPACK_RANGE_MASK,
            tuple(reversed(INITIAL_BACKPACK.items)),
        )
        self.assertNotEqual(reordered, INITIAL_BACKPACK)
        self.assertFalse(is_unmoved_baseline(reordered))
        admission = bag_admission.classify(reordered)
        self.assertFalse(admission.admissible)
        self.assertEqual(
            admission.reason, bag_admission.REASON_ITEM_ORDER_DIFFERS,
        )

    def test_malformed_input_is_refused_and_never_raises(self):
        """Fail-closed: gate 1 raises on these, this module must not."""
        for label, value in (
            ("none", None),
            ("tuple", ()),
            ("string", "backpack"),
            ("wrong item type", BackpackState(
                BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY,
                BACKPACK_RANGE_MASK, ("not an item",),
            )),
        ):
            with self.subTest(value=label):
                admission = bag_admission.classify(value)
                # Its own verdict, not VERDICT_REFUSED with a special reason
                # string: may_enter_world has to treat "not a Backpack"
                # differently from every other refusal, and a verdict cannot
                # be reused by a future refusal the way a reason can.
                self.assertEqual(
                    admission.verdict, bag_admission.VERDICT_MALFORMED,
                )
                self.assertFalse(admission.admissible)
                self.assertEqual(
                    admission.reason, bag_admission.REASON_MALFORMED,
                )
                self.assertFalse(bag_admission.may_enter_world(
                    value, allow_hypothesized_item_move=False,
                ))
                # Even the opt-in must not admit a bag that is not a bag.
                self.assertFalse(bag_admission.may_enter_world(
                    value, allow_hypothesized_item_move=True,
                ))


class ContractTests(unittest.TestCase):
    def test_the_duplicated_new_row_constants_match_mob_pickup(self):
        """NONCLAIM 4: duplicated to keep mob_loot off the select path."""
        self.assertEqual(
            bag_admission.NEW_ROW_RAW_U8_38, mob_pickup.NEW_ROW_RAW_U8_38,
        )
        self.assertEqual(
            bag_admission.NEW_ROW_RAW_U8_39, mob_pickup.NEW_ROW_RAW_U8_39,
        )
        self.assertEqual(
            bag_admission.NEW_ROW_DETAIL_PRESENT,
            mob_pickup.NEW_ROW_DETAIL_PRESENT,
        )
        self.assertEqual(
            bag_admission.BAG_SLOT_COUNT, mob_pickup.BAG_SLOT_COUNT,
        )
        self.assertEqual(
            bag_admission.MAX_SLOT_QUANTITY, mob_pickup.MAX_SLOT_QUANTITY,
        )

    def test_the_goldens_are_exactly_the_ones_is_unmoved_baseline_compares_against(self):
        """Both directions, and the reverse one needs the source, not a call.

        The first draft asserted only ``GOLDEN_BACKPACKS -> baseline``, which
        cannot see a THIRD baseline being added to ``is_unmoved_baseline``:
        pf-adversary added one and this test stayed green while
        ``may_enter_world`` refused a bag today's gate admits -- i.e. this
        module silently became stricter than the gate it claims to reproduce.
        No call can enumerate that tuple, and ``inventory.py`` is outside this
        lane's write zone, so the reverse direction is asserted against the
        function's own source.
        """
        for index, golden in enumerate(bag_admission.GOLDEN_BACKPACKS):
            with self.subTest(golden=index):
                self.assertTrue(is_unmoved_baseline(golden))

        source = Path(inventory.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "is_unmoved_baseline"
        )
        compared = [
            element.id
            for node in ast.walk(function)
            if isinstance(node, ast.Compare)
            for comparator in node.comparators
            if isinstance(comparator, ast.Tuple)
            for element in comparator.elts
            if isinstance(element, ast.Name)
        ]
        self.assertEqual(
            compared, ["INITIAL_BACKPACK", "MERGED_V111_BACKPACK"],
            "inventory.is_unmoved_baseline no longer compares against exactly "
            "the two snapshots bag_admission.GOLDEN_BACKPACKS lists, in that "
            "order.  Update GOLDEN_BACKPACKS in the same commit, or this "
            "module is a different gate from the one it claims to reproduce.",
        )
        self.assertEqual(
            len(compared), len(bag_admission.GOLDEN_BACKPACKS),
        )
        self.assertEqual(
            len(bag_admission.GOLDEN_NAMES),
            len(bag_admission.GOLDEN_BACKPACKS),
        )

    def test_the_console_line_is_one_greppable_token(self):
        line = bag_admission.console_line(
            bag_admission.classify(INITIAL_BACKPACK),
        )
        self.assertTrue(line.startswith("BAG_ADMISSION "), line)
        self.assertIn("verdict=golden", line)
        self.assertIn("acquired=0", line)
        self.assertNotIn("\n", line)

        after, _ = mob_pickup.place_in_bag(INITIAL_BACKPACK, a_drop())
        acquired_line = bag_admission.console_line(
            bag_admission.classify(after),
        )
        self.assertIn("verdict=golden_plus_acquired", acquired_line)
        self.assertIn("acquired=1", acquired_line)

        refused_line = bag_admission.console_line(
            bag_admission.classify(HYPOTHESIZED_V111_SLOT2_BACKPACK),
        )
        self.assertIn("verdict=refused", refused_line)
        self.assertIn("reason=", refused_line)

    def test_the_wiring_note_names_the_method_it_changes(self):
        wiring = bag_admission.BAG_ADMISSION_WIRING
        self.assertIn("select_and_start", wiring)
        self.assertIn("may_enter_world", wiring)
        self.assertIn("is_unmoved_baseline", wiring)
        self.assertEqual(len(bag_admission.BAG_ADMISSION_NONCLAIMS), 7)


if __name__ == "__main__":
    unittest.main()
