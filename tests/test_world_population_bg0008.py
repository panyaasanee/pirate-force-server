"""LANE-A: Bg0008's census, on the real frozen serializers.

The wire/DB half of the two-layer evidence rule for this scene.  What this
file can prove without a client: the collection header count equals the
number of bodies actually in the frame (the failure that produces
``ErrorData=28317``), every entry carries a real ``MOBS.n_ID`` rather than a
Mob-Set number, the builder refuses every scene but 8, and the console lines
a headless boot would print say the true numbers including the shortfall.

What it cannot prove, and does not: that a client draws any of it.  Nobody
has been in this scene as of this module's own construction round.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0008_identity as identity  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0008 as census  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The scene's own registry spawn (scenarios/world_scene_registry_001.json,
# n_id=8): SCENE_NAME[8].n_MARKER = 8 -> MARKER[8].
ANCHOR = (19440.0, 23997.0, 560.0)


class Bg0008Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def _build(self, **kwargs):
        return census.build_bg0008_population(
            self.legacy, ANCHOR, scene_id=census.SCENE_N_ID,
            count_source=census.COUNT_SOURCE_FULL_ROSTER, **kwargs)

    def test_the_whole_roster_assembles(self) -> None:
        generation = self._build()
        self.assertEqual(generation.actor_count, 69)
        self.assertEqual(len(generation.placement_indices), 69)
        self.assertEqual(len(generation.n_ids), 69)

    def test_header_count_equals_the_bodies_in_the_frame(self) -> None:
        for count in (1, 7, 55, 69):
            with self.subTest(count=count):
                generation = census.build_bg0008_population(
                    self.legacy, ANCHOR, count, scene_id=census.SCENE_N_ID)
                report = census.dispatch_report(generation)
                self.assertEqual(report["wire_actor_count"], count)
                self.assertEqual(report["assembled_count"], count)
                self.assertTrue(report["counts_agree"])
                self.assertTrue(report["bodies_intact"])
                self.assertEqual(
                    report["body_bytes"], report["entry_bytes_total"])

    def test_every_entry_carries_a_real_mobs_n_id_ON_THE_WIRE(self) -> None:
        """The GT-078 regression, checked in the BYTES that go out.

        Checked ONE ENTRY AT A TIME, not against the whole concatenated
        ``generation.pc`` blob -- round `l03cgh`'s own bg0005 sibling found a
        numeric coincidence a whole-blob search would false-fail on, and this
        scene's own table was checked for the same shape before deciding
        which comparison to use (none found this round, but per-entry
        checking is the honest default regardless).
        """
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        for index, placement in placements.items():
            with self.subTest(placement=index):
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

    def test_nearest_first_order_puts_the_anchor_placement_first(self) -> None:
        # Placement 0 (the closest to the registry's own spawn point, 8.8
        # units away) carries Mob-Set 1, which is UNRESOLVED (leader 249 has
        # no CONSTDATA MOBS row) - so the nearest SHIPPABLE placement is
        # index 2 (Mob-Set 3, "Chamber sailor"), not index 0.  Measured
        # directly, not assumed from the marker-geometry note.
        generation = self._build()
        self.assertEqual(generation.placement_indices[0], 2)
        self.assertEqual(generation.display_names[0], "Chamber sailor")

    def test_it_refuses_every_scene_but_eight(self) -> None:
        for scene_id in (1, 2, 4, 5, 6, 10, 11, 14, 278, "8", None):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(census.Bg0008CensusError):
                    census.build_bg0008_population(
                        self.legacy, ANCHOR, scene_id=scene_id)

    def test_it_refuses_a_bad_anchor_or_count(self) -> None:
        for anchor in ((1.0, 2.0), [1.0, 2.0, 3.0], (1.0, 2.0, float("nan"))):
            with self.subTest(anchor=anchor):
                with self.assertRaises(census.Bg0008CensusError):
                    census.build_bg0008_population(
                        self.legacy, anchor, scene_id=census.SCENE_N_ID)
        for count in (0, -1, 70, True, 3.0):
            with self.subTest(count=count):
                with self.assertRaises(census.Bg0008CensusError):
                    census.build_bg0008_population(
                        self.legacy, ANCHOR, count,
                        scene_id=census.SCENE_N_ID)

    def test_the_console_line_states_the_true_shortfall(self) -> None:
        line = census.census_console_line(self._build())
        self.assertTrue(line.isascii())
        self.assertIn("assembled=69/76", line)
        self.assertIn("shippable=69", line)
        self.assertIn("wire=69", line)
        self.assertIn("bodies=ok", line)
        self.assertIn("unresolved=7", line)
        self.assertIn("shortfall=identity_unresolved=7", line)
        # The 76 target is never quietly rewritten to 69 (CHARTER-02).
        self.assertNotIn("assembled=69/69", line)

    def test_a_caller_truncated_census_says_so_instead_of_blaming_identity(
        self,
    ) -> None:
        generation = census.build_bg0008_population(
            self.legacy, ANCHOR, 12, scene_id=census.SCENE_N_ID)
        report = census.dispatch_report(generation)
        self.assertEqual(report["shortfall_reason"], "caller_requested=12")

    def test_the_headless_lines_name_every_actor_and_every_drop(self) -> None:
        lines = census.census_console_lines(self.legacy, ANCHOR)
        self.assertEqual(len(lines), 1 + 69 + 7)
        self.assertTrue(all(line.isascii() for line in lines))
        self.assertTrue(lines[0].startswith("WORLD_CENSUS_BG0008 "))
        self.assertEqual(
            sum(1 for line in lines if line.startswith("BG0008_UNSHIPPED ")),
            7)
        self.assertIn("Columbus", "\n".join(lines))

    def test_every_console_line_is_cp874_encodable(self) -> None:
        # The bridge console is cp874, not merely ASCII (Thai prose is fine
        # there; this project's own source is ASCII-only, checked here as
        # the stricter, sufficient condition).
        for line in census.census_console_lines(self.legacy, ANCHOR):
            with self.subTest(line=line[:40]):
                line.encode("cp874")

    def test_the_wire_constants_are_imported_not_redefined(self) -> None:
        self.assertIs(census.WIRE_HEADER_BYTES, world_population.WIRE_HEADER_BYTES)
        self.assertIs(census.COLLECTION_TAG, world_population.COLLECTION_TAG)
        self.assertIs(census.INITIAL_REAPPLY_MS, world_population.INITIAL_REAPPLY_MS)

    def test_no_entry_carries_a_faction_bit(self) -> None:
        """Hostility is lane B's decision, not this module's."""
        generation = self._build()
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        hostile_mask_bit = 0x0400
        for index in generation.placement_indices:
            placement = placements[index]
            body = self.legacy.make_npc_attr(
                placement.n_id, placement.actor_identity,
                census.SCENE_N_ID, census.SCENE_SEQUENCE,
                placement.visual_preset,
                current_hp=placement.max_hp, max_hp=placement.max_hp,
                basic_name=placement.display_name,
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
        with self.assertRaises(census.Bg0008CensusError):
            census.build_bg0008_population(
                self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID,
                count_source=census.COUNT_SOURCE_FULL_ROSTER)
        self.assertEqual(self._build().actor_count, census.ROSTER_COUNT)

    def test_only_the_population_seam_imports_this_module(self) -> None:
        # Built, wired AND opened in the same round (`l03cgh`'s/`fx0007`'s
        # precedent for scenes 5 and 6), so this module never carries the
        # "nothing imports this yet" tripwire its earlier siblings each had
        # to rename in a later round -- this file starts with the widened,
        # final shape directly.
        import ast

        importers = []
        for path in (ROOT / "src").rglob("*.py"):
            if path.name == "world_population_bg0008.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                    if node.module:
                        names.append(node.module)
                if any("world_population_bg0008" in name for name in names):
                    importers.append(path.name)
                    break
        self.assertEqual(
            sorted(importers),
            ["lane_a_scene_census.py", "world_population_handoff.py"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
