"""LANE-A: the Pale Silver Sea crosswalk, driven rather than read back.

Scene 305 is the third ocean panel this lane has composed for, and its table
carries one shape no sibling table has: NOTHING IS DROPPED.  All 47 first-leg
Mob-Set numbers its 59 placements use resolve through CLINE type 3008, where
the sibling scene 304 lost 16 of its 66 placements to four bodyless CLINE
leaders.  An empty ``UNRESOLVED`` is easy to mistake for an unfinished table,
so the emptiness is asserted here with the reason, and ``_self_check``
refuses a drop that appears without a code change naming it.

Runs on the Windows gate, with no bridge clone beside it.  The half that
needs the sources is ``test_world_bg3008_identity_rederived.py``, which
skips there and says so.

What this file cannot prove, and does not: that a client draws any of it.
Nobody has stood in scene 305 in this project's history.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3008_identity as identity  # noqa: E402


class TheTableSaysWhatTheDocstringSays(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 305)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg3008")
        self.assertEqual(identity.SCENE_CLINE_TYPE, 3008)
        # 80, and NOT the sibling's 30: a copied constant is the exact
        # failure this line exists to catch.
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 80)
        self.assertEqual(identity.SCENE_SAVE_FLAG, 0)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(identity.PLACEMENT_COUNT, 59)
        self.assertEqual(len(identity.shippable_placements()), 59)
        self.assertEqual(len(identity.unshippable_placements()), 0)
        self.assertEqual(len(identity.IDENTITIES), 47)
        self.assertEqual(identity.UNRESOLVED, {})

    def test_nothing_is_dropped_and_that_is_measured_not_assumed(
        self,
    ) -> None:
        """The one number this scene does not share with its sibling.

        Every placement resolves, so the census's shortfall line has nothing
        to report - and an empty ``unshippable_placements()`` here means the
        loop ran over 59 rows and found none, not that the loop is missing.
        """
        self.assertEqual(identity.unshippable_placements(), ())
        shipped = {p.placement_index for p in identity.shippable_placements()}
        self.assertEqual(shipped, {row[0] for row in identity._PLACEMENT_ROWS})

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_47(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(scene_sets, table_sets)
        self.assertEqual(len(table_sets), 47)
        # And the second leg is NOT in either: it is a key the placements
        # reach only as the discarded half of a two-set column.
        self.assertEqual(set(identity.SECOND_LEG_ONLY), {58})
        self.assertNotIn(58, table_sets)

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
                with self.assertRaises(identity.Bg3008IdentityError):
                    identity._cp874(bad)

    def test_only_the_known_invisible_sets_ship_without_a_name(self) -> None:
        nameless = {row.template_id for row in identity.IDENTITIES.values()
                    if not row.name}
        self.assertEqual(nameless, {56, 57})
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
        self.assertEqual(len(invisible), 21)
        shipped = {p.template_id for p in identity.shippable_placements()}
        for row in invisible:
            with self.subTest(set=row.template_id):
                self.assertIn(row.template_id, shipped)

    def test_the_five_islands_are_this_scenes_own_and_not_the_siblings(
        self,
    ) -> None:
        """Scene 304 ships two islands whose names ALSO appear in scene
        126's table.  This scene's five are its own five, and pinning them
        is what would catch a table regenerated against the wrong CLINE
        type - the join would still produce 47 rows, but not these names.
        """
        islands = {row.name for row in identity.IDENTITIES.values()
                   if row.outfit == "MAP_ISLAND_01"}
        self.assertEqual(
            islands,
            {"Ice Island", "Turtle Island", "Dragon Turtle Island",
             "Guawa Island", "Snow Island"})

    def test_the_multi_set_placements_ship_their_first_leg(self) -> None:
        by_index = {p.placement_index: p
                    for p in identity.shippable_placements()}
        self.assertEqual(sorted(identity.MULTI_SET_PLACEMENTS),
                         [55, 56, 57, 58])
        for index, raw in identity.MULTI_SET_PLACEMENTS.items():
            with self.subTest(placement=index):
                self.assertEqual(raw, "57|58")
                self.assertEqual(by_index[index].template_id, 57)
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
                    58: identity.SceneIdentity(
                        58, 61657, 8171, "INVISIBLE", "", "", 111, 0,
                        260787, 7),
                },
            },
            "a visible leg": {
                "SECOND_LEG_IDENTITIES": {
                    58: identity.SceneIdentity(
                        58, 61657, 8171, "SP_005_000_000_N", "", "", 110, 0,
                        260787, 7),
                },
            },
            "a leg with a name plate": {
                "MULTI_SET_LEG_HAS_TIP_ROW": {57: False, 58: True},
            },
            "a leg this table has never heard of": {
                "MULTI_SET_PLACEMENTS": {55: "57|99"},
            },
            "a malformed raw column": {
                "MULTI_SET_PLACEMENTS": {55: "57|"},
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
        identity.MULTI_SET_LEG_HAS_TIP_ROW = {57: False}
        try:
            self.assertNotEqual(identity.multi_set_placement_refusals(), ())
        finally:
            identity.MULTI_SET_LEG_HAS_TIP_ROW = original

    def test_no_extra_spawn_triple_becomes_an_actor(self) -> None:
        self.assertEqual(sum(identity.EXTRA_TRIPLES_NOT_SHIPPED.values()), 780)
        self.assertEqual(len(identity.EXTRA_TRIPLES_NOT_SHIPPED), 19)
        self.assertEqual(len(identity.shippable_placements()), 59)

    def test_identity_for_never_substitutes(self) -> None:
        self.assertIsNone(identity.identity_for(9999))
        self.assertIsNone(identity.identity_for(58))
        with self.assertRaises(identity.Bg3008IdentityError):
            identity.identity_for("57")

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(min(ids), 0x2000 + 1)

    def test_the_source_digests_are_pinned(self) -> None:
        """Shape only, and this test says so out loud.

        The real check - hashing the files - lives in
        ``test_world_bg3008_identity_rederived.py``, which SKIPS on the
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
        but nothing here reads the file.  The digest is pinned against the
        sibling's by value, because the two modules sit side by side and
        five of their six source files ARE the same table."""
        self.assertIn(
            "gamedata/scene/Bg3008/Bg3008.placements.tsv",
            identity.SOURCE_SHA256)
        from pirateforce_foundation import world_bg3007_identity as sibling
        self.assertNotEqual(
            identity.SOURCE_SHA256["gamedata/scene/Bg3008/"
                                   "Bg3008.placements.tsv"],
            sibling.SOURCE_SHA256["gamedata/scene/Bg3007/"
                                  "Bg3007.placements.tsv"])


class TheSelfCheckRefusesADriftedTable(unittest.TestCase):
    """Each mutation below was run against the real ``_self_check`` before it
    was written down."""

    def _refuses(self, **patches):
        originals = {name: getattr(identity, name) for name in patches}
        for name, value in patches.items():
            setattr(identity, name, value)
        try:
            with self.assertRaises(identity.Bg3008IdentityError):
                identity._self_check()
        finally:
            for name, value in originals.items():
                setattr(identity, name, value)
        identity._self_check()

    def test_a_row_short_of_the_declared_count_refuses(self) -> None:
        self._refuses(_RESOLVED_ROWS=identity._RESOLVED_ROWS[:-1],
                      IDENTITIES=dict(list(identity.IDENTITIES.items())[:-1]))

    def test_an_unresolved_set_appearing_from_nowhere_refuses(self) -> None:
        """This scene's answer is ZERO drops.  A regeneration that produced
        one must land as a code change that states the new count, not as a
        table quietly losing a row - which is what the sibling's "expected 4
        unresolved" shape would have allowed here.
        """
        self._refuses(UNRESOLVED={99: (1, 1, "invented")})

    def test_a_multi_variant_outfit_reaching_the_column_refuses(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[3] = row[3] + ";M999_000_000_N"
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_second_leg_shipped_as_well_refuses(self) -> None:
        extra = dict(identity.IDENTITIES)
        extra[58] = identity.SceneIdentity(
            58, 61657, 8171, "INVISIBLE", "", "", 110, 0, 260787, 7)
        self._refuses(IDENTITIES=extra)

    def test_a_nameless_row_with_a_real_body_refuses(self) -> None:
        bad = list(identity._RESOLVED_ROWS)
        row = list(bad[0])
        row[4] = ""
        bad[0] = tuple(row)
        self._refuses(_RESOLVED_ROWS=tuple(bad))

    def test_a_stale_nameless_exemption_refuses(self) -> None:
        """The exemption list may not outlive the rows it exempts, and it
        may not bless a row that has a name: either way the next nameless
        row to take that set number would ship unchallenged.
        """
        self._refuses(NAMELESS_INVISIBLE_SETS=frozenset({56, 57, 3}))
        self._refuses(NAMELESS_INVISIBLE_SETS=frozenset({56, 57, 999}))

    def test_a_multi_set_row_that_does_not_ship_its_first_leg_refuses(
        self,
    ) -> None:
        self._refuses(MULTI_SET_PLACEMENTS={55: "58|57"})

    def test_an_extra_triple_row_outside_the_table_refuses(self) -> None:
        bad = dict(identity.EXTRA_TRIPLES_NOT_SHIPPED)
        bad[999] = 1
        self._refuses(EXTRA_TRIPLES_NOT_SHIPPED=bad)

    def test_a_placement_whose_instance_count_was_renumbered_refuses(
        self,
    ) -> None:
        """Control 2: this scene's set 56 is split across placements 53-54
        with set 32 landing between two blocks at index 52, so a reordering
        that renumbered the instances would be invisible to every other
        check here."""
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
