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
    is_unmoved_baseline,
    make_backpack_attr,
    require_backpack_shape,
    require_known_backpack,
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

    def test_a_non_int_is_refused_by_its_own_term_of_the_guard(self):
        """The guard's two terms are separately reachable (pf-adversary D7).

        bool is refused by the first term and only by it; a string is
        refused by the second and only by it.  The earlier `type() is not
        int or isinstance(bool)` form had a term nothing could reach, so a
        mutant that deleted the bool half stayed green.
        """
        for value in ("1", 1.0, None, (1,)):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    class_starting_gear.starting_backpack_state(value)

    def test_an_int_subclass_is_still_a_class_id(self):
        """The seam's own resolver is annotated `int | None`; an IntEnum
        must not be refused for being a subclass (pf-adversary D7).
        """
        import enum

        class _ClassId(enum.IntEnum):
            GLADIATOR = 1

        self.assertIs(
            class_starting_gear.starting_backpack_state(_ClassId.GLADIATOR),
            INITIAL_BACKPACK,
        )


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
                    # ONE byte, measured, not "at most four" (pf-adversary
                    # D8: an assertLessEqual also passes at 0, so a module
                    # that handed back the Gladiator bag for every class
                    # would have satisfied the earlier form).  The four
                    # weapon ids differ from 2200002 in one byte each; the
                    # identity list, both counts and the masks are the ones
                    # V141 already ships.
                    self.assertEqual(differing, 1)


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

    def test_the_shipping_path_re_derives_and_does_not_read_a_global(self):
        """pf-adversary D2: both `WEAPON_ROW_INDEX = 3` and `= len(...) - 1`
        passed the earlier suite, because `starting_backpack_state` read the
        global while only the helper was tested.  Moving the global alone
        must now change nothing.
        """
        original = class_starting_gear.WEAPON_ROW_INDEX
        try:
            class_starting_gear.WEAPON_ROW_INDEX = 0
            state = class_starting_gear.starting_backpack_state(2)
            changed = [
                index
                for index, (new, old) in enumerate(
                    zip(state.items, INITIAL_BACKPACK.items)
                )
                if new != old
            ]
            self.assertEqual(changed, [original])
        finally:
            class_starting_gear.WEAPON_ROW_INDEX = original

    def test_a_weapon_id_that_lands_on_another_row_refuses(self):
        """pf-adversary D2: "exactly one hit" cannot tell a weapon row from a
        cask row.  With class 1's table weapon drifted to the cask template
        (which is also in the bag exactly once), the earlier derivation
        returned the CASK row and composed a Sniper carrying a rifle in the
        cask slot with the Gladiator sword still in the weapon slot.
        """
        original = class_catalog.starting_hand_slots
        cask = INITIAL_BACKPACK.items[1].template_id
        try:
            class_catalog.starting_hand_slots = lambda class_id: (cask, 0)
            with self.assertRaises(class_starting_gear.ClassStartingGearError):
                class_starting_gear._weapon_row_index()
        finally:
            class_catalog.starting_hand_slots = original

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
        roots = [
            ROOT / "src",
            ROOT / "tools",
            ROOT / "migrations",
            ROOT / "scenarios",
            ROOT / "current",
        ]
        # pf-adversary D9: `src/` alone is narrower than the precedent
        # `persistence_class_id.py`'s own isolation pin records; a caller
        # under tools/ or scenarios/ was invisible.
        paths = [
            path
            for root in roots
            if root.exists()
            for path in root.rglob("*.py")
        ]
        for path in sorted(paths):
            if path == SOURCE_PATH:
                continue
            text = path.read_text(encoding="utf-8")
            if MODULE_NAME not in text:
                continue
            mentions.append(path.relative_to(ROOT).as_posix())
            try:
                tree = ast.parse(text)
            except SyntaxError:  # pragma: no cover - a broken tree is not ours
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[-1] == MODULE_NAME for a in node.names):
                        importers.append(path.relative_to(ROOT).as_posix())
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[-1] == MODULE_NAME or any(
                        a.name == MODULE_NAME for a in node.names
                    ):
                        importers.append(path.relative_to(ROOT).as_posix())
                elif isinstance(node, ast.Call):
                    func = node.func
                    name = getattr(func, "attr", getattr(func, "id", ""))
                    if name in ("import_module", "__import__"):
                        importers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(importers, [])
        # Recorded, not enforced: today the mentions are two comments, and
        # NEITHER is a caller.  `class_catalog` points readers here from its
        # docstring.  `inventory.py` gained its line while this branch was
        # closed -- LANE-DB changed STARTING_BACKPACKS from a name comparison
        # to a set membership and named this module as the owner of the
        # contents it will one day hold (their commit 7b8fff6, on main).  A
        # comment that names a module is not an import of it, which is why
        # this list is recorded and `importers` is the assertion that bites.
        self.assertEqual(
            mentions,
            [
                "src/pirateforce_foundation/class_catalog.py",
                "src/pirateforce_foundation/inventory.py",
            ],
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
        # pf-adversary D6: the earlier set held only the six hand-slot ids,
        # so a literal 2600001 (the potion, in the bag twice) or 2400901
        # (the cask) could be spelled in the module and this pin stayed
        # green.  Every id the starting bag carries counts.
        ids |= {item.template_id for item in INITIAL_BACKPACK.items}
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
        # The zero is now counted, not spelled (pf-adversary D3): the same
        # function the token calls must return the same number this test
        # measures for itself.
        self.assertEqual(class_starting_gear.count_production_importers(), 0)

    def test_the_token_reports_a_real_importer_when_one_exists(self):
        """The number must be able to be something other than zero.

        pf-adversary D3 dropped a genuine importer into the package and the
        token still printed `wired_callers=0`, because the zero lived in the
        format string.  This writes such a module, runs the SAME console
        entry the operator runs, and removes it again -- a literal zero
        cannot pass.
        """
        intruder = (
            ROOT / "src" / "pirateforce_foundation" / "_class_starting_gear_probe.py"
        )
        self.assertFalse(intruder.exists())
        intruder.write_text(
            "from . import class_starting_gear\n"
            "STATE = class_starting_gear.starting_backpack_state(1)\n",
            encoding="ascii",
        )
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pirateforce_foundation.class_starting_gear"],
                cwd=str(ROOT),
                env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
                capture_output=True,
                check=True,
            )
            self.assertIn("wired_callers=1", result.stdout.decode("ascii"))
        finally:
            intruder.unlink()
        self.assertEqual(class_starting_gear.count_production_importers(), 0)

    def test_the_token_says_which_class_is_the_untouched_one(self):
        self.assertIn("same_object_as_v141=YES", class_starting_gear.describe(1))
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                self.assertIn(
                    "same_object_as_v141=NO", class_starting_gear.describe(class_id)
                )


