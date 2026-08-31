"""LANE-A: Bg0004's census, on the real frozen serializers.

The wire/DB half of the two-layer evidence rule for this scene.  What this
file can prove without a client: the collection header count equals the
number of bodies actually in the frame (the failure that produces
``ErrorData=28317``), every entry carries a real ``MOBS.n_ID`` rather than a
Mob-Set number, the builder refuses every scene but 4, and the console lines
a headless boot would print say the true numbers including the shortfall.

What it cannot prove, and does not: that a client draws any of it.  Nobody
has been in this scene.  There is no ticket number for it yet -- see the
module's own "NOT WIRED" paragraph for why.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0004_identity as identity  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0004 as census  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The scene's own registry spawn (scenarios/world_scene_registry_001.json,
# n_id=4): SCENE_NAME[4].n_MARKER = 4 -> MARKER[4].
ANCHOR = (-19076.0, 17634.0, 1440.0)


class Bg0004Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def _build(self, **kwargs):
        return census.build_bg0004_population(
            self.legacy, ANCHOR, scene_id=census.SCENE_N_ID,
            count_source=census.COUNT_SOURCE_FULL_ROSTER, **kwargs)

    def test_the_whole_roster_assembles(self) -> None:
        generation = self._build()
        self.assertEqual(generation.actor_count, 109)
        self.assertEqual(len(generation.placement_indices), 109)
        self.assertEqual(len(generation.n_ids), 109)

    def test_header_count_equals_the_bodies_in_the_frame(self) -> None:
        for count in (1, 7, 55, 109):
            with self.subTest(count=count):
                generation = census.build_bg0004_population(
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

        Same discipline ``test_world_population_bg0015.py`` uses: look for
        the exact NPCAttr identity-tag sequence
        (``u8tag(0x0B, mask)`` then ``u16tag(0x12, n_id)``, v141:1196-1197)
        rather than a bare u16 any coincidental byte pair could match, and
        assert the Mob-Set number's OWN encoding is absent.
        """
        generation = self._build()
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        for index in generation.placement_indices:
            placement = placements[index]
            with self.subTest(placement=index):
                id_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.n_id)
                )
                set_number_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.template_id)
                )
                self.assertIn(id_tags, generation.pc)
                if placement.n_id != placement.template_id:
                    self.assertNotIn(set_number_tags, generation.pc)
                self.assertIn(
                    self.legacy.wstr_tag(placement.visual_preset),
                    generation.pc)

    def test_nearest_first_order_puts_the_anchor_placement_first(self) -> None:
        generation = self._build()
        self.assertEqual(generation.placement_indices[0], 81)
        self.assertEqual(generation.display_names[0], "Salahuddin")

    def test_it_refuses_every_scene_but_four(self) -> None:
        for scene_id in (1, 2, 3, 5, 14, 278, "4", None):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(census.Bg0004CensusError):
                    census.build_bg0004_population(
                        self.legacy, ANCHOR, scene_id=scene_id)

    def test_it_refuses_a_bad_anchor_or_count(self) -> None:
        for anchor in ((1.0, 2.0), [1.0, 2.0, 3.0], (1.0, 2.0, float("nan"))):
            with self.subTest(anchor=anchor):
                with self.assertRaises(census.Bg0004CensusError):
                    census.build_bg0004_population(
                        self.legacy, anchor, scene_id=census.SCENE_N_ID)
        for count in (0, -1, 110, True, 3.0):
            with self.subTest(count=count):
                with self.assertRaises(census.Bg0004CensusError):
                    census.build_bg0004_population(
                        self.legacy, ANCHOR, count,
                        scene_id=census.SCENE_N_ID)

    def test_the_console_line_states_the_true_shortfall(self) -> None:
        line = census.census_console_line(self._build())
        self.assertTrue(line.isascii())
        self.assertIn("assembled=109/116", line)
        self.assertIn("shippable=109", line)
        self.assertIn("wire=109", line)
        self.assertIn("bodies=ok", line)
        self.assertIn("unresolved=7", line)
        self.assertIn("shortfall=identity_unresolved=7", line)
        # The 116 target is never quietly rewritten to 109 (CHARTER-02).
        self.assertNotIn("assembled=109/109", line)

    def test_a_caller_truncated_census_says_so_instead_of_blaming_identity(
        self,
    ) -> None:
        generation = census.build_bg0004_population(
            self.legacy, ANCHOR, 12, scene_id=census.SCENE_N_ID)
        report = census.dispatch_report(generation)
        self.assertEqual(report["shortfall_reason"], "caller_requested=12")

    def test_the_headless_lines_name_every_actor_and_every_drop(self) -> None:
        lines = census.census_console_lines(self.legacy, ANCHOR)
        self.assertEqual(len(lines), 1 + 109 + 7)
        self.assertTrue(all(line.isascii() for line in lines))
        self.assertTrue(lines[0].startswith("WORLD_CENSUS_BG0004 "))
        self.assertEqual(
            sum(1 for line in lines if line.startswith("BG0004_UNSHIPPED ")),
            7)
        self.assertIn("Orc Chief", "\n".join(lines))

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
        with self.assertRaises(census.Bg0004CensusError):
            census.build_bg0004_population(
                self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID,
                count_source=census.COUNT_SOURCE_FULL_ROSTER)
        self.assertEqual(self._build().actor_count, census.ROSTER_COUNT)

    def test_only_the_population_seam_imports_this_module(self) -> None:
        # ~~test_nothing_under_src_imports_this_module_yet~~ -- renamed and
        # widened round 2jdde8 (LANE-A), deliberately and in the same round
        # as the change that made it fail, mirroring exactly what
        # ``test_world_population_bg0015.py``'s own history of this test
        # required of that module in round 80x5ba/ga91m5-r2.
        #
        # WHAT CHANGED, AND WHAT DID NOT.  ``world_population_handoff`` now
        # imports this module, because the arrival seam composes THIS roster
        # for a scene-4 arrival.  ``lane_hooks/lane_a_scene_census.py`` also
        # imports it, for its console readers only (census_console_line /
        # actor_lines / unresolved_lines) - the roster itself still comes
        # from the seam.  What has NOT changed: ``runtime.py`` still does not
        # import either, and scene 4's registry row stays shut, so no player
        # reaches this roster because of this round.  An AST walk, not a text
        # search: this module's NAME appears in sibling docstrings on purpose
        # (world_bg0004_identity points at it), and a grep would call that
        # wiring.
        import ast

        importers = []
        for path in (ROOT / "src").rglob("*.py"):
            if path.name == "world_population_bg0004.py":
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
                if any("world_population_bg0004" in name for name in names):
                    importers.append(path.name)
                    break
        # EXACT SET, not "contains" - a third importer, or the seam being
        # swapped for a direct runtime.py import, both fail here and have to
        # be argued for in a round of their own.
        self.assertEqual(
            sorted(importers),
            ["lane_a_scene_census.py", "world_population_handoff.py"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
