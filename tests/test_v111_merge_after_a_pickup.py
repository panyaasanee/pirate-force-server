"""COO-DECISION 20260908_0542 section 4: the V111 stack merge survives a pickup.

THE PLAYER-FACING FACT THIS FILE MEASURES.  Before this round, the pre-state
door of ``store.apply_v111_stack_merge`` asked ``before in
inventory.STARTING_BACKPACKS`` -- literal membership.  A character who picks
one item up off a mob leaves that set for good, so from that moment the
server refused their stack merge forever; ``runtime.py``'s V111 dispatch
catches the refusal and returns no bytes at all, so the player clicks the
stack and nothing happens, with nothing in the reply to say why.  The door
now asks whether the rows the transaction is about to touch are still the
ones a starting bag was born with, which an acquired row cannot change.

WHAT THIS FILE DOES NOT PROVE.
* Not client-observable.  No window opens.  It measures the store's answer
  and the rows in the database afterwards; nobody has seen two stacks become
  one on a screen with a picked-up item in the same bag.
* It does NOT prove any live player can reach this today: the inbound pickup
  REQUEST half of MOB_PICKUP_WIRING is still unwired (there is no known vital
  id for a client-originated pickup on this wire -- see the comment at
  ``runtime.py`` around line 10180), so the acquired row here is written
  through the production store method directly, not by a client.
* WARNING -- it does NOT prove the round trip is safe end to end.  ``runtime.py``
  compares the committed bag against the single ``MERGED_V111_BACKPACK`` it
  imported and raises AFTER the commit (``runtime.py:1945``); a golden+
  acquired bag merges to a state that constant can never equal.  That module
  belongs to chief and the fix is CORE-REQUEST 20260908_0206, still open.
  ``test_the_runtime_comparison_this_lane_cannot_reach`` below PINS that
  hazard from this side so it cannot be forgotten, and the round file says
  it out loud.
"""
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import inventory  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    persistence_class_weapon as class_weapon,
)
from pirateforce_foundation.inventory import (  # noqa: E402
    INITIAL_BACKPACK, MERGED_V111_BACKPACK, ItemAttrState,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _a_free_slot(bag):
    taken = {row.slot for row in bag.items}
    return next(slot for slot in range(40) if slot not in taken)


class TheDoorReadsTheRowsItIsAboutToTouchTests(unittest.TestCase):
    """The predicates alone, with no database in the way."""

    def _acquired(self, bag, identity=None, template=3000001):
        return ItemAttrState(
            max(row.identity for row in bag.items) + 1
            if identity is None else identity,
            template, 1, _a_free_slot(bag),
        )

    def test_an_untouched_starting_bag_still_answers_with_itself(self):
        for core in inventory.STARTING_BACKPACKS:
            with self.subTest(core=core.items[0].template_id):
                self.assertIs(inventory.starting_core_of(core), core)
                self.assertIsNone(inventory.settled_core_of(core))

    def test_a_starting_bag_that_acquired_a_row_still_names_its_core(self):
        for core in inventory.STARTING_BACKPACKS:
            with self.subTest(core=core.items[0].template_id):
                grown = replace(
                    core, items=core.items + (self._acquired(core),))
                self.assertNotIn(grown, inventory.STARTING_BACKPACKS)
                self.assertIs(inventory.starting_core_of(grown), core)
                self.assertIsNone(inventory.settled_core_of(grown))

    def test_a_merged_bag_that_acquired_a_row_reads_as_settled(self):
        for core in inventory.STARTING_BACKPACKS:
            if not inventory.can_merge_v111(core):
                continue
            merged = inventory.merged_v111_state(core)
            grown = replace(
                merged, items=merged.items + (self._acquired(core),))
            self.assertIsNone(inventory.starting_core_of(grown))
            self.assertIs(inventory.settled_core_of(grown), core)

    def test_a_golden_row_that_moved_is_not_a_core_any_more(self):
        """Slot is part of the row, so a moved item is not "the same bag plus"."""
        core = INITIAL_BACKPACK
        moved = replace(
            core,
            items=tuple(
                replace(row, slot=_a_free_slot(core)) if row.identity == 2
                else row
                for row in core.items
            ),
        )
        self.assertIsNone(inventory.starting_core_of(moved))
        self.assertIsNone(inventory.settled_core_of(moved))

    def test_a_golden_row_that_was_spent_is_not_a_core_any_more(self):
        core = INITIAL_BACKPACK
        spent = replace(
            core,
            items=tuple(
                replace(row, quantity=row.quantity + 1) if row.identity == 1
                else row
                for row in core.items
            ),
        )
        self.assertIsNone(inventory.starting_core_of(spent))

    def test_a_missing_golden_row_is_not_a_core(self):
        core = INITIAL_BACKPACK
        short = replace(
            core, items=tuple(r for r in core.items if r.identity != 2))
        self.assertIsNone(inventory.starting_core_of(short))

    def test_a_drifted_header_is_a_different_bag_not_a_grown_one(self):
        core = INITIAL_BACKPACK
        for field in ("base_mask", "base_identity", "range_mask"):
            with self.subTest(field=field):
                drifted = replace(
                    core, **{field: getattr(core, field) ^ 1})
                grown = replace(
                    drifted, items=drifted.items + (self._acquired(core),))
                self.assertIsNone(inventory.starting_core_of(grown))

    def test_an_extra_row_below_the_counter_is_refused(self):
        """The bound is the pickup path's own, not a taste in numbers.

        ``store.commit_acquired_backpack_item`` refuses any identity that is
        not ``character_backpacks.next_item_identity``, and that column is
        seeded at ``max(starting identities) + 1``.  A row at or below the
        core's highest identity was therefore never issued by a pickup, and
        without this bound a forged row wearing identity 0 would ride in as
        "acquired".  Drop the ``>`` in ``_core_is_carried_unchanged`` and
        this test is the one that goes red.
        """
        core = INITIAL_BACKPACK
        highest = max(row.identity for row in core.items)
        forged = ItemAttrState(0, 3000001, 1, _a_free_slot(core))
        self.assertIsNone(
            inventory.starting_core_of(
                replace(core, items=core.items + (forged,))))
        legitimate = ItemAttrState(
            highest + 1, 3000001, 1, _a_free_slot(core))
        self.assertIsNotNone(
            inventory.starting_core_of(
                replace(core, items=core.items + (legitimate,))))

    def test_an_empty_core_admits_nothing(self):
        empty = replace(INITIAL_BACKPACK, items=())
        self.assertFalse(
            inventory._core_is_carried_unchanged(INITIAL_BACKPACK, empty))

    def test_a_bag_from_nowhere_is_still_refused(self):
        alien = replace(
            INITIAL_BACKPACK,
            items=(ItemAttrState(1, 999, 1, 0), ItemAttrState(3, 999, 1, 1)),
        )
        self.assertIsNone(inventory.starting_core_of(alien))
        self.assertIsNone(inventory.settled_core_of(alien))


class TheMergeRunsOnARealRowAfterAPickupTests(unittest.TestCase):
    """The same question asked of the production store, on real rows."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _selected(self, login_name):
        session = FoundationSession(self.lifecycle, self.projector, login_name)
        character, _ = session.create(
            "test01", self.legacy.get_preset_actor_wire())
        relog = FoundationSession(self.lifecycle, self.projector, login_name)
        selected, _started = relog.select_and_start(character.selector)
        return relog, selected

    def _pick_one_up(self, session, character):
        """Through the production write, not an INSERT typed here."""
        issued = self.store.backpack_issued_through(
            session.session_id, character.id)
        bag = self.store.get_backpack(session.session_id, character.id)
        row = ItemAttrState(issued + 1, 3000001, 1, _a_free_slot(bag))
        after = self.store.commit_acquired_backpack_item(
            session.session_id, character.id, row)
        self.assertIn(row, after.items)
        return row

    def test_the_merge_runs_for_a_character_who_picked_something_up(self):
        session, character = self._selected("picked-up")
        acquired = self._pick_one_up(session, character)

        after = self.store.apply_v111_stack_merge(
            session.session_id, character.id)

        self.assertIsNotNone(after)
        by_identity = {row.identity: row for row in after.items}
        # The stack folded ...
        self.assertNotIn(3, by_identity)
        self.assertEqual(
            by_identity[1].quantity,
            sum(row.quantity for row in INITIAL_BACKPACK.items
                if row.identity in (1, 3)),
        )
        # ... and the picked-up row is untouched, not "merged into" anything.
        self.assertEqual(by_identity[acquired.identity], acquired)

    def test_the_second_call_is_a_replay_not_a_second_merge(self):
        session, character = self._selected("replay")
        self._pick_one_up(session, character)
        first = self.store.apply_v111_stack_merge(
            session.session_id, character.id)
        self.assertIsNotNone(first)

        self.assertIsNone(
            self.store.apply_v111_stack_merge(session.session_id, character.id))

        self.assertEqual(
            self.store.get_backpack(session.session_id, character.id), first)

    def test_picking_up_after_the_merge_still_replays(self):
        session, character = self._selected("pickup-after")
        merged = self.store.apply_v111_stack_merge(
            session.session_id, character.id)
        self.assertIsNotNone(merged)
        acquired = self._pick_one_up(session, character)

        self.assertIsNone(
            self.store.apply_v111_stack_merge(session.session_id, character.id))

        bag = self.store.get_backpack(session.session_id, character.id)
        self.assertIn(acquired, bag.items)

    def test_the_control_a_bag_whose_golden_row_moved_is_still_refused(self):
        """Without this the file would pass against a door that admits all."""
        session, character = self._selected("control")
        with self.store.connect() as db:
            moved = db.execute(
                "UPDATE character_backpack_items SET slot=? "
                "WHERE character_id=? AND item_identity=?",
                (39, character.id, 2),
            )
            self.assertEqual(moved.rowcount, 1)

        with self.assertRaises(ValueError):
            self.store.apply_v111_stack_merge(
                session.session_id, character.id)

        # And nothing was written by the refusal.
        bag = self.store.get_backpack(session.session_id, character.id)
        self.assertEqual({row.identity for row in bag.items}, {1, 2, 3, 4})

    def test_a_starting_bag_with_no_stack_to_fold_refuses_by_sentence(self):
        """Was a KeyError naming a dict subscript; now it is a sentence.

        The population is the one ``inventory.can_merge_v111`` was written
        for: a starting bag with no identity 3, which LANE-CS's table may
        hold one day.  It is installed into ``inventory`` rather than
        imagined, because that is the only way this branch is reachable -- a
        bag that merely LOST identity 3 fails the core check one line
        earlier, which the control above already covers.
        """
        session, character = self._selected("no-stack")
        with self.store.connect() as db:
            db.execute(
                "DELETE FROM character_backpack_items "
                "WHERE character_id=? AND item_identity=3",
                (character.id,),
            )
        stub = replace(
            INITIAL_BACKPACK,
            items=tuple(
                row for row in INITIAL_BACKPACK.items if row.identity != 3),
        )
        self.assertFalse(inventory.can_merge_v111(stub))
        with mock.patch.object(inventory, "STARTING_BACKPACKS", (stub,)):
            with self.assertRaises(ValueError) as caught:
                self.store.apply_v111_stack_merge(
                    session.session_id, character.id)
        self.assertIn("V111 stack", str(caught.exception))

    def test_the_runtime_comparison_this_lane_cannot_reach(self):
        """WARNING -- the hazard this widening hands to CORE-REQUEST 20260908_0206.

        ``runtime.py:1945`` raises AFTER the merge commits when the committed
        bag is not ``MERGED_V111_BACKPACK``.  A bag that acquired a row can
        never equal that constant, so the day the inbound pickup request is
        wired, this lane's widened door hands that comparison a bag it will
        reject post-commit.  This test does not fix it -- ``runtime.py`` is
        chief's file -- it MEASURES it, so the claim in the round file is a
        number and not a worry, and so it goes green by itself the day the
        comparison becomes set-shaped.
        """
        session, character = self._selected("hazard")
        self._pick_one_up(session, character)
        after = self.store.apply_v111_stack_merge(
            session.session_id, character.id)
        self.assertNotEqual(after, MERGED_V111_BACKPACK)


class TheCensusCountsAndNeverWritesTests(unittest.TestCase):
    """The read-only half of PANYA's item 4 (letter 20260908_0025).

    The census is what tells the owner how big the attended run under
    LOCK_GAME will be.  It runs on a database this test builds through the
    production ``create``, never on the canonical one, which does not exist
    in this clone.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _create(self, login_name):
        session = FoundationSession(self.lifecycle, self.projector, login_name)
        character, _ = session.create(
            "test01", self.legacy.get_preset_actor_wire())
        return character

    def test_an_empty_database_reports_nothing_to_change(self):
        with self.store.connect() as db:
            self.assertEqual(class_weapon.census_rows(db), ())
            self.assertIn(
                "rows_to_change=0", class_weapon.census_lines(db)[-1])

    def test_the_numbers_move_with_the_rows(self):
        """A spelled zero cannot pass: three shapes, three different counts."""
        right = self._create("right")
        wrong = self._create("wrong")
        gone = self._create("gone")
        weapon_identity = class_weapon.weapon_row(INITIAL_BACKPACK).identity
        other_class = next(
            class_id for class_id in class_weapon.CLASS_ID_TO_WEAPON_TEMPLATE
            if class_weapon.CLASS_ID_TO_WEAPON_TEMPLATE[class_id]
            != class_weapon.weapon_row(INITIAL_BACKPACK).template_id
        )
        with self.store.connect() as db:
            db.execute(
                "UPDATE characters SET class_id=? WHERE id=?",
                (other_class, wrong.id))
            db.execute(
                "DELETE FROM character_backpack_items "
                "WHERE character_id=? AND item_identity=?",
                (gone.id, weapon_identity))
        with self.store.connect() as db:
            by_class = {row[0]: row for row in class_weapon.census_rows(db)}
        with self.store.connect() as db:
            born_class = int(db.execute(
                "SELECT class_id FROM characters WHERE id=?",
                (right.id,),
            ).fetchone()[0])
        self.assertNotEqual(born_class, other_class)
        self.assertEqual(by_class[born_class][1], 2)   # right + gone
        self.assertEqual(by_class[born_class][2], 1)   # only "right" is ok
        self.assertEqual(by_class[born_class][4], 1)   # "gone" has no row
        self.assertEqual(by_class[other_class][3], 1)  # "wrong" is wrong

    def test_the_console_entry_cannot_write(self):
        """``mode=ro`` is the mechanism, and it is measured, not promised."""
        self._create("readonly")
        import sqlite3
        uri = "file:%s?mode=ro" % self.path
        with sqlite3.connect(uri, uri=True) as db:
            self.assertTrue(class_weapon.census_lines(db))
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM characters")

    def test_a_class_the_weapon_table_does_not_know_is_counted_not_raised(self):
        stray = self._create("stray")
        with self.store.connect() as db:
            db.execute(
                "UPDATE characters SET class_id=? WHERE id=?", (99, stray.id))
        with self.store.connect() as db:
            rows = {row[0]: row for row in class_weapon.census_rows(db)}
            self.assertEqual(rows[99][4], 1)
            self.assertIn(
                "class_id=99 name=UNKNOWN", "\n".join(
                    class_weapon.census_lines(db)))


if __name__ == "__main__":
    unittest.main()
