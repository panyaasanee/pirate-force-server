"""COO-DECISION 20260907_2342: the bag gates accept a SET of starting bags.

Every character in this game is born holding one bag, and until this round
the three gates that decide whether that bag may enter the world compared it
against one constant BY NAME (``inventory.INITIAL_BACKPACK``).  LANE-CS is
about to make each of the five classes born holding its own weapon
(``class_starting_gear.starting_backpack_states()``, their PR #1091, not on
main while this file is written).  A gate that names one constant refuses
four of those five characters at the character-select screen -- the player
sits on "connecting" forever -- so the gates had to become set-shaped BEFORE
the set grows.  That ordering is COO's, not this lane's.

WHAT THIS FILE MEASURES, and it is the reason it boots the real line rather
than a stub: a character whose bag is a member of the starting set gets
through ``FoundationSession.select_and_start`` -- real ``SQLiteStore``, real
``migrations/``, real ``CharacterLifecycle``, real legacy projector -- and
comes back with wire bytes.  The gate-2 predicate has its own
enumerating test file; only this file measures the PLAYER's path through it.

This file deliberately imports NOTHING from the gate-2 predicate module.
NOW.md's ``2050`` pin forbids answering a cross-lane pin with a skip, an
xfail or an allowlist entry, and that module carries a pin naming every file
allowed to reach for it; the honest way past it is to not reach.  Every
assertion here is the answer ``select_and_start`` gave, which is the answer
that matters to a player anyway.

THE BAG IS NOT HAND-BUILT INTO THE DATABASE BY THE TEST'S OWN IDEA OF ONE.
It is written the way the day-after weapon migration will write it: the
character is created by the production ``create``, and then exactly one
column of one row is moved (``character_backpack_items.template_id`` of the
weapon row), which is the entire difference between the five bags per
LANE-CS's letter 20260908_0022.

WHAT THIS FILE DOES NOT PROVE.
* Not client-observable.  No window opens; nobody sees a cutlass become a
  musket.  It measures the server's answer and the bytes it composes.
* It does NOT prove the production set has five members today.  It has one
  (``inventory.STARTING_BACKPACKS``).  The five-member case is measured by
  installing a five-member set into that module, which is the mechanism, not
  the contents -- the contents are LANE-CS's to land, and the moment they do,
  the first test here covers all five with no edit to this file.
* It does not touch ``production_allowed`` for anything.
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
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

WEAPON_IDENTITY = 4


def _weapon_templates_from_the_committed_table():
    """The five ids READ from the table, never typed from a letter.

    The first draft hardcoded them and cited LANE-CS's letter 20260908_0022.
    They were right -- pf-adversary re-derived them and they match -- but a
    fourth copy of a mapping that is committed right here goes stale silently
    the day the table moves, and this repository already has other readers of
    the same file.  ``n_SLOT_RHAND`` is the right-hand weapon column, and the
    row order is ``class_catalog.CLASS_IDS``.
    """
    table = (
        ROOT / "src" / "pirateforce_foundation" / "data"
        / "creation_gear_by_class.tsv"
    )
    lines = table.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    weapon = header.index("n_SLOT_RHAND")
    return tuple(int(line.split("\t")[weapon]) for line in lines[1:] if line)


CS_WEAPON_TEMPLATES = _weapon_templates_from_the_committed_table()


def bag_holding_weapon(template_id: int):
    """``INITIAL_BACKPACK`` with only the weapon row's template moved."""
    return replace(
        INITIAL_BACKPACK,
        items=tuple(
            replace(row, template_id=template_id)
            if row.identity == WEAPON_IDENTITY else row
            for row in INITIAL_BACKPACK.items
        ),
    )


