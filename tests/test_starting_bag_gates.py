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
comes back with wire bytes.  ``tests/test_bag_admission.py`` measures the
predicate; only this file measures the PLAYER's path through it.

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

from pirateforce_foundation import bag_admission, inventory  # noqa: E402
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The weapon row every character is born holding today, and the five
#: template ids LANE-CS lifted from the real ``CHARCREATE_CLASS`` rows
#: (letter 20260908_0022).  They are written here as the SHAPE of the
#: five-member case, never as a second source of truth: nothing in
#: ``src/`` reads this file, and the day ``starting_backpack_states()``
#: lands, the first test below stops needing it.
WEAPON_IDENTITY = 4
CS_WEAPON_TEMPLATES = (2200002, 2200003, 2200006, 2200005, 2200008)


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
        merged = tuple(inventory.merged_v111_state(bag) for bag in bags)

        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags), \
                mock.patch.object(inventory, "MERGED_V111_BACKPACKS", merged):
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
        merged = tuple(inventory.merged_v111_state(bag) for bag in bags)
        with mock.patch.object(inventory, "STARTING_BACKPACKS", bags), \
                mock.patch.object(inventory, "MERGED_V111_BACKPACKS", merged):
            session, character = self._create("stranger")
            self._move_the_weapon_row(character.id, stranger)
            relog = FoundationSession(
                self.lifecycle, self.projector, "stranger")
            with self.assertRaises(PermissionError):
                relog.select_and_start(character.selector)
            self.assertFalse(
                bag_admission.may_enter_world(
                    bag_holding_weapon(stranger),
                    allow_hypothesized_item_move=False, issued_through=4,
                ),
            )


if __name__ == "__main__":
    unittest.main()
