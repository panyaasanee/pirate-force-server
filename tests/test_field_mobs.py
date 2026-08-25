"""LANE-B: named hostile monsters built from real MOBS rows.

The load-bearing tests in this file are the first three.

``test_the_hostile_body_is_the_frozen_body_plus_exactly_five_bytes`` is the one
that matters most: the body this lane sends has never been on the wire in this
combination (named AND hostile), so the only thing that keeps it honest is that
it differs from the frozen, client-rendered body by exactly the GT-032 splice
and by nothing else.  If that test starts passing for a body that is not the
frozen body, the lane is guessing.

``test_the_derived_columns_re_derive_two_frozen_constants`` pins the HP
derivation and the mined name against ``v141``'s own constants, which were
frozen from a live run rather than from a table join.  ``test_the_roster_is_a_
subset_of_the_census`` pins the integration hazard: these monsters ARE census
members, so anything that sends both collections duplicates identities.
"""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_tables, field_mobs
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    NPC_ATTR_ID,
    SCENE_ID,
    SCENE_SEQUENCE,
    load_port_royal_placements,
)
from pirateforce_foundation.field_mobs import (
    BASIC_BIT_FACTION,
    BASIC_BIT_NAME,
    FACTION_SPLICE_BYTES,
    FACTION_TAG,
    FIELD_MOB_FACTION,
    FieldMob,
    FieldMobContractError,
    PLAYER_PAIR_FACTION,
    assert_frozen_controls,
    build_field_mob_population,
    hostile_actor_entry,
    hostile_npc_attr,
    hostile_placement_indices,
    load_roster,
    nearest_first,
    neighbour_census,
    overlapping_identities,
    production_allowed,
    roster_report,
    test_only,
)


class FieldMobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    # --- the three load-bearing tests ------------------------------------

    def test_the_hostile_body_is_the_frozen_body_plus_exactly_five_bytes(self) -> None:
        for mob in load_roster():
            baseline = self.legacy.make_npc_attr(
                mob.template_id, mob.actor_identity, SCENE_ID, SCENE_SEQUENCE,
                mob.visual_preset, mob.max_hp, mob.max_hp,
                basic_name=mob.display_name,
            )
            hostile = hostile_npc_attr(self.legacy, mob)
            self.assertEqual(len(hostile), len(baseline) + FACTION_SPLICE_BYTES)

            # Everything except the mask and the five spliced bytes must be
            # untouched, and the splice must be the tagged faction u32.
            faction_bytes = bytes(
                self.legacy.u32tag(FACTION_TAG, FIELD_MOB_FACTION),
            )
            self.assertEqual(len(faction_bytes), FACTION_SPLICE_BYTES)

            # The POSITION is the claim, not merely the presence: ascending
            # mask-bit order puts 0x0400 after the whole BasicAttr block and
            # before the NPCAttr block, so the splice offset is the length of
            # the body minus the length of the NPCAttr tail.  Derived here
            # from the legacy serializers, independently of the module.
            npc_mask = 0x01 | (0x04 if mob.visual_preset else 0)
            tail = (
                bytes(self.legacy.u8tag(0x0B, npc_mask))
                + bytes(self.legacy.u16tag(0x12, mob.template_id))
                + bytes(self.legacy.wstr_tag(mob.visual_preset))
            )
            offset = len(hostile) - len(tail) - FACTION_SPLICE_BYTES
            self.assertEqual(
                hostile[offset:offset + FACTION_SPLICE_BYTES], faction_bytes,
                "faction is not spliced at the ascending-mask-order position",
            )
            self.assertTrue(hostile.endswith(tail))
            # And the field immediately before it is the BasicAttr block's
            # last member, the tagged scene-sequence qword (bit 0x0200).
            scene_sequence = bytes(
                self.legacy.qwordtag(0x32, SCENE_SEQUENCE),
            )
            self.assertEqual(
                hostile[offset - len(scene_sequence):offset], scene_sequence,
            )
            rebuilt = hostile[:offset] + hostile[offset + FACTION_SPLICE_BYTES:]

            head = (
                bytes(self.legacy.u8tag(0x0B, 1))
                + bytes(self.legacy.qwordtag(0x32, mob.actor_identity))
            )
            mask_at = len(head) + 1
            baseline_mask = int.from_bytes(
                baseline[mask_at:mask_at + 2], "little",
            )
            hostile_mask = int.from_bytes(
                rebuilt[mask_at:mask_at + 2], "little",
            )
            self.assertEqual(hostile_mask, baseline_mask | BASIC_BIT_FACTION)
            self.assertTrue(baseline_mask & BASIC_BIT_NAME)
            self.assertFalse(baseline_mask & BASIC_BIT_FACTION)

            # With the mask restored, the rest is byte-identical.
            restored = (
                rebuilt[:mask_at]
                + baseline[mask_at:mask_at + 2]
                + rebuilt[mask_at + 2:]
            )
            self.assertEqual(restored, baseline)

    def test_the_derived_columns_re_derive_two_frozen_constants(self) -> None:
        assert_frozen_controls(self.legacy)
        control = {
            mob.placement_index: mob for mob in load_roster()
        }[self.legacy.V112_MONSTER_INDEX]
        self.assertEqual(control.max_hp, self.legacy.V117_P30_EXACT_HP)
        self.assertEqual(control.display_name, self.legacy.V119_P30_TARGET_NAME)
        self.assertEqual(control.template_id, 31)
        self.assertEqual(control.level, 27)

    def test_the_roster_is_a_subset_of_the_census(self) -> None:
        census = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        for mob in load_roster():
            self.assertIn(mob.placement_index, census)
            placement = census[mob.placement_index]
            # Same row, mined twice by two different pipelines.
            self.assertEqual(mob.template_id, placement.template_id)
            self.assertEqual(mob.visual_preset, placement.visual_preset)
            self.assertEqual(mob.x, placement.x)
            self.assertEqual(mob.y, placement.y)
            self.assertEqual(mob.z, placement.z)
            self.assertEqual(mob.actor_identity, placement.actor_identity)
        shared = overlapping_identities(tuple(census))
        self.assertEqual(len(shared), len(load_roster()))

    # --- the roster ------------------------------------------------------

    def test_the_roster_is_the_mined_thirteen(self) -> None:
        roster = load_roster()
        self.assertEqual(len(roster), 13)
        self.assertEqual(len({mob.template_id for mob in roster}), 10)
        self.assertEqual(
            hostile_placement_indices(),
            (12, 30, 33, 58, 59, 60, 63, 95, 103, 105, 107, 109, 132),
        )
        for mob in roster:
            self.assertGreater(mob.max_hp, 0)
            self.assertGreater(mob.rank, 0)
            self.assertGreater(mob.ai_combat, 0)
            self.assertTrue(mob.display_name.isascii())
            self.assertTrue(mob.visual_preset.isascii())

    def test_the_generated_module_carries_its_sources_and_its_census(self) -> None:
        self.assertEqual(field_mob_tables.SCENE, "bg0001")
        self.assertEqual(
            sorted(field_mob_tables.SOURCE_DIGESTS),
            ["mobs", "mobs_tip", "placements", "standard_mob"],
        )
        for digest in field_mob_tables.SOURCE_DIGESTS.values():
            self.assertEqual(len(digest), 64)
            int(digest, 16)
        census = field_mob_tables.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], 115)
        # On THIS scene the four readings agree.  They do not agree over the
        # whole MOBS table, which is why the census is carried at all.
        self.assertEqual(census["rank"], 13)
        self.assertEqual(census["ai_combat"], 13)
        self.assertEqual(census["drops_normal"], 13)
        self.assertEqual(census["rank_and_ai_combat"], 13)

    def test_the_generated_module_is_pure_ascii(self) -> None:
        # Lesson 86: one character with no code page 874 mapping raises
        # UnicodeEncodeError inside print() and kills a tool mid-report.
        for name in ("field_mob_tables.py", "field_mobs.py"):
            source = (ROOT / "src/pirateforce_foundation" / name).read_bytes()
            self.assertTrue(source.decode("utf-8").isascii(), name)
        tool = ROOT / "tools/pf_mine_scene_mob_roster.py"
        self.assertTrue(tool.read_bytes().decode("utf-8").isascii())

    # --- what this scene cannot deliver ----------------------------------

    def test_this_town_cannot_crowd_one_view(self) -> None:
        close = neighbour_census(1000.0)
        self.assertEqual(close["with_a_neighbour"], 0)
        wider = neighbour_census(2000.0)
        self.assertEqual(wider["best"], 103)
        self.assertEqual(wider["best_count"], 2)
        nearest = nearest_first(self.spawn)[0]
        distance = (
            (nearest.x - self.spawn[0]) ** 2
            + (nearest.y - self.spawn[1]) ** 2
            + (nearest.z - self.spawn[2]) ** 2
        ) ** 0.5
        self.assertGreater(distance, 12000.0)

    # --- the collection --------------------------------------------------

    def test_the_collection_is_nearest_first_and_reframes(self) -> None:
        generation = build_field_mob_population(self.legacy, self.spawn)
        self.assertEqual(generation.scene, "bg0001")
        self.assertEqual(generation.mob_count, 13)
        self.assertEqual(generation.faction, FIELD_MOB_FACTION)
        self.assertEqual(len(set(generation.actor_identities)), 13)
        self.assertEqual(generation.frame, self.legacy.frame_pc(generation.pc))
        self.assertGreater(generation.frame_bytes, generation.pc_bytes)
        ordered = nearest_first(self.spawn)
        self.assertEqual(
            generation.placement_indices,
            tuple(mob.placement_index for mob in ordered),
        )

    def test_a_shorter_collection_is_a_prefix_of_the_full_one(self) -> None:
        full = build_field_mob_population(self.legacy, self.spawn)
        for count in (1, 4, 12):
            partial = build_field_mob_population(self.legacy, self.spawn, count)
            self.assertEqual(partial.mob_count, count)
            self.assertEqual(
                partial.placement_indices, full.placement_indices[:count],
            )

    def test_the_entry_carries_the_hostile_body_and_full_movement(self) -> None:
        mob = load_roster()[0]
        entry = hostile_actor_entry(self.legacy, mob)
        body = hostile_npc_attr(self.legacy, mob)
        self.assertIn(body, entry)
        movement = self.legacy.make_remote_movement_attr(
            mob.actor_identity, mob.x, mob.y, mob.z,
            field_mobs.HEADINGS[mob.placement_index & 3],
            mask=0xFF,
        )
        self.assertIn(bytes(movement), entry)
        expected = self.legacy.make_remote_actor_entry(
            4, mob.actor_identity,
            [(NPC_ATTR_ID, body), (0x2067, movement)],
        )
        self.assertEqual(entry, expected)

    def test_a_nameless_body_is_the_gt032_shape(self) -> None:
        # GT-032 shipped faction with no name bit at all.  Asking for that
        # shape here must still splice the faction and must not set 0x0001.
        mob = load_roster()[0]
        body = hostile_npc_attr(self.legacy, mob, with_name=False)
        head = (
            bytes(self.legacy.u8tag(0x0B, 1))
            + bytes(self.legacy.qwordtag(0x32, mob.actor_identity))
        )
        mask = int.from_bytes(body[len(head) + 1:len(head) + 3], "little")
        self.assertFalse(mask & BASIC_BIT_NAME)
        self.assertTrue(mask & BASIC_BIT_FACTION)
        self.assertLess(len(body), len(hostile_npc_attr(self.legacy, mob)))

    # --- refusals --------------------------------------------------------

    def test_it_refuses_the_neutral_pairing_and_a_zero_hp_spawn(self) -> None:
        mob = load_roster()[0]
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, mob, faction=0)
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, mob, current_hp=0)
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, "not a mob")

    def test_it_refuses_a_bad_anchor_and_a_bad_count(self) -> None:
        for anchor in ((0.0, 0.0), [0.0, 0.0, 0.0], (0.0, 0.0, float("nan"))):
            with self.assertRaises(FieldMobContractError):
                build_field_mob_population(self.legacy, anchor)
        for count in (0, 14, True, 2.0):
            with self.assertRaises(FieldMobContractError):
                build_field_mob_population(self.legacy, self.spawn, count)

    def test_it_refuses_a_control_that_no_longer_re_derives(self) -> None:
        class Drifted:
            def __getattr__(self, name):
                return getattr(FieldMobTests.legacy, name)
            V117_P30_EXACT_HP = 1

        with self.assertRaises(FieldMobContractError):
            assert_frozen_controls(Drifted())

    def test_a_current_hp_below_max_is_allowed_and_changes_only_that_field(self) -> None:
        # M4 needs a body whose current HP is lower than its max; the shape
        # must not otherwise move.
        mob = load_roster()[0]
        full = hostile_npc_attr(self.legacy, mob)
        hurt = hostile_npc_attr(self.legacy, mob, current_hp=mob.max_hp // 2)
        self.assertEqual(len(full), len(hurt))
        self.assertNotEqual(full, hurt)

    # --- the lane's own conventions --------------------------------------

    def test_it_declares_itself_shippable_and_installs_nothing(self) -> None:
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        source = (ROOT / "src/pirateforce_foundation").glob("*.py")
        importers = [
            path.name for path in source
            if path.name != "field_mobs.py"
            and "field_mobs" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(importers, [], "field_mobs is wired; update the letter")
        self.assertEqual(PLAYER_PAIR_FACTION, 1)
        self.assertEqual(FIELD_MOB_FACTION, 6)

    def test_the_wire_constants_are_the_gt032_ones(self) -> None:
        # Pinned as literals on purpose.  Every other test in this file reads
        # these through the module, so only a literal here can catch the case
        # where the constant itself moves and the assertions move with it.
        self.assertEqual(BASIC_BIT_FACTION, 0x0400)
        self.assertEqual(BASIC_BIT_NAME, 0x0001)
        self.assertEqual(FACTION_TAG, 0x14)
        self.assertEqual(FACTION_SPLICE_BYTES, 5)

    def test_the_committed_pin_is_what_the_code_produces(self) -> None:
        path = ROOT / "scenarios/field_mobs_hostile_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        self.assertEqual(committed, field_mobs.pin_document(self.legacy))
        self.assertTrue(committed["production_allowed"])
        self.assertFalse(committed["test_only"])
        self.assertEqual(
            committed["selection"], "none_default_behaviour_no_scenario_flag",
        )
        self.assertEqual(len(committed["roster"]), 13)
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_report_is_ascii_safe(self) -> None:
        report = roster_report(self.legacy, self.spawn)
        self.assertEqual(report["mob_count"], 13)
        self.assertEqual(report["distinct_templates"], 10)
        self.assertTrue(repr(report).isascii())


class FieldMobTypeTests(unittest.TestCase):
    def test_actor_identity_follows_the_census_rule(self) -> None:
        mob = FieldMob(
            30, 31, 0.0, 0.0, 0.0, "P", "N", 27, 1, 0, 1, 100, 3857, 0, 0, 0,
        )
        self.assertEqual(mob.actor_identity, 0x2000 + 30 + 1)


if __name__ == "__main__":
    unittest.main()
