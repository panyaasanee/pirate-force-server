"""Pins for ``pirateforce_foundation.class_starting_gear``.

WHAT THIS FILE IS FOR.  ``COO-DECISION 20260907_2148`` (file
``20260907_2148_COO-DECISION-db2032-class-weapon-at-birth-owner-is-cs-
LANE-CS.md``) made two things binding when LANE-CS took the class-weapon
map: every class other than 1 gets ``n_SLOT_RHAND`` from the committed
table and never a literal, and class 1's ``BackpackAttr`` bytes do not move
by one bit.  Both are pinned here against sources this module does not own:
the table is re-read from disk by this file with its own parser, and the
class-1 bytes are compared against the frozen V141 encoder
(``legacy.make_backpack_attr_four_items()``), not against
``class_starting_gear``'s own output.

WHAT IS DELIBERATELY NOT PINNED.  Nothing here claims a live character's
bag changed: this module has no write path and no caller (a test below
measures that, rather than trusting the docstring).  Nothing here claims
anything about what the player HOLDS on screen -- that is ``AvatarAttr``,
which the client already sends per class; this bag is what she CARRIES.
"""

from __future__ import annotations

import ast
import csv
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import class_catalog, class_starting_gear
from pirateforce_foundation.inventory import (
    INITIAL_BACKPACK,
    make_backpack_attr,
    require_backpack_shape,
)
from pirateforce_foundation.legacy_bridge import load_legacy

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
TABLE_PATH = ROOT / "src" / "pirateforce_foundation" / "data" / "charcreate_class.tsv"
SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "class_starting_gear.py"
MODULE_NAME = "class_starting_gear"


def _table_hand_slots() -> dict:
    """Re-read the committed table here, with this file's own parser.

    Deliberately not ``class_catalog``'s dictionary: a pin that reads the
    value from the module under test would stay green if that module
    stopped reading the table at all -- the mutant that killed an earlier
    LANE-CS round (``#1002`` finding A4).
    """
    with TABLE_PATH.open("r", encoding="ascii", newline="") as handle:
        return {
            int(row["n_ID"]): (int(row["n_SLOT_RHAND"]), int(row["n_SLOT_LHAND"]))
            for row in csv.DictReader(handle, delimiter="\t")
        }


class TableSourcedTests(unittest.TestCase):
    def test_every_class_weapon_equals_the_committed_table_row(self):
        table = _table_hand_slots()
        self.assertEqual(sorted(table), sorted(class_catalog.CLASS_IDS))
        for class_id, (rhand, _lhand) in sorted(table.items()):
            with self.subTest(class_id=class_id):
                self.assertEqual(
                    class_starting_gear.starting_weapon_template(class_id), rhand
                )
                state = class_starting_gear.starting_backpack_state(class_id)
                weapon = state.items[class_starting_gear.WEAPON_ROW_INDEX]
                self.assertEqual(weapon.template_id, rhand)

    def test_the_five_classes_do_not_all_get_the_same_weapon(self):
        """The bug this module exists to end, stated as a measurement.

        Four of five characters are born with 2200002 today; if this ever
        collapses back to one value for every class, that is the bug
        returning, not a table change.
        """
        weapons = {
            class_id: class_starting_gear.starting_weapon_template(class_id)
            for class_id in class_catalog.CLASS_IDS
        }
        self.assertEqual(len(set(weapons.values())), len(weapons))

    def test_catalog_hand_slots_match_the_table_for_both_hands(self):
        table = _table_hand_slots()
        for class_id, pair in sorted(table.items()):
            with self.subTest(class_id=class_id):
                self.assertEqual(class_catalog.starting_hand_slots(class_id), pair)

    def test_an_unknown_class_id_raises_and_never_falls_back_to_class_1(self):
        for unknown in (0, 3, 99, -1):
            with self.subTest(unknown=unknown):
                with self.assertRaises(KeyError):
                    class_starting_gear.starting_backpack_state(unknown)

    def test_a_bool_is_not_a_class_id(self):
        """``True`` is an ``int`` in Python and sqlite binds it as 1.

        Same trap that survived a mutant in round ``b2cnxe``: without this
        guard ``starting_backpack_state(True)`` would quietly hand back the
        Gladiator bag.
        """
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    class_starting_gear.starting_backpack_state(value)


class ClassOneIsUntouchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_class_1_returns_the_committed_object_itself(self):
        self.assertIs(
            class_starting_gear.starting_backpack_state(1), INITIAL_BACKPACK
        )

    def test_class_1_wire_bytes_equal_the_frozen_v141_encoder(self):
        wire = make_backpack_attr(
            self.legacy, class_starting_gear.starting_backpack_state(1)
        )
        self.assertEqual(wire, self.legacy.make_backpack_attr_four_items())

    def test_every_other_class_differs_from_class_1_in_the_weapon_row_only(self):
        base = class_starting_gear.starting_backpack_state(1)
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                state = class_starting_gear.starting_backpack_state(class_id)
                self.assertIsNot(state, INITIAL_BACKPACK)
                self.assertEqual(state.base_mask, base.base_mask)
                self.assertEqual(state.base_identity, base.base_identity)
                self.assertEqual(state.range_mask, base.range_mask)
                self.assertEqual(len(state.items), len(base.items))
                differing = [
                    index
                    for index, (new, old) in enumerate(zip(state.items, base.items))
                    if new != old
                ]
                self.assertEqual(differing, [class_starting_gear.WEAPON_ROW_INDEX])
                new = state.items[class_starting_gear.WEAPON_ROW_INDEX]
                old = base.items[class_starting_gear.WEAPON_ROW_INDEX]
                self.assertEqual(new.identity, old.identity)
                self.assertEqual(new.slot, old.slot)
                self.assertEqual(new.quantity, old.quantity)
                self.assertEqual(new.raw_u8_38, old.raw_u8_38)
                self.assertEqual(new.raw_u8_39, old.raw_u8_39)
                self.assertEqual(new.detail_present, old.detail_present)

    def test_every_class_bag_passes_the_encoder_gate_and_encodes(self):
        """The wire half: a class-2..32 bag is not a shape the wall refuses."""
        base_wire = make_backpack_attr(self.legacy, INITIAL_BACKPACK)
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                state = class_starting_gear.starting_backpack_state(class_id)
                require_backpack_shape(state)
                wire = make_backpack_attr(self.legacy, state)
                self.assertEqual(len(wire), len(base_wire))
                if class_id != 1:
                    differing = sum(
                        1 for a, b in zip(wire, base_wire) if a != b
                    )
                    # One u32 template field, four bytes wide, and nothing
                    # else: the identity list, the two counts and the masks
                    # are byte-for-byte the ones V141 already ships.
                    self.assertLessEqual(differing, 4)


class DerivedNotCountedTests(unittest.TestCase):
    def test_the_weapon_row_is_found_by_the_table_value_not_by_index(self):
        """Move class 1's weapon in the table and the derivation must refuse.

        ``_weapon_row_index`` is re-run against a patched catalog rather
        than reading the cached ``WEAPON_ROW_INDEX``; a module that had
        hardcoded index 3 would return 3 here and stay green.
        """
        original = class_catalog.starting_hand_slots
        try:
            class_catalog.starting_hand_slots = lambda class_id: (7777777, 0)
            with self.assertRaises(class_starting_gear.ClassStartingGearError):
                class_starting_gear._weapon_row_index()
        finally:
            class_catalog.starting_hand_slots = original
        self.assertEqual(class_starting_gear._weapon_row_index(), 3)

    def test_an_ambiguous_weapon_id_refuses_rather_than_picking_one(self):
        original = class_catalog.starting_hand_slots
        try:
            # 2600001 is in the committed bag twice (rows 0 and 2).
            class_catalog.starting_hand_slots = lambda class_id: (2600001, 0)
            with self.assertRaises(class_starting_gear.ClassStartingGearError):
                class_starting_gear._weapon_row_index()
        finally:
            class_catalog.starting_hand_slots = original

    def test_a_class_with_no_right_hand_item_would_refuse(self):
        """No class has ``n_SLOT_RHAND = 0`` today; two have no LEFT hand.

        If a future table row ever leaves the right hand empty, composing a
        bag with template 0 is not an answer this module is allowed to
        invent.
        """
        original = class_catalog.starting_hand_slots
        try:
            class_catalog.starting_hand_slots = lambda class_id: (0, 0)
            with self.assertRaises(class_starting_gear.ClassStartingGearError):
                class_starting_gear.starting_weapon_template(2)
        finally:
            class_catalog.starting_hand_slots = original