class Gate2RefusesEveryClassButOneTodayTests(unittest.TestCase):
    """The wall this round did NOT clear, pinned so nobody wires past it.

    ``pf-adversary`` (round ``e8pss9``, D1) booted a real store, real
    migrations, real ``lifecycle`` and ``FoundationSession.select_and_start``
    with a Sniper whose bag was written exactly as the proposed ``store.py``
    seam would write it, and measured::

        BAG_ADMISSION verdict=refused golden=initial acquired=0
                      reason=golden_item_moved_or_altered
        SELECT_AND_START_RAISED PermissionError

    ``runtime.py`` answers that branch with
    ``foundation_start_game_rejected_no_reply`` and NO frame, so the client
    would sit on "connecting" forever.  ``INITIAL_BACKPACK`` is four goldens
    at once -- the V141 encoder pin (which stays green), gate 2's admission
    golden, ``require_known_backpack``'s allowlist and
    ``store.apply_v111_stack_merge``'s pre-state -- and three of the four
    still spell "carries the Gladiator sword" as part of "is a legal bag".

    WHY THIS PINS THE TERM AND NOT THE PREDICATE.  The gate-2 module carries
    another lane's guard admitting exactly one caller in the package plus a
    named list of files that may even mention it.  A first cut of this file
    imported it, turned that guard red, and the only ways out would have
    been to widen someone else's list or to delete a correct check -- both
    forbidden by ``COO-DECISION 20260907_2050``.  So the wall is pinned by
    the term gate 2 turns on for an untouched bag,
    ``inventory.is_unmoved_baseline``, plus gate 3's own raise.  Those are
    the two facts that make the refusal happen; the end-to-end refusal
    itself is measured in the adversary token quoted above.

    These tests pass BECAUSE the refusal is real.  The day someone answers
    "what is a legal Paladin bag", they go red and must be rewritten by the
    person who answered -- that is the point of pinning a wall rather than
    describing it.
    """

    def test_only_class_1_still_looks_like_the_untouched_baseline(self):
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                state = class_starting_gear.starting_backpack_state(class_id)
                self.assertIs(is_unmoved_baseline(state), class_id == 1)

    def test_the_governed_item_gates_refuse_them_too(self):
        """Not one gate to widen: three sites, measured (pf-adversary D5)."""
        for class_id in class_catalog.CLASS_IDS:
            if class_id == 1:
                continue
            with self.subTest(class_id=class_id):
                state = class_starting_gear.starting_backpack_state(class_id)
                with self.assertRaises(ValueError):
                    require_known_backpack(state)


