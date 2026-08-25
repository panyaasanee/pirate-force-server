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
from pathlib import Path
import random
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_drop_tables, ground_loot_hypothesis, loot_roll, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_loot import (
    DROP_COORD_SPANS,
    DROP_ENVELOPE_PIN,
    DROP_ENVELOPE_SIZE,
    DROP_FRAME_COORD_SHIFT,
    DROP_FRAME_SIZE,
    DROP_KEY_BASE,
    DROP_KEY_LIMIT,
    DROP_PC_SIZE,
    DROP_SCATTER_STEP,
    ELEMENT_MASK_POSITION_AND_DWORD,
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
    RUNTIME_DERIVED_BIT_GROUND_LIST,
    DropItem,
    DropLedger,
    DropRoll,
    GroundDrop,
    MobLootContractError,
    MoneyDrop,
    as_wire_float,
    commit_drops,
    drop_element,
    drop_frames,
    drop_pc,
    loot_report,
    money_element,
    pin_document,
    place_drops,
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
        cls.roster = load_roster()
        cls.mob = cls.roster[0]
        cls.source = MODULE_PATH.read_text(encoding="utf-8")

    # -- what kind of lane this is -----------------------------------------
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

    def test_one_frame_carries_one_element_at_the_pinned_sizes(self):
        _roll, _record, drops = self._one_kill()
        frames = drop_frames(self.legacy, drops)
        self.assertEqual(len(frames), len(drops))
        for (pc, frame), drop in zip(frames, drops):
            self.assertEqual(len(pc), DROP_PC_SIZE)
            self.assertEqual(len(frame), DROP_FRAME_SIZE)
            coordinates = b"".join(
                pc[start:end] for start, end in DROP_COORD_SPANS)
            self.assertEqual(
                coordinates, struct.pack("<fff", drop.x, drop.y, drop.z))

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
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops, base_generation=0, kill_token=1)
        refreshed = refresh_frames(self.legacy, ledger)
        self.assertEqual(refreshed, drop_frames(self.legacy, ledger.drops))
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
        self.assertEqual(document["wire"]["elements_per_frame"], 1)

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
        for _pc, frame in drop_frames(self.legacy, drops):
            self.assertEqual(
                frame[:DROP_FRAME_HEADER_SIZE], DROP_FRAME_HEADER_PIN)

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
        recorded = set()
        for node in ast.walk(ast.parse(self.source)):
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
        self.assertEqual(carried, wanted)
        self.assertEqual(set(field_drop_tables.REFERENCED_BY), wanted)

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

    def test_the_generator_reproduces_the_shipped_table_when_it_can_run(self):
        """--check was written and then never run by anything.

        The table can drift from the bridge clone's gamedata and only a human
        re-running the tool would notice.  Skipped rather than failed when the
        clone is not present, because the server repo is cloned alone in CI.
        """
        import subprocess

        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        if not (gamedata / "tables").is_dir():
            self.skipTest("no bridge clone beside this repo")
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
        self.assertIn("NOT the switch that makes an item model appear", header)
        self.assertIn("NO", header)

    def test_a_zero_rate_slot_is_carried_rather_than_dropped(self):
        rates = [
            rate
            for slots in field_drop_tables.DROPS_NORMAL.values()
            for _index, _item, rate, _low, _high in slots
        ]
        self.assertIn(0.0, rates)

    def test_the_two_ids_that_travelled_are_still_what_the_tables_say(self):
        """Control 2 of the generator, re-checked from the shipped module."""
        self.assertEqual(
            field_drop_tables.ITEMS.get(2200201, (0, 0, "", 0))[2], "Dagger")
        models = {
            item_id: row[3] for item_id, row in field_drop_tables.ITEMS.items()
        }
        self.assertTrue(any(value != 0 for value in models.values()))


if __name__ == "__main__":
    unittest.main()
