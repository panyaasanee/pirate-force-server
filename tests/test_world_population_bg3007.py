"""LANE-A: the Dark Fog Sea's census, on the real frozen serializers.

The wire/DB half of the two-layer evidence rule for scene 304.  What this
file can prove without a client: the collection header count equals the
number of bodies actually in the frame (the failure that produces
``ErrorData=28317``), every entry carries a real ``MOBS.n_ID`` rather than a
Mob-Set number, the builder refuses every scene but 304, and the console
lines a headless boot would print say the true numbers including all sixteen
drops.

What it cannot prove, and does not: that a client draws any of it - and on
this scene the gap is wider than on the islands, because 20 of the 50 shipped
bodies are ``INVISIBLE`` weather markers and 2 more are ``MAP_ISLAND_01``,
neither of which anyone has watched a client render as an actor.  The
attended ticket this round files is where that is settled.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3007_identity as identity  # noqa: E402
from pirateforce_foundation import world_census_level  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg3007 as census  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.population import (  # noqa: E402
    FULL_MOVEMENT_MASK,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The scene's own registry arrival point (scenarios/world_scene_registry_
# 001.json, n_id=304): CONSTDATA_TH__MARKER row 343, pinned by COO-DECISION
# 20260905_1748 as ``decreed_provisional``.  Read from the registry rather
# than retyped, so a registry edit cannot leave this file testing a point
# nobody uses.
ANCHOR = tuple(
    world_scene_travel.spawn_position(world_scene_travel.destination(304)))


class Bg3007Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def _build(self, **kwargs):
        return census.build_bg3007_population(
            self.legacy, ANCHOR, scene_id=census.SCENE_N_ID,
            count_source=census.COUNT_SOURCE_FULL_ROSTER, **kwargs)

    def test_the_whole_roster_assembles(self) -> None:
        generation = self._build()
        self.assertEqual(generation.actor_count, 50)
        self.assertEqual(len(generation.placement_indices), 50)
        self.assertEqual(len(generation.n_ids), 50)

    def test_header_count_equals_the_bodies_in_the_frame(self) -> None:
        for count in (1, 7, 21, 50):
            with self.subTest(count=count):
                generation = census.build_bg3007_population(
                    self.legacy, ANCHOR, count, scene_id=census.SCENE_N_ID)
                report = census.dispatch_report(generation)
                self.assertEqual(report["wire_actor_count"], count)
                self.assertEqual(report["assembled_count"], count)
                self.assertTrue(report["counts_agree"])
                self.assertTrue(report["bodies_intact"])
                self.assertEqual(
                    report["body_bytes"], report["entry_bytes_total"])

    def test_every_entry_carries_a_real_mobs_n_id_ON_THE_WIRE(self) -> None:
        """The GT-078 regression, checked in the BYTES that go out, one entry
        at a time rather than against the concatenated blob."""
        for placement in identity.shippable_placements():
            with self.subTest(placement=placement.placement_index):
                entry = census._entry(self.legacy, placement)
                id_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.n_id)
                )
                set_number_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.template_id)
                )
                self.assertIn(id_tags, entry)
                if placement.n_id != placement.template_id:
                    self.assertNotIn(set_number_tags, entry)
                self.assertIn(
                    self.legacy.wstr_tag(placement.visual_preset), entry)

    def test_the_six_two_set_placements_ship_the_first_legs_body(
        self,
    ) -> None:
        """Leg 53 is MOBS 8167; leg 54 is MOBS 8171.  The rule is only worth
        writing down if the bytes obey it."""
        by_index = {
            p.placement_index: p for p in identity.shippable_placements()}
        for index in identity.MULTI_SET_PLACEMENTS:
            with self.subTest(placement=index):
                entry = census._entry(self.legacy, by_index[index])
                self.assertIn(self.legacy.u16tag(0x12, 8167), entry)
                self.assertNotIn(self.legacy.u16tag(0x12, 8171), entry)

    def test_no_dropped_placement_reaches_the_wire(self) -> None:
        """The sixteen bodyless-leader placements are absent from the frame,
        and the four leader numbers they name are absent from the bytes."""
        generation = self._build()
        for index in range(50, 66):
            with self.subTest(placement=index):
                self.assertNotIn(index, generation.placement_indices)
        for leader in (8176, 8177, 8178, 8179):
            with self.subTest(leader=leader):
                self.assertNotIn(
                    self.legacy.u16tag(0x12, leader), generation.pc)

    def test_the_census_is_ordered_by_distance_and_not_by_file_order(
        self,
    ) -> None:
        """Asserts the PROPERTY rather than re-implementing the sort key:
        distances never decrease along the shipped order, and the shipped
        order is not the file order."""
        generation = self._build()
        by_index = {
            p.placement_index: p for p in identity.shippable_placements()}

        def distance(index):
            placement = by_index[index]
            return (
                (placement.x - ANCHOR[0]) ** 2
                + (placement.y - ANCHOR[1]) ** 2
                + (placement.z - ANCHOR[2]) ** 2
            )

        distances = [distance(i) for i in generation.placement_indices]
        self.assertEqual(distances, sorted(distances))
        self.assertNotEqual(
            list(generation.placement_indices), sorted(by_index),
            "the census went out in file order: the nearest-first rule is "
            "gone and no distance assertion above can see it",
        )

    def test_a_truncated_census_carries_the_nearest_actors(self) -> None:
        few = census.build_bg3007_population(
            self.legacy, ANCHOR, 3, scene_id=census.SCENE_N_ID)
        whole = self._build()
        self.assertEqual(
            list(few.placement_indices),
            list(whole.placement_indices[:3]))
        self.assertNotEqual(
            sorted(few.placement_indices),
            sorted(p.placement_index
                   for p in identity.shippable_placements()[:3]),
        )

    def test_each_actor_carries_the_heading_its_placement_index_picks(
        self,
    ) -> None:
        """pf-adversary measured on the sibling scene that shifting the
        heading table index by one left the whole suite green.  The heading
        is a real byte in a real frame."""
        for placement in identity.shippable_placements()[:6]:
            with self.subTest(placement=placement.placement_index):
                entry = census._entry(self.legacy, placement)
                right = self.legacy.make_remote_movement_attr(
                    placement.actor_identity,
                    placement.x, placement.y, placement.z,
                    world_population.HEADINGS[placement.placement_index & 3],
                    mask=FULL_MOVEMENT_MASK,
                )
                self.assertIn(right, entry)
                wrong = self.legacy.make_remote_movement_attr(
                    placement.actor_identity,
                    placement.x, placement.y, placement.z,
                    world_population.HEADINGS[
                        (placement.placement_index + 1) & 3],
                    mask=FULL_MOVEMENT_MASK,
                )
                if wrong != right:
                    self.assertNotIn(wrong, entry)

    def test_it_refuses_every_scene_but_304(self) -> None:
        for scene_id in (1, 2, 3, 11, 14, 17, 126, 130, 278, 305, "304", None):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(census.Bg3007CensusError):
                    census.build_bg3007_population(
                        self.legacy, ANCHOR, scene_id=scene_id)

    def test_it_refuses_a_bad_anchor_or_count(self) -> None:
        for anchor in ((1.0, 2.0), [1.0, 2.0, 3.0], (1.0, 2.0, float("nan"))):
            with self.subTest(anchor=anchor):
                with self.assertRaises(census.Bg3007CensusError):
                    census.build_bg3007_population(
                        self.legacy, anchor, scene_id=census.SCENE_N_ID)
        # 51 is one past the roster - a caller may not ask for more actors
        # than this scene has bodies for.
        for count in (0, -1, 51, True, 3.0):
            with self.subTest(count=count):
                with self.assertRaises(census.Bg3007CensusError):
                    census.build_bg3007_population(
                        self.legacy, ANCHOR, count,
                        scene_id=census.SCENE_N_ID)

    def test_the_console_line_states_the_true_shortfall(self) -> None:
        line = census.census_console_line(self._build())
        self.assertTrue(line.isascii())
        self.assertIn("assembled=50/66", line)
        self.assertIn("shippable=50", line)
        self.assertIn("wire=50", line)
        self.assertIn("unresolved=16", line)
        self.assertIn("shortfall=identity_unresolved=16", line)

    def test_a_caller_truncated_census_says_so_instead_of_blaming_identity(
        self,
    ) -> None:
        generation = census.build_bg3007_population(
            self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID)
        line = census.census_console_line(generation)
        self.assertIn("shortfall=caller_requested=5", line)

    def test_the_headless_lines_name_every_actor_and_every_drop(self) -> None:
        generation = self._build()
        actor_lines = census.actor_lines(generation)
        self.assertEqual(len(actor_lines), 50)
        self.assertEqual(len(census.unresolved_lines()), 16)
        joined = "\n".join(actor_lines)
        for name in ("Ulysses", "Bismarck", "Yamato", "Black beard",
                     "Red beard", "Merchant Ship", "Pirate Ship", "Tornado",
                     "Mad Sand Island", "Pirate Lair", "Smuggling Ship"):
            with self.subTest(name=name):
                self.assertIn(name, joined)
        for line in actor_lines:
            with self.subTest(line=line[:32]):
                self.assertTrue(line.startswith("placement="))
        indices = sorted(
            int(line.split()[0].split("=")[1]) for line in actor_lines)
        self.assertEqual(indices, sorted(generation.placement_indices))

    def test_the_drop_lines_name_the_ship_the_tip_table_names(self) -> None:
        """A tester reading the console must be able to tell the shipped
        Ulysses (set 1, MOBS 8000) from the dropped one (set 55, leader
        8176), because the tip table gives both rows the same name."""
        lines = census.unresolved_lines()
        self.assertEqual(len(lines), 16)
        joined = "\n".join(lines)
        self.assertIn("leader_n_id=8176", joined)
        self.assertIn("Ulysses", joined)
        for line in lines:
            with self.subTest(line=line[:40]):
                self.assertTrue(line.startswith("BG3007_UNSHIPPED placement="))
                self.assertIn("reason=CLINE_leader_has_no_CONSTDATA_MOBS_row",
                              line)

    def test_every_console_line_is_cp874_encodable(self) -> None:
        lines = census.census_console_lines(self.legacy, ANCHOR)
        for line in lines:
            with self.subTest(line=line[:40]):
                line.encode("cp874")
                self.assertTrue(line.isascii())

    def test_the_wire_constants_are_imported_not_redefined(self) -> None:
        self.assertIs(
            census.WIRE_HEADER_BYTES, world_population.WIRE_HEADER_BYTES)
        self.assertIs(census.COLLECTION_TAG, world_population.COLLECTION_TAG)
        self.assertIs(
            census.INITIAL_REAPPLY_MS, world_population.INITIAL_REAPPLY_MS)

    def test_no_entry_carries_a_faction_bit(self) -> None:
        """Hostility is lane B's decision, not this module's."""
        generation = self._build()
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        hostile_mask_bit = 0x0400
        for index in generation.placement_indices:
            placement = placements[index]
            body = world_census_level.leveled_npc_attr(
                self.legacy,
                template_n_id=placement.n_id,
                actor_identity=placement.actor_identity,
                scene_id=census.SCENE_N_ID,
                scene_sequence=census.SCENE_SEQUENCE,
                visual_preset=placement.visual_preset,
                current_hp=placement.max_hp, max_hp=placement.max_hp,
                basic_name=placement.display_name,
                level=placement.identity.level,
            )
            with self.subTest(placement=index):
                self.assertIn(body, generation.pc)
                self.assertNotIn(
                    self.legacy.u16tag(0x12, hostile_mask_bit)
                    + self.legacy.u16tag(0x12, placement.n_id),
                    generation.pc)
        self.assertEqual(generation.pc, self._build().pc)

    def test_the_level_120_ships_ship_their_own_level_and_hp(self) -> None:
        """The scene's only rows with a real HP number.  A composer that
        substituted the level-1 floor would still assemble 50 actors and
        still agree with its own counts."""
        by_index = {p.placement_index: p
                    for p in identity.shippable_placements()}
        heavies = [p for p in by_index.values() if p.identity.level == 120]
        self.assertEqual(len(heavies), 9)
        for placement in heavies:
            with self.subTest(placement=placement.placement_index):
                self.assertEqual(placement.max_hp, 335459)
                entry = census._entry(self.legacy, placement)
                right = world_census_level.leveled_npc_attr(
                    self.legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=census.SCENE_N_ID,
                    scene_sequence=census.SCENE_SEQUENCE,
                    visual_preset=placement.visual_preset,
                    current_hp=placement.max_hp, max_hp=placement.max_hp,
                    basic_name=placement.display_name,
                    level=120,
                )
                self.assertIn(right, entry)
                wrong = world_census_level.leveled_npc_attr(
                    self.legacy,
                    template_n_id=placement.n_id,
                    actor_identity=placement.actor_identity,
                    scene_id=census.SCENE_N_ID,
                    scene_sequence=census.SCENE_SEQUENCE,
                    visual_preset=placement.visual_preset,
                    current_hp=106, max_hp=106,
                    basic_name=placement.display_name,
                    level=1,
                )
                self.assertNotIn(wrong, entry)

    def test_a_full_roster_label_cannot_be_put_on_a_truncated_census(
        self,
    ) -> None:
        with self.assertRaises(census.Bg3007CensusError):
            census.build_bg3007_population(
                self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID,
                count_source=census.COUNT_SOURCE_FULL_ROSTER)
        self.assertEqual(self._build().actor_count, census.ROSTER_COUNT)

    def test_only_the_population_seam_imports_this_module(self) -> None:
        import ast

        importers = []
        for path in (ROOT / "src").rglob("*.py"):
            if path.name == "world_population_bg3007.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.Import):
                    names = [alias.name.rsplit(".", 1)[-1]
                             for alias in node.names]
                if "world_population_bg3007" in names:
                    importers.append(path.name)
        self.assertEqual(
            sorted(set(importers)),
            ["lane_a_scene_census.py", "world_population_handoff.py"])


if __name__ == "__main__":
    unittest.main()
