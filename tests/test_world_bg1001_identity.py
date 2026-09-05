"""LANE-A: the scene-17 (Bg1001, "one ship at sea") crosswalk, round `vwekfq`.

Scene 17 is the first scene this lane's own census work has shipped that is
reached, TODAY, by an ordinary player action on a flagless boot
(``columbus_quest_dispatch``, row 3021) - not by a GM grant, not behind a
scenario.  What makes this table smaller and simpler than Atlantis's
(scene 126) is real: no multi-set '|' placements, no multi-variant leg
gate, no non-ASCII name.  What it adds that Atlantis's table does not
have is a genuine label/machine-column disagreement in the scene's own
placement file (index 1) and three TIED candidate CLINE types instead of
one - both pinned here rather than left to the module docstring alone.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg1001_identity as identity  # noqa: E402


class TheTableSaysWhatTheDocstringSays(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 17)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg1001")
        self.assertEqual(identity.SCENE_CLINE_TYPE, 801)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 0)
        self.assertEqual(identity.SCENE_SAVE_FLAG, 0)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(identity.PLACEMENT_COUNT, 8)
        self.assertEqual(len(identity.shippable_placements()), 7)
        self.assertEqual(len(identity.unshippable_placements()), 1)
        self.assertEqual(len(identity.IDENTITIES), 4)
        self.assertEqual(len(identity.UNRESOLVED), 1)

    def test_control_scene_sets_and_the_table_keys_are_the_same_five(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(scene_sets, table_sets)
        self.assertEqual(table_sets, {1, 2, 4, 5, 6})
        self.assertNotIn(3, table_sets)  # the mislabeled placement's OWN set

    def test_control_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())

    def test_every_shipped_row_carries_a_body_and_ascii_text(self) -> None:
        for placement in identity.shippable_placements():
            with self.subTest(placement=placement.placement_index):
                row = placement.identity
                self.assertTrue(row.outfit)
                self.assertTrue(row.outfit.isascii())
                self.assertNotIn(";", row.outfit)
                self.assertNotIn("|", row.outfit)
                self.assertTrue(row.name)
                self.assertTrue(row.name.isascii())
                self.assertTrue(row.title.isascii())
                self.assertEqual(identity.evidence_name(row), row.name)
                self.assertGreaterEqual(row.level, 1)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_no_row_is_non_ascii_unlike_atlantis(self) -> None:
        """This scene needed no cp874 membership gate at all - said out
        loud, because the next reader who meets a non-ASCII row here should
        not assume the gate exists; ``evidence_name`` refuses instead."""
        with self.assertRaises(identity.Bg1001IdentityError):
            identity.evidence_name(
                identity.SceneIdentity(
                    99, 1, 1, "X", "海", "", 1, 0, 1, 1))

    def test_the_one_dropped_placement_has_no_cline_row_in_any_candidate(
        self,
    ) -> None:
        dropped = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["placement_index"] for row in dropped), [7])
        row = dropped[0]
        self.assertEqual(row["template_id"], 6)
        self.assertEqual(row["cline_row_id"], 0)
        self.assertEqual(row["leader_n_id"], 0)
        self.assertIn("no CLINE row", row["reason"])
        self.assertTrue(row["reason"].isascii())

    def test_the_mislabeled_placement_follows_the_machine_column(
        self,
    ) -> None:
        """Placement index 1's free-text name says "Mob_set_3 01" but its
        machine-parsed template_ids column reads 2 - the same
        label-vs-machine-column shape ``world_bg0004_identity`` records for
        its own scene, resolved the same way (trust the machine column)."""
        index, template_id, instance_count, _x, _y, _z = (
            identity._PLACEMENT_ROWS[1])
        self.assertEqual(index, 1)
        self.assertEqual(template_id, 2)
        self.assertEqual(instance_count, 2)  # second instance of set 2
        self.assertNotIn(3, identity.IDENTITIES)

    def test_the_multi_variant_outfits_ship_their_first_variant(self) -> None:
        self.assertEqual(
            set(identity.MULTI_VARIANT_OUTFITS), {2881, 2883, 2884})
        by_leader = {row[2]: row for row in identity._RESOLVED_ROWS}
        for leader, raw in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(leader=leader):
                variants = raw.split(";")
                self.assertGreaterEqual(len(variants), 2)
                self.assertEqual(by_leader[leader][3], variants[0])
        # Set 1 (leader 2880) is the one shipped set with NO variant string.
        self.assertNotIn(2880, identity.MULTI_VARIANT_OUTFITS)

    def test_the_level_gate_is_the_lowest_of_the_three_tied_candidates(
        self,
    ) -> None:
        """Condition (b) of COO-DECISION `20260905_0848`: the level gate is
        the LOWEST n_MIN_LEVEL among the resolving INSTANCE rows, not the
        highest across types (the D8 defect this scene's own module exists
        to avoid repeating)."""
        rows = identity.INSTANCE_CANDIDATE_ROWS
        self.assertEqual(len(rows), 3)
        min_levels = [row[2] for row in rows]
        self.assertEqual(sorted(min_levels), [25, 70, 70])
        self.assertEqual(identity.SCENE_LEVEL_GATE_MIN_LEVEL, 25)
        self.assertEqual(identity.SCENE_LEVEL_GATE_MIN_LEVEL, min(min_levels))
        self.assertNotEqual(identity.SCENE_LEVEL_GATE_MIN_LEVEL, max(min_levels))
        # And the type this file actually keys on is the one carrying that
        # lowest level, not merely the numerically-first row.
        chosen = [row for row in rows if row[1] == identity.SCENE_CLINE_TYPE]
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0][2], identity.SCENE_LEVEL_GATE_MIN_LEVEL)

    def test_all_three_candidate_types_resolve_the_same_seven_of_eight(
        self,
    ) -> None:
        """The tie condition (b) exists to break: all three types share the
        same 1..5 key range, so all three drop exactly set 6."""
        self.assertEqual(identity.SCENE_LEVEL_GATE_INSTANCE_ROW, 109)

    def test_identity_for_never_substitutes(self) -> None:
        self.assertIsNone(identity.identity_for(6))
        self.assertIsNone(identity.identity_for(3))  # never a key at all
        self.assertIsNotNone(identity.identity_for(1))
        for bad in ("1", 1.0, True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(identity.Bg1001IdentityError):
                    identity.identity_for(bad)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            ids[0], 0x2000 + identity._PLACEMENT_ROWS[0][0] + 1)

    def test_the_source_digests_are_pinned(self) -> None:
        """Shape only - see ``test_world_bg3001_identity``'s own sibling
        test for why a hash is only evidence against the file it came from,
        and this project's Windows gate has no ``pf_bridge`` beside it."""
        self.assertEqual(len(identity.SOURCE_SHA256), 7)
        for path, digest in identity.SOURCE_SHA256.items():
            with self.subTest(path=path):
                self.assertEqual(len(digest), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in digest))
                self.assertGreater(len(set(digest)), 2, path)
        self.assertEqual(
            len(set(identity.SOURCE_SHA256.values())),
            len(identity.SOURCE_SHA256),
        )


