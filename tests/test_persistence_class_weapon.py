"""The class-weapon door, and the two measured reasons it may not run yet.

PANYA tick `pf_bridge/notes_to_chief/20260908_0025_KA1A-PANYA-TICK-*.md`
item 4.  The mapping half is pinned against the shipped table (never against
numbers typed in a test, which would only pin this lane's own copy of them);
the refusal half is pinned against the production predicates themselves, so
the day either widens these tests say so by failing.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pirateforce_foundation import class_catalog, inventory
from pirateforce_foundation import persistence_class_weapon as weapons
from pirateforce_foundation.model import Position
from pirateforce_foundation.store import SQLiteStore

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")
STAMP = "2026-09-08T04:00:00Z"

# One past INITIAL_BACKPACK's own slots (0..3): the lowest free slot on a
# freshly created character, the same derivation
# tests/test_store_acquired_item_insert.py uses for its own seed.
FIRST_FREE_SLOT = max(item.slot for item in inventory.INITIAL_BACKPACK.items) + 1
# The shape gate's own ceiling, asked of the same private helper
# mint_class_weapon itself calls -- not a literal 39 typed a second time,
# which is exactly the drift pf-adversary's D7 (module docstring) warns
# against.
LAST_SLOT = weapons._slot_ceiling()


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


def _tsv_column(index: int) -> dict[int, int]:
    """The table read by COLUMN POSITION, the way LANE-CS's letter says to
    re-check it (`awk -F'\\t' '{print $1, $8, $9}'`).

    The module under test reads by column NAME.  Two readings that agree is
    the pin; one reading twice would only pin the header row.
    """
    lines = class_catalog._DATA_PATH.read_text(encoding="ascii").splitlines()
    out: dict[int, int] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        out[int(fields[0])] = int(fields[index - 1])
    return out


class ClassWeaponMappingTest(unittest.TestCase):
    def test_mapping_is_the_rhand_column_read_by_position(self):
        self.assertEqual(
            weapons.CLASS_ID_TO_WEAPON_TEMPLATE, _tsv_column(8))

    def test_every_catalog_class_has_a_weapon(self):
        self.assertEqual(
            sorted(weapons.CLASS_ID_TO_WEAPON_TEMPLATE),
            sorted(class_catalog.CLASS_IDS))

    def test_the_left_hand_column_is_not_what_this_module_answers(self):
        lhand = _tsv_column(9)
        differing = [
            class_id for class_id in weapons.CLASS_ID_TO_WEAPON_TEMPLATE
            if lhand[class_id] != weapons.CLASS_ID_TO_WEAPON_TEMPLATE[class_id]
        ]
        # LANE-CS's letter: two classes carry 0 in the left hand and one
        # repeats its right.  If the table ever stops differing at all, the
        # "do not read LHAND" reasoning has lost its evidence and a human
        # should re-read the letter rather than trust this test's silence.
        self.assertTrue(differing, "no class differs between the two hands")
        for class_id in differing:
            self.assertNotEqual(
                weapons.class_weapon_template_id(class_id), lhand[class_id])

    def test_an_unknown_class_is_refused_not_defaulted(self):
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.class_weapon_template_id(3)


class WeaponRowTest(unittest.TestCase):
    def test_the_committed_starting_bag_has_exactly_one(self):
        row = weapons.weapon_row(inventory.INITIAL_BACKPACK)
        self.assertEqual(
            row.template_id, weapons.class_weapon_template_id(1))

    def test_two_rows_where_the_bag_was_born_holding_one_refuse(self):
        bag = inventory.INITIAL_BACKPACK
        born = weapons.weapon_row(bag)
        doubled = replace(bag, items=tuple(
            item for item in bag.items if item.identity != born.identity
        ) + (replace(born, identity=98), replace(born, identity=99)))
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.weapon_row(doubled)

    def test_no_weapon_row_refuses(self):
        bag = inventory.INITIAL_BACKPACK
        weapon = weapons.weapon_row(bag)
        stripped = replace(bag, items=tuple(
            item for item in bag.items if item.identity != weapon.identity))
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.weapon_row(stripped)


class CarryOldWeaponForwardTest(unittest.TestCase):
    def test_the_old_template_survives_in_the_bag(self):
        before = inventory.INITIAL_BACKPACK
        old = weapons.weapon_row(before).template_id
        post, issued = weapons.carry_old_weapon_forward(before, 2, 4)
        self.assertIn(old, [item.template_id for item in post.items])
        self.assertEqual(
            weapons.weapon_row(replace(post, items=tuple(
                item for item in post.items if item.template_id != old
            ))).template_id,
            weapons.class_weapon_template_id(2))
        self.assertEqual(issued, 5)
        self.assertEqual(len(post.items), len(before.items) + 1)

    def test_the_carried_row_takes_a_never_issued_identity(self):
        before = inventory.INITIAL_BACKPACK
        post, issued = weapons.carry_old_weapon_forward(before, 2, 4)
        carried = post.items[-1]
        self.assertEqual(carried.identity, 5)
        self.assertNotIn(carried.identity, [i.identity for i in before.items])
        self.assertEqual(issued, carried.identity)

    def test_a_class_already_holding_its_weapon_is_refused(self):
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.carry_old_weapon_forward(inventory.INITIAL_BACKPACK, 1, 4)


class AdmissionBlockersTest(unittest.TestCase):
    """The round's central claim, asked of the production predicates."""

    def test_a_gladiator_bag_is_a_starting_bag_today(self):
        self.assertIn(inventory.INITIAL_BACKPACK, inventory.STARTING_BACKPACKS)

    def test_every_other_class_is_blocked_by_the_door_this_lane_owns(self):
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                found = weapons.admission_blockers(
                    inventory.INITIAL_BACKPACK, class_id, 4)
                self.assertEqual(len(found), 1, found)
                self.assertIn("apply_v111_stack_merge", found[0])

    def test_the_merge_door_that_refuses_is_the_one_that_runs_first(self):
        """pf-adversary D1: the first draft blamed ``runtime.py`` for a bag
        that never reaches it.  This pins WHICH door answers, by calling the
        store method itself on a migrated bag rather than by reasoning."""
        post, issued = weapons.carry_old_weapon_forward(
            inventory.INITIAL_BACKPACK, 2, 4)
        widened = tuple(
            weapons.retarget_weapon_row(inventory.INITIAL_BACKPACK, class_id)
            for class_id in class_catalog.CLASS_IDS)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", widened):
            self.assertNotIn(post, inventory.STARTING_BACKPACKS)
            self.assertNotIn(post, inventory.merged_v111_states())

    def test_the_runtime_warning_is_stated_about_new_characters_only(self):
        self.assertIsNone(weapons.newly_created_character_merge_warning())
        widened = tuple(
            weapons.retarget_weapon_row(inventory.INITIAL_BACKPACK, class_id)
            for class_id in class_catalog.CLASS_IDS)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", widened):
            warning = weapons.newly_created_character_merge_warning()
        self.assertIsNotNone(warning)
        self.assertIn("0206", warning)

    def test_a_picked_up_class_weapon_does_not_hide_the_born_row(self):
        """``2200003`` is a measured ground-drop id (``mob_loot``), so a
        second 'weapon' row is a played bag, not a corrupt one."""
        bag = inventory.INITIAL_BACKPACK
        born = weapons.weapon_row(bag)
        played = replace(bag, items=bag.items + (
            weapons.ItemAttrState(
                identity=5, template_id=weapons.class_weapon_template_id(2),
                quantity=1, slot=4),))
        self.assertEqual(weapons.weapon_row(played), born)

    def test_the_blocker_clears_once_the_post_state_is_a_starting_bag(self):
        """Not a prediction, and not a patched constant either: BOTH doors
        are asked with the post-state itself put into the starting set, which
        is the shape the two remaining halves produce.  The first draft
        patched ``inventory.MERGED_V111_BACKPACK`` instead -- a name
        ``runtime.py`` binds by value at import, so the patch proved nothing
        about ``runtime.py`` (pf-adversary D2)."""
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                post, _ = weapons.carry_old_weapon_forward(
                    inventory.INITIAL_BACKPACK, class_id, 4)
                with mock.patch.object(
                    inventory, "STARTING_BACKPACKS",
                    inventory.STARTING_BACKPACKS + (post,),
                ):
                    self.assertEqual(
                        weapons.admission_blockers(
                            inventory.INITIAL_BACKPACK, class_id, 4),
                        ())


