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
        self.assertEqual(len(identity.shippable_placements()), 37)
        self.assertEqual(len(identity.unshippable_placements()), 1)
        self.assertEqual(len(identity.IDENTITIES), 24)
        self.assertEqual(len(identity.UNRESOLVED), 1)

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
                # NAMES are no longer flatly ASCII - COO-DECISION
                # 20260902_2146 shape 1 - but the rule that replaced it is
                # not weaker: a non-ASCII name must round-trip through
                # cp874 AND be pinned as its own bytes, and the EVIDENCE
                # line stays ASCII either way.  Titles are still ASCII.
                self.assertTrue(row.title.isascii())
                if not row.name.isascii():
                    self.assertIn(row.template_id, identity.NAME_CP874_HEX)
                    self.assertEqual(
                        row.name.encode("cp874").hex(),
                        identity.NAME_CP874_HEX[row.template_id])
                self.assertTrue(identity.evidence_name(row).isascii())
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

    def test_the_one_dropped_placement_is_the_zero_leader_shape(
        self,
    ) -> None:
        """Was ``the_two_dropped_placements_are_two_different_shapes``.

        Placement 37 (Mob-Set 56, the Thai name) is no longer a drop:
        ``COO-DECISION 20260902_2146`` shape 1 overruled that reading and
        it ships.  The zero-leader drop is untouched and is still the one
        shape this scene has.
        """
        dropped = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["placement_index"] for row in dropped), [28])
        by_set = {row["template_id"]: row for row in dropped}
        self.assertEqual(by_set[16]["leader_n_id"], 0)
        self.assertIn("leader 0", by_set[16]["reason"])
        self.assertNotIn(56, by_set)
        for row in dropped:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())

    def test_the_thai_named_row_ships_and_prints_as_hex(self) -> None:
        """Shape 1 of ``COO-DECISION 20260902_2146``, end to end.

        The wire gets the real name; the evidence layer gets ASCII bytes;
        the row is on the roster rather than in the shortfall.
        """
        row = identity.IDENTITIES[56]
        self.assertEqual(row.mobs_n_id, 8180)
        self.assertEqual(row.outfit, "M081_000_000_N")
        self.assertEqual(row.level, 60)
        self.assertEqual(row.max_hp, 43275)
        self.assertFalse(row.name.isascii())
        self.assertEqual(row.name.encode("cp874").hex(), "a1c3d0b7a7")
        self.assertEqual(
            identity.evidence_name(row), "name_cp874_hex=a1c3d0b7a7")
        shipped = {p.placement_index for p in identity.shippable_placements()}
        self.assertIn(37, shipped)

    def test_a_name_that_is_not_cp874_cannot_be_pinned_at_all(self) -> None:
        """The exception the decision kept: bg0006's CJK still cannot ship.

        The membership gate is not a comment - it is the only door a
        non-ASCII name can come through, and these are the four ways
        through it that are shut.
        """
        # A CJK name has no cp874 bytes to pin in the first place.
        with self.assertRaises(UnicodeEncodeError):
            "\u6d77\u4e0a".encode("cp874")
        for bad in ("zz", "", "a1c3d0b7a7ff"):
            with self.subTest(pin=bad):
                with self.assertRaises(identity.Bg3001IdentityError):
                    identity._cp874(bad)
        # An ASCII pin is refused too: that row must carry the literal.
        with self.assertRaises(identity.Bg3001IdentityError):
            identity._cp874("41424344")
        with self.assertRaises(identity.Bg3001IdentityError):
            identity._cp874(b"a1c3d0b7a7")

    def test_the_multi_set_placements_ship_their_first_leg(self) -> None:
        self.assertEqual(
            sorted(identity.MULTI_SET_PLACEMENTS), [30, 31, 32, 33, 34, 35])
        by_index = {row[0]: row[1] for row in identity._PLACEMENT_ROWS}
        for index, raw in identity.MULTI_SET_PLACEMENTS.items():
            with self.subTest(placement=index):
                self.assertEqual(raw, "53|54")
                self.assertEqual(by_index[index], 53)
                self.assertNotIn(54, identity.IDENTITIES)

    def test_the_compared_columns_are_every_shipped_one_but_the_mobs_id(
        self,
    ) -> None:
        """pf-adversary D5: the list used to be hand-typed and nothing
        checked it for completeness - deleting ``rank`` from it left the
        whole suite green while making a rank-64 leg interchangeable with
        a rank-0 one.  It is derived now, and this is the check that says
        so rather than restating the same tuple."""
        import dataclasses

        every = tuple(f.name for f in dataclasses.fields(identity.SceneIdentity))
        exempt = set(identity._LEG_COMPARISON_EXEMPT)
        self.assertEqual(
            set(identity.SHIPPED_COLUMNS_EXCEPT_MOBS_ID),
            set(every) - exempt)
        # The MOBS id is the ONE column the decision lets the legs differ
        # on; the other two exemptions are locators, not shipped columns.
        self.assertIn("mobs_n_id", exempt)
        self.assertIn("cline_row_id", exempt)
        self.assertIn("template_id", exempt)
        for column in ("rank", "title", "mob_usage", "level", "max_hp",
                       "outfit", "name"):
            with self.subTest(column=column):
                self.assertIn(column, identity.SHIPPED_COLUMNS_EXCEPT_MOBS_ID)

    def test_an_unmeasured_leg_is_treated_as_having_a_name_plate(
        self,
    ) -> None:
        """pf-adversary D6: the gate's fail-closed default.  ``_self_check``
        now checks the inputs BEFORE the gate reads them, so this drives the
        default directly rather than relying on which check runs first."""
        real = dict(identity.MULTI_SET_LEG_HAS_TIP_ROW)
        del identity.MULTI_SET_LEG_HAS_TIP_ROW[54]
        try:
            refusals = identity.multi_set_placement_refusals()
            self.assertTrue(refusals)
            self.assertTrue(
                all(row["condition"] == 2 for row in refusals), refusals)
            with self.assertRaises(identity.Bg3001IdentityError):
                identity._self_check()
        finally:
            identity.MULTI_SET_LEG_HAS_TIP_ROW.clear()
            identity.MULTI_SET_LEG_HAS_TIP_ROW.update(real)
        identity._self_check()

    def test_the_multi_set_gate_passes_on_this_scenes_own_pair(self) -> None:
        """Shape 2 of ``COO-DECISION 20260902_2146``: the six placements
        PASS the gate rather than being exempt from it."""
        self.assertEqual(identity.multi_set_placement_refusals(), ())
        first = identity.IDENTITIES[53]
        second = identity.SECOND_LEG_IDENTITIES[54]
        for column in identity.SHIPPED_COLUMNS_EXCEPT_MOBS_ID:
            with self.subTest(column=column):
                self.assertEqual(
                    getattr(first, column), getattr(second, column))
        self.assertNotEqual(first.mobs_n_id, second.mobs_n_id)
        self.assertEqual(first.outfit, identity.INVISIBLE_OUTFIT)
        self.assertEqual(second.outfit, identity.INVISIBLE_OUTFIT)
        self.assertEqual(
            identity.MULTI_SET_LEG_HAS_TIP_ROW, {53: False, 54: False})

    def test_the_multi_set_gate_refuses_each_shape_it_was_built_for(
        self,
    ) -> None:
        """Every condition of the decision, fired on a mutated table.

        The gate is the whole reason shipping the first leg was approved,
        so a green suite that never fires it proves nothing.  Each case
        restores the table afterwards, and the last assertion checks the
        restore rather than trusting it.
        """
        import dataclasses

        real_second = identity.SECOND_LEG_IDENTITIES[54]
        cases = {
            # Condition 1: a shipped column disagrees.
            "outfit_differs": dataclasses.replace(
                real_second, outfit="SP_005_000_000_N"),
            "level_differs": dataclasses.replace(real_second, level=1),
            "hp_differs": dataclasses.replace(real_second, max_hp=1),
            "usage_differs": dataclasses.replace(real_second, mob_usage=1),
            # Condition 2: the leg is visible / carries a name plate.
            "named": dataclasses.replace(real_second, name="Kraken"),
        }
        for label, mutant in cases.items():
            with self.subTest(case=label):
                identity.SECOND_LEG_IDENTITIES[54] = mutant
                try:
                    refusals = identity.multi_set_placement_refusals()
                    self.assertTrue(refusals, label)
                    self.assertEqual(
                        {row["placement_index"] for row in refusals},
                        {30, 31, 32, 33, 34, 35})
                    with self.assertRaises(identity.Bg3001IdentityError):
                        identity._self_check()
                finally:
                    identity.SECOND_LEG_IDENTITIES[54] = real_second

        # Condition 2, the other half: a leg WITH a MOBS_TIP row.
        identity.MULTI_SET_LEG_HAS_TIP_ROW[54] = True
        try:
            refusals = identity.multi_set_placement_refusals()
            self.assertTrue(refusals)
            self.assertTrue(
                all(row["condition"] == 2 for row in refusals), refusals)
        finally:
            identity.MULTI_SET_LEG_HAS_TIP_ROW[54] = False

        # Condition 1, the "unknown is not equal" half: a leg this module
        # has never heard of is refused, not assumed identical.
        identity.MULTI_SET_PLACEMENTS[30] = "53|99"
        try:
            refusals = identity.multi_set_placement_refusals()
            self.assertTrue(
                any(row["leg"] == 99 for row in refusals), refusals)
        finally:
            identity.MULTI_SET_PLACEMENTS[30] = "53|54"

        # A leg that is not a number at all is REFUSED, not skipped: a gate
        # that drops what it cannot parse passes the case it exists for.
        identity.MULTI_SET_PLACEMENTS[30] = "53|weather"
        try:
            refusals = identity.multi_set_placement_refusals()
            self.assertTrue(
                any(row["leg"] == "weather" for row in refusals), refusals)
        finally:
            identity.MULTI_SET_PLACEMENTS[30] = "53|54"

        self.assertEqual(identity.multi_set_placement_refusals(), ())
        identity._self_check()

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
        """Shape only, and this test says so out loud.

        WIDENED ROUND ``l6at2v`` (pf-adversary D2).  The real check --
        hashing the files -- lives in
        ``test_world_bg3001_identity_rederived.py``, which SKIPS on the
        Windows gate because the gate has no ``pf_bridge`` beside it.  So
        on the one machine that closes pull requests, this test is the
        entire digest claim, and as written it accepted the exact mutant
        the round before this one was built to kill: the adversary
        replaced a digest with ``0`` x 62 + ``ff`` and every check here
        passed by construction.

        The three assertions below kill a DEGENERATE digest -- all one
        character, or a run of one character with a short tail.  They
        cannot kill a plausible-looking wrong digest, and nothing that
        runs on the gate can: a hash is only evidence against the file it
        came from, and the file is not there.  Do not read a green here
        as "the pins are right".
        """
        self.assertEqual(len(identity.SOURCE_SHA256), 6)
        for path, digest in identity.SOURCE_SHA256.items():
            with self.subTest(path=path):
                self.assertEqual(len(digest), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in digest))
                # A real sha256 uses far more than two of the sixteen
                # nibbles; 0*62+"ff" uses two, and "0"*64 uses one.
                self.assertGreater(
                    len(set(digest)), 2,
                    "%s: this is not a digest, it is a placeholder" % path,
                )
        # And no two files hash the same, which is what a copy-paste of one
        # pinned digest onto another row looks like.
        self.assertEqual(
            len(set(identity.SOURCE_SHA256.values())),
            len(identity.SOURCE_SHA256),
        )


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
