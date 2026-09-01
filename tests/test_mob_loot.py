"""LANE-B: the monster a player kills announces the name of its own loot.

The load-bearing tests in this file are the byte tests and the primitive pins.

``test_the_element_is_byte_equal_to_the_probe_lane`` is the one that matters
most: the ONLY reason to believe a client will do anything with this lane's
bytes is that an attended run watched the SAME bytes make the client draw the
item's NAME on the ground (a label, and no object -- GT-045 CLOSED-ANSWERED).  This lane re-derives that encoder instead of importing the probe
(a scenario-gated lane a flagless build cannot reach), so if the two ever stop
agreeing, the re-derivation is guessing and the test says so.

``test_the_three_primitives_agree_with_loot_roll`` pins the roll semantics
against the project's other roller value by value.  Two rollers with different
boundary behaviour would mean a drop rate means one thing in one file and
something else in another, which nobody would notice until a player did.

``test_no_refusal_name_is_unreachable`` is the rule ``mob_combat`` wrote for
itself when its floor moved: a refusal name that cannot happen is a lie to
whoever counts them.
"""

import ast
from dataclasses import replace
from pathlib import Path
import random
import struct
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA
from pirateforce_foundation import (
    field_drop_tables, field_mobs, ground_loot_hypothesis, loot_roll, mob_loot)
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_loot import (
    DROP_COORD_SPANS,
    DROP_ELEMENT_SIZE,
    DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE,
    DROP_ELEMENT_MODEL_TYPE_SPAN,
    DROP_ELEMENT_SIZE_WITH_MODEL_TYPE,
    DROP_ENVELOPE_PIN,
    DROP_ENVELOPE_SIZE,
    DROP_FRAME_COORD_SHIFT,
    DROP_FRAME_SIZE,
    DROP_FRAME_SIZE_WITH_MODEL_TYPE,
    DROP_KEY_BASE,
    DROP_KEY_LIMIT,
    DROP_MODEL_TYPE_FIELD_ENABLED,
    DROP_PC_SIZE,
    DROP_PC_SIZE_WITH_MODEL_TYPE,
    DROP_SCATTER_STEP,
    ELEMENT_MASK_POSITION_AND_DWORD,
    ELEMENT_MASK_WITH_MODEL_TYPE,
    ELEMENT_MODEL_TYPE_TAG,
    DROP_FRAME_HEADER_PIN,
    DROP_FRAME_HEADER_SIZE,
    GROUND_DROP_DOES_NOT_PERSIST,
    GROUND_LABEL_OBSERVED_LIFETIME_SECONDS,
    NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN,
    WIRE_TO_SCREEN_SECONDS,
    DropLedgerCell,
    MAX_DROPS_PER_KILL,
    MOB_LOOT_NONCLAIMS,
    MOB_LOOT_REFUSAL_REASONS,
    MONEY_ITEM_ID,
    PRESERVE_GROUND_HEARTBEAT_FRAME_SIZE,
    PRESERVE_GROUND_HEARTBEAT_PC_SIZE,
    RUNTIME_DERIVED_BIT_GROUND_LIST,
    DropItem,
    DropLedger,
    DropRoll,
    GroundDrop,
    MobLootContractError,
    MoneyDrop,
    as_wire_float,
    commit_drops,
    drop_collection_pc,
    drop_collection_pc_with_model_type,
    drop_element,
    drop_element_with_model_type,
    drop_frames,
    drop_frames_with_model_type,
    drop_pc,
    drop_pc_with_model_type,
    drops_console_line,
    loot_report,
    money_element,
    pin_document,
    place_drops,
    preserve_ground_heartbeat_frame,
    preserve_ground_heartbeat_pc,
    production_allowed,
    rate_succeeds,
    refresh_frames,
    roll_drops,
    take_drop,
    test_only,
    uniform_quantity,
    weighted_pick,
)


MODULE_PATH = ROOT / "src" / "pirateforce_foundation" / "mob_loot.py"
TABLE_PATH = ROOT / "src" / "pirateforce_foundation" / "field_drop_tables.py"
# The project's player identity in the sibling lane's tests, not a round
# number: an adversarial pass pointed out that 0x0101 never exercises the
# identity surface with anything a real session would carry.
KILLER = 0x750059


class _FixedRng(random.Random, mob_loot._FixedStream):
    """An rng whose draws are a script.  Records what was asked of it.

    A SUBCLASS of random.Random since the lane now enforces the type rather
    than duck-typing it: an adversarial pass showed that a duck-type check
    accepts the module-global ``random``, which silently makes the lane's
    determinism paragraph false.
    """

    def __init__(self, draws):
        super().__init__(0)
        self.draws = list(draws)
        self.calls = []

    def random(self):
        self.calls.append("random")
        if not self.draws:
            return 0.999999
        return self.draws.pop(0)

    def randrange(self, *args, **kwargs):        # pragma: no cover - a trap
        raise AssertionError("this lane must draw through random() only")

    def choice(self, *args, **kwargs):           # pragma: no cover - a trap
        raise AssertionError("this lane must draw through random() only")

    def choices(self, *args, **kwargs):          # pragma: no cover - a trap
        raise AssertionError("this lane must draw through random() only")


class MobLootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        # ROUND 8ftmbx: ~~load_roster()~~ (bg0001).  COO-DECISION
        # 2026-08-29T00:41+07:00 withdrew bg0001's nine set-number rows, and
        # what the town still ships is four practice dummies with
        # n_DROPS_NORMAL 0 -- nothing in Port Royal drops anything, which is
        # the correct answer for a town and a useless subject for a loot
        # fixture.  The subject moves to Bg0002, the scene the owner has
        # confirmed by sight and the only one this lane loads whose monsters
        # carry real drop sets.  Nothing about the roller changed; only which
        # real roster it is exercised on.
        cls.roster = load_roster(scene=field_mobs.BG0002_SCENE)
        cls.mob = cls.roster[0]
        # bg0001's roster is loaded to be ASSERTED ON, not as scenery: the
        # reason this fixture moved scenes is that the town drops nothing,
        # and that is a fact worth failing on rather than a comment.
        cls.bg0001_roster = load_roster()
        cls.source = MODULE_PATH.read_text(encoding="utf-8")

    # -- what kind of lane this is -----------------------------------------
    def test_port_royal_drops_nothing_which_is_why_this_lane_reads_bg0002(
            self):
        """The reason this fixture is not on bg0001, asserted rather than
        written in a comment.

        COO-DECISION 2026-08-29T00:41+07:00 withdrew the town's nine
        set-number rows; what it still ships is four n_ID 916 practice
        dummies whose n_DROPS_NORMAL, n_DROPS_EQUIPMENT and
        n_DROPS_SPECIALLY are all zero in the game's own tables.  A loot
        fixture on that roster would roll nothing forever and every test
        below would pass vacuously.  If the town ever ships a monster with a
        drop set again, this fails and the fixture should move back.
        """
        for mob in self.bg0001_roster:
            with self.subTest(placement=mob.placement_index):
                self.assertEqual(
                    (mob.drops_normal, mob.drops_equipment,
                     mob.drops_specially), (0, 0, 0))
        self.assertNotEqual(self.roster[0].scene, self.bg0001_roster[0].scene)
        # And the scene this lane DID move to has real drop sets, so the
        # tests below are exercising the roller rather than its refusals.
        self.assertTrue(
            any(mob.drops_normal for mob in self.roster),
            "the loot fixture's own scene has no drop set either")

    def test_the_lane_is_production_and_has_no_flag(self):
        """No flag machinery in the CODE.  Prose may name one; code may not.

        The first draft of this test read the raw source and failed on the
        docstring sentence that says this lane has no unlock object, which
        would have taught the lane to stop explaining itself.  So it walks the
        tree instead and skips docstrings.
        """
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        tree = ast.parse(self.source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        forbidden = ("scenario_id", "hypothesis_id", "unlock", "allowlist")
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                for word in forbidden:
                    self.assertNotIn(
                        word, node.value,
                        "a production lane may not carry %r in a value" % word)
            if isinstance(node, ast.Name):
                for word in forbidden:
                    self.assertNotIn(word, node.id)
            if isinstance(node, ast.Attribute):
                for word in forbidden:
                    self.assertNotIn(word, node.attr)

    def test_the_module_imports_no_probe_lane_and_no_roller(self):
        """BLIND IN ITS FIRST FORM, and an adversarial pass proved it.

        ``if isinstance(node, ast.ImportFrom) and node.module`` skips the whole
        branch for ``from . import X``, because a relative import of a sibling
        has ``module is None`` -- which is the exact form this module uses.  A
        probe lane was added to the production module at module scope and the
        entire suite stayed green.  The names of a relative import live in its
        ALIASES, so they are collected here whether or not there is a module.
        """
        imported = self._imported_names(self.source)
        self.assertIn(
            "field_drop_tables", imported,
            "the tripwire cannot see this module's own relative import")
        self.assertNotIn("loot_roll", imported)
        for name in imported:
            self.assertNotIn(
                "hypothesis", name,
                "a production lane may not import a scenario-gated probe")
        # NAME-MATCHING ALONE CANNOT HOLD THIS.  The second adversarial pass
        # reached both the probe lane and the roller with
        # `import_module("pirateforce_foundation." + "loot_" + "roll")` and
        # every name check in this file stayed green, because the name is not
        # in the source as a string at all.  So the rule is now structural: a
        # production lane in this project has NO business importing anything
        # dynamically, and the machinery for it may not appear here.
        for node in ast.walk(ast.parse(self.source)):
            if isinstance(node, ast.Call):
                func = node.func
                target = getattr(func, "attr", getattr(func, "id", ""))
                self.assertNotIn(
                    target, ("import_module", "__import__"),
                    "a production lane may not import dynamically; a name "
                    "check cannot see through string arithmetic")
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, "import_module")
        self.assertNotIn("importlib", imported)

    @staticmethod
    def _imported_names(source):
        names = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                    names.update(node.module.split("."))
                for alias in node.names:
                    names.add(alias.name)
                    if alias.asname:
                        names.add(alias.asname)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
                    names.update(alias.name.split("."))
                    if alias.asname:
                        names.add(alias.asname)
            elif isinstance(node, ast.Call):
                func = node.func
                target = getattr(func, "attr", getattr(func, "id", ""))
                if target in ("import_module", "__import__"):
                    for argument in node.args:
                        if isinstance(argument, ast.Constant):
                            names.add(str(argument.value))
                            names.update(str(argument.value).split("."))
        return names

    def test_the_import_tripwire_catches_the_form_the_module_uses(self):
        """The tripwire above, tested against the attack that defeated it."""
        for attack in (
            "from . import ground_loot_hypothesis\n",
            "from .loot_roll import rate_succeeds\n",
            "import pirateforce_foundation.loot_roll\n",
            "import importlib\n"
            "loot = importlib.import_module('pirateforce_foundation.loot_roll')\n",
        ):
            imported = self._imported_names(attack)
            self.assertTrue(
                any("loot_roll" in name or "hypothesis" in name
                    for name in imported),
                "the tripwire is blind to %r" % attack)

    def test_the_module_and_the_table_are_pure_ascii(self):
        for path in (MODULE_PATH, TABLE_PATH):
            path.read_text(encoding="ascii")

    # -- the three primitives ----------------------------------------------
    def test_the_three_primitives_agree_with_loot_roll(self):
        for rate in (0.0, 0.5, 1.0, 15.0, 30.0, 50.0, 99.9, 100.0):
            for draw in (0.0, 0.0049, 0.005, 0.1499, 0.15, 0.4999, 0.999999):
                self.assertEqual(
                    rate_succeeds(rate, draw),
                    loot_roll.rate_succeeds(rate, draw),
                    "rate %r draw %r" % (rate, draw))
        for low, high in ((1, 1), (1, 3), (2, 7), (0, 0)):
            for draw in (0.0, 0.24, 0.25, 0.33, 0.5, 0.99, 0.999999):
                self.assertEqual(
                    uniform_quantity(low, high, draw),
                    loot_roll.uniform_quantity(low, high, draw))
        for weights in ((100, 100, 100), (700, 299, 1), (0, 5, 0), (1,)):
            for draw in (0.0, 0.3333, 0.5, 0.6999, 0.7, 0.999999):
                self.assertEqual(
                    weighted_pick(weights, draw),
                    loot_roll.weighted_pick(weights, draw))

    def test_a_rate_of_zero_never_fires_and_a_rate_of_one_hundred_always_does(self):
        for draw in (0.0, 0.5, 0.999999):
            self.assertFalse(rate_succeeds(0.0, draw))
            self.assertTrue(rate_succeeds(100.0, draw))

    def test_the_entry_exactly_at_its_threshold_fails(self):
        self.assertFalse(rate_succeeds(0.5, 0.005))
        self.assertTrue(rate_succeeds(0.5, 0.00499))

    def test_a_zero_weight_entry_can_never_be_picked(self):
        picked = {weighted_pick((0, 5, 0), draw / 1000.0)
                  for draw in range(1000)}
        self.assertEqual(picked, {1})

    def test_the_weighted_walk_owns_the_interval_its_predecessor_ended(self):
        weights = (700, 299, 1)
        self.assertEqual(weighted_pick(weights, 0.6999), 0)
        self.assertEqual(weighted_pick(weights, 0.7), 1)
        self.assertEqual(weighted_pick(weights, 0.9989), 1)
        self.assertEqual(weighted_pick(weights, 0.999), 2)

    def test_a_draw_outside_the_unit_interval_is_refused_by_name(self):
        for bad in (-0.0001, 1.0, 2.0, float("nan")):
            with self.assertRaises(MobLootContractError) as caught:
                rate_succeeds(50.0, bad)
            self.assertEqual(caught.exception.args[0], "draw_out_of_unit_interval")

    def test_an_inverted_quantity_span_is_refused_by_name(self):
        with self.assertRaises(MobLootContractError) as caught:
            uniform_quantity(5, 2, 0.5)
        self.assertEqual(caught.exception.args[0], "quantity_range_inverted")

    # -- the roll -----------------------------------------------------------
    def test_the_same_seed_rolls_the_same_loot_in_any_process(self):
        for seed in (0, 1, 7, 4242):
            first = roll_drops(self.mob, random.Random(seed))
            second = roll_drops(self.mob, random.Random(seed))
            self.assertEqual(first, second)

    def test_every_draw_goes_through_random_and_nothing_else(self):
        rng = _FixedRng([0.0] * 40)
        roll_drops(self.mob, rng)
        self.assertEqual(set(rng.calls), {"random"})

    def test_a_roll_with_every_draw_at_zero_takes_every_slot_it_can(self):
        roll = roll_drops(self.mob, _FixedRng([0.0] * 40))
        normal = field_drop_tables.DROPS_NORMAL[self.mob.drops_normal]
        expected_items = [
            item for _index, item, rate, _low, _high in normal
            if rate > 0.0 and item != MONEY_ITEM_ID
        ]
        rolled = [item.item_id for item in roll.items
                  if item.source_table == "DROPS_NORMAL"]
        self.assertEqual(rolled, expected_items)
        expected_money = [
            index for index, item, rate, _low, _high in normal
            if rate > 0.0 and item == MONEY_ITEM_ID
        ]
        self.assertEqual(
            [row.source_index for row in roll.money
             if row.source_table == "DROPS_NORMAL"],
            expected_money)

    def test_a_roll_with_every_draw_just_under_one_takes_only_certain_slots(self):
        roll = roll_drops(self.mob, _FixedRng([0.999999] * 40))
        for item in roll.items:
            if item.source_table != "DROPS_NORMAL":
                continue
            rate = {
                index: rate for index, _item, rate, _low, _high
                in field_drop_tables.DROPS_NORMAL[self.mob.drops_normal]
            }[item.source_index]
            self.assertGreaterEqual(rate, 100.0)

    def test_the_quantity_draw_is_consumed_even_when_the_id_is_refused(self):
        """The draw stream must not depend on whether a row decodes."""
        original = field_drop_tables.DROPS_NORMAL[self.mob.drops_normal]
        broken = ((1, 999999999, 100.0, 1, 1),) + original[1:]
        field_drop_tables.DROPS_NORMAL[self.mob.drops_normal] = broken
        try:
            rng = _FixedRng([0.0] * 40)
            roll = roll_drops(self.mob, rng)
        finally:
            field_drop_tables.DROPS_NORMAL[self.mob.drops_normal] = original
        self.assertIn(("unknown_item_id", self.mob.drops_normal, 1), roll.refusals)
        clean = _FixedRng([0.0] * 40)
        roll_drops(self.mob, clean)
        self.assertEqual(len(rng.calls), len(clean.calls))

    def test_a_roll_refuses_an_untyped_mob_and_a_missing_rng(self):
        with self.assertRaises(MobLootContractError) as caught:
            roll_drops({"template_id": 35}, random.Random(1))
        self.assertEqual(caught.exception.args[0], "type_not_typed_record")
        with self.assertRaises(MobLootContractError) as caught:
            roll_drops(self.mob, object())
        self.assertEqual(caught.exception.args[0], "rng_has_no_random")

    def test_every_roster_mob_resolves_its_own_sets(self):
        for mob in self.roster:
            roll = roll_drops(mob, random.Random(mob.placement_index))
            self.assertEqual(roll.mob_identity, mob.actor_identity)
            self.assertEqual(roll.mob_template_id, mob.template_id)
            for item in roll.items:
                self.assertIn(item.item_id, field_drop_tables.ITEMS)

    def test_a_quantity_span_wider_than_one_stays_inside_its_span(self):
        wide = [
            (set_id, index, low, high)
            for set_id, slots in field_drop_tables.DROPS_NORMAL.items()
            for index, _item, _rate, low, high in slots
            if high > low
        ]
        self.assertTrue(wide, "the mined tables should carry a wide span")
        for _set_id, _index, low, high in wide:
            for draw in (0.0, 0.5, 0.999999):
                value = uniform_quantity(low, high, draw)
                self.assertGreaterEqual(value, low)
                self.assertLessEqual(value, high)

    def test_money_is_recorded_and_can_never_be_placed(self):
        roll = roll_drops(self.mob, _FixedRng([0.0] * 40))
        self.assertTrue(roll.money)
        for row in roll.money:
            self.assertEqual(row.tag, "INFERENCE_MONEY_SLOT")
            self.assertIn(
                row.amount_provenance,
                ("AMOUNT_FROM_QUANTITY_SPAN", "AMOUNT_HAS_NO_COLUMN"))
            if row.source_table == "DROPS_NORMAL":
                self.assertEqual(
                    row.amount_provenance, "AMOUNT_FROM_QUANTITY_SPAN")
            else:
                self.assertEqual(
                    row.amount_provenance, "AMOUNT_HAS_NO_COLUMN")
        with self.assertRaises(MobLootContractError) as caught:
            money_element(self.legacy, roll.money[0])
        self.assertEqual(caught.exception.args[0], "money_has_no_element")
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        drops = place_drops(self.mob, record, roll, DROP_KEY_BASE)
        self.assertEqual(len(drops), len(roll.items))

    # -- placing ------------------------------------------------------------
    def _one_kill(self, seed=3, minimum=2, attempts=500):
        """Roll until a kill drops at least ``minimum`` objects.

        Bounded rather than ``while True``: if a regenerated table ever made
        that impossible, an unbounded loop would HANG the suite instead of
        failing it, and a hung test says nothing to whoever reads the run.
        """
        rng = random.Random(seed)
        for _attempt in range(attempts):
            roll = roll_drops(self.mob, rng)
            if len(roll.items) >= minimum:
                break
        else:
            self.fail(
                "%s did not drop %d objects in %d rolls; the tables changed"
                % (self.mob.display_name, minimum, attempts))
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        return roll, record, place_drops(self.mob, record, roll, DROP_KEY_BASE)

    def test_drops_stand_at_the_placement_position_scattered_on_x(self):
        _roll, _record, drops = self._one_kill()
        for offset, drop in enumerate(drops):
            self.assertEqual(drop.drop_key, DROP_KEY_BASE + offset)
            self.assertEqual(
                drop.x, as_wire_float(self.mob.x + DROP_SCATTER_STEP * offset))
            self.assertEqual(drop.y, as_wire_float(self.mob.y))
            self.assertEqual(drop.z, as_wire_float(self.mob.z))
            self.assertEqual(drop.mob_identity, self.mob.actor_identity)
            self.assertEqual(drop.killer_identity, KILLER)

    def test_an_explicit_death_position_is_used_instead_of_the_placement(self):
        roll, record, _drops = self._one_kill()
        where = (1000.5, -20.25, 7.0)
        drops = place_drops(
            self.mob, record, roll, DROP_KEY_BASE, position=where)
        self.assertEqual(drops[0].x, as_wire_float(where[0]))
        self.assertEqual(drops[0].y, as_wire_float(where[1]))
        self.assertEqual(drops[0].z, as_wire_float(where[2]))

    def test_placing_refuses_a_record_that_names_another_monster(self):
        roll, _record, _drops = self._one_kill()
        other = DeathRecord(self.mob.actor_identity + 1, KILLER, self.mob.max_hp)
        with self.assertRaises(MobLootContractError) as caught:
            place_drops(self.mob, other, roll, DROP_KEY_BASE)
        self.assertEqual(caught.exception.args[0], "roll_names_another_monster")

    def test_placing_refuses_a_key_outside_the_lane_block(self):
        roll, record, _drops = self._one_kill()
        for bad in (1, DROP_KEY_BASE - 1, DROP_KEY_LIMIT):
            with self.assertRaises(MobLootContractError) as caught:
                place_drops(self.mob, record, roll, bad)
            self.assertEqual(
                caught.exception.args[0], "key_outside_the_lane_block")

    def test_placing_refuses_more_objects_than_the_lane_ceiling(self):
        item = DropItem(2400046, 1, "DROPS_NORMAL", self.mob.drops_normal, 1)
        roll = DropRoll(
            self.mob.template_id, self.mob.actor_identity,
            (item,) * (MAX_DROPS_PER_KILL + 1), (), 0, ())
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        with self.assertRaises(MobLootContractError) as caught:
            place_drops(self.mob, record, roll, DROP_KEY_BASE)
        self.assertEqual(
            caught.exception.args[0], "too_many_drops_for_one_kill")

    def test_a_ground_drop_refuses_a_coordinate_that_is_not_an_exact_f32(self):
        with self.assertRaises(MobLootContractError) as caught:
            GroundDrop(DROP_KEY_BASE, 2400046, 1, 0.1, 0.0, 0.0,
                       self.mob.actor_identity, KILLER)
        self.assertEqual(
            caught.exception.args[0], "position_off_the_f32_grid")

    def test_a_ground_drop_refuses_a_monster_looting_itself(self):
        with self.assertRaises(MobLootContractError) as caught:
            GroundDrop(DROP_KEY_BASE, 2400046, 1, 0.0, 0.0, 0.0,
                       self.mob.actor_identity, self.mob.actor_identity)
        self.assertEqual(
            caught.exception.args[0], "roll_names_another_monster")

    def test_a_ground_drop_refuses_an_item_that_is_not_in_the_mined_table(self):
        with self.assertRaises(MobLootContractError) as caught:
            GroundDrop(DROP_KEY_BASE, 999999999, 1, 0.0, 0.0, 0.0,
                       self.mob.actor_identity, KILLER)
        self.assertEqual(caught.exception.args[0], "unknown_item_id")

    # -- the ledger ---------------------------------------------------------
    def test_the_ledger_is_sorted_and_refuses_a_duplicate_key(self):
        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            DropLedger(tuple(reversed(drops)))
        self.assertEqual(caught.exception.args[0], "ledger_not_sorted")
        with self.assertRaises(MobLootContractError) as caught:
            DropLedger((drops[0], drops[0]))
        self.assertEqual(caught.exception.args[0], "duplicate_ledger_key")

    def test_committing_the_same_keys_twice_is_refused_rather_than_merged(self):
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        self.assertEqual(ledger.generation, 1)
        self.assertEqual(len(ledger.drops), len(drops))
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(ledger, drops, base_generation=ledger.generation, kill_token=1)
        self.assertEqual(caught.exception.args[0], "mob_already_looted")
        second = DeathRecord(
            self.roster[1].actor_identity, KILLER, self.roster[1].max_hp)
        colliding = place_drops(
            self.roster[1], second,
            DropRoll(self.roster[1].template_id, second.actor_identity,
                     (DropItem(2400046, 1, "DROPS_NORMAL",
                               self.roster[1].drops_normal, 1),), (), 0, ()),
            DROP_KEY_BASE)
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(ledger, colliding, base_generation=ledger.generation, kill_token=1)
        self.assertEqual(caught.exception.args[0], "ledger_stale")

    def test_a_kill_token_that_moves_backward_for_the_same_identity_is_refused_the_same_way_a_replay_is(
            self):
        """The exact boundary ``DropLedger.looted`` depends on, pinned.

        ROUND `h40iwu`, naming the risk
        `pf_bridge/notes_to_chief/20260901_0106_LANE-B-STATUS-bg0015-combat-
        ledger-gap-measured-*.md` recorded but left unfixed: ``looted`` has
        NO scene term, only ``actor_identity``.  It stays safe today only
        because ``kill_token`` counts up forever across every scene and
        the guard in :func:`commit_drops` is genuinely ``previous >=
        kill_token`` -- refuse anything NOT strictly increasing -- not
        merely ``previous == kill_token`` -- refuse only an exact replay.
        Every OTHER test in this file exercises kill_token 1 then 1 (an
        exact replay) or 1 then 2 (a genuine respawn); neither tells the
        two guards apart.  This one does, with a token that goes DOWN --
        exactly what a future per-scene-scoped or per-scene-reset token
        would hand this ledger the day two live scenes' identity ranges
        ever collide (see the field's own comment in ``mob_loot.py`` for
        the two facts that keep this safe today).  If this test ever goes
        red because the guard loosened to ``!=``, that is the day this
        module needs a scene term of its own.
        """
        identity = self.mob.actor_identity
        ledger = commit_drops(
            DropLedger(), (), base_generation=0, kill_token=5,
            mob_identity=identity)
        self.assertEqual(ledger.looted, ((identity, 5),))
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(
                ledger, (), base_generation=ledger.generation, kill_token=3,
                mob_identity=identity)
        self.assertEqual(caught.exception.args[0], "mob_already_looted")
        # The boundary is exactly ">=": one token HIGHER than what is
        # already recorded is accepted (a genuine respawn)...
        accepted = commit_drops(
            ledger, (), base_generation=ledger.generation, kill_token=6,
            mob_identity=identity)
        self.assertEqual(accepted.looted, ((identity, 6),))
        # ...and the SAME token as what is already recorded is refused,
        # the exact replay case this guard exists for.
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(
                accepted, (), base_generation=accepted.generation,
                kill_token=6, mob_identity=identity)
        self.assertEqual(caught.exception.args[0], "mob_already_looted")

    def test_the_next_key_follows_the_highest_key_ever_issued(self):
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        self.assertEqual(ledger.next_key, drops[-1].drop_key + 1)
        self.assertEqual(DropLedger().next_key, DROP_KEY_BASE)

    def test_a_key_is_never_reused_after_its_drop_leaves_the_ground(self):
        """The bug the first draft of this module shipped.

        Taking the NEWEST drop off the ledger used to lower the next key,
        because it was derived from the rows still on the ground.  The next
        kill would then hand that same key to a different item while the
        client may still be holding the old object under it -- two different
        items, one key, and nothing raised anywhere.
        """
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        after_pickup, taken = take_drop(ledger, drops[-1].drop_key)
        self.assertEqual(taken, drops[-1])
        self.assertEqual(after_pickup.next_key, ledger.next_key)
        emptied = after_pickup
        for drop in drops[:-1]:
            emptied, _taken = take_drop(emptied, drop.drop_key)
        self.assertEqual(emptied.drops, ())
        self.assertEqual(emptied.next_key, ledger.next_key)

    def test_a_ledger_refuses_a_key_it_never_issued(self):
        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            DropLedger(drops, 0, DROP_KEY_BASE)
        self.assertEqual(
            caught.exception.args[0], "key_outside_the_lane_block")

    def test_taking_a_drop_removes_exactly_that_row(self):
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        remaining, taken = take_drop(ledger, drops[0].drop_key)
        self.assertEqual(taken, drops[0])
        self.assertEqual(len(remaining.drops), len(drops) - 1)
        self.assertEqual(remaining.generation, ledger.generation + 1)
        with self.assertRaises(MobLootContractError) as caught:
            take_drop(remaining, drops[0].drop_key)
        self.assertEqual(caught.exception.args[0], "drop_not_in_ledger")

    # -- the bytes ----------------------------------------------------------
    def test_the_element_is_byte_equal_to_the_probe_lane(self):
        _roll, _record, drops = self._one_kill()
        for drop in drops:
            probe = ground_loot_hypothesis._element_wire(
                self.legacy,
                ground_loot_hypothesis.GroundLootElement(
                    drop.drop_key, drop.item_id, 0.0),
                drop.x, drop.y, drop.z)
            self.assertEqual(drop_element(self.legacy, drop), probe)

    def test_the_pc_is_byte_equal_to_the_probe_lanes_envelope(self):
        _roll, _record, drops = self._one_kill()
        drop = drops[0]
        expected = bytearray()
        expected += self.legacy.u16tag(
            0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_RES)
        expected += self.legacy.u32tag(0x14, 0)
        expected += self.legacy.u8tag(0x08, 4)
        expected += self.legacy.u8tag(0x0B, 0)
        expected += self.legacy.u8tag(
            0x0B, ground_loot_hypothesis.GROUND_LOOT_DERIVED_BIT)
        expected += self.legacy.u16tag(0x12, 1)
        expected += ground_loot_hypothesis._element_wire(
            self.legacy,
            ground_loot_hypothesis.GroundLootElement(
                drop.drop_key, drop.item_id, 0.0),
            drop.x, drop.y, drop.z)
        self.assertEqual(drop_pc(self.legacy, drop), bytes(expected))

    def test_every_wire_constant_equals_the_lane_that_measured_it(self):
        self.assertEqual(
            RUNTIME_DERIVED_BIT_GROUND_LIST,
            ground_loot_hypothesis.GROUND_LOOT_DERIVED_BIT)
        self.assertEqual(
            ELEMENT_MASK_POSITION_AND_DWORD,
            ground_loot_hypothesis.GROUND_LOOT_ELEMENT_MASK)
        self.assertEqual(
            DROP_PC_SIZE, ground_loot_hypothesis.GROUND_LOOT_PC_SIZE)
        self.assertEqual(
            DROP_FRAME_SIZE, ground_loot_hypothesis.GROUND_LOOT_FRAME_SIZE)
        self.assertEqual(
            DROP_COORD_SPANS, ground_loot_hypothesis.GROUND_LOOT_COORD_SPANS)
        self.assertEqual(
            DROP_FRAME_COORD_SHIFT,
            ground_loot_hypothesis.GROUND_LOOT_FRAME_COORD_SHIFT)

    def test_a_one_drop_kill_is_still_the_pinned_44_and_54_bytes(self):
        """~~one frame per drop~~ -- but a ONE-drop kill must not move.

        Struck and rewritten in round ``zxnwtd`` on ``RE-130``.  The old
        assertion (``len(frames) == len(drops)``) is now false by design and
        the shape it described is the defect RE-130 named.  What must NOT
        move is the single-drop case: those 44 pc bytes and 54 frame bytes
        are the ones GT-045 put in front of a real client, and they are the
        only bytes of this lane a client has ever accepted.
        """
        _roll, _record, drops = self._one_kill()
        frames = drop_frames(self.legacy, drops[:1])
        self.assertEqual(len(frames), 1)
        (pc, frame), = frames
        self.assertEqual(len(pc), DROP_PC_SIZE)
        self.assertEqual(len(frame), DROP_FRAME_SIZE)
        coordinates = b"".join(
            pc[start:end] for start, end in DROP_COORD_SPANS)
        self.assertEqual(
            coordinates, struct.pack("<fff", drops[0].x, drops[0].y,
                                     drops[0].z))

    def test_a_multi_drop_kill_is_one_generation_carrying_every_key(self):
        """RE-130's BUILD_IMPACT, asserted on composed bytes.

        Not on the count field alone: an accumulating emitter that declared
        the right count in front of a one-element payload would pass that,
        and this lane has been bitten by exactly that class of test before.
        So the PAYLOAD WIDTH and every element's presence are asserted too.
        """
        _roll, _record, drops = self._one_kill()
        self.assertGreaterEqual(
            len(drops), 2,
            "this test needs a multi-drop kill; _one_kill no longer gives "
            "one and the assertions below would be vacuous")
        frames = drop_frames(self.legacy, drops)
        self.assertEqual(
            len(frames), 1,
            "a kill's drops must travel as ONE generation (RE-130): a "
            "second nonempty generation erases the first one's keys")
        pc, frame = frames[0]
        self.assertEqual(
            struct.unpack("<H", pc[15:17])[0], len(drops),
            "the generation does not declare the number of drops it carries")
        self.assertEqual(
            len(pc), DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE * len(drops),
            "the payload is not exactly %d elements wide, so the declared "
            "count is a lie" % len(drops))
        elements = [drop_element(self.legacy, drop) for drop in drops]
        self.assertEqual(
            len(set(elements)), len(elements),
            "the drops composed to identical element bytes; the containment "
            "assertions below would pass for the wrong reason")
        self.assertEqual(pc[DROP_ENVELOPE_SIZE:], b"".join(elements))
        for element in elements:
            self.assertIn(element, frame)
        # And the keys the consumer will build its tree from are all there
        # and all different (RE-130 T3: wire tag 0x14 -> element +0x10).
        keys = [
            struct.unpack(
                "<I",
                pc[DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE + 1:
                   DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE + 5])[0]
            for index in range(len(drops))
        ]
        self.assertEqual(keys, [drop.drop_key for drop in drops])
        self.assertEqual(len(set(keys)), len(keys))

    def test_the_wide_frame_still_decompresses_back_to_the_pc(self):
        """The one check that does not trust either composer.

        Both the legacy framing layer and this lane's re-derivation build
        the frame going FORWARDS.  This runs the legacy DECOMPRESSOR over
        the composed frame and compares what comes out with the pc that
        went in, which is the only assertion here that would survive both
        encoders being wrong in the same way.
        """
        _roll, _record, drops = self._one_kill()
        for width in (1, 2, len(drops)):
            if width > len(drops):
                continue
            (pc, frame), = drop_frames(self.legacy, drops[:width])
            self.assertEqual(
                self.legacy.snappy_raw_decompress(frame[8:]), pc,
                "the %d-element frame does not decompress to its own pc"
                % width)

    def _wide_drops(self, count):
        """``count`` synthetic drops, scattered the way place_drops does.

        The rolled kills in this file top out at two objects, which is why
        pf-adversary D6 found the framing arithmetic above two elements had
        never executed.  These are built by hand so the widths that change
        the SNAPPY HEADER can be reached at all: the varint goes to two
        bytes at pc >= 128 (N >= 5) and the literal tag gains a length byte
        at pc >= 257 (N >= 9).
        """
        item = next(
            item_id for item_id, row in sorted(field_drop_tables.ITEMS.items())
            if str(row[2]).strip())
        return tuple(
            mob_loot.GroundDrop(
                DROP_KEY_BASE + index, item, 1,
                mob_loot.as_wire_float(1.0 + DROP_SCATTER_STEP * index),
                mob_loot.as_wire_float(2.0), mob_loot.as_wire_float(3.0),
                0x201F, 0x0101,
            )
            for index in range(count)
        )

    def test_the_wide_generations_that_change_the_snappy_header_compose(self):
        """Every width up to a full kill, checked against the decompressor.

        MAX_DROPS_PER_KILL is 16, so 16 is a REACHABLE generation and its
        header (a two-byte varint and an extended literal tag) had no test
        at all.  Each width is decompressed back with the legacy decoder --
        the one assertion here that does not trust either composer.
        """
        self.assertGreaterEqual(mob_loot.MAX_DROPS_PER_KILL, 16)
        for count in (1, 2, 4, 5, 8, 9, 16, mob_loot.MAX_DROPS_PER_KILL):
            drops = self._wide_drops(count)
            (pc, frame), = drop_frames(self.legacy, drops)
            self.assertEqual(
                len(pc), DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE * count)
            self.assertEqual(
                struct.unpack("<H", pc[15:17])[0], count)
            self.assertEqual(
                self.legacy.snappy_raw_decompress(frame[8:]), pc,
                "the %d-element frame does not decompress to its own pc"
                % count)
            self.assertEqual(
                struct.unpack("<I", frame[4:8])[0], len(frame) - 8)

    def test_the_ceiling_refusal_is_reachable_and_the_ceiling_is_ours(self):
        """``generation_too_wide_to_frame`` had no test until D5 said so.

        This module's rule is that an unreachable refusal is a lie to
        whoever counts them, and the precedent (round ``vvkff9``) is that
        such a token gets deleted.  It is kept because it IS reachable --
        here -- and because the shape above it is one this lane genuinely
        does not re-derive.  It is NOT reachable from a real kill:
        MAX_DROPS_PER_KILL is 16 and the ceiling is 2426.
        """
        ceiling = mob_loot.DROP_MAX_ELEMENTS_PER_FRAME
        self.assertGreater(ceiling, mob_loot.MAX_DROPS_PER_KILL)
        self.assertEqual(
            ceiling,
            (0x10000 - DROP_ENVELOPE_SIZE) // DROP_ELEMENT_SIZE,
            "the ceiling is no longer the single-literal-run arithmetic it "
            "claims to be")
        # And the widest ALLOWED generation still fits in one literal run,
        # which is the whole reason the ceiling has that value.
        widest = self._wide_drops(ceiling)
        pc = mob_loot.drop_collection_pc(self.legacy, widest)
        self.assertLess(len(pc), 0x10000)
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.drop_collection_pc(self.legacy, self._wide_drops(
                ceiling + 1))
        self.assertEqual(
            caught.exception.args[0], "generation_too_wide_to_frame")

    # -- mask 0x04, n_DROPMODEL_TYPE (ka1-B, [DERIVED, not yet client-------
    # -- measured]) ----------------------------------------------------------
    def test_the_model_type_mask_and_tag_constants(self):
        """The one candidate NONCLAIM 16 did not already rule out.

        RE-067 pinned mask 0x08 and mask 0x20 as the client's text-label
        COLOR property; this asserts the new bit is neither of those and is
        exactly the proven mask plus the one untouched bit.
        """
        self.assertEqual(mob_loot.ELEMENT_MODEL_TYPE_TAG, 0x0F)
        self.assertEqual(mob_loot.ELEMENT_MASK_MODEL_TYPE_BIT, 0x04)
        self.assertEqual(ELEMENT_MASK_WITH_MODEL_TYPE, 0x16)
        self.assertEqual(
            ELEMENT_MASK_WITH_MODEL_TYPE,
            ELEMENT_MASK_POSITION_AND_DWORD | mob_loot.ELEMENT_MASK_MODEL_TYPE_BIT)
        # NONCLAIM 16's pinned color bits, untouched by this round.
        for reserved_bit in (0x08, 0x20):
            self.assertEqual(
                ELEMENT_MASK_WITH_MODEL_TYPE & reserved_bit, 0,
                "mask 0x%02X is RE-067's text-label-color property "
                "(NONCLAIM 16); this lane must not set it" % reserved_bit)

    def test_the_wide_element_size_and_pc_size_are_derived_arithmetic(self):
        self.assertEqual(
            DROP_ELEMENT_SIZE_WITH_MODEL_TYPE,
            DROP_ELEMENT_SIZE + 3,
            "the model-type field is one tag byte plus a u16 value")
        self.assertEqual(
            DROP_PC_SIZE_WITH_MODEL_TYPE,
            DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE_WITH_MODEL_TYPE)
        self.assertEqual(
            DROP_FRAME_SIZE_WITH_MODEL_TYPE,
            DROP_PC_SIZE_WITH_MODEL_TYPE + DROP_FRAME_HEADER_SIZE)
        self.assertEqual(
            DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE,
            tuple((start + 3, end + 3) for start, end in
                  mob_loot.DROP_ELEMENT_COORD_SPANS))

    def test_the_wide_element_is_byte_exact_for_a_known_weapon_item(self):
        """[DERIVED, not yet client-measured].

        There is no probe lane for mask 0x16 to cross-pin against (the task
        that added this field found none in the repo), so this test derives
        the expected bytes independently -- tag by tag, through the same
        legacy primitives the composer uses -- rather than trusting the
        composer's own arithmetic.  2200201 is field_drop_tables' own
        lowest item id, a weapon (Dagger) with drop_model_type 1.
        """
        item_id = 2200201
        self.assertEqual(field_drop_tables.ITEMS[item_id][3], 1)
        drop = GroundDrop(
            DROP_KEY_BASE, item_id, 1,
            as_wire_float(1.0), as_wire_float(2.0), as_wire_float(3.0),
            0x201F, KILLER,
        )
        expected = bytearray()
        expected += self.legacy.u32tag(mob_loot.ELEMENT_KEY_TAG, drop.drop_key)
        expected += self.legacy.u8tag(
            mob_loot.ELEMENT_MASK_TAG, ELEMENT_MASK_WITH_MODEL_TYPE)
        expected += self.legacy.u32tag(mob_loot.ELEMENT_PAYLOAD_TAG, item_id)
        expected += self.legacy.u16tag(ELEMENT_MODEL_TYPE_TAG, 1)
        expected += self.legacy.f32tag(drop.x)
        expected += self.legacy.f32tag(drop.y)
        expected += self.legacy.f32tag(drop.z)
        expected = bytes(expected)
        self.assertEqual(len(expected), DROP_ELEMENT_SIZE_WITH_MODEL_TYPE)
        self.assertEqual(
            drop_element_with_model_type(self.legacy, drop), expected)

    def test_the_wide_element_model_type_matches_field_drop_tables_column(
            self):
        """The value is PULLED, never guessed, across every item category."""
        for item_id in sorted(field_drop_tables.ITEMS):
            row = field_drop_tables.ITEMS[item_id]
            if not str(row[2]).strip():
                continue   # a nameless row is refused before it gets here
            drop = GroundDrop(
                DROP_KEY_BASE, item_id, 1,
                as_wire_float(1.0), as_wire_float(2.0), as_wire_float(3.0),
                0x201F, KILLER,
            )
            element = drop_element_with_model_type(self.legacy, drop)
            start, end = DROP_ELEMENT_MODEL_TYPE_SPAN
            composed = struct.unpack("<H", element[start:end])[0]
            self.assertEqual(
                composed, row[3],
                "item %d composed model type %d, table says %d"
                % (item_id, composed, row[3]))

    def test_the_wide_pc_is_byte_exact_for_a_one_drop_generation(self):
        """[DERIVED, not yet client-measured].  Same derivation style as the
        element test above: built tag by tag, not trusted from the composer.
        """
        item_id = 2200201
        drop = GroundDrop(
            DROP_KEY_BASE, item_id, 1,
            as_wire_float(1.0), as_wire_float(2.0), as_wire_float(3.0),
            0x201F, KILLER,
        )
        expected = bytearray()
        expected += self.legacy.u16tag(
            0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_RES)
        expected += self.legacy.u32tag(0x14, 0)
        expected += self.legacy.u8tag(0x08, 4)
        expected += self.legacy.u8tag(0x0B, 0)
        expected += self.legacy.u8tag(0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)
        expected += self.legacy.u16tag(0x12, 1)
        expected += self.legacy.u32tag(mob_loot.ELEMENT_KEY_TAG, drop.drop_key)
        expected += self.legacy.u8tag(
            mob_loot.ELEMENT_MASK_TAG, ELEMENT_MASK_WITH_MODEL_TYPE)
        expected += self.legacy.u32tag(mob_loot.ELEMENT_PAYLOAD_TAG, item_id)
        expected += self.legacy.u16tag(ELEMENT_MODEL_TYPE_TAG, 1)
        expected += self.legacy.f32tag(drop.x)
        expected += self.legacy.f32tag(drop.y)
        expected += self.legacy.f32tag(drop.z)
        expected = bytes(expected)
        self.assertEqual(len(expected), DROP_PC_SIZE_WITH_MODEL_TYPE)
        pc = drop_pc_with_model_type(self.legacy, drop)
        self.assertEqual(pc, expected)
        # The envelope is IDENTICAL to the narrow, proven shape -- only the
        # element widened -- so it must still equal DROP_ENVELOPE_PIN.
        self.assertEqual(pc[:DROP_ENVELOPE_SIZE], DROP_ENVELOPE_PIN)

    def test_the_wide_one_drop_frame_is_47_and_57_bytes_and_decompresses(
            self):
        item_id = 2200201
        drop = GroundDrop(
            DROP_KEY_BASE, item_id, 1,
            as_wire_float(1.0), as_wire_float(2.0), as_wire_float(3.0),
            0x201F, KILLER,
        )
        (pc, frame), = drop_frames_with_model_type(self.legacy, (drop,))
        self.assertEqual(len(pc), DROP_PC_SIZE_WITH_MODEL_TYPE)
        self.assertEqual(len(frame), DROP_FRAME_SIZE_WITH_MODEL_TYPE)
        self.assertEqual(
            self.legacy.snappy_raw_decompress(frame[8:]), pc,
            "the wide one-element frame does not decompress to its own pc")

    def test_the_wide_multi_drop_generation_carries_every_element_and_model(
            self):
        """The mask-0x16 sibling of the narrow multi-drop containment test."""
        items = (2200201, 2204001, 2205001, 2400047)   # 1, 2, 3, 10
        drops = tuple(
            GroundDrop(
                DROP_KEY_BASE + index, item_id, 1,
                as_wire_float(1.0 + DROP_SCATTER_STEP * index),
                as_wire_float(2.0), as_wire_float(3.0), 0x201F, KILLER,
            )
            for index, item_id in enumerate(items)
        )
        (pc, frame), = drop_frames_with_model_type(self.legacy, drops)
        self.assertEqual(
            len(pc),
            DROP_ENVELOPE_SIZE + DROP_ELEMENT_SIZE_WITH_MODEL_TYPE * len(drops))
        self.assertEqual(
            struct.unpack("<H", pc[15:17])[0], len(drops))
        self.assertEqual(
            self.legacy.snappy_raw_decompress(frame[8:]), pc,
            "the wide multi-element frame does not decompress to its own pc")
        for index, (item_id, drop) in enumerate(zip(items, drops)):
            base = DROP_ENVELOPE_SIZE + index * DROP_ELEMENT_SIZE_WITH_MODEL_TYPE
            start, end = DROP_ELEMENT_MODEL_TYPE_SPAN
            model_type = struct.unpack(
                "<H", pc[base + start:base + end])[0]
            self.assertEqual(model_type, field_drop_tables.ITEMS[item_id][3])
            coordinates = b"".join(
                pc[base + s:base + e]
                for s, e in DROP_ELEMENT_COORD_SPANS_WITH_MODEL_TYPE
            )
            self.assertEqual(
                coordinates, struct.pack("<fff", drop.x, drop.y, drop.z))

    def test_the_wide_composer_reuses_the_encoder_disagreement_refusal(self):
        """Same refusal name as the narrow encoder, same reachability rule."""
        class _BrokenLegacy:
            GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                if tag == ELEMENT_MODEL_TYPE_TAG:
                    return self._real.u16tag(tag, value ^ 1)
                return self._real.u16tag(tag, value)

        drop = GroundDrop(
            DROP_KEY_BASE, 2200201, 1, as_wire_float(1.0), as_wire_float(2.0),
            as_wire_float(3.0), 0x201F, KILLER,
        )
        with self.assertRaises(MobLootContractError) as caught:
            drop_element_with_model_type(_BrokenLegacy(self.legacy), drop)
        self.assertEqual(
            caught.exception.args[0], "element_encoder_disagrees")

    def test_the_narrow_path_is_unaffected_by_the_new_flag(self):
        """GT-045's proven shape does not move, regardless of the flag.

        drop_frames -- what runtime.py actually calls per MOB_LOOT_WIRING --
        must keep composing exactly 44/54 bytes for a one-drop kill even
        though DROP_MODEL_TYPE_FIELD_ENABLED defaults to True: this module's
        own rule says the mask-0x12 path may not be weakened, and the flag
        exists to gate a SIBLING function, not this one.
        """
        self.assertTrue(
            DROP_MODEL_TYPE_FIELD_ENABLED,
            "this round's own default is True; if that changed, the "
            "assertions below about drop_frames still must not")
        drop = GroundDrop(
            DROP_KEY_BASE, 2200201, 1, as_wire_float(1.0), as_wire_float(2.0),
            as_wire_float(3.0), 0x201F, KILLER,
        )
        (pc, frame), = drop_frames(self.legacy, (drop,))
        self.assertEqual(len(pc), DROP_PC_SIZE)
        self.assertEqual(len(frame), DROP_FRAME_SIZE)
        self.assertEqual(pc[:DROP_ENVELOPE_SIZE], DROP_ENVELOPE_PIN)
        self.assertEqual(pc[DROP_ENVELOPE_SIZE + 6], ELEMENT_MASK_POSITION_AND_DWORD)

    def test_the_flag_is_a_real_rollback_lever_not_only_a_comment(self):
        """DROP_MODEL_TYPE_FIELD_ENABLED = False must actually do something.

        drop_frames_with_model_type reads the flag itself: flipped off, it
        must fall back to exactly drop_frames's own proven bytes, so "leave
        this False" (the docstring's stated rollback) is true of the code,
        not only of the comment describing it.
        """
        drop = GroundDrop(
            DROP_KEY_BASE, 2200201, 1, as_wire_float(1.0), as_wire_float(2.0),
            as_wire_float(3.0), 0x201F, KILLER,
        )
        narrow = drop_frames(self.legacy, (drop,))
        mob_loot.DROP_MODEL_TYPE_FIELD_ENABLED = False
        try:
            fell_back = drop_frames_with_model_type(self.legacy, (drop,))
        finally:
            mob_loot.DROP_MODEL_TYPE_FIELD_ENABLED = True
        self.assertEqual(fell_back, narrow)
        # And with the flag at its shipped default, the two must differ --
        # otherwise this test would pass for the wrong reason.
        wide = drop_frames_with_model_type(self.legacy, (drop,))
        self.assertNotEqual(wide, narrow)

    def test_the_declared_count_is_cross_checked_against_the_payload(self):
        """A legacy shim that lies in the count record must not ship.

        Without this the cross-check is dead code: nothing else in the
        suite makes ``u16tag`` disagree with the number of elements.
        """
        class _LyingCount:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                if tag == mob_loot.ELEMENT_LIST_COUNT_TAG:
                    return self._real.u16tag(tag, value + 1)
                return self._real.u16tag(tag, value)

        drops = self._wide_drops(3)
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.drop_collection_pc(_LyingCount(self.legacy), drops)
        self.assertEqual(caught.exception.args[0], "composed_bytes_off_pin")

    def test_the_element_width_is_derived_from_the_pinned_pc_not_typed(self):
        """The comment on DROP_ELEMENT_SIZE says derived; this checks it."""
        self.assertEqual(
            DROP_ELEMENT_SIZE, DROP_PC_SIZE - DROP_ENVELOPE_SIZE)
        self.assertEqual(
            mob_loot.DROP_ELEMENT_COORD_SPANS,
            tuple((start - DROP_ENVELOPE_SIZE, end - DROP_ENVELOPE_SIZE)
                  for start, end in DROP_COORD_SPANS))
        self.assertEqual(
            mob_loot.DROP_ENVELOPE_CONSTANT_PIN,
            DROP_ENVELOPE_PIN[:mob_loot.DROP_ENVELOPE_CONSTANT_SIZE])

    def test_the_one_drop_emission_really_goes_through_drop_pc(self):
        """Three shipped artifacts say so; pf-adversary D2 said it was false.

        It is true now because the code routes the one-drop case through
        ``drop_pc``.  A shim that breaks only ``drop_pc``'s own pin must
        therefore stop a real one-drop emission.
        """
        calls = []
        real = mob_loot.drop_pc

        def _counting(legacy, drop):
            calls.append(drop.drop_key)
            return real(legacy, drop)

        mob_loot.drop_pc = _counting
        try:
            drop_frames(self.legacy, self._wide_drops(1))
            self.assertEqual(len(calls), 1)
            calls.clear()
            drop_frames(self.legacy, self._wide_drops(3))
            self.assertEqual(
                calls, [],
                "the wide path must not go through the one-drop pin")
        finally:
            mob_loot.drop_pc = real

    def test_the_console_line_reports_the_shape_that_is_actually_composed(
            self):
        """GT-132's build check reads these two numbers off the console.

        They are useless if they are the module's arithmetic and not the
        emitter's, so both are compared against a REALLY COMPOSED frame.
        """
        _roll, _record, drops = self._one_kill()
        for count in (1, 2, len(drops), 5):
            rows = self._wide_drops(count)
            line = mob_loot.drops_console_line(self.mob, rows)
            (pc, _frame), = drop_frames(self.legacy, rows)
            self.assertIn("generations=1 ", line)
            self.assertIn("pc_bytes=%d " % len(pc), line)
            self.assertIn("drops=%d " % count, line)
        empty = mob_loot.drops_console_line(self.mob, ())
        self.assertIn("generations=0 ", empty)
        self.assertEqual(drop_frames(self.legacy, ()), ())

    def test_the_generation_refuses_a_repeated_key(self):
        """Two elements with one key is a silent replacement, not a drop."""
        _roll, _record, drops = self._one_kill()
        twinned = (drops[0], drops[0])
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.drop_collection_pc(self.legacy, twinned)
        self.assertEqual(
            caught.exception.args[0], "duplicate_key_in_generation")

    def test_the_generation_refuses_to_be_empty(self):
        """count=0 is a no-op in this consumer, not a clear (RE-130 T3)."""
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.drop_collection_pc(self.legacy, ())
        self.assertEqual(caught.exception.args[0], "generation_is_empty")
        self.assertEqual(drop_frames(self.legacy, ()), ())

    def test_the_frame_re_derivation_catches_a_drifted_compressor(self):
        """``frame_encoder_disagrees`` is reachable, and this is how.

        The magic and the length field are checked against the pins BEFORE
        the re-derivation, so a shim has to keep both and still get the
        body wrong to reach this refusal -- which is exactly what a
        compressor swap looks like.
        """
        class _DriftedCompressor:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def frame_pc(self, pc):
                # A legal-looking varint that is two bytes where one would
                # do.  Magic intact, length field honest, body off-format.
                body = (bytes([(len(pc) & 0x7F) | 0x80, len(pc) >> 7])
                        + bytes([(len(pc) - 1) << 2 & 0xFF]) + pc)
                return struct.pack(
                    "<II", self._real.MAGIC, len(body)) + body

        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            drop_frames(_DriftedCompressor(self.legacy), drops)
        self.assertEqual(
            caught.exception.args[0], "frame_encoder_disagrees")

    def test_the_composer_refuses_when_the_two_derivations_disagree(self):
        class _BrokenLegacy:
            GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u32tag(self, tag, value):
                return self._real.u32tag(tag, value ^ 1)

        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            drop_element(_BrokenLegacy(self.legacy), drops[0])
        self.assertEqual(
            caught.exception.args[0], "element_encoder_disagrees")

    def test_the_composer_refuses_a_pc_that_is_not_the_pinned_size(self):
        class _PaddingLegacy:
            GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                return self._real.u16tag(tag, value) + b"\x00"

        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            drop_pc(_PaddingLegacy(self.legacy), drops[0])
        self.assertEqual(caught.exception.args[0], "composed_bytes_off_pin")

    def test_refreshing_re_emits_the_live_ledger_in_key_order(self):
        """ROUND KA1B-DROPMODEL FOLLOW-UP, 2026-09-01: this pin used to
        compare against ``drop_frames`` (the narrow mask-0x12 shape).
        ``refresh_frames`` now calls ``drop_frames_with_model_type`` (see
        NONCLAIM 23 and the function's own docstring) -- a deliberate,
        understood behaviour change to THIS function, not to ``drop_frames``
        itself, which stays pinned to the narrow shape byte-for-byte
        elsewhere in this file and is never touched by this edit."""
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        refreshed = refresh_frames(self.legacy, ledger)
        self.assertEqual(
            refreshed, drop_frames_with_model_type(self.legacy, ledger.drops))
        self.assertNotEqual(refreshed, drop_frames(self.legacy, ledger.drops))
        with self.assertRaises(MobLootContractError) as caught:
            refresh_frames(self.legacy, drops)
        self.assertEqual(caught.exception.args[0], "type_not_typed_record")

    # -- the things an adversarial pass proved were only prose -------------
    def test_the_module_global_random_is_refused_by_name(self):
        """A duck-type check accepted it, and no test in this file would care.

        The lane's determinism paragraph says the rng is injected.  Passing
        the module-global ``random`` satisfies "has a callable .random" and
        silently makes that paragraph false for every consumer in the process.
        """
        for bad in (random, object(), type("X", (), {"random": lambda s: 0.5})()):
            with self.assertRaises(MobLootContractError) as caught:
                roll_drops(self.mob, bad)
            self.assertEqual(caught.exception.args[0], "rng_has_no_random")
        self.assertIsInstance(roll_drops(self.mob, random.Random(1)), DropRoll)

    def test_an_item_with_no_name_is_refused_everywhere_it_can_enter(self):
        """The name is the only thing this lane was measured to draw."""
        item_id = 2400046
        original = field_drop_tables.ITEMS[item_id]
        field_drop_tables.ITEMS[item_id] = original[:2] + ("",) + original[3:]
        try:
            with self.assertRaises(MobLootContractError) as caught:
                DropItem(item_id, 1, "DROPS_NORMAL", self.mob.drops_normal, 1)
            self.assertEqual(caught.exception.args[0], "item_has_no_name")
            with self.assertRaises(MobLootContractError) as caught:
                GroundDrop(DROP_KEY_BASE, item_id, 1, 0.0, 0.0, 0.0,
                           self.mob.actor_identity, KILLER)
            self.assertEqual(caught.exception.args[0], "item_has_no_name")
            roll = roll_drops(self.mob, _FixedRng([0.0] * 40))
            self.assertIn(
                "item_has_no_name", [row[0] for row in roll.refusals])
            self.assertNotIn(item_id, [row.item_id for row in roll.items])
        finally:
            field_drop_tables.ITEMS[item_id] = original

    def test_a_rate_outside_zero_to_one_hundred_is_refused_by_name(self):
        set_id = self.mob.drops_normal
        original = field_drop_tables.DROPS_NORMAL[set_id]
        field_drop_tables.DROPS_NORMAL[set_id] = (
            (1, 2400046, 300.0, 1, 1),) + original[1:]
        try:
            roll = roll_drops(self.mob, _FixedRng([0.0] * 40))
        finally:
            field_drop_tables.DROPS_NORMAL[set_id] = original
        self.assertIn("rate_out_of_range", [row[0] for row in roll.refusals])
        self.assertNotIn(2400046, [
            item.item_id for item in roll.items
            if item.source_index == 1])

    def test_a_stale_writer_cannot_win_the_race_by_writing(self):
        """The failure the first draft's "compare-and-swap" did not stop.

        A pruner takes a drop off generation 1 and stores generation 2.  A
        kill that read generation 1 then commits its non-colliding key, its
        merge puts the TAKEN drop back on the ground, and both results report
        generation 2 with nothing raised.  Executed here as the refusal.
        """
        _roll, _record, drops = self._one_kill()
        stored = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        pruned, taken = take_drop(stored, drops[0].drop_key)
        second = self.roster[1]
        record = DeathRecord(second.actor_identity, KILLER, second.max_hp)
        roll = DropRoll(
            second.template_id, second.actor_identity,
            (DropItem(2400046, 1, "DROPS_NORMAL", second.drops_normal, 1),),
            (), 0, ())
        fresh = place_drops(second, record, roll, pruned.next_key)
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(pruned, fresh, base_generation=stored.generation, kill_token=2)
        self.assertEqual(
            caught.exception.args[0], "ledger_generation_moved")
        accepted = commit_drops(
            pruned, fresh, base_generation=pruned.generation, kill_token=2)
        self.assertNotIn(
            taken.drop_key, [row.drop_key for row in accepted.drops])

    def test_a_commit_without_a_base_generation_is_refused(self):
        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(DropLedger(), drops, kill_token=1)
        self.assertEqual(
            caught.exception.args[0], "ledger_generation_moved")

    def test_one_corpse_cannot_be_looted_twice(self):
        roll, record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        emptied = ledger
        for drop in drops:
            emptied, _taken = take_drop(emptied, drop.drop_key)
        again = place_drops(self.mob, record, roll, emptied.next_key)
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(emptied, again, base_generation=emptied.generation, kill_token=1)
        self.assertEqual(caught.exception.args[0], "mob_already_looted")

    def test_the_envelope_is_pinned_at_run_time_not_only_in_a_test(self):
        """A test does not run inside the server; this refusal does.

        The element was dual-derived from the start, but the twenty bytes in
        front of it came from the legacy module on trust: a shim with a moved
        message id shipped 44 bytes no client has accepted, and the only red
        would have been a test-time pin.
        """
        class _DriftedLegacy:
            GSCN_RUNTIME_PROTOCOL_RES = 0x6E9E   # one bit off

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            drop_pc(_DriftedLegacy(self.legacy), drops[0])
        self.assertEqual(caught.exception.args[0], "composed_bytes_off_pin")
        pc = drop_pc(self.legacy, drops[0])
        self.assertEqual(pc[:DROP_ENVELOPE_SIZE], DROP_ENVELOPE_PIN)

    def test_the_refresh_cadence_is_refused_for_production_by_the_coo(self):
        """A ruling from outside this lane, pinned where the lane can see it.

        COO-DECISION 2026-08-26 07:45 +07:00 (pf_bridge/notes_to_chief/
        20260826_0745_COO-DECISION-M5-stays-whole-M5a-ships-now.md, section
        1a) REFUSED this lane's assumption 4: DROP_REFRESH_MS may not be wired
        into a production path, because 12.5 frames a second per row is the
        price of a mechanism nobody has measured.  The shipped behaviour is
        one announcement per drop.

        Pinned as a test rather than a paragraph so that a future round which
        quietly puts refresh_frames on a timer has to delete an assertion with
        the ruling's date on it.
        """
        self.assertTrue(mob_loot.DROP_REFRESH_MS_IS_EXPERIMENT_ONLY)
        self.assertTrue(
            pin_document(self.legacy)["lane_constants"][
                "refresh_ms_is_experiment_only"])
        wiring = mob_loot.MOB_LOOT_WIRING
        self.assertIn("ONE ANNOUNCEMENT PER DROP", wiring)
        self.assertIn("EXPERIMENT TOOLS", wiring)
        self.assertNotIn(
            "if you want to experiment with holding a label", wiring,
            "the wiring line still offers the cadence the COO refused")

    def test_the_scatter_and_the_label_limits_are_written_as_nonclaims(self):
        text = " ".join(MOB_LOOT_NONCLAIMS)
        for owed in (
            "SCATTER IS OURS",          # 30 units multiplied by the row index
            "ONE LABEL WAS SEEN",       # two elements, one label, unresolved
            "NOT A COLOUR WE CHOSE",    # RE-067 divergence, default property
            "SCENE-LOAD ONE-SHOT",      # every byte of evidence was one
            "CENSUS INTERACTION",       # the 3 s re-apply
            "HALF THAT DOES NOT EXIST", # the ledger's own justification
        ):
            self.assertIn(owed, text)

    # -- the paperwork ------------------------------------------------------
    def test_the_pin_document_says_what_the_lane_is_and_is_not(self):
        document = pin_document(self.legacy)
        self.assertTrue(document["production_allowed"])
        self.assertFalse(document["test_only"])
        self.assertIsNone(document["scenario"])
        self.assertFalse(document["measured"]["ground_drop_persists"])
        self.assertEqual(
            document["refusals"], list(MOB_LOOT_REFUSAL_REASONS))
        self.assertEqual(document["nonclaims"], list(MOB_LOOT_NONCLAIMS))
        self.assertEqual(
            document["wire"]["element_mask"], ELEMENT_MASK_POSITION_AND_DWORD)
        self.assertEqual(document["wire"]["generations_per_kill"], 1)
        self.assertEqual(document["wire"]["element_size"], DROP_ELEMENT_SIZE)
        # The shipped pin has to describe the WIDE shape too, composed
        # through the real path -- a document that only ever reports the
        # 44-byte case would still look right after a regression back to
        # one-frame-per-drop.
        self.assertEqual(
            document["wire"]["two_element_pc_size"],
            DROP_ENVELOPE_SIZE + 2 * DROP_ELEMENT_SIZE)
        self.assertGreater(
            document["wire"]["two_element_frame_size"],
            document["wire"]["sample_frame_size"])
        self.assertNotIn("elements_per_frame", document["wire"])

    def test_the_shipped_pin_file_is_what_the_code_computes(self):
        import json

        path = ROOT / "scenarios/combat_loot_001.json"
        shipped = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(shipped, pin_document(self.legacy))
        self.assertEqual(
            path.read_text(encoding="ascii"),
            json.dumps(
                pin_document(self.legacy), indent=2, ensure_ascii=True,
                sort_keys=True) + "\n")

    def test_the_cell_is_the_thing_that_makes_a_race_lose(self):
        """The answer to the question both adversarial passes asked.

        A ledger is a frozen value, so ``base_generation`` alone could always
        be satisfied from the same object the caller was holding - the two
        passes each executed a scenario where a pruner and a kill both stored
        generation 2 and a taken drop came back.  The cell owns the value and
        does read-build-fold inside one lock, so a caller cannot supply a
        stale generation or an already-issued key at all.
        """
        cell = DropLedgerCell()
        record = DeathRecord(
            self.mob.actor_identity, KILLER, self.mob.max_hp)
        rng = random.Random(3)
        first = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, rng), kill_token=1)
        self.assertEqual(cell.ledger.generation, 1)
        with self.assertRaises(MobLootContractError) as caught:
            cell.loot_a_kill(
                self.mob, record, roll_drops(self.mob, rng), kill_token=1)
        self.assertEqual(caught.exception.args[0], "mob_already_looted")
        self.assertEqual(
            cell.ledger.generation, 1, "a refusal must not move the cell")
        respawned = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, rng), kill_token=2)
        keys = [row.drop_key for row in first] + [
            row.drop_key for row in respawned]
        self.assertEqual(len(set(keys)), len(keys))
        for row in list(cell.ledger.drops):
            cell.take(row.drop_key)
        after = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, rng), kill_token=3)
        for row in after:
            self.assertNotIn(row.drop_key, keys)

    def test_pruning_the_previous_kill_leaves_the_newest_kill_pickable(self):
        """chief's ni2wh2 control, with this round's primitive in the loop.

        Their measurement, on the real cell and the real dispatch: prune the
        way ``runtime.py`` does today -- every key of the kill just sent, in
        the same dispatch -- and a pickup is refused ``drop_already_taken``
        100% of the time; do not prune at all and it is accepted.  Neither is
        shippable: the first makes M5 impossible, the second grows the ledger
        without bound.

        ``prune_issued_before`` is the third thing.  Prune the PREVIOUS kill's
        rows when the next kill lands: the newest rows -- the only ones a
        player could be reaching for -- stay, and the ledger is still bounded.
        """
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        first = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        self.assertTrue(first, "this test needs a kill that dropped something")
        second = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(4)),
            kill_token=2)
        self.assertTrue(second)
        # the cut point is the first key of the newest kill: everything the
        # cell issued BEFORE it goes, everything from it on stays
        removed = cell.prune_issued_before(second[0].drop_key)
        self.assertEqual(
            [row.drop_key for row in removed],
            [row.drop_key for row in first])
        live = [row.drop_key for row in cell.ledger.drops]
        self.assertEqual(live, [row.drop_key for row in second])
        # and the surviving rows are genuinely takeable -- the property the
        # runtime loop destroys today
        for key in live:
            self.assertIsNotNone(cell.take(key))

    def test_pruning_before_the_oldest_live_key_removes_nothing(self):
        # A cut point below everything is a no-op, not "prune the lot": a
        # caller that passes the wrong end of the ledger must not silently
        # clear it.
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        drops = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        self.assertTrue(drops)
        before = tuple(cell.ledger.drops)
        self.assertEqual(cell.prune_issued_before(min(
            row.drop_key for row in drops)), ())
        self.assertEqual(cell.ledger.drops, before)
        # ...and a cut point ABOVE the newest kill is refused by name rather
        # than clearing the ledger.  pf-adversary, this round: the first draft
        # asserted the opposite here, five lines under a comment saying "a
        # caller that passes the wrong end of the ledger must not silently
        # clear it" -- the property was enforced on one end only, and
        # `prune_issued_before(cell.ledger.next_key)` is the most natural line
        # a caller would type.
        for cut in (max(row.drop_key for row in drops) + 1,
                    cell.ledger.next_key,
                    0xFFFFFFFF):
            with self.subTest(cut=hex(cut)):
                with self.assertRaises(MobLootContractError) as caught:
                    cell.prune_issued_before(cut)
                self.assertEqual(
                    caught.exception.args[0],
                    mob_loot.REFUSE_PRUNE_WOULD_TAKE_THE_NEWEST_KILL)
                self.assertEqual(cell.ledger.drops, before,
                                 "a refusal moved the cell")

    def test_the_prune_key_is_validated_as_a_key(self):
        cell = DropLedgerCell()
        for bad in (-1, 0x1_0000_0000, "0x100000", 1.0, True):
            with self.subTest(value=bad):
                with self.assertRaises(MobLootContractError):
                    cell.prune_issued_before(bad)

    def test_a_refused_prune_leaves_the_cell_exactly_as_it_was(self):
        """The contract ``loot_a_kill`` states, held for this method too.

        pf-adversary, this round: the validation test ran on an EMPTY cell, so
        moving the range check to after the loop -- a refusal that mutates
        first -- stayed green, and so did committing each row inside the loop
        instead of at the end.  Both are pinned here on a populated cell.
        """
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        second = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(4)),
            kill_token=2)
        self.assertTrue(second)
        before = cell.ledger
        # (1) a badly typed cut point refuses BEFORE anything moves
        with self.assertRaises(MobLootContractError):
            cell.prune_issued_before("not a key")
        self.assertIs(cell.ledger, before)
        # (2) a failure part way through the loop leaves NOTHING removed:
        #     the rebuild is local until the last row is done
        real_take = mob_loot.take_drop
        calls = []

        def fails_on_the_second_row(ledger_now, drop_key):
            calls.append(drop_key)
            if len(calls) > 1:
                raise MobLootContractError(
                    mob_loot.REFUSE_DROP_NOT_IN_LEDGER, "injected")
            return real_take(ledger_now, drop_key)

        if len(before.drops) - len(second) >= 2:
            with mock.patch.object(
                    mob_loot, "take_drop", fails_on_the_second_row):
                with self.assertRaises(MobLootContractError):
                    cell.prune_issued_before(second[0].drop_key)
            self.assertIs(cell.ledger, before, "a partial prune was committed")

    def test_prune_previous_kills_needs_no_cut_point_and_keeps_the_newest(self):
        """The call the wiring note names, and the reason it takes nothing.

        pf-adversary asked where a caller gets a cut point it cannot get
        wrong.  It does not: the cell knows the newest kill's first key, so
        this derives it.  A kill that dropped nothing does not move the mark.
        """
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        self.assertEqual(
            cell.prune_previous_kills(), (),
            "with no kill yet there is nothing older than the newest one")
        first = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        self.assertTrue(first)
        self.assertEqual(
            cell.prune_previous_kills(), (),
            "the only kill on the ground is the newest one")
        self.assertEqual(len(cell.ledger.drops), len(first))
        second = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(4)),
            kill_token=2)
        self.assertTrue(second)
        removed = cell.prune_previous_kills()
        self.assertEqual(
            [row.drop_key for row in removed],
            [row.drop_key for row in first])
        self.assertEqual(
            [row.drop_key for row in cell.ledger.drops],
            [row.drop_key for row in second])
        # the surviving rows are takeable -- the property the runtime loop
        # destroys today
        for row in second:
            self.assertIsNotNone(cell.take(row.drop_key))

    # -- CODEX_URGENT 2026-09-01T20:40+07:00 / COO-DECISION 2026-09-01T21:48
    # +07:00, item 2: DropLedger has no scene term and every kill sends the
    # live ledger whole, so a drop still on the ground in scene A rides along
    # into scene B's first publication.  reconcile_scene_transition() is the
    # bounded fix -- clear the whole ledger at the scene boundary, before the
    # next publish, keeping issued_through/looted (never reused, never a
    # scene fact) so a respawn-and-rekill later still cannot replay.

    def test_reconcile_scene_transition_clears_every_live_row(self):
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        placed = cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        self.assertTrue(placed, "fixture needs a kill that actually drops")
        self.assertEqual(len(cell.ledger.drops), len(placed))
        removed = cell.reconcile_scene_transition()
        self.assertEqual(
            [row.drop_key for row in removed],
            [row.drop_key for row in placed])
        self.assertEqual(cell.ledger.drops, ())

    def test_reconcile_scene_transition_carries_issued_through_and_looted(
            self):
        # A key must never be reused (a client may still hold it under a
        # stale reference) and a kill token already spent must still refuse a
        # replay in the NEXT scene -- neither of those is "what is on the
        # ground", so neither resets with the ground.
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        before_issued = cell.ledger.issued_through
        before_looted = cell.ledger.looted
        self.assertTrue(before_looted)
        cell.reconcile_scene_transition()
        self.assertEqual(cell.ledger.issued_through, before_issued)
        self.assertEqual(cell.ledger.looted, before_looted)

    def test_reconcile_scene_transition_a_kill_next_door_carries_nothing_from_the_old_scene(
            self):
        # THE REGRESSION ITSELF, END TO END: scene A has a live drop, the
        # player crosses to scene B, scene B's first kill publishes -- and
        # that publication must not carry scene A's key or position.
        cell = DropLedgerCell()
        mob_a = self.roster[0]
        record_a = DeathRecord(mob_a.actor_identity, KILLER, mob_a.max_hp)
        drops_a = cell.loot_a_kill(
            mob_a, record_a, roll_drops(mob_a, random.Random(3)),
            kill_token=1)
        self.assertTrue(drops_a)
        keys_a = frozenset(row.drop_key for row in drops_a)
        cell.reconcile_scene_transition()  # the scene boundary
        mob_b = self.roster[1]
        record_b = DeathRecord(mob_b.actor_identity, KILLER, mob_b.max_hp)
        drops_b = cell.loot_a_kill(
            mob_b, record_b, roll_drops(mob_b, random.Random(4)),
            kill_token=2)
        publication = cell.ledger.drops
        self.assertFalse(keys_a & frozenset(row.drop_key for row in publication))
        for row in publication:
            self.assertNotEqual(row.mob_identity, mob_a.actor_identity)
        if drops_b:
            self.assertEqual(
                frozenset(row.drop_key for row in publication),
                frozenset(row.drop_key for row in drops_b))

    def test_reconcile_scene_transition_on_an_empty_cell_is_a_no_op(self):
        cell = DropLedgerCell()
        before = cell.ledger
        removed = cell.reconcile_scene_transition()
        self.assertEqual(removed, ())
        self.assertEqual(cell.ledger, before)

    def test_reconcile_scene_transition_advances_generation_by_one(self):
        cell = DropLedgerCell()
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        cell.loot_a_kill(
            self.mob, record, roll_drops(self.mob, random.Random(3)),
            kill_token=1)
        before_generation = cell.ledger.generation
        cell.reconcile_scene_transition()
        self.assertEqual(cell.ledger.generation, before_generation + 1)

    def test_reconcile_scene_transition_module_function_matches_the_cell(
            self):
        ledger = commit_drops(
            DropLedger(), place_drops(
                self.mob, DeathRecord(
                    self.mob.actor_identity, KILLER, self.mob.max_hp),
                roll_drops(self.mob, random.Random(3)), DROP_KEY_BASE),
            base_generation=0, kill_token=1,
            mob_identity=self.mob.actor_identity)
        if not ledger.drops:
            self.skipTest("this seed's roll dropped nothing")
        cleared, removed = mob_loot.reconcile_scene_transition(ledger)
        self.assertEqual(cleared.drops, ())
        self.assertEqual(cleared.issued_through, ledger.issued_through)
        self.assertEqual(cleared.looted, ledger.looted)
        self.assertEqual(cleared.generation, ledger.generation + 1)
        self.assertEqual(removed, ledger.drops)

    def test_reconcile_scene_transition_refuses_a_non_ledger(self):
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.reconcile_scene_transition("not a ledger")
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_the_wiring_note_names_the_scene_transition_call_site(self):
        note = mob_loot.MOB_LOOT_WIRING
        self.assertIn("cell.reconcile_scene_transition()", note)

    def test_the_wiring_note_stopped_telling_the_caller_to_take_every_key(self):
        """P1 of this round's adversarial pass, held by a test.

        The fix went into a method docstring while ``MOB_LOOT_WIRING`` -- the
        contract the caller actually reads, and the one this module's header
        says is written in code "because letters get lost" -- still said
        ``cell.take(key)`` per drop.  A chief following it would have
        reproduced chief's own measured 100%-refusal.
        """
        note = mob_loot.MOB_LOOT_WIRING
        self.assertIn("cell.prune_previous_kills()", note)
        self.assertIn("drop_already_taken", note)
        self.assertNotIn("PRUNE THROUGH THE CELL (cell.take(key))", note)
        # and the assumption is labelled where the caller reads it, not only
        # in a letter: the COO has not ruled on what replaces the ceiling
        self.assertIn("[ASSUMPTION OF LANE B - AWAITING COO]", note)

    def test_a_respawned_monster_killed_again_still_drops(self):
        """The register used to brick the scene after 13 kills.

        Identities are a static function of the roster, so a per-identity
        register with no notion of WHICH death refuses every respawn kill -
        and the domain this feeds is literally named hp_death_and_respawn.
        """
        cell = DropLedgerCell()
        rolled = 0
        for wave in range(1, 4):
            for mob in self.roster:
                record = DeathRecord(mob.actor_identity, KILLER, mob.max_hp)
                drops = cell.loot_a_kill(
                    mob, record, roll_drops(mob, random.Random(wave)),
                    kill_token=wave)
                rolled += len(drops)
                for row in drops:            # the caller prunes; the label is
                    cell.take(row.drop_key)  # off screen in under half a second
        self.assertEqual(len(cell.ledger.looted), len(self.roster))
        self.assertGreater(rolled, 0)

    def test_a_key_that_was_issued_is_refused_even_if_the_caller_offers_it(self):
        _roll, record, drops = self._one_kill()
        ledger = commit_drops(
            DropLedger(), drops, base_generation=0, kill_token=1)
        pruned, _taken = take_drop(ledger, drops[0].drop_key)
        replayed = place_drops(
            self.mob, record, _roll, drops[0].drop_key)
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(
                pruned, replayed, base_generation=pruned.generation,
                kill_token=2)
        self.assertEqual(
            caught.exception.args[0], "key_outside_the_lane_block")

    def test_the_frame_header_is_pinned_at_run_time_too(self):
        """The first repair stopped at the pc; the dispatcher reads these."""
        class _DriftedFraming:
            MAGIC = 0xDEADBEEF

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def frame_pc(self, pc):
                compressed = self._real.snappy_raw_literal(pc)
                return struct.pack(
                    "<II", self.MAGIC, len(compressed)) + compressed

        _roll, _record, drops = self._one_kill()
        with self.assertRaises(MobLootContractError) as caught:
            drop_frames(_DriftedFraming(self.legacy), drops)
        self.assertEqual(caught.exception.args[0], "composed_bytes_off_pin")
        # The FULL ten-byte header is pinned for the one-element frame only:
        # after round ``zxnwtd`` the length field and the literal tag move
        # with the number of drops (RE-130), so the wider frames are pinned
        # on the four magic bytes, which do not.
        (_pc, one_frame), = drop_frames(self.legacy, drops[:1])
        self.assertEqual(
            one_frame[:DROP_FRAME_HEADER_SIZE], DROP_FRAME_HEADER_PIN)
        for _pc, frame in drop_frames(self.legacy, drops):
            self.assertEqual(frame[:4], DROP_FRAME_HEADER_PIN[:4])

    def test_the_lane_states_what_gt045_actually_measured(self):
        """The correction an adversarial pass forced, pinned so it cannot rot.

        The first draft of this module said an item MODEL was drawn and that
        n_DROPMODEL_TYPE was the difference.  GT-045 closed ANSWERED with the
        opposite: a red NAME LABEL, no model at all, brown dust, ~0.2-0.3 s.
        """
        self.assertTrue(GROUND_DROP_DOES_NOT_PERSIST)
        self.assertTrue(NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN)
        # 0.30 s measured, +/-0.1 s mandatory => 0.2-0.4, and writing a single
        # figure is forbidden by the letter that measured it.
        self.assertEqual(GROUND_LABEL_OBSERVED_LIFETIME_SECONDS, (0.2, 0.4))
        self.assertEqual(WIRE_TO_SCREEN_SECONDS, 0.12)
        for forbidden in ("~0.25 s", "for about a quarter of a second"):
            self.assertNotIn(
                forbidden, self.source,
                "a single-figure lifetime the measurement forbids")
        self.assertIn("NO OBJECT IS DRAWN", MOB_LOOT_NONCLAIMS[1])
        source = self.source
        self.assertNotIn("drew a MODEL and a", source.split("~~")[2:] and "" or source)
        for struck in ("~~", "IS STRUCK"):
            self.assertIn(struck, source)

    def test_every_named_refusal_reason_can_actually_happen(self):
        """SET EQUALITY over the names actually RAISED, not a source count.

        The first form counted occurrences and passed for a refusal that was
        declared, mentioned in a comment and raised nowhere -- an adversarial
        pass added exactly that and the suite stayed green.  This is the shape
        ``tests/test_mob_combat.py`` already proved: collect the names in
        ``raise MobLootContractError(NAME, ...)`` nodes and compare the SET.
        """
        constants = {}
        for line in self.source.splitlines():
            if line.startswith("REFUSE_") and " = " in line:
                name, value = line.split(" = ", 1)
                constants[name.strip()] = value.strip().strip('"')
        raised = set()
        for node in ast.walk(ast.parse(self.source)):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            call = node.exc
            if not isinstance(call, ast.Call):
                continue
            if getattr(call.func, "id", "") != "MobLootContractError":
                continue
            if not call.args:
                continue
            first = call.args[0]
            if isinstance(first, ast.Name) and first.id in constants:
                raised.add(constants[first.id])
            elif isinstance(first, ast.Constant):
                raised.add(str(first.value))
        # Names that reach a caller through a refusals LIST rather than a
        # raise: the roll records them per slot instead of aborting the kill.
        #
        # THE DECLARATION TUPLE IS EXCLUDED, and the second adversarial pass is
        # why: MOB_LOOT_REFUSAL_REASONS is itself a tuple whose first element
        # is a refusal constant, so the collector was whitelisting the head of
        # the very list it was checking - a name placed first there needed no
        # code path at all.
        declaration = None
        tree = ast.parse(self.source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if getattr(target, "id", "") == "MOB_LOOT_REFUSAL_REASONS":
                        declaration = node.value
        self.assertIsNotNone(declaration)
        declared_nodes = {id(node) for node in ast.walk(declaration)}
        recorded = set()
        for node in ast.walk(tree):
            if id(node) in declared_nodes:
                continue
            if isinstance(node, ast.Tuple) and node.elts:
                head = node.elts[0]
                if isinstance(head, ast.Name) and head.id in constants:
                    recorded.add(constants[head.id])
        self.assertEqual(
            set(MOB_LOOT_REFUSAL_REASONS) - (raised | recorded), set(),
            "declared refusal names that no code path produces")
        self.assertEqual(
            (raised | recorded) - set(MOB_LOOT_REFUSAL_REASONS), set(),
            "refusal names produced but not declared")

    def test_the_refusal_names_are_unique(self):
        self.assertEqual(
            len(set(MOB_LOOT_REFUSAL_REASONS)), len(MOB_LOOT_REFUSAL_REASONS))

    def test_the_report_names_the_items_a_player_would_read(self):
        roll, _record, _drops = self._one_kill()
        report = loot_report(self.mob, roll)
        self.assertEqual(report["mob"], self.mob.display_name)
        self.assertEqual(report["placeable"], len(roll.items))
        for row in report["items"]:
            self.assertEqual(
                row["name"], field_drop_tables.ITEMS[row["item_id"]][2])

    # -- the console line -----------------------------------------------
    def test_the_console_line_carries_the_token_and_the_real_drop_count(self):
        _roll, _record, drops = self._one_kill()
        line = drops_console_line(self.mob, drops)
        self.assertTrue(line.startswith("MOB_LOOT_DROPS_CENSUS "))
        self.assertIn("drops=%d" % len(drops), line)
        self.assertIn("template=%d" % self.mob.template_id, line)
        self.assertIn("identity=0x%X" % self.mob.actor_identity, line)
        for drop in drops:
            self.assertIn("%d:x%d@0x%X" % (
                drop.item_id, drop.quantity, drop.drop_key), line)
        line.encode("ascii")  # cp874-safe: the whole line is 7-bit ASCII

    def test_the_console_line_says_none_rather_than_an_empty_field(self):
        line = drops_console_line(self.mob, ())
        self.assertIn("drops=0", line)
        self.assertIn("items=none", line)

    def test_the_console_line_escapes_a_display_name_cp874_cannot_map(self):
        odd_mob = replace(self.mob, display_name="東")  # CJK, not cp874
        line = drops_console_line(odd_mob, ())
        line.encode("ascii")
        self.assertNotIn("東", line)

    def test_the_console_line_refuses_a_drops_list_that_is_not_a_tuple(self):
        with self.assertRaises(MobLootContractError):
            drops_console_line(self.mob, list(self._one_kill()[2]))

    # -- the mined table ----------------------------------------------------
    def test_every_item_the_tables_name_is_in_the_item_table(self):
        for set_id, slots in field_drop_tables.DROPS_NORMAL.items():
            self.assertEqual(set_id // 100000, 27)
            for _index, item, _rate, _low, _high in slots:
                if item != MONEY_ITEM_ID:
                    self.assertIn(item, field_drop_tables.ITEMS)
        for table, prefix in (
            (field_drop_tables.DROPS_EQUIPMENT, 54),
            (field_drop_tables.DROPS_SPECIALLY, 28),
        ):
            for set_id, (_rate, _low, _high, entries) in table.items():
                self.assertEqual(set_id // 100000, prefix)
                for _index, item, _weight in entries:
                    if item != MONEY_ITEM_ID:
                        self.assertIn(item, field_drop_tables.ITEMS)

    def test_the_table_carries_exactly_the_sets_the_roster_names(self):
        wanted = set()
        for mob in self.roster:
            for set_id in (mob.drops_normal, mob.drops_equipment,
                           mob.drops_specially):
                if set_id:
                    wanted.add(set_id)
        carried = (
            set(field_drop_tables.DROPS_NORMAL)
            | set(field_drop_tables.DROPS_EQUIPMENT)
            | set(field_drop_tables.DROPS_SPECIALLY)
        )
        # ROUND wmomy7: ~~equal~~ a superset by exactly the Orc Chief's two
        # drop sets.  The drop tables are mined over every placement the
        # scene HAS; ``self.roster`` is what this lane SHIPS, and the
        # owner's ``owner_says_do_not_place`` ruling on the n_id 101-104
        # block keeps placements 92-96 (template 103, "Orc Chief") out of
        # the second set.  Its drop sets stay carried -- they are mined
        # data, not a claim that something drops them today.  The difference
        # is asserted by name so an UNEXPLAINED extra set still fails.
        orc_chief_sets = {2701003, 5400003}
        self.assertEqual(carried - wanted, orc_chief_sets)
        self.assertEqual(wanted - carried, set())
        # BOTH directions.  pf-adversary killed the first draft of this
        # assertion by deleting the row ``2802234: (31,)`` from
        # REFERENCED_BY: that set is one the roster DOES name, so checking
        # only "no unexplained extras" stayed green while a real reference
        # went missing.  The extras direction is the one the owner-refusal
        # loosened; the coverage direction must stay exact.
        self.assertEqual(set(field_drop_tables.REFERENCED_BY) - wanted,
                         orc_chief_sets)
        self.assertEqual(wanted - set(field_drop_tables.REFERENCED_BY), set())

    def test_no_roster_row_can_roll_past_the_lane_ceiling(self):
        """The ceiling must never be reachable by a LEGITIMATE roll.

        ``place_drops`` refuses above ``MAX_DROPS_PER_KILL``, and a refusal in
        production is a kill that drops nothing.  So the ceiling has to sit
        above the worst case the SHIPPED tables can produce, and a regenerated
        table for a richer scene has to fail here rather than in a player's
        session.  Worst case on bg0001 today is 12.
        """
        for mob in self.roster:
            normal = sum(
                1 for _index, item, rate, _low, _high
                in field_drop_tables.DROPS_NORMAL.get(mob.drops_normal, ())
                if rate > 0.0 and item != MONEY_ITEM_ID)
            worst = normal
            for table, set_id in (
                (field_drop_tables.DROPS_EQUIPMENT, mob.drops_equipment),
                (field_drop_tables.DROPS_SPECIALLY, mob.drops_specially),
            ):
                row = table.get(set_id)
                if row and row[0] > 0.0:
                    worst += row[2]
            self.assertLessEqual(
                worst, MAX_DROPS_PER_KILL,
                "%s can roll %d objects and the ceiling is %d"
                % (mob.display_name, worst, MAX_DROPS_PER_KILL))

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_table_when_it_can_run(self):
        """--check was written and then never run by anything.

        The table can drift from the bridge clone's gamedata and only a human
        re-running the tool would notice.  The skip is DECLARED through
        pf_preconditions rather than written by hand, because an undeclared
        skip is exactly what the skip census exists to catch - and it caught
        this one on the gate before the round closed.
        """
        import subprocess

        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable, str(ROOT / "tools/pf_mine_scene_drop_tables.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped table is not what a fresh mining produces:\n%s%s"
            % (finished.stdout, finished.stderr))
        self.assertIn("CHECK OK", finished.stdout)

    def test_the_table_does_not_claim_the_model_column_draws_anything(self):
        header = TABLE_PATH.read_text(encoding="ascii")[:4000]
        self.assertIn("NOT SUFFICIENT to make an item model", header)
        self.assertIn("BOTH carry 1", header)
        self.assertNotIn("NOT the switch", header)

    def test_a_zero_rate_slot_is_carried_rather_than_dropped(self):
        rates = [
            rate
            for slots in field_drop_tables.DROPS_NORMAL.values()
            for _index, _item, rate, _low, _high in slots
        ]
        self.assertIn(0.0, rates)

    def test_no_id_this_lane_can_emit_has_ever_been_on_a_wire(self):
        """The true, stronger version of what this test used to check.

        It was named for "the two ids that travelled" and then asserted that
        2200201 is called Dagger -- an id that never travelled -- because
        neither id that DID travel is in this table at all.  Green for the
        wrong reason, and it hid the fact worth stating: the label evidence is
        about the PIPE, and every id this lane can send is new to the client.

        The 43 below is len(field_drop_tables.ITEMS), the PRODUCTION EMIT
        UNIVERSE (field_drop_tables.py:149-193) -- a different count from the
        externally-specified 43-ID AUDIT SET Codex's GDL-IMG-017 checkpoint
        finding names for the client-side ground-drop asset-decode chain.
        The two currently share a number by coincidence; do not read one for
        the other, and do not change this literal without re-deriving
        len(field_drop_tables.ITEMS) first.
        """
        travelled = set(mob_loot.IDS_ON_THE_WIRE_GT045_V3) | set(
            mob_loot.IDS_ON_THE_WIRE_ROUND_1104)
        self.assertEqual(travelled & set(field_drop_tables.ITEMS), set())
        self.assertIn(
            "NOT ONE OF THE 43 IDS THIS LANE CAN EMIT",
            " ".join(MOB_LOOT_NONCLAIMS))
        self.assertTrue(
            any(row[3] != 0 for row in field_drop_tables.ITEMS.values()),
            "the model column is still carried as a table fingerprint")


class PreserveGroundHeartbeatTests(unittest.TestCase):
    """HEARTBEAT-PRESERVE-001 (COO-DECISION 20260901_0347, CODEX_URGENT
    20260901_0324): the pool-present, count=0 heartbeat body this lane
    composed as the CORE-REQUEST answer for the transport heartbeat that
    otherwise sends a NULL ground-object pool every ~2 s.

    Nothing here calls the listener, the socket, or v141's heartbeat_worker
    -- that wiring is chief's, per the COO's own routing.  These tests pin
    only the bytes this module composes and offers.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_preserve_pc_is_the_pinned_seventeen_bytes(self):
        pc = preserve_ground_heartbeat_pc(self.legacy)
        self.assertEqual(len(pc), PRESERVE_GROUND_HEARTBEAT_PC_SIZE)
        self.assertEqual(len(pc), DROP_ENVELOPE_SIZE)
        self.assertEqual(
            pc.hex(), "129d6e140000000008040b000b08120000",
            "the preserve-heartbeat body drifted from the byte pin this "
            "lane measured against the legacy encoder")

    def test_preserve_pc_derived_mask_is_present_not_absent(self):
        """The whole point: byte 12 (0-indexed) is 0x08, not 0x00.

        ``make_runtime_res_empty_exact`` (v141) writes ``0x0B, 0x00`` in this
        position -- an ABSENT ground list, which Codex's image evidence reads
        as a NULL pool that clears every drop.  This function writes
        ``0x0B, 0x08`` -- a PRESENT, empty (count=0) list, which the same
        evidence reads as preserve/no-op.
        """
        pc = preserve_ground_heartbeat_pc(self.legacy)
        self.assertEqual(pc[10], 0x0B)
        self.assertEqual(pc[11], 0x00, "inherited VitalData mask must stay absent")
        self.assertEqual(pc[12], 0x0B)
        self.assertEqual(
            pc[13], RUNTIME_DERIVED_BIT_GROUND_LIST,
            "ground-list derived mask must be PRESENT, unlike the empty "
            "heartbeat v141 sends today")
        empty_pc, _empty_frame = self.legacy.make_runtime_res_empty_exact()
        self.assertEqual(
            empty_pc[12:14], self.legacy.u8tag(0x0B, 0),
            "confirms what this test is contrasted against: v141's own "
            "empty heartbeat marks the ground list ABSENT")

    def test_preserve_pc_declares_zero_elements(self):
        pc = preserve_ground_heartbeat_pc(self.legacy)
        declared = struct.unpack("<H", pc[15:17])[0]
        self.assertEqual(declared, 0)
        self.assertEqual(len(pc), DROP_ENVELOPE_SIZE)  # no element payload

    def test_preserve_frame_is_the_pinned_twenty_seven_bytes(self):
        pc, frame = preserve_ground_heartbeat_frame(self.legacy)
        self.assertEqual(len(frame), PRESERVE_GROUND_HEARTBEAT_FRAME_SIZE)
        self.assertEqual(
            frame.hex(),
            "ac3e255f130000001140129d6e140000000008040b000b08120000")
        self.assertEqual(frame[len(frame) - len(pc):], pc)

    def test_preserve_frame_matches_the_legacy_framer(self):
        """Cross-check against ``legacy.frame_pc`` directly, the same framing
        entry point ``drop_frames`` uses -- so a moved framer fails here
        too, not only inside a kill-time emission."""
        pc = preserve_ground_heartbeat_pc(self.legacy)
        self.assertEqual(self.legacy.frame_pc(pc), preserve_ground_heartbeat_frame(self.legacy)[1])

    def test_preserve_is_not_the_refused_empty_generation(self):
        """``drop_collection_pc(legacy, ())`` refuses on purpose (RE-130: an
        empty KILL generation is meaningless).  The preserve heartbeat is a
        different situation -- nothing new to reconcile, not "a kill
        dropped nothing" -- and must not raise the same way."""
        with self.assertRaises(MobLootContractError) as caught:
            drop_collection_pc(self.legacy, ())
        self.assertEqual(caught.exception.args[0], "generation_is_empty")
        # The preserve function does not raise for the same shape.
        preserve_ground_heartbeat_pc(self.legacy)

    def test_preserve_pc_is_shorter_than_any_real_drop_pc(self):
        """No element payload ever rides on this frame -- it is strictly the
        envelope, always, so it can never be mistaken for a one-drop
        announcement by length alone."""
        pc = preserve_ground_heartbeat_pc(self.legacy)
        self.assertLess(len(pc), DROP_PC_SIZE)


if __name__ == "__main__":
    unittest.main()
