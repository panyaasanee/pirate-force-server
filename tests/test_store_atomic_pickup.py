"""M5: a pickup that fails halfway does NOT eat the player's item.

WHAT THIS FILE IS THE EVIDENCE FOR.  ``mob_pickup.py`` note 16 states the
shape this round closes: the drop leaves the ground in one transaction and
``store.commit_acquired_backpack_item`` is "a separate later call that can
refuse (lease taken over, database locked, disk full)".  Between those two
transactions the item is off the ground and in no bag, and BOTH halves are on
disk -- so the loss survives relog, which is the worst kind of loss there is.
``store.commit_pickup_taking_the_drop_off_the_ground`` is the pair as ONE
transaction; this file measures that the halfway state cannot be reached.

HOW THE FAILURE IS INJECTED.  Not by mocking the store's own method (that
would prove the mock rolls back).  The bag half is made to refuse the way it
really refuses -- the identity counter is moved out from under the caller by
a stranger write, which is the exact refusal ``commit_acquired_backpack_item``
raises "identity counter changed during the pickup transaction" for -- and
then the GROUND table is read raw to see whether the drop is still standing.

WHAT THIS FILE DOES NOT PROVE.  There is still no call site: nothing in
``runtime.py`` calls this door yet (that is ``GT-124``), so nothing here says
a player clicking a label gets this behaviour.  Nothing here is
client-observable evidence either -- every read-back is SQL.
"""
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_loot, mob_pickup  # noqa: E402
from pirateforce_foundation.inventory import ItemAttrState  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

ITEM = 2400046
MOB = 0x2068
KILLER = 0x750059
SCENE = "bg0001"


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


def a_drop(key_offset=0, quantity=1):
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, quantity,
        mob_loot.as_wire_float(10.0),
        mob_loot.as_wire_float(20.0),
        mob_loot.as_wire_float(30.0),
        MOB, KILLER, SCENE,
    )


class AtomicPickupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("atomic-pickup")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "AtomicPickupOne", "atomicpickupone",
            "fingerprint-atomic-pickup", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    # ----- harness ------------------------------------------------------

    @contextmanager
    def _raw(self):
        """A connection this helper CLOSES (see test_store_acquired_item_insert)."""
        db = sqlite3.connect(self.path)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _mint(self, key_offset=0, quantity=1):
        bag = self.store.get_backpack(self.sid, self.character.id)
        issued = self.store.backpack_issued_through(self.sid, self.character.id)
        _, item = mob_pickup.place_in_bag(bag, a_drop(key_offset, quantity), issued)
        return item

    def _put_on_the_ground(self, key_offset=0, quantity=1):
        drop = a_drop(key_offset, quantity)
        self.store.commit_ground_drop(
            SCENE, drop.drop_key, drop.item_id, drop.quantity,
            10.0, 20.0, 30.0, MOB, KILLER,
        )
        return drop

    def _taken_at(self, drop_key):
        with self._raw() as db:
            row = db.execute(
                "SELECT taken_at FROM ground_drops "
                "WHERE scene_fold=? AND drop_key=?",
                (SCENE.casefold(), drop_key),
            ).fetchone()
        return None if row is None else row[0]

    def _rows(self):
        with self._raw() as db:
            return [
                tuple(row) for row in db.execute(
                    "SELECT item_identity,template_id,quantity,slot "
                    "FROM character_backpack_items WHERE character_id=? "
                    "ORDER BY item_identity",
                    (self.character.id,),
                )
            ]

    # ----- the door works at all ----------------------------------------

    def test_both_halves_land(self):
        drop = self._put_on_the_ground()
        item = self._mint()
        before = len(self._rows())
        after = self.store.commit_pickup_taking_the_drop_off_the_ground(
            self.sid, self.character.id, item, SCENE, drop.drop_key,
        )
        self.assertEqual(len(self._rows()), before + 1)
        self.assertIn(item, after.items)
        self.assertIsNotNone(self._taken_at(drop.drop_key))
        self.assertEqual(
            self.store.list_ground_drops_still_on_the_ground(SCENE), (),
        )

    # ----- the failure that used to eat the item ------------------------

    def test_a_refused_bag_half_leaves_the_drop_on_the_ground(self):
        """THE POINT OF THE ROUND.

        The bag half refuses for a reason that really happens (the counter
        moved under the caller).  The old two-call shape had already marked
        the ground row taken by then, so the item was gone from both places.
        Here the marker must roll back with it.
        """
        drop = self._put_on_the_ground()
        item = self._mint()
        # A stranger advances the counter between the mint and the commit --
        # the exact drift `commit_acquired_backpack_item` refuses on.
        with self._raw() as db:
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (item.identity + 7, self.character.id),
            )
        rows_before = self._rows()
        with self.assertRaises(ValueError):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, item, SCENE, drop.drop_key,
            )
        # Neither half landed.
        self.assertEqual(self._rows(), rows_before)
        self.assertIsNone(self._taken_at(drop.drop_key))
        # And the player can still walk over it.
        still = self.store.list_ground_drops_still_on_the_ground(SCENE)
        self.assertEqual([row.drop_key for row in still], [drop.drop_key])

    def test_the_same_refusal_through_the_two_old_doors_does_eat_it(self):
        """The measurement that makes the new door worth having.

        Same refusal, driven through the two separate doors the call site
        uses today.  The ground row ends up taken and the bag row does not
        exist: the item is gone.  This test asserts the OLD behaviour on
        purpose -- if some later round makes the two-call path atomic on its
        own, this test fails and that is the right time to delete the new
        door, not before.
        """
        drop = self._put_on_the_ground()
        item = self._mint()
        with self._raw() as db:
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (item.identity + 7, self.character.id),
            )
        rows_before = self._rows()
        self.assertTrue(
            self.store.mark_ground_drop_taken(SCENE, drop.drop_key)
        )
        with self.assertRaises(ValueError):
            self.store.commit_acquired_backpack_item(
                self.sid, self.character.id, item,
            )
        self.assertEqual(self._rows(), rows_before)          # no bag row
        self.assertIsNotNone(self._taken_at(drop.drop_key))  # but gone anyway
        self.assertEqual(
            self.store.list_ground_drops_still_on_the_ground(SCENE), (),
        )

    def test_the_loss_survives_relog(self):
        """Why the halfway state is worse than a crash: it is durable."""
        drop = self._put_on_the_ground()
        item = self._mint()
        with self._raw() as db:
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (item.identity + 7, self.character.id),
            )
        with self.assertRaises(ValueError):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, item, SCENE, drop.drop_key,
            )
        self.store.close_session(self.sid)
        self.sid = self.store.open_session(self.account_id)
        self.store.select_character(self.sid, self.character.selector)
        reopened = SQLiteStore(self.path, ROOT / "migrations")
        still = reopened.list_ground_drops_still_on_the_ground(SCENE)
        self.assertEqual([row.drop_key for row in still], [drop.drop_key])

    # ----- refusals -----------------------------------------------------

    def test_a_drop_key_the_scene_never_had_is_refused_and_writes_nothing(self):
        """An item out of nothing is worse than a refused pickup."""
        item = self._mint()
        rows_before = self._rows()
        with self.assertRaises(ValueError) as caught:
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, item,
                SCENE, mob_loot.DROP_KEY_BASE + 999,
            )
        self.assertIn("never existed", str(caught.exception))
        self.assertEqual(self._rows(), rows_before)

    def test_a_second_delivery_of_one_drop_does_not_write_a_second_row(self):
        """LANE-B's letter says pickup can be delivered twice.

        The ground half is idempotent by design, so the SECOND delivery gets
        past it; the identity check inside the bag half is what refuses, and
        it must, or one drop becomes two items.
        """
        drop = self._put_on_the_ground()
        item = self._mint()
        self.store.commit_pickup_taking_the_drop_off_the_ground(
            self.sid, self.character.id, item, SCENE, drop.drop_key,
        )
        after_first = self._rows()
        with self.assertRaises(ValueError):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, item, SCENE, drop.drop_key,
            )
        self.assertEqual(self._rows(), after_first)

    def test_a_session_without_this_character_selected_writes_neither_half(self):
        drop = self._put_on_the_ground()
        item = self._mint()
        stranger = self.store.open_session(self.account_id)
        with self.assertRaises(Exception):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                stranger, self.character.id, item, SCENE, drop.drop_key,
            )
        self.assertIsNone(self._taken_at(drop.drop_key))

    def test_a_row_gate_2_would_refuse_forever_never_touches_the_ground(self):
        drop = self._put_on_the_ground()
        item = self._mint()
        bad = ItemAttrState(
            item.identity, item.template_id, 0, item.slot,
            item.raw_u8_38, item.raw_u8_39, item.detail_present,
        )
        with self.assertRaises(ValueError):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, bad, SCENE, drop.drop_key,
            )
        self.assertIsNone(self._taken_at(drop.drop_key))

    def test_a_drop_key_outside_u32_is_refused_before_the_lock(self):
        item = self._mint()
        with self.assertRaises(ValueError):
            self.store.commit_pickup_taking_the_drop_off_the_ground(
                self.sid, self.character.id, item, SCENE, 0x1_0000_0000,
            )

    # ----- the split changed nothing --------------------------------------

    def test_the_two_old_doors_still_behave_as_before(self):
        drop = self._put_on_the_ground()
        self.assertTrue(self.store.mark_ground_drop_taken(SCENE, drop.drop_key))
        first = self._taken_at(drop.drop_key)
        self.assertTrue(self.store.mark_ground_drop_taken(SCENE, drop.drop_key))
        self.assertEqual(self._taken_at(drop.drop_key), first)
        self.assertFalse(
            self.store.mark_ground_drop_taken(SCENE, mob_loot.DROP_KEY_BASE + 555)
        )
        with self.assertRaises(TypeError):
            self.store.mark_ground_drop_taken(SCENE, True)


if __name__ == "__main__":
    unittest.main()
