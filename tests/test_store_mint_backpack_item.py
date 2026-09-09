"""LANE-DB: ``SQLiteStore.mint_backpack_item`` -- give a character one row
for a known catalog item with NO ground drop involved.

WHY THIS FILE EXISTS.  ``COO-DECISION 20260908_2055`` ("the item minter next
to your own door is yours") answers LANE-Q's `20260908_1942` ask (routed to
COO): the write door (``commit_acquired_backpack_item``) already existed,
what was missing was something that composes an ``ItemAttrState`` from an
item number and a quantity instead of a caller building one by hand.  This
file is the evidence that the new door (a) actually lands a row, (b) lands
it THROUGH the existing gate rather than a second write path, (c) refuses
the four named cases readably instead of writing a half-row, and (d) never
lets a category-ambiguous id through unscoped.

THE `category` PARAMETER WAS NOT IN THE FIRST DRAFT.  pf-adversary (round
`ukgmj3`) measured that a bare ``is_known_item(item_id)`` call accepts any
id present in ANY of ``gm.item_catalog``'s three tables, and that the
suite's own fixture item (id 1, "Adventure Key" in misc) is itself one of
hundreds of ids that mean a DIFFERENT item in a different table ("Sky
Lantern" in quest) -- with no way for a caller to say which one they meant.
This file's category-focused tests exist to close exactly that gap and to
prove it stays closed.

THE NAME IS [PROPOSED].  `COO-DECISION 20260908_2055` requires agreeing
the function name with LANE-Q by letter before landing; this round proposes
`mint_backpack_item` in `pf_bridge/notes_to_chief/` and implements under
that name.  If LANE-Q's own pinned test wants a different one, that is a
rename in this file and in `store.py`, not a redesign -- the shape is
already the one COO ordered.
"""
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import tempfile  # noqa: E402

from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.gm import item_catalog  # noqa: E402
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


def _table_ids(filename: str) -> "set[int]":
    """Every `n_ID` in one committed category file, read the same way
    ``item_catalog`` itself parses it (tab-separated, header row first)."""
    data_path = Path(item_catalog.__file__).parent / "data" / filename
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        next(handle)  # header
        return {int(line.split("\t", 1)[0]) for line in handle if line.strip()}


_MISC_IDS = _table_ids("gm_item_misc.tsv")
_CONSUMABLE_IDS = _table_ids("gm_item_consumable.tsv")
_QUEST_IDS = _table_ids("gm_item_quest.tsv")


def _known_misc_item_id() -> int:
    """One real id from the committed misc catalog, DERIVED from the same
    file ``item_catalog`` reads rather than a literal picked by hand -- if
    the extraction ever drops row one this test moves with it instead of
    silently testing an id nobody ships any more."""
    item_id = min(_MISC_IDS)
    assert item_catalog.is_known_item(item_id, category="misc"), (
        "the derived id is not what item_catalog itself reports as known -- "
        "the two are reading different files"
    )
    return item_id


def _misc_only_item_id() -> int:
    """A real misc id that is NOT also a consumable or quest id -- so a
    category mismatch on this one is guaranteed to refuse rather than
    accidentally succeed on an unrelated collision."""
    candidates = sorted(_MISC_IDS - _CONSUMABLE_IDS - _QUEST_IDS)
    assert candidates, (
        "every misc id collides with consumable or quest today -- the "
        "category-mismatch test needs a genuinely misc-only id"
    )
    return candidates[0]


def _colliding_item_id() -> int:
    """The lowest id that means a DIFFERENT item depending on category --
    derived by intersecting the committed tables, not asserted from memory
    of what a fixed id happens to be today."""
    common = _MISC_IDS & _QUEST_IDS
    assert common, (
        "no id collides between misc and quest today -- the disambiguation "
        "test needs a genuine collision to prove anything"
    )
    return min(common)


KNOWN_ITEM_ID = _known_misc_item_id()
MISC_ONLY_ITEM_ID = _misc_only_item_id()

# One past INITIAL_BACKPACK's own slots (0..3): the lowest free slot on a
# freshly created character, derived rather than spelled, the same way
# tests/test_store_acquired_item_insert.py derives its own seed.
FIRST_FREE_SLOT = max(item.slot for item in INITIAL_BACKPACK.items) + 1
LAST_SLOT = 39  # inventory.require_backpack_shape's own bound: item.slot in 0..39


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


class MintBackpackItemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("mint-backpack-item")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "MintOne", "mintone",
            "fingerprint-mint-backpack-item", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    def _ground_drop_count(self):
        with self.store.connect() as db:
            return db.execute("SELECT count(*) FROM ground_drops").fetchone()[0]

    def _fill_slots(self, first_slot, last_slot_inclusive):
        """Occupy every slot in [first_slot, last_slot_inclusive] with a
        real row, the same raw-SQL shape test_store_acquired_item_insert.py
        uses for its own fixtures."""
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            next_identity = db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?", (self.character.id,),
            ).fetchone()[0]
            filler_rows = [
                (self.character.id, next_identity + offset, KNOWN_ITEM_ID, 1, slot, 0, 0xFF, 0)
                for offset, slot in enumerate(range(first_slot, last_slot_inclusive + 1))
            ]
            db.executemany(
                "INSERT INTO character_backpack_items("
                "character_id,item_identity,template_id,quantity,slot,"
                "raw_u8_38,raw_u8_39,detail_present"
                ") VALUES (?,?,?,?,?,?,?,?)",
                filler_rows,
            )
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (next_identity + len(filler_rows), self.character.id),
            )

    # ----- the happy path -----------------------------------------------

    def test_mints_a_known_item_into_the_first_free_slot_with_no_ground_drop(self):
        before_drops = self._ground_drop_count()
        after = self.store.mint_backpack_item(
            self.sid, self.character.id, KNOWN_ITEM_ID, 3, category="misc",
        )
        new_rows = [row for row in after.items if row.template_id == KNOWN_ITEM_ID]
        self.assertEqual(len(new_rows), 1)
        minted = new_rows[0]
        self.assertEqual(minted.slot, FIRST_FREE_SLOT)
        self.assertEqual(minted.quantity, 3)
        self.assertEqual(
            minted.identity,
            max(item.identity for item in INITIAL_BACKPACK.items) + 1,
        )
        # No ground drop was ever involved -- this is the whole point of the
        # door existing (LANE-Q's reward payout has no drop to pick up).
        self.assertEqual(self._ground_drop_count(), before_drops)
        # Read back through a fresh call, same as a relog would see.
        reread = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(reread, after)

    def test_lands_the_row_through_the_existing_door_not_a_new_one(self):
        """The contract COO wrote: 'writes through the existing gate -- not
        a new one'.  Proven by SPYING on the real door rather than re-typing
        its SQL here: if this method ever stops calling it and starts
        executing its own INSERT, this goes red without needing an AST walk
        of store.py to notice."""
        with mock.patch.object(
            self.store, "commit_acquired_backpack_item",
            wraps=self.store.commit_acquired_backpack_item,
        ) as spy:
            self.store.mint_backpack_item(
                self.sid, self.character.id, KNOWN_ITEM_ID, 1, category="misc",
            )
        spy.assert_called_once()
        (sid_arg, cid_arg, item_arg), _kwargs = spy.call_args
        self.assertEqual(sid_arg, self.sid)
        self.assertEqual(cid_arg, self.character.id)
        self.assertEqual(item_arg.template_id, KNOWN_ITEM_ID)

    def test_mints_into_the_true_last_slot_not_just_the_first_free_one(self):
        """The happy path above only ever exercises slot 4.  This fills
        every OTHER slot first (leaving exactly slot 39 free) so a mint has
        to walk the whole range and land at the true top of it -- an
        off-by-one that shrank the scanned range would refuse here even
        though a real slot is free."""
        self._fill_slots(FIRST_FREE_SLOT, LAST_SLOT - 1)  # fills 4..38
        before = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(before.items), LAST_SLOT)  # 39 occupied, 1 free
        after = self.store.mint_backpack_item(
            self.sid, self.character.id, KNOWN_ITEM_ID, 1, category="misc",
        )
        new_rows = [
            row for row in after.items
            if row.slot == LAST_SLOT and row.template_id == KNOWN_ITEM_ID
        ]
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(len(after.items), LAST_SLOT + 1)

    # ----- the four named refusals ----------------------------------------

    def test_refuses_an_item_id_outside_the_committed_catalog(self):
        unknown_id = 0xFFFFFFF  # not in any of the three committed tables
        self.assertFalse(item_catalog.is_known_item(unknown_id))
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(KeyError):
            self.store.mint_backpack_item(
                self.sid, self.character.id, unknown_id, 1, category="misc",
            )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_a_real_id_under_the_wrong_category(self):
        """The whole point of requiring `category`: a misc-only id must be
        refused when asked for under a category it does not belong to, even
        though the id itself is real and even though the SAME check without
        `category` would have accepted it."""
        self.assertTrue(item_catalog.is_known_item(MISC_ONLY_ITEM_ID, category="misc"))
        self.assertFalse(item_catalog.is_known_item(MISC_ONLY_ITEM_ID, category="quest"))
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(KeyError):
            self.store.mint_backpack_item(
                self.sid, self.character.id, MISC_ONLY_ITEM_ID, 1,
                category="quest",
            )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_a_colliding_id_still_requires_the_caller_to_name_a_category(self):
        """A genuinely ambiguous id (known in BOTH misc and quest, meaning
        two different real items) mints successfully under EITHER category
        -- the fix is not that collisions are refused, it is that the
        caller's choice is now explicit and recorded in which table was
        asked, instead of the door silently picking one."""
        colliding_id = _colliding_item_id()
        misc_name = item_catalog.item_name(colliding_id, category="misc")
        quest_name = item_catalog.item_name(colliding_id, category="quest")
        self.assertNotEqual(
            misc_name, quest_name,
            "the derived id is not actually a collision -- the two "
            "category lookups agree, so this test proves nothing",
        )
        after = self.store.mint_backpack_item(
            self.sid, self.character.id, colliding_id, 1, category="quest",
        )
        self.assertTrue(
            any(row.template_id == colliding_id for row in after.items)
        )

    def test_refuses_a_category_the_catalog_does_not_have(self):
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(ValueError):
            self.store.mint_backpack_item(
                self.sid, self.character.id, KNOWN_ITEM_ID, 1,
                category="weapon",
            )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_a_missing_category_by_type(self):
        """`category=None` must not silently fall through to
        `item_catalog.is_known_item`'s own bare (ambiguous) lookup."""
        for bad_category in (None, 1, b"misc"):
            with self.assertRaises(TypeError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, KNOWN_ITEM_ID, 1,
                    category=bad_category,
                )

    def test_refuses_a_zero_or_negative_quantity(self):
        before = self.store.get_backpack(self.sid, self.character.id)
        for bad_quantity in (0, -1, -100):
            with self.assertRaises(ValueError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, KNOWN_ITEM_ID, bad_quantity,
                    category="misc",
                )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_a_non_integer_quantity_by_type(self):
        for bad_quantity in (1.0, "1", True, None):
            with self.assertRaises(TypeError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, KNOWN_ITEM_ID, bad_quantity,
                    category="misc",
                )

    def test_refuses_a_non_integer_item_id_by_type(self):
        for bad_item_id in (1.0, "1", True, None):
            with self.assertRaises(TypeError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, bad_item_id, 1,
                    category="misc",
                )

    def test_refuses_when_the_backpack_is_full_before_composing_anything(self):
        # Fill every remaining slot (4..39), so the next mint has nowhere
        # free to land.
        self._fill_slots(FIRST_FREE_SLOT, LAST_SLOT)
        before = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(before.items), 40)
        with self.assertRaises(ValueError) as raised:
            self.store.mint_backpack_item(
                self.sid, self.character.id, KNOWN_ITEM_ID, 1, category="misc",
            )
        self.assertIn("full", str(raised.exception))
        self.assertIn("40", str(raised.exception))
        # Nothing moved: a full bag refuses before anything is composed,
        # not after a half-written row.
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_on_a_session_that_has_not_selected_the_character(self):
        """The session-ownership guard is inherited for free from
        `get_backpack` -- untested until now, so a future reordering that
        touched the identity/slot computation before `get_backpack` could
        silently drop it without any test noticing."""
        other_account = self.store.ensure_account("mint-backpack-item-other")
        other_sid = self.store.open_session(other_account)
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(PermissionError):
            self.store.mint_backpack_item(
                other_sid, self.character.id, KNOWN_ITEM_ID, 1,
                category="misc",
            )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    # ----- concurrency -----------------------------------------------------

    def test_concurrent_mints_never_corrupt_the_bag(self):
        """pf-adversary verified this manually with a 30-thread stress test
        and found no corruption, but flagged that nothing in this suite
        PINS it.  This is that pin: many threads mint at once on one
        character; every accepted mint gets a unique identity and a unique
        slot, every refusal is a clean ValueError (never a different
        exception, never a corrupted read), and the bag that comes back
        afterward is internally consistent."""
        threads_n = 12
        results = [None] * threads_n
        barrier = threading.Barrier(threads_n)

        def _attempt(index):
            barrier.wait()
            try:
                results[index] = (
                    "ok",
                    self.store.mint_backpack_item(
                        self.sid, self.character.id, KNOWN_ITEM_ID, 1,
                        category="misc",
                    ),
                )
            except ValueError as exc:
                results[index] = ("refused", exc)
            except BaseException as exc:  # pragma: no cover - failure path
                results[index] = ("unexpected", exc)

        threads = [
            threading.Thread(target=_attempt, args=(i,))
            for i in range(threads_n)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        kinds = [kind for kind, _ in results]
        self.assertNotIn(None, kinds, "a thread never finished")
        self.assertNotIn(
            "unexpected", kinds,
            "a concurrent mint raised something other than ValueError: %r"
            % [payload for kind, payload in results if kind == "unexpected"],
        )
        self.assertGreaterEqual(kinds.count("ok"), 1)

        final = self.store.get_backpack(self.sid, self.character.id)
        identities = [row.identity for row in final.items]
        slots = [row.slot for row in final.items]
        self.assertEqual(len(identities), len(set(identities)), "duplicate identity")
        self.assertEqual(len(slots), len(set(slots)), "duplicate slot")
        minted_rows = [
            row for row in final.items if row.template_id == KNOWN_ITEM_ID
        ]
        self.assertEqual(len(minted_rows), kinds.count("ok"))


if __name__ == "__main__":
    unittest.main()
