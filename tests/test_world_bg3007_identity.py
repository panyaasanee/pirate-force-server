"""LANE-A: the Dark Fog Sea crosswalk, driven rather than read back.

Scene 304 is the second ocean panel this lane has composed for, and its
table carries one shape no sibling table has: FOUR sets dropped because the
CLINE leader they name has no ``CONSTDATA_TH__MOBS`` row at all, while
``TEXTDATA_TH__MOBS_TIP`` names all four.  A tip row is a label, not a body;
16 of the scene's 66 placements are lost to it, which is by far the largest
drop this lane has shipped, so it is pinned here with the number it claims.

Runs on the Windows gate, with no bridge clone beside it.  The half that
needs the sources is ``test_world_bg3007_identity_rederived.py``, which
skips there and says so.

What this file cannot prove, and does not: that a client draws any of it.
Nobody has stood in scene 304 in this project's history.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3007_identity as identity  # noqa: E402


class TheTableSaysWhatTheDocstringSays(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 304)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg3007")
        self.assertEqual(identity.SCENE_CLINE_TYPE, 3007)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 30)
        self.assertEqual(identity.SCENE_SAVE_FLAG, 0)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(identity.PLACEMENT_COUNT, 66)
        self.assertEqual(len(identity.shippable_placements()), 50)
        self.assertEqual(len(identity.unshippable_placements()), 16)
        self.assertEqual(len(identity.IDENTITIES), 37)
        self.assertEqual(len(identity.UNRESOLVED), 4)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_41(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(scene_sets, table_sets)
        self.assertEqual(len(table_sets), 41)
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
                self.assertTrue(row.title.isascii())
                self.assertGreaterEqual(row.level, 1)
                self.assertGreaterEqual(row.max_hp, 1)
                self.assertGreaterEqual(row.mobs_n_id, 1)
                self.assertGreaterEqual(row.cline_row_id, 1)

    def test_every_shipped_row_is_cp874_encodable(self) -> None:
        """The membership gate, on the rows themselves: a name this console
        cannot print is a name this lane does not ship."""
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                row.name.encode(identity.NAME_ENCODING)
                row.title.encode(identity.NAME_ENCODING)

    def test_every_name_on_this_scene_is_ascii_and_nothing_is_pinned(
        self,
    ) -> None:
        """This scene needs no ``NAME_CP874_HEX`` entry, and the emptiness
        is asserted rather than assumed - a pin appearing here without a
        non-ASCII name is exactly what ``_self_check`` refuses."""
        self.assertEqual(identity.NAME_CP874_HEX, {})
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                self.assertTrue(row.name.isascii())
                self.assertEqual(identity.evidence_name(row), row.name)

    def test_the_cp874_helper_still_works_for_the_day_it_is_needed(
        self,
    ) -> None:
        """``_cp874`` has no caller on this scene's data, so it is driven
        directly rather than left as code nothing runs."""
        # The bytes, never the characters: every file in this lane is ASCII
        # (the bridge console is cp874 and a source file has to survive
        # being opened there).  This is the same five-byte Thai name scene
        # 126's own table pins, decoded here rather than typed.
        pinned = "a1c3d0b7a7"
        thai = bytes.fromhex(pinned).decode("cp874")
        self.assertFalse(thai.isascii())
        self.assertEqual(identity._cp874(pinned), thai)
        for bad in ("not hex", "ff", "41424344"):
            with self.subTest(pin=bad):
                with self.assertRaises(identity.Bg3007IdentityError):
                    identity._cp874(bad)

    def test_only_the_known_invisible_set_ships_without_a_name(self) -> None:
        nameless = {row.template_id for row in identity.IDENTITIES.values()
                    if not row.name}
        self.assertEqual(nameless, set(identity.NAMELESS_INVISIBLE_SETS))
        for template_id in nameless:
            with self.subTest(set=template_id):
                self.assertEqual(
                    identity.IDENTITIES[template_id].outfit,
                    identity.INVISIBLE_OUTFIT)

    def test_the_invisible_bodies_are_shipped_not_dropped(self) -> None:
        """``INVISIBLE`` is a real, non-empty ``s_OUTFIT``: the refusal rule
        this project keys on is an EMPTY outfit column."""
        invisible = [row for row in identity.IDENTITIES.values()
                     if row.outfit == identity.INVISIBLE_OUTFIT]
        self.assertEqual(len(invisible), 15)
        shipped = {p.template_id for p in identity.shippable_placements()}
        for row in invisible:
            with self.subTest(set=row.template_id):
                self.assertIn(row.template_id, shipped)

    def test_the_sixteen_dropped_placements_are_the_bodyless_leader_shape(
        self,
    ) -> None:
        """This scene's whole shortfall, and its one reason.

        Not "some placements do not resolve": four named sets, sixteen
        named placements, one shape.  A regeneration that changed the
        reason has to change this test too.
        """
        dropped = identity.unshippable_placements()
        self.assertEqual(len(dropped), 16)
        self.assertEqual({row["template_id"] for row in dropped},
                         {55, 56, 57, 58})
        self.assertEqual(
            sorted(row["placement_index"] for row in dropped),
            [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65])
        for row in dropped:
            with self.subTest(placement=row["placement_index"]):
                self.assertNotEqual(row["leader_n_id"], 0)
                self.assertIn("no CONSTDATA MOBS row", row["reason"])
                self.assertTrue(row["reason"].isascii())

    def test_the_multi_set_placements_ship_their_first_leg(self) -> None:
        by_index = {p.placement_index: p
                    for p in identity.shippable_placements()}
        self.assertEqual(sorted(identity.MULTI_SET_PLACEMENTS),
                         [44, 45, 46, 47, 48, 49])
        for index, raw in identity.MULTI_SET_PLACEMENTS.items():
            with self.subTest(placement=index):
                self.assertEqual(raw, "53|54")
                self.assertEqual(by_index[index].template_id, 53)
                self.assertEqual(by_index[index].n_id, 8167)

    def test_the_compared_columns_are_every_shipped_one_but_the_mobs_id(
        self,
    ) -> None:
        """DERIVED, not typed: a column added to ``SceneIdentity`` must join
        the leg comparison by existing."""
        self.assertEqual(
            set(identity.SHIPPED_COLUMNS_EXCEPT_MOBS_ID),
            {"outfit", "name", "title", "level", "rank", "max_hp",
             "mob_usage"},
        )

    def test_the_multi_set_gate_passes_on_this_scenes_own_pair(self) -> None:
        self.assertEqual(identity.multi_set_placement_refusals(), ())

    def test_the_multi_set_gate_refuses_each_shape_it_was_built_for(
        self,
    ) -> None:
        """Every refusal below was run against the real gate before it was
        written down.  A gate nobody drives is a gate nobody has."""
        cases = {
            "a leg that disagrees on a shipped column": {
                "SECOND_LEG_IDENTITIES": {
                    54: identity.SceneIdentity(
                        54, 61453, 8171, "INVISIBLE", "", "", 111, 0,
                        260787, 7),
                },
            },
            "a visible leg": {
                "SECOND_LEG_IDENTITIES": {
                    54: identity.SceneIdentity(
                        54, 61453, 8171, "SP_005_000_000_N", "", "", 110, 0,
                        260787, 7),
                },
            },
            "a leg with a name plate": {
                "MULTI_SET_LEG_HAS_TIP_ROW": {53: False, 54: True},
            },
            "a leg this table has never heard of": {
                "MULTI_SET_PLACEMENTS": {44: "53|99"},
            },
            "a malformed raw column": {
                "MULTI_SET_PLACEMENTS": {44: "53|"},
            },
        }
        for label, patches in cases.items():
            with self.subTest(case=label):
                originals = {name: getattr(identity, name)
                             for name in patches}
                for name, value in patches.items():
                    setattr(identity, name, value)
                try:
                    self.assertNotEqual(
                        identity.multi_set_placement_refusals(), ())
                finally:
                    for name, value in originals.items():
                        setattr(identity, name, value)
        self.assertEqual(identity.multi_set_placement_refusals(), ())

    def test_an_unmeasured_leg_is_treated_as_having_a_name_plate(
        self,
    ) -> None:
        """Fail-closed default: an answer this table does not have is not
        an answer of False."""
        original = identity.MULTI_SET_LEG_HAS_TIP_ROW
        identity.MULTI_SET_LEG_HAS_TIP_ROW = {53: False}
        try:
            self.assertNotEqual(identity.multi_set_placement_refusals(), ())
        finally:
            identity.MULTI_SET_LEG_HAS_TIP_ROW = original

    def test_no_extra_spawn_triple_becomes_an_actor(self) -> None:
        self.assertEqual(sum(identity.EXTRA_TRIPLES_NOT_SHIPPED.values()), 656)
        self.assertEqual(len(identity.EXTRA_TRIPLES_NOT_SHIPPED), 18)
        self.assertEqual(len(identity.shippable_placements()), 50)

    def test_identity_for_never_substitutes(self) -> None:
        for template_id in identity.UNRESOLVED:
            with self.subTest(set=template_id):
                self.assertIsNone(identity.identity_for(template_id))
        self.assertIsNone(identity.identity_for(9999))
        self.assertIsNone(identity.identity_for(54))
        with self.assertRaises(identity.Bg3007IdentityError):
            identity.identity_for("53")

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(min(ids), 0x2000 + 1)

    def test_the_source_digests_are_pinned(self) -> None:
        """Shape only, and this test says so out loud.

        The real check - hashing the files - lives in
        ``test_world_bg3007_identity_rederived.py``, which SKIPS on the
        Windows gate because the gate has no ``pf_bridge`` beside it.  So on
        the one machine that closes pull requests, this test is the entire
        digest claim, and it can only kill a DEGENERATE digest.  Do not read
        a green here as "the pins are right".
        """
        self.assertEqual(len(identity.SOURCE_SHA256), 6)
        for path, digest in identity.SOURCE_SHA256.items():
            with self.subTest(path=path):
                self.assertEqual(len(digest), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in digest))
                self.assertGreater(
                    len(set(digest)), 2,
                    "%s: this is not a digest, it is a placeholder" % path,
                )
        self.assertEqual(
            len(set(identity.SOURCE_SHA256.values())),
            len(identity.SOURCE_SHA256),
        )

    def test_the_placement_file_this_table_pins_is_this_scenes_own(
        self,
    ) -> None:
        """A copy-paste of the sibling scene's placement digest would leave
        every count above green: the two files have different row counts,
        but nothing here reads the file."""
        self.assertIn(
            "gamedata/scene/Bg3007/Bg3007.placements.tsv",
            identity.SOURCE_SHA256)


class TheSelfCheckRefusesADriftedTable(unittest.TestCase):
    """Each mutation below was run against the real ``_self_check`` before it
    was written down."""

    def _refuses(self, **patches):
        originals = {name: getattr(identity, name) for name in patches}
        for name, value in patches.items():
            setattr(identity, name, value)
        try:
            with self.assertRaises(identity.Bg3007IdentityError):
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
            54, 61453, 8171, "INVISIBLE", "", "", 110, 0, 260787, 7)
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
        self._refuses(MULTI_SET_PLACEMENTS={44: "54|53"})

    def test_an_extra_triple_row_outside_the_table_refuses(self) -> None:
        bad = dict(identity.EXTRA_TRIPLES_NOT_SHIPPED)
        bad[999] = 1
        self._refuses(EXTRA_TRIPLES_NOT_SHIPPED=bad)

    def test_a_placement_whose_instance_count_was_renumbered_refuses(
        self,
    ) -> None:
        """Control 2, which the sibling scene's table does not carry: this
        scene interleaves sets 56 and 58 across two blocks (placements
        50-53 and 54-65), so a reordering that renumbered the instances
        would be invisible to every other check here."""
        bad = list(identity._PLACEMENT_ROWS)
        row = list(bad[54])
        row[2] = 1
        bad[54] = tuple(row)
        self._refuses(_PLACEMENT_ROWS=tuple(bad))

    def test_a_placement_keyed_by_an_unknown_set_refuses(self) -> None:
        bad = list(identity._PLACEMENT_ROWS)
        row = list(bad[0])
        row[1] = 999
        bad[0] = tuple(row)
        self._refuses(_PLACEMENT_ROWS=tuple(bad))


if __name__ == "__main__":
    unittest.main()