class TheSetOfFiveIsTheGoldenNowTests(unittest.TestCase):
    """`starting_backpack_states()` -- the collection COO-DECISION 2342 named.

    LANE-DB will change gates 2/3/4 from `== INITIAL_BACKPACK` to
    `in starting_backpack_states()`.  These tests are what that lane is
    entitled to rely on, so each one states a property of the SET, not of
    this module's internals.
    """

    def test_the_set_is_one_bag_per_class_in_class_id_order(self):
        states = class_starting_gear.starting_backpack_states()
        self.assertIsInstance(states, tuple)
        self.assertEqual(len(class_catalog.CLASS_IDS), len(states))
        for class_id, state in zip(class_catalog.CLASS_IDS, states):
            with self.subTest(class_id=class_id):
                self.assertEqual(
                    class_starting_gear.starting_backpack_state(class_id),
                    state,
                )

    def test_the_committed_bag_is_a_member_by_identity_not_by_copy(self):
        # An old character's untouched bag must be admitted by the object the
        # tree already ships, which is the entire reason COO chose the set
        # over a per-class golden.  `assertIn` alone would pass on an equal
        # copy, so identity is checked on its own.
        states = class_starting_gear.starting_backpack_states()
        self.assertIn(INITIAL_BACKPACK, states)
        self.assertTrue(any(state is INITIAL_BACKPACK for state in states))

    def test_every_bag_differs_from_the_committed_one_in_one_field_only(self):
        """The property COO-DECISION 2342 asked to be pinned, stated exactly.

        Not "one field somewhere": the weapon row's `template_id` and
        nothing else.  Walked field by field over every row, so a change to
        quantity, slot, identity, mask or row count is a failure here even
        if the template ids still look right.
        """
        fields = (
            "identity", "template_id", "quantity", "slot",
            "raw_u8_38", "raw_u8_39", "detail_present",
        )
        seen_templates = []
        for class_id, state in zip(
            class_catalog.CLASS_IDS,
            class_starting_gear.starting_backpack_states(),
        ):
            with self.subTest(class_id=class_id):
                self.assertEqual(
                    INITIAL_BACKPACK.base_mask, state.base_mask,
                )
                self.assertEqual(
                    INITIAL_BACKPACK.base_identity, state.base_identity,
                )
                self.assertEqual(
                    INITIAL_BACKPACK.range_mask, state.range_mask,
                )
                self.assertEqual(
                    len(INITIAL_BACKPACK.items), len(state.items),
                )
                differing = []
                for row, (before, after) in enumerate(
                    zip(INITIAL_BACKPACK.items, state.items)
                ):
                    for field in fields:
                        if getattr(before, field) != getattr(after, field):
                            differing.append((row, field))
                if class_id == 1:
                    self.assertEqual([], differing)
                else:
                    self.assertEqual(
                        [(class_starting_gear.WEAPON_ROW_INDEX,
                          "template_id")],
                        differing,
                    )
                seen_templates.append(
                    state.items[
                        class_starting_gear.WEAPON_ROW_INDEX
                    ].template_id
                )
        # Five classes, five different weapons: if two entries collapsed onto
        # one template the set would still satisfy every check above while
        # quietly handing two classes the same sword.
        self.assertEqual(len(seen_templates), len(set(seen_templates)))

    def test_the_set_is_pure_and_rebuilt_every_call(self):
        first = class_starting_gear.starting_backpack_states()
        second = class_starting_gear.starting_backpack_states()
        self.assertEqual(first, second)
        # Equal, and no shared mutable cache the DB gates could be handed a
        # mutated view of: the tuple itself is a fresh object each call.
        self.assertIsNot(first, second)

    def test_the_set_still_has_no_production_importer(self):
        # COO-DECISION 2342 step 1: "no caller until DB wires it".  Measured,
        # not promised.
        self.assertEqual(0, class_starting_gear.count_production_importers())
        self.assertFalse(class_starting_gear.production_allowed)



if __name__ == "__main__":
    unittest.main()