class ReadOnlyPlanTest(unittest.TestCase):
    """Only the read-only half ships this round; the writing half is
    withdrawn under NOW.md `2050` (see the comment at the end of
    ``store.py``), so what is pinned here is the plan, not a write."""

    def setUp(self):
        handle, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        os.unlink(path)
        self.path = path
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        self.store = SQLiteStore(path, MIGRATIONS)
        self.store.migrate()
        self.glad = self._seed(selector=0, class_id=1, name="glad")
        self.pal = self._seed(selector=1, class_id=2, name="pal")
        self.unknown = self._seed(selector=2, class_id=None, name="nul")

    def _seed(self, *, selector, class_id, name):
        db = sqlite3.connect(self.path)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("INSERT OR IGNORE INTO accounts(login_name,created_at) "
                       "VALUES (?,?)", ("acct", STAMP))
            account_id = int(db.execute(
                "SELECT id FROM accounts WHERE login_name=?", ("acct",)
            ).fetchone()[0])
            cursor = db.execute(
                "INSERT INTO characters(account_id,selector,name,actor_wire,"
                "avatar_wire,identity_lo,identity_hi,created_at,updated_at,"
                "name_key,create_fingerprint,class_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (account_id, selector, name, b"\x00" * 8, b"\x00" * 8,
                 1000 + selector, 0, STAMP, STAMP, name.lower(),
                 "fp-%s" % name.lower(), class_id))
            cid = int(cursor.lastrowid)
            self.store._insert_initial_backpack(db, cid, STAMP)
            db.commit()
            return cid
        finally:
            db.close()

    def test_the_plan_names_the_target_and_the_reason_per_character(self):
        by_id = {e["character_id"]: e for e in
                 self.store.class_weapon_migration_plan()}
        self.assertEqual(by_id[self.glad]["skipped"],
                         "already holds its class weapon")
        # `1059`: an unmeasured class is not class 1.
        self.assertEqual(by_id[self.unknown]["skipped"], "class_id is NULL")
        entry = by_id[self.pal]
        self.assertEqual(entry["current_template"],
                         weapons.class_weapon_template_id(1))
        self.assertEqual(entry["target_template"],
                         weapons.class_weapon_template_id(2))
        self.assertEqual(len(entry["blockers"]), 1)

    def test_the_plan_writes_nothing(self):
        before = self._bags()
        self.store.class_weapon_migration_plan()
        self.assertEqual(self._bags(), before)

    def _bags(self):
        db = sqlite3.connect(self.path)
        try:
            return db.execute(
                "SELECT character_id,item_identity,template_id,slot "
                "FROM character_backpack_items ORDER BY character_id,item_identity"
            ).fetchall()
        finally:
            db.close()


