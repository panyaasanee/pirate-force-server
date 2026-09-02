"""LANE-A: Atlantis's census, on the real frozen serializers.

The wire/DB half of the two-layer evidence rule for scene 126.  What this
file can prove without a client: the collection header count equals the
number of bodies actually in the frame (the failure that produces
``ErrorData=28317``), every entry carries a real ``MOBS.n_ID`` rather than a
Mob-Set number, the builder refuses every scene but 126, and the console
lines a headless boot would print say the true numbers including both
drops.

What it cannot prove, and does not: that a client draws any of it - and on
this scene that gap is wider than on the islands, because four of the
shipped bodies are ``INVISIBLE`` weather markers and four more are
``MAP_ISLAND_01``, neither of which anyone has watched a client render as
an actor.  ``GT-217`` is where that is settled.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3001_identity as identity  # noqa: E402
from pirateforce_foundation import world_census_level  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg3001 as census  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.population import (  # noqa: E402
    FULL_MOVEMENT_MASK,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The scene's own registry spawn (scenarios/world_scene_registry_001.json,
# n_id=126): CONSTDATA_TH__MARKER row 17, pinned by CHIEF-DECISION
# 20260829_1603 item 1.  Read from the registry rather than retyped, so a
# registry edit cannot leave this file testing a point nobody uses.
ANCHOR = tuple(
    world_scene_travel.spawn_position(world_scene_travel.destination(126)))


class Bg3001Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def _build(self, **kwargs):
        return census.build_bg3001_population(
            self.legacy, ANCHOR, scene_id=census.SCENE_N_ID,
            count_source=census.COUNT_SOURCE_FULL_ROSTER, **kwargs)

    def test_the_whole_roster_assembles(self) -> None:
        generation = self._build()
        self.assertEqual(generation.actor_count, 37)
        self.assertEqual(len(generation.placement_indices), 37)
        self.assertEqual(len(generation.n_ids), 37)

    def test_header_count_equals_the_bodies_in_the_frame(self) -> None:
        for count in (1, 7, 21, 37):
            with self.subTest(count=count):
                generation = census.build_bg3001_population(
                    self.legacy, ANCHOR, count, scene_id=census.SCENE_N_ID)
                report = census.dispatch_report(generation)
                self.assertEqual(report["wire_actor_count"], count)
                self.assertEqual(report["assembled_count"], count)
                self.assertTrue(report["counts_agree"])
                self.assertTrue(report["bodies_intact"])
                self.assertEqual(
                    report["body_bytes"], report["entry_bytes_total"])

    def test_every_entry_carries_a_real_mobs_n_id_ON_THE_WIRE(self) -> None:
        """The GT-078 regression, checked in the BYTES that go out, one
        entry at a time rather than against the concatenated blob."""
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

    def test_the_one_dropped_placement_does_not_reach_the_wire(self) -> None:
        """Was ``neither_dropped_placement_reaches_the_wire``.

        ~~Placement 37 (MOBS 8180) is absent from the frame.~~ STRUCK,
        round ``gx7xtp``: ``COO-DECISION 20260902_2146`` shape 1 ships that
        row, so this test now asserts the OPPOSITE for it - its body is on
        the wire - and keeps the zero-leader drop's absence unchanged.
        """
        generation = self._build()
        self.assertNotIn(28, generation.placement_indices)
        self.assertIn(37, generation.placement_indices)
        # The Thai-named row's REAL MOBS id is in the bytes: a decision to
        # ship is only kept if the body is in the frame, not in the count.
        self.assertIn(self.legacy.u16tag(0x12, 8180), generation.pc)
        # And its name reached the wire as the client reads it - UTF-16LE
        # via ``wstr_tag``, which is what the frozen serializer does with
        # every display name.  The premise that the column carries cp874
        # bytes is corrected in the identity module's THE TWO NAME LAYERS.
        thai = identity.IDENTITIES[56].name
        self.assertIn(thai.encode("utf-16le"), generation.pc)
        self.assertNotIn(thai.encode("cp874"), generation.pc)

    def test_the_census_is_ordered_by_distance_and_not_by_file_order(
        self,
    ) -> None:
        """~~test_nearest_first_order_puts_the_anchor_placement_first~~
        REPLACED, pf-adversary (round `4uztfj`): that test re-implemented
        the sort key it was testing and then compared only element [0] --
        and at this scene's own anchor the nearest placement IS placement
        0, so deleting the sort entirely left it green.  This one asserts
        the PROPERTY instead: distances never decrease along the shipped
        order, and the shipped order is not the file order."""
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
        """What nearest-first is FOR, in the composer's own words: a caller
        asking for fewer than the whole roster shows the player the actors
        around them rather than an arbitrary slice of the ocean."""
        few = census.build_bg3001_population(
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
        """pf-adversary: shifting the heading table index by one left the
        whole suite green.  The heading is a real byte in a real frame."""
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

    def test_it_refuses_every_scene_but_126(self) -> None:
        for scene_id in (1, 2, 3, 11, 14, 17, 130, 278, "126", None):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(census.Bg3001CensusError):
                    census.build_bg3001_population(
                        self.legacy, ANCHOR, scene_id=scene_id)

    def test_it_refuses_a_bad_anchor_or_count(self) -> None:
        for anchor in ((1.0, 2.0), [1.0, 2.0, 3.0], (1.0, 2.0, float("nan"))):
            with self.subTest(anchor=anchor):
                with self.assertRaises(census.Bg3001CensusError):
                    census.build_bg3001_population(
                        self.legacy, anchor, scene_id=census.SCENE_N_ID)
        # 38 is one past the roster (37 since ``COO-DECISION 20260902_2146``
        # shape 1 landed the Thai-named row) - a caller may not ask for more
        # actors than this scene has bodies for.
        for count in (0, -1, 38, True, 3.0):
            with self.subTest(count=count):
                with self.assertRaises(census.Bg3001CensusError):
                    census.build_bg3001_population(
                        self.legacy, ANCHOR, count,
                        scene_id=census.SCENE_N_ID)

    def test_the_console_line_states_the_true_shortfall(self) -> None:
        line = census.census_console_line(self._build())
        self.assertTrue(line.isascii())
        self.assertIn("assembled=37/38", line)
        self.assertIn("shippable=37", line)
        self.assertIn("wire=37", line)
        self.assertIn("unresolved=1", line)
        self.assertIn("shortfall=identity_unresolved=1", line)

    def test_a_caller_truncated_census_says_so_instead_of_blaming_identity(
        self,
    ) -> None:
        generation = census.build_bg3001_population(
            self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID)
        line = census.census_console_line(generation)
        self.assertIn("shortfall=caller_requested=5", line)

    def test_the_headless_lines_name_every_actor_and_every_drop(self) -> None:
        generation = self._build()
        actor_lines = census.actor_lines(generation)
        self.assertEqual(len(actor_lines), 37)
        self.assertEqual(len(census.unresolved_lines()), 1)
        joined = "\n".join(actor_lines)
        for name in ("Intrepid", "Santa Maria", "Jellyfish King",
                     "Blood Blade Island", "Tornado", "Repair ship"):
            with self.subTest(name=name):
                self.assertIn(name, joined)
        # The Thai-named row is NAMED here too, in the only form a cp874
        # console can print - and paired with its placement, which is what
        # ``COO-DECISION 20260902_2146`` shape 1 requires so a tester can
        # still say which of the 38 rows a hex token means.
        self.assertIn("name_cp874_hex=a1c3d0b7a7", joined)
        self.assertIn("placement=37 n_ID=8180 name_cp874_hex=a1c3d0b7a7",
                      joined)
        for line in actor_lines:
            with self.subTest(line=line[:32]):
                self.assertTrue(line.startswith("placement="))
        # Every placement the census shipped is identifiable by index, so
        # no row is reachable only by a name a grader cannot type.
        indices = sorted(
            int(line.split()[0].split("=")[1]) for line in actor_lines)
        self.assertEqual(indices, sorted(generation.placement_indices))

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

    def test_a_full_roster_label_cannot_be_put_on_a_truncated_census(
        self,
    ) -> None:
        with self.assertRaises(census.Bg3001CensusError):
            census.build_bg3001_population(
                self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID,
                count_source=census.COUNT_SOURCE_FULL_ROSTER)
        self.assertEqual(self._build().actor_count, census.ROSTER_COUNT)

    def test_only_the_population_seam_imports_this_module(self) -> None:
        import ast

        importers = []
        for path in (ROOT / "src").rglob("*.py"):
            if path.name == "world_population_bg3001.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.Import):
                    names = [alias.name.rsplit(".", 1)[-1]
                             for alias in node.names]
                if "world_population_bg3001" in names:
                    importers.append(path.name)
        self.assertEqual(
            sorted(set(importers)),
            ["lane_a_scene_census.py", "world_population_handoff.py"])


if __name__ == "__main__":
    unittest.main()
