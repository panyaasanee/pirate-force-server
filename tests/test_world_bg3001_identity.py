"""LANE-A: the Atlantis crosswalk, driven rather than read back.

Scene 126 is the first scene this lane has composed for that is NOT one of
the ten island doors, and its table carries three shapes no sibling table
has all at once: placements that name TWO Mob-Sets in one column, a set
dropped for a Thai (cp874-representable but non-ASCII) name, and 814 extra
spawn triples that are deliberately not shipped.  Each of those is a
decision, so each is pinned here with the number it claims.

What this file cannot prove, and does not: that a client draws any of it.
Nobody has stood in scene 126 in this project's history.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3001_identity as identity  # noqa: E402


class TheTableSaysWhatTheDocstringSays(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 126)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg3001")
        self.assertEqual(identity.SCENE_CLINE_TYPE, 3001)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 0)
        self.assertEqual(identity.SCENE_SAVE_FLAG, 0)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(identity.PLACEMENT_COUNT, 38)
        self.assertEqual(len(identity.shippable_placements()), 36)
        self.assertEqual(len(identity.unshippable_placements()), 2)
        self.assertEqual(len(identity.IDENTITIES), 23)
        self.assertEqual(len(identity.UNRESOLVED), 2)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_25(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(scene_sets, table_sets)
        self.assertEqual(len(table_sets), 25)
        # And the second leg is NOT in either: it is a key the placements
        # reach only as the discarded half of a two-set column.
        self.assertEqual(set(identity.SECOND_LEG_ONLY), {54})
        self.assertNotIn(54, table_sets)

    def test_control_3_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())

    def test_every_shipped_row_carries_a_body_and_ascii_text(self) -> None:
        for placement in identity.shippable_placements():
            with self.subTest(placement=placement.placement_index):
                row = placement.identity
                self.assertTrue(row.outfit)
                self.assertTrue(row.outfit.isascii())
                self.assertNotIn(";", row.outfit)
                self.assertNotIn("|", row.outfit)
                self.assertTrue(row.name.isascii())
                self.assertTrue(row.title.isascii())
                self.assertGreaterEqual(row.level, 1)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_every_shipped_row_is_cp874_encodable(self) -> None:
        for row in identity._RESOLVED_ROWS:
            with self.subTest(set=row[0]):
                for column in row[3:6]:
                    column.encode("cp874")

    def test_only_the_known_invisible_set_ships_without_a_name(self) -> None:
        nameless = {
            row[0] for row in identity._RESOLVED_ROWS if not row[4]
        }
        self.assertEqual(nameless, set(identity.NAMELESS_INVISIBLE_SETS))
        for set_number in nameless:
            with self.subTest(set=set_number):
                self.assertEqual(
                    identity.IDENTITIES[set_number].outfit,
                    identity.INVISIBLE_OUTFIT)

    def test_the_invisible_bodies_are_shipped_not_dropped(self) -> None:
        """``INVISIBLE`` is a real outfit string; the drop rule keys on an
        EMPTY one.  Same reading bg0004's set 107 ships under."""
        invisible = {
            row[0] for row in identity._RESOLVED_ROWS
            if row[3] == identity.INVISIBLE_OUTFIT
        }
        self.assertEqual(invisible, {31, 32, 34, 40, 53})
        for set_number in invisible:
            with self.subTest(set=set_number):
                self.assertNotIn(set_number, identity.UNRESOLVED)

    def test_the_two_dropped_placements_are_two_different_shapes(
        self,
    ) -> None:
        dropped = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["placement_index"] for row in dropped), [28, 37])
        by_set = {row["template_id"]: row for row in dropped}
        self.assertEqual(by_set[16]["leader_n_id"], 0)
        self.assertIn("leader 0", by_set[16]["reason"])
        self.assertEqual(by_set[56]["leader_n_id"], 8180)
        self.assertIn("Thai", by_set[56]["reason"])
        # Two DIFFERENT reasons, not one repeated: a scene whose drops all
        # read alike is a scene whose drop rule was never exercised.
        self.assertEqual(
            len({row["reason"] for row in dropped}), 2)

    def test_the_multi_set_placements_ship_their_first_leg(self) -> None:
        self.assertEqual(
            sorted(identity.MULTI_SET_PLACEMENTS), [30, 31, 32, 33, 34, 35])
        by_index = {row[0]: row[1] for row in identity._PLACEMENT_ROWS}
        for index, raw in identity.MULTI_SET_PLACEMENTS.items():
            with self.subTest(placement=index):
                self.assertEqual(raw, "53|54")
                self.assertEqual(by_index[index], 53)
                self.assertNotIn(54, identity.IDENTITIES)

    def test_no_extra_spawn_triple_becomes_an_actor(self) -> None:
        """814 extra points exist; the roster is still one per placement."""
        self.assertEqual(sum(identity.EXTRA_TRIPLES_NOT_SHIPPED.values()), 814)
        self.assertEqual(len(identity.EXTRA_TRIPLES_NOT_SHIPPED), 22)
        self.assertLessEqual(
            len(identity.shippable_placements()), identity.PLACEMENT_COUNT)
        indices = {row[0] for row in identity._PLACEMENT_ROWS}
        for index in identity.EXTRA_TRIPLES_NOT_SHIPPED:
            with self.subTest(placement=index):
                self.assertIn(index, indices)

    def test_identity_for_never_substitutes(self) -> None:
        for set_number in identity.UNRESOLVED:
            with self.subTest(set=set_number):
                self.assertIsNone(identity.identity_for(set_number))
        self.assertIsNone(identity.identity_for(54))
        self.assertIsNotNone(identity.identity_for(53))
        for bad in ("53", 53.0, True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(identity.Bg3001IdentityError):
                    identity.identity_for(bad)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            ids[0], 0x2000 + identity._PLACEMENT_ROWS[0][0] + 1)

    def test_the_source_digests_are_pinned(self) -> None:
        self.assertEqual(len(identity.SOURCE_SHA256), 6)
        for path, digest in identity.SOURCE_SHA256.items():
            with self.subTest(path=path):
                self.assertEqual(len(digest), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in digest))


class TheSelfCheckRefusesADriftedTable(unittest.TestCase):
    """Each mutation below was run against the real ``_self_check`` before
    it was written down.  A guard nobody drives is a guard nobody has."""

    def _refuses(self, **patches):
        originals = {name: getattr(identity, name) for name in patches}
        for name, value in patches.items():
            setattr(identity, name, value)
        try:
            with self.assertRaises(identity.Bg3001IdentityError):
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

    def test_a_second_leg_shipped_as_well_refuses(self) -> None:
        extra = dict(identity.IDENTITIES)
        extra[54] = identity.SceneIdentity(
            54, 60453, 8171, "INVISIBLE", "", "", 110, 0, 260787, 7)
        self._refuses(IDENTITIES=extra)

    def test_a_nameless_row_with_a_real_body_refuses(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[4] = ""
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_multi_set_row_that_does_not_ship_its_first_leg_refuses(
        self,
    ) -> None:
        self._refuses(MULTI_SET_PLACEMENTS={30: "54|53"})

    def test_an_extra_triple_row_outside_the_table_refuses(self) -> None:
        bad = dict(identity.EXTRA_TRIPLES_NOT_SHIPPED)
        bad[999] = 1
        self._refuses(EXTRA_TRIPLES_NOT_SHIPPED=bad)


if __name__ == "__main__":
    unittest.main()