class MintClassWeaponTests(unittest.TestCase):
    """``weapons.mint_class_weapon`` -- the GM-test-range door, `1455`'s
    weapon half.  Not the migration half above: this gives a NEW row, it
    does not retarget or carry forward an existing one."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("mint-class-weapon")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "WeaponOne", "weaponone",
            "fingerprint-mint-class-weapon", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    def _ground_drop_count(self):
        with self.store.connect() as db:
            return db.execute("SELECT count(*) FROM ground_drops").fetchone()[0]

    def _fill_slots(self, first_slot, last_slot_inclusive):
        """Occupy every slot in [first_slot, last_slot_inclusive] with a
        real row -- same raw-SQL shape ``test_store_mint_backpack_item.py``
        uses for its own full-bag fixture."""
        filler_template = weapons.class_weapon_template_id(1)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            next_identity = db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?", (self.character.id,),
            ).fetchone()[0]
            filler_rows = [
                (self.character.id, next_identity + offset, filler_template,
                 1, slot, 0, 0xFF, 0)
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

    def test_mints_the_class_weapon_into_the_first_free_slot_with_no_ground_drop(self):
        before_drops = self._ground_drop_count()
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                after = weapons.mint_class_weapon(
                    self.store, self.sid, self.character.id, class_id)
                new_rows = [
                    row for row in after.items
                    if row.template_id == weapons.class_weapon_template_id(class_id)
                    and row.slot >= FIRST_FREE_SLOT
                ]
                self.assertEqual(len(new_rows), 1, after.items)
                self.assertEqual(new_rows[0].quantity, 1)
        # No ground drop was ever involved.
        self.assertEqual(self._ground_drop_count(), before_drops)
        # Read back through a fresh call, same as a relog would see.
        reread = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(
            len(reread.items),
            len(inventory.INITIAL_BACKPACK.items) + class_catalog.CLASS_COUNT)

    def test_mints_into_the_true_last_slot_not_just_the_first_free_one(self):
        """pf-adversary (round xpcq8r): every existing test leaves several
        slots free, so a scan truncated by one (``range(0, ceiling)``
        instead of ``range(0, ceiling + 1)``) still finds A free slot and
        stays green.  This fills every slot except the ceiling itself, so
        only an off-by-one-correct scan can find the one that is left."""
        self._fill_slots(FIRST_FREE_SLOT, LAST_SLOT - 1)  # every slot but the ceiling
        before = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(before.items), LAST_SLOT)  # LAST_SLOT occupied, 1 free
        after = weapons.mint_class_weapon(
            self.store, self.sid, self.character.id, 2)
        new_rows = [
            row for row in after.items
            if row.slot == LAST_SLOT
            and row.template_id == weapons.class_weapon_template_id(2)
        ]
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(len(after.items), LAST_SLOT + 1)

    def test_the_first_mint_lands_at_the_true_first_free_slot(self):
        after = weapons.mint_class_weapon(
            self.store, self.sid, self.character.id, 2)
        minted = next(
            row for row in after.items
            if row.template_id == weapons.class_weapon_template_id(2))
        self.assertEqual(minted.slot, FIRST_FREE_SLOT)
        self.assertEqual(
            minted.identity,
            max(item.identity for item in inventory.INITIAL_BACKPACK.items) + 1)

    def test_lands_the_row_through_the_existing_door_not_a_new_one(self):
        """Proven by spying on the real door rather than re-typing its SQL
        here, the same shape ``test_store_mint_backpack_item.py`` uses: if
        this function ever stops calling it and starts executing its own
        INSERT, this goes red without an AST walk of this file to notice --
        and ``test_bag_admission_expiry.py``'s inserter-allowlist pin would
        also catch the same defect from the other side."""
        with mock.patch.object(
            self.store, "commit_acquired_backpack_item",
            wraps=self.store.commit_acquired_backpack_item,
        ) as spy:
            weapons.mint_class_weapon(self.store, self.sid, self.character.id, 4)
        spy.assert_called_once()
        (sid_arg, cid_arg, item_arg), _kwargs = spy.call_args
        self.assertEqual(sid_arg, self.sid)
        self.assertEqual(cid_arg, self.character.id)
        self.assertEqual(item_arg.template_id, weapons.class_weapon_template_id(4))

    def test_repeated_calls_do_not_dedupe(self):
        """Nonclaim, proven: a GM testing the same class twice gets two
        rows, not a silently-ignored second call."""
        first = weapons.mint_class_weapon(
            self.store, self.sid, self.character.id, 16)
        second = weapons.mint_class_weapon(
            self.store, self.sid, self.character.id, 16)
        template = weapons.class_weapon_template_id(16)
        self.assertEqual(
            len([row for row in second.items if row.template_id == template]), 2)
        self.assertGreater(len(second.items), len(first.items))

    # ----- named refusals -------------------------------------------------

    def test_an_unknown_class_id_is_refused_not_defaulted(self):
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.mint_class_weapon(self.store, self.sid, self.character.id, 3)
        self.assertEqual(self.store.get_backpack(self.sid, self.character.id), before)

    def test_a_full_backpack_refuses_before_writing_anything(self):
        self._fill_slots(FIRST_FREE_SLOT, LAST_SLOT)  # every remaining slot taken
        before = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(before.items), LAST_SLOT + 1)
        before_drops = self._ground_drop_count()
        with self.assertRaises(weapons.ClassWeaponError):
            weapons.mint_class_weapon(self.store, self.sid, self.character.id, 2)
        self.assertEqual(self.store.get_backpack(self.sid, self.character.id), before)
        self.assertEqual(self._ground_drop_count(), before_drops)

    def test_refuses_on_a_session_that_has_not_selected_the_character(self):
        other_account = self.store.ensure_account("mint-class-weapon-other")
        other_sid = self.store.open_session(other_account)
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(PermissionError):
            weapons.mint_class_weapon(
                self.store, other_sid, self.character.id, 2)
        self.assertEqual(self.store.get_backpack(self.sid, self.character.id), before)


if __name__ == "__main__":
    unittest.main()
