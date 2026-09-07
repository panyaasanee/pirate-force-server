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
from pirateforce_foundation.store import SQLiteStore

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")
STAMP = "2026-09-08T04:00:00Z"


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


if __name__ == "__main__":
    unittest.main()
