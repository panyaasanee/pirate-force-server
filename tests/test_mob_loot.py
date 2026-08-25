"""LANE-B: the monster a player kills leaves its own loot where it fell.

The load-bearing tests in this file are the byte tests and the primitive pins.

``test_the_element_is_byte_equal_to_the_probe_lane`` is the one that matters
most: the ONLY reason to believe a client will do anything with this lane's
bytes is that an attended run watched the SAME bytes draw a named object on
the ground.  This lane re-derives that encoder instead of importing the probe
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
    DROP_FRAME_COORD_SHIFT,
    DROP_FRAME_SIZE,
    DROP_KEY_BASE,
    DROP_KEY_LIMIT,
    DROP_PC_SIZE,
    DROP_SCATTER_STEP,
    ELEMENT_MASK_POSITION_AND_DWORD,
    GROUND_DROP_DOES_NOT_PERSIST,
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
KILLER = 0x0101


class _FixedRng:
    """An rng whose draws are a script.  Records what was asked of it."""

    def __init__(self, draws):
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
        tree = ast.parse(self.source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
        self.assertNotIn("loot_roll", imported)
        for name in imported:
            self.assertNotIn(
                "hypothesis", name,
                "a production lane may not import a scenario-gated probe")

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
        with self.assertRaises(MobLootContractError) as caught:
            money_element(self.legacy, roll.money[0])
        self.assertEqual(caught.exception.args[0], "money_has_no_element")
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        drops = place_drops(self.mob, record, roll, DROP_KEY_BASE)
        self.assertEqual(len(drops), len(roll.items))

    # -- placing ------------------------------------------------------------
    def _one_kill(self, seed=3, minimum=2):
        rng = random.Random(seed)
        while True:
            roll = roll_drops(self.mob, rng)
            if len(roll.items) >= minimum:
                break
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
        ledger = commit_drops(DropLedger(), drops)
        self.assertEqual(ledger.generation, 1)
        self.assertEqual(len(ledger.drops), len(drops))
        with self.assertRaises(MobLootContractError) as caught:
            commit_drops(ledger, drops)
        self.assertEqual(caught.exception.args[0], "ledger_stale")

    def test_the_next_key_follows_the_highest_key_on_the_ground(self):
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops)
        self.assertEqual(ledger.next_key, drops[-1].drop_key + 1)
        self.assertEqual(DropLedger().next_key, DROP_KEY_BASE)

    def test_taking_a_drop_removes_exactly_that_row(self):
        _roll, _record, drops = self._one_kill()
        ledger = commit_drops(DropLedger(), drops)
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
        ledger = commit_drops(DropLedger(), drops)
        refreshed = refresh_frames(self.legacy, ledger)
        self.assertEqual(refreshed, drop_frames(self.legacy, ledger.drops))
        with self.assertRaises(MobLootContractError) as caught:
            refresh_frames(self.legacy, drops)
        self.assertEqual(caught.exception.args[0], "type_not_typed_record")

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

    def test_the_lane_states_that_the_drop_does_not_stay(self):
        self.assertTrue(GROUND_DROP_DOES_NOT_PERSIST)
        self.assertIn("DO NOT STAY", MOB_LOOT_NONCLAIMS[1])

    def test_no_refusal_name_is_unreachable(self):
        for reason in MOB_LOOT_REFUSAL_REASONS:
            self.assertEqual(
                self.source.count('"%s"' % reason), 1,
                "%s should be defined exactly once" % reason)
            constant = [
                line.split(" = ")[0] for line in self.source.splitlines()
                if line.startswith("REFUSE_") and line.endswith('"%s"' % reason)
            ]
            self.assertEqual(len(constant), 1)
            self.assertGreaterEqual(
                self.source.count(constant[0]), 3,
                "%s is defined, listed and never raised" % constant[0])

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