class NotWiredYetTests(unittest.TestCase):
    def test_the_module_has_no_production_caller(self):
        """Measured, not asserted in prose (``NOW.md``: WIRED = observed).

        The measurement walks the PARSED module, not its text: round
        `b2cnxe` was bitten from the other side by a sibling lane's pin
        that grepped prose, so naming a module in a comment turned that
        pin red.  A mention is not a caller; an ``import`` is.  A dynamic
        ``importlib`` call by name would slip past an AST walk, so the
        text scan below still runs -- it just reports mentions separately
        instead of failing on them.
        """
        importers = []
        mentions = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            if path == SOURCE_PATH:
                continue
            text = path.read_text(encoding="utf-8")
            if MODULE_NAME not in text:
                continue
            mentions.append(str(path.relative_to(ROOT)))
            try:
                tree = ast.parse(text)
            except SyntaxError:  # pragma: no cover - a broken tree is not ours
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[-1] == MODULE_NAME for a in node.names):
                        importers.append(str(path.relative_to(ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[-1] == MODULE_NAME or any(
                        a.name == MODULE_NAME for a in node.names
                    ):
                        importers.append(str(path.relative_to(ROOT)))
                elif isinstance(node, ast.Call):
                    func = node.func
                    name = getattr(func, "attr", getattr(func, "id", ""))
                    if name in ("import_module", "__import__"):
                        importers.append(str(path.relative_to(ROOT)))
        self.assertEqual(importers, [])
        # Recorded, not enforced: today the only mention is class_catalog's
        # docstring pointing readers at this module.
        self.assertEqual(
            mentions, ["src/pirateforce_foundation/class_catalog.py"]
        )

    def test_production_allowed_is_false_while_there_is_no_seam(self):
        self.assertIs(class_starting_gear.production_allowed, False)

    def test_no_item_id_is_an_executable_literal_in_the_module(self):
        """Ids come from the table, never from code.

        Docstrings are excluded on purpose: the module cites LANE-DB's
        measured `2200002` in prose, which is the citation this round was
        built on.  What must not exist is an item id the interpreter can
        reach -- a constant, a default, a comparison.
        """
        tree = ast.parse(SOURCE_PATH.read_text(encoding="ascii"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                body = getattr(node, "body", [])
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    docstrings.add(id(body[0].value))
        table = _table_hand_slots()
        ids = {value for pair in table.values() for value in pair if value}
        spelled = sorted(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and id(node) not in docstrings
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
            and node.value in ids
        )
        self.assertEqual(spelled, [])


class ConsoleTokenTests(unittest.TestCase):
    def test_the_headless_token_prints_one_line_per_class_in_ascii(self):
        result = subprocess.run(
            [sys.executable, "-m", "pirateforce_foundation.class_starting_gear"],
            cwd=str(ROOT),
            env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            check=True,
        )
        lines = result.stdout.decode("ascii").splitlines()
        self.assertEqual(len(lines), class_catalog.CLASS_COUNT + 1)
        table = _table_hand_slots()
        for class_id, (rhand, _lhand) in sorted(table.items()):
            with self.subTest(class_id=class_id):
                self.assertIn(
                    "CLASS_STARTING_GEAR class_id=%d " % class_id,
                    result.stdout.decode("ascii"),
                )
                self.assertIn("rhand=%d" % rhand, result.stdout.decode("ascii"))
        self.assertIn("wired_callers=0", lines[-1])

    def test_the_token_says_which_class_is_the_untouched_one(self):
        self.assertIn("same_object_as_v141=YES", class_starting_gear.describe(1))
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                self.assertIn(
                    "same_object_as_v141=NO", class_starting_gear.describe(class_id)
                )


if __name__ == "__main__":
    unittest.main()