class StartingBagEntersTheWorldTests(unittest.TestCase):
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

    def _create(self, login_name):
        session = FoundationSession(self.lifecycle, self.projector, login_name)
        character, _ = session.create(
            "test01", self.legacy.get_preset_actor_wire())
        return session, character

    def _move_the_weapon_row(self, character_id, template_id):
        """Exactly what the weapon migration will do, and nothing else."""
        with self.store.connect() as db:
            moved = db.execute(
                "UPDATE character_backpack_items SET template_id=? "
                "WHERE character_id=? AND item_identity=?",
                (template_id, character_id, WEAPON_IDENTITY),
            )
            self.assertEqual(moved.rowcount, 1)

    def test_gate_accepts_every_starting_bag(self):
        """COO 20260907_2342's own pass criterion, over the live set.

        Iterating ``inventory.STARTING_BACKPACKS`` rather than a list written
        here is the point: this test needs no edit on the day LANE-CS's five
        replace today's one, and it fails the day a bag is added to the set
        that the production path cannot actually seat.
        """
        for index, bag in enumerate(inventory.STARTING_BACKPACKS):
            with self.subTest(starting_bag=index):
                session, character = self._create(f"start-bag-{index}")
                weapon = next(
                    row.template_id for row in bag.items
                    if row.identity == WEAPON_IDENTITY
                )
                self._move_the_weapon_row(character.id, weapon)

                relog = FoundationSession(
                    self.lifecycle, self.projector, f"start-bag-{index}")
                selected, (start_pc, start_frame) = relog.select_and_start(
                    character.selector)

                self.assertEqual(selected.id, character.id)
                self.assertEqual(relog.backpack, bag)
                self.assertTrue(start_pc)
                self.assertTrue(start_frame)

    def test_five_class_bags_all_enter_the_world_once_the_set_holds_them(self):
        """The five-member case, measured on the real line.

        The set is installed into ``inventory`` rather than imported from
        LANE-CS, because their module is not on main yet.  What is being
        measured is the MECHANISM -- that a bag's admission depends on set
        membership and on nothing else -- so the ids only have to be five
        distinct plausible weapons, which is what makes the control below
        meaningful.
        """
        bags = tuple(
            bag_holding_weapon(template) for template in CS_WEAPON_TEMPLATES
        )
        self.assertEqual(bags[0], INITIAL_BACKPACK)
        self.assertEqual(len(set(bags)), len(CS_WEAPON_TEMPLATES))
        # ONE patch, not two.  The merged half is derived live now, and
        # patching it separately was hiding a real defect: with the set
        # widened in `inventory` alone, `store` still refused four of the
        # five classes because it had bound the tuple by value at import
        # (pf-adversary).  A single patch that every gate must follow is the
        # measurement; two patches were a way of not measuring one of them.
        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags):
            for index, (template, bag) in enumerate(
                    zip(CS_WEAPON_TEMPLATES, bags)):
                with self.subTest(weapon=template):
                    session, character = self._create(f"five-{index}")
                    self._move_the_weapon_row(character.id, template)
                    relog = FoundationSession(
                        self.lifecycle, self.projector, f"five-{index}")
                    _selected, (start_pc, _frame) = relog.select_and_start(
                        character.selector)
                    self.assertEqual(relog.backpack, bag)
                    self.assertTrue(start_pc)

    def test_the_stack_merge_follows_the_set_from_inventory_alone(self):
        """Gate 3, the one no five-bag measurement in this round reached.

        pf-adversary's D2: ``store`` had bound the starting tuples BY VALUE at
        import, so widening the set in ``inventory`` moved gates 1 and 2 and
        left this one refusing four of five classes -- while the module
        comment claimed no gate could be left behind.  The patch here is on
        ``inventory`` ONLY, which is the whole point: if ``store`` ever binds
        by value again, this test is the one that goes red.

        It also pins the derived post-state end to end: the merged bag keeps
        the class's own weapon row, which a constant post-state check would
        have called a failed merge after the rows were written.
        """
        bags = tuple(
            bag_holding_weapon(template) for template in CS_WEAPON_TEMPLATES
        )
        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags):
            for index, (template, bag) in enumerate(
                    zip(CS_WEAPON_TEMPLATES, bags)):
                with self.subTest(weapon=template):
                    session, character = self._create(f"merge-{index}")
                    self._move_the_weapon_row(character.id, template)
                    relog = FoundationSession(
                        self.lifecycle, self.projector, f"merge-{index}")
                    selected, _started = relog.select_and_start(
                        character.selector)

                    after = self.lifecycle.store.apply_v111_stack_merge(
                        relog.session_id, selected.id)

                    self.assertEqual(after, inventory.merged_v111_state(bag))
                    self.assertEqual(
                        [row.template_id for row in after.items
                         if row.identity == WEAPON_IDENTITY],
                        [template],
                    )
                    # Idempotent, and the merged bag is itself admitted.
                    self.assertIsNone(
                        self.lifecycle.store.apply_v111_stack_merge(
                            relog.session_id, selected.id),
                    )

    def test_the_slot2_move_derives_the_golden_it_used_to_compare_against(self):
        """The V111_SLOT2_DESTINATION pin, on the set production holds today.

        A derivation that does not reproduce the measured constant is a new
        rule wearing the old one's name.  This is the whole of the evidence
        that renaming the literal 2 changed nothing.
        """
        self.assertEqual(
            inventory.hypothesized_v111_slot2_state(
                inventory.MERGED_V111_BACKPACK),
            inventory.HYPOTHESIZED_V111_SLOT2_BACKPACK,
        )
        self.assertEqual(
            inventory.hypothesized_v111_slot2_states(),
            (inventory.HYPOTHESIZED_V111_SLOT2_BACKPACK,),
        )

    def test_the_slot2_move_follows_the_set_from_inventory_alone(self):
        """Gate 4 -- chief's R404, the half of CORE-REQUEST 0206 left here.

        Same shape as the stack-merge test above and for the same reason: the
        patch is on ``inventory`` ONLY.  ``store`` used to bind BOTH V111
        goldens by value and compare its pre-state, its UPDATE literals and
        its post-state against them, so a character born in any class but the
        first merged successfully and then had the follow-up move rolled back
        by its own post-state check, with no reply to the client.

        NONCLAIM, and it is why the next test exists: the five bags in the
        committed table differ ONLY at the right-hand weapon row (identity
        4), so the identity-1 row the UPDATE names is the same in all five.
        What THIS test measures red is the pre-state and post-state
        comparisons, not the WHERE literals.
        """
        bags = tuple(
            bag_holding_weapon(template) for template in CS_WEAPON_TEMPLATES
        )
        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags):
            for index, (template, bag) in enumerate(
                    zip(CS_WEAPON_TEMPLATES, bags)):
                with self.subTest(weapon=template):
                    session, character = self._create(f"slot2-{index}")
                    self._move_the_weapon_row(character.id, template)
                    relog = FoundationSession(
                        self.lifecycle, self.projector, f"slot2-{index}")
                    selected, _started = relog.select_and_start(
                        character.selector)
                    merged = self.lifecycle.store.apply_v111_stack_merge(
                        relog.session_id, selected.id)
                    self.assertEqual(merged, inventory.merged_v111_state(bag))

                    after = (
                        self.lifecycle.store
                        .apply_hypothesized_v111_slot2_move(
                            relog.session_id, selected.id)
                    )

                    self.assertEqual(
                        after,
                        inventory.hypothesized_v111_slot2_state(merged),
                    )
                    # The class keeps its own weapon across the move, and the
                    # surviving stack is the row that moved.
                    self.assertEqual(
                        [row.template_id for row in after.items
                         if row.identity == WEAPON_IDENTITY],
                        [template],
                    )
                    self.assertEqual(
                        [row.slot for row in after.items if row.identity == 1],
                        [inventory.V111_SLOT2_DESTINATION],
                    )
                    # Idempotent: the moved bag is itself admitted by the
                    # first door, so a repeat is a quiet None, not a raise.
                    self.assertIsNone(
                        self.lifecycle.store
                        .apply_hypothesized_v111_slot2_move(
                            relog.session_id, selected.id),
                    )

    def test_the_moved_row_is_found_by_the_bag_not_by_typed_literals(self):
        """The UPDATE's WHERE clause, measured where the committed table cannot.

        The old statement spelled ``template_id=2600001 AND quantity=2 AND
        slot=0`` -- three values that are facts about ONE bag, derived from
        ``INITIAL_BACKPACK`` and frozen.  The five ids in
        ``creation_gear_by_class.tsv`` do not vary the identity-1 stack, so
        no measurement over that table can tell a derived WHERE from a typed
        one; this test installs a starting set that does vary it.

        NONCLAIM: the bag below is NOT a class bag anyone has landed.  It is
        the MECHANISM -- "the row named is the row the character holds" --
        and it is the reason the fix is not carried by the five-class test
        alone.  A merged stack of 6 also proves the frozen ``quantity=2`` was
        a value and not a shape.
        """
        stacked = replace(
            INITIAL_BACKPACK,
            items=tuple(
                replace(row, template_id=2600002, quantity=3)
                if row.identity in (1, 3) else row
                for row in INITIAL_BACKPACK.items
            ),
        )
        self.assertNotEqual(stacked, INITIAL_BACKPACK)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", (stacked,)):
            session, character = self._create("stacked")
            with self.store.connect() as db:
                changed = db.execute(
                    "UPDATE character_backpack_items "
                    "SET template_id=?, quantity=? "
                    "WHERE character_id=? AND item_identity IN (1, 3)",
                    (2600002, 3, character.id),
                )
                self.assertEqual(changed.rowcount, 2)
            relog = FoundationSession(
                self.lifecycle, self.projector, "stacked")
            selected, _started = relog.select_and_start(character.selector)
            self.assertEqual(relog.backpack, stacked)

            merged = self.lifecycle.store.apply_v111_stack_merge(
                relog.session_id, selected.id)
            self.assertEqual(
                [row.quantity for row in merged.items if row.identity == 1],
                [6],
            )

            after = self.lifecycle.store.apply_hypothesized_v111_slot2_move(
                relog.session_id, selected.id)

            self.assertEqual(
                after, inventory.hypothesized_v111_slot2_state(merged))
            surviving = [row for row in after.items if row.identity == 1]
            self.assertEqual(
                [(row.template_id, row.quantity, row.slot)
                 for row in surviving],
                [(2600002, 6, inventory.V111_SLOT2_DESTINATION)],
            )

    def test_a_merged_bag_outside_the_set_is_still_refused_by_the_move(self):
        """The control for the two tests above.

        Widening the pre-state door to a SET is not opening it.  A bag that
        is nobody's merged state is refused before any row is touched, and
        the refusal is the same ``ValueError`` the constant comparison
        raised, so callers upstream see no change of contract.
        """
        session, character = self._create("unmerged")
        relog = FoundationSession(self.lifecycle, self.projector, "unmerged")
        selected, _started = relog.select_and_start(character.selector)
        # A freshly seated character holds a STARTING bag, which is nobody's
        # merged state -- the move must refuse it.
        self.assertNotIn(
            relog.backpack, inventory.merged_v111_states())
        with self.assertRaises(ValueError):
            self.lifecycle.store.apply_hypothesized_v111_slot2_move(
                relog.session_id, selected.id)
        with self.store.connect() as db:
            slots = [
                row[0] for row in db.execute(
                    "SELECT slot FROM character_backpack_items "
                    "WHERE character_id=? AND item_identity=1",
                    (selected.id,),
                )
            ]
        self.assertEqual(slots, [0])

    def test_the_control_a_bag_outside_the_set_is_still_refused(self):
        """Without this the file would pass against a gate that admits all.

        The same four-of-five characters, on the set as production holds it
        today, are refused -- which is exactly the state main is in and the
        reason COO ordered the widening before LANE-CS's five land.
        """
        for index, template in enumerate(CS_WEAPON_TEMPLATES[1:], start=1):
            with self.subTest(weapon=template):
                session, character = self._create(f"refused-{index}")
                self._move_the_weapon_row(character.id, template)
                relog = FoundationSession(
                    self.lifecycle, self.projector, f"refused-{index}")
                with self.assertRaises(PermissionError):
                    relog.select_and_start(character.selector)

    def test_a_bag_that_is_no_class_starting_bag_is_refused_either_way(self):
        """Widening the set is not the same as opening the gate.

        A template no class is born holding stays refused with the five-member
        set installed, so the set is the whole of the rule and "any moved
        weapon row" is not.
        """
        stranger = 2200099
        self.assertNotIn(stranger, CS_WEAPON_TEMPLATES)
        bags = tuple(
            bag_holding_weapon(template) for template in CS_WEAPON_TEMPLATES
        )
        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags):
            session, character = self._create("stranger")
            self._move_the_weapon_row(character.id, stranger)
            relog = FoundationSession(
                self.lifecycle, self.projector, "stranger")
            with self.assertRaises(PermissionError):
                relog.select_and_start(character.selector)


if __name__ == "__main__":
    unittest.main()