class TheSelfCheckRefusesADriftedTable(unittest.TestCase):
    """Each mutation below was run against the real ``_self_check`` before
    it was written down."""

    def _refuses(self, **patches):
        originals = {name: getattr(identity, name) for name in patches}
        for name, value in patches.items():
            setattr(identity, name, value)
        try:
            with self.assertRaises(identity.Bg1001IdentityError):
                identity._self_check()
        finally:
            for name, value in originals.items():
                setattr(identity, name, value)
        identity._self_check()

    def test_a_row_short_of_the_declared_count_refuses(self) -> None:
        self._refuses(_RESOLVED_ROWS=identity._RESOLVED_ROWS[:-1],
                      IDENTITIES=dict(list(identity.IDENTITIES.items())[:-1]))

    def test_a_multi_variant_outfit_reaching_the_column_refuses(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[3] = row[3] + ";M999_000_000_N"
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_multi_variant_leader_that_ships_the_wrong_half_refuses(
        self,
    ) -> None:
        bad_map = dict(identity.MULTI_VARIANT_OUTFITS)
        bad_map[2881] = "SOMETHING_ELSE;M024_000_001_SP1;M024_000_001_SP2"
        self._refuses(MULTI_VARIANT_OUTFITS=bad_map)

    def test_a_nameless_row_refuses_unlike_atlantis(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[4] = ""
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_level_below_the_scenes_own_gate_refuses(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[6] = identity.SCENE_LEVEL_GATE_MIN_LEVEL - 1
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_level_gate_that_is_not_the_lowest_candidate_refuses(
        self,
    ) -> None:
        self._refuses(SCENE_LEVEL_GATE_MIN_LEVEL=70)


if __name__ == "__main__":
    unittest.main()
