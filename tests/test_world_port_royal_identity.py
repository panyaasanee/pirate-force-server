"""LANE-A / RE-128: who each bg0001 placement actually IS, checked end to end.

WHY THIS FILE EXISTS.  ``world_port_royal_identity`` is a table, and a table
that is only read by the module that ships it proves nothing: the failure mode
GT-078 put on the owner's screen was not a crash, it was 115 correctly placed
actors wearing the wrong people's faces and names.  Nothing in a byte count
catches that.  So this file checks the four things the owner can check with his
own eyes, in the order he checked them:

1.  Every ``MOBS.n_ID`` the owner filmed in Port Royal is reachable from this
    scene's crosswalk (32 of them, PANYA-EVIDENCE video2 2026-08-27 12:40).
2.  The two placement-level anchors the owner named by hand reproduce exactly -
    placement 1 is Columbus and placement 65 is Loie, not the other way round
    and not the slave market's Columbus, which was his exact complaint.
3.  No placement ships its Mob-Set number as an identity anywhere, which is the
    one rule ``world_scene_numbering`` refuses over.
4.  The census that a flagless boot builds out of all this assembles 108 of the
    115 frozen placements, says so on its own console line with the reason
    attached, and puts that same 108 in the collection header the client reads.

NONCLAIM, and it is the big one: nothing here says the client draws any of it.
Only a person in front of Port Royal can say that.  What this file can say is
that the bytes carry the identities the client's own tables give those
placements, instead of the scene file's Mob-Set numbers.
"""

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_port_royal_identity as identity  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.population import (  # noqa: E402
    PORT_ROYAL_SOURCE_COUNT,
    load_port_royal_placements,
)


# The seven of the frozen 115 placements that have no shippable identity, and
# the whole reason the census is 108 rather than 115.  Written out as a literal
# here on purpose: if this set ever changes, a human has to look at WHY before
# the number on the console line moves.
UNSHIPPABLE_PLACEMENT_INDICES = (0, 75, 86, 87, 145, 147, 148)
SHIPPED_CENSUS_COUNT = 108


class SceneCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(cls.legacy)
        }

    # --- what the owner saw on screen ------------------------------------

    def test_every_owner_video_confirmed_id_is_reachable_from_this_scene(
        self,
    ) -> None:
        """32/32, and the module refuses to import if it is not.

        This is the measurement that separates this crosswalk from the Mob-Set
        numbering it replaces: all 32 ids the owner tabulated off his own video
        are in this scene's CLINE leader set, and NONE of them is in the
        1..113 Mob-Set number range this tree used to ship.  Checked here as
        well as at import so the claim is visible to a reader of the tests, not
        only to whoever reads the traceback of a failed import.
        """
        reachable = {
            identity.resolve(template_id).mobs_n_id
            for template_id in range(1, 114)
            if identity.resolve(template_id) is not None
        }
        self.assertEqual(len(identity.OWNER_VIDEO_CONFIRMED_N_IDS), 32)
        missing = [
            n_id for n_id in identity.OWNER_VIDEO_CONFIRMED_N_IDS
            if n_id not in reachable
        ]
        self.assertEqual(missing, [])
        # ...and the negative half, which is the one that made the owner
        # reject GT-078: not one of those ids is a Mob-Set number of this
        # scene, so the old wire could not have produced any of them.
        self.assertTrue(
            all(n_id > 113 for n_id in identity.OWNER_VIDEO_CONFIRMED_N_IDS)
        )

    def test_the_two_owner_placement_anchors_reproduce_exactly(self) -> None:
        """A crosswalk that misses either of these is not this crosswalk.

        Placement 1 shipped as "Sebastian" and is Columbus (156).  Placement 65
        shipped as "Columbus" and is Loie (802) - the owner's complaint in his
        own words was that the Columbus he was being shown is the slave
        market's, not Port Royal's.  Both are resolved through the SAME public
        entry point the census uses, from the frozen placement row, so this
        cannot pass by reading the anchor dict back to itself.
        """
        self.assertEqual(identity.OWNER_PLACEMENT_ANCHORS, {1: 156, 65: 802})
        expected_names = {1: "Columbus", 65: "Loie"}
        for placement_index, n_id in identity.OWNER_PLACEMENT_ANCHORS.items():
            placement = self.placements[placement_index]
            resolved = identity.resolve(placement.template_id)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.mobs_n_id, n_id)
            self.assertEqual(resolved.name, expected_names[placement_index])
            # The name the frozen table carried for that row is NOT the name
            # that goes out any more.
            self.assertNotEqual(placement.source_name, resolved.name)

    def test_no_resolved_identity_is_its_own_mob_set_number(self) -> None:
        """The executable form of what ``world_scene_numbering`` refuses over.

        Checked over the whole shipped table (105 rows), not only the 81
        Mob-Set numbers today's placement source happens to use, because the
        crosswalk is a property of the scene and a wider placement source must
        not be able to reintroduce the defect.
        """
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())
        for template_id, resolved in sorted(identity._BY_TEMPLATE.items()):
            self.assertNotEqual(template_id, resolved.mobs_n_id)
            self.assertTrue(resolved.outfit)
            self.assertTrue(1 <= resolved.mobs_n_id <= 0xFFFF)

    def test_every_frozen_placement_is_resolved_or_refused_with_a_reason(
        self,
    ) -> None:
        """Never "not found": every Mob-Set number is in exactly one mapping.

        The seven refusals are pinned by index, by Mob-Set number and by
        reason.  A refusal without a reason is the thing this lane is forbidden
        to ship - a smaller world is fine, an unexplained one is not.
        """
        resolved = 0
        refused = []
        for placement in load_port_royal_placements(self.legacy):
            hit = identity.resolve(placement.template_id)
            reason = identity.unresolved_reason(placement.template_id)
            if hit is None:
                self.assertIsNotNone(reason)
                self.assertTrue(reason.strip())
                refused.append((placement.placement_index, reason))
            else:
                self.assertIsNone(reason)
                resolved += 1
        self.assertEqual(
            tuple(index for index, _reason in refused),
            UNSHIPPABLE_PLACEMENT_INDICES,
        )
        self.assertEqual(resolved, SHIPPED_CENSUS_COUNT)
        self.assertEqual(resolved + len(refused), PORT_ROYAL_SOURCE_COUNT)

    def test_the_census_reports_the_same_seven_refusals_with_the_same_reasons(
        self,
    ) -> None:
        """``unshippable_placements`` reads the same two sources the census
        reads, so a boot log and this table cannot disagree about who is
        missing.
        """
        dropped = world_population.unshippable_placements(self.legacy)
        self.assertEqual(
            tuple(item[0] for item in dropped), UNSHIPPABLE_PLACEMENT_INDICES)
        for placement_index, template_id, reason in dropped:
            self.assertEqual(
                template_id, self.placements[placement_index].template_id)
            self.assertEqual(
                (identity.UNRESOLVED[template_id][1]), reason)
        # The five distinct refusal reasons, so a future silent widening of
        # any one of them is visible here.
        self.assertEqual(
            sorted({item[2] for item in dropped}),
            [
                "CLINE leader 155 has no CONSTDATA MOBS row, so no s_OUTFIT "
                "(MOBS_TIP does name it: Port transportation)",
                "CLINE leader 819 has no CONSTDATA MOBS row, so no s_OUTFIT "
                "(MOBS_TIP names it: Tuna)",
                "CLINE leader 9107 has no CONSTDATA MOBS row, so no s_OUTFIT "
                "(MOBS_TIP names it: Jack)",
                "CLINE leader 937 has no CONSTDATA MOBS row, so no s_OUTFIT "
                "(MOBS_TIP names it: Mengsk)",
                "CLINE leader 942 has no CONSTDATA MOBS row, so no s_OUTFIT "
                "(MOBS_TIP has a name for it)",
                "CLINE leader is 0 (no creature)",
            ],
        )
        # Every refusal names what is MISSING (the s_OUTFIT avatar template a
        # client-side actor cannot be raised without), not merely that a
        # lookup failed - a refusal a reader cannot act on is half a refusal.
        for _index, _template_id, reason in dropped:
            self.assertTrue(
                "no CONSTDATA MOBS row" in reason
                or "no creature" in reason
                or "no s_OUTFIT" in reason,
                reason,
            )

    # --- refusals of the module's own inputs -----------------------------

    def test_resolve_refuses_anything_that_is_not_a_plain_int(self) -> None:
        for bad in ("31", 31.0, None, True, b"31"):
            with self.assertRaises(ValueError):
                identity.resolve(bad)
            with self.assertRaises(ValueError):
                identity.unresolved_reason(bad)
        # A Mob-Set number this scene does not define is simply absent from
        # both mappings, which is a different answer from a refusal.
        self.assertIsNone(identity.resolve(9999))
        self.assertIsNone(identity.unresolved_reason(9999))

    def test_the_console_token_tells_a_short_rung_from_a_short_census(
        self,
    ) -> None:
        """Two different shortfalls, two different lines, one grep.

        A 20-actor diagnostic rung is short because someone asked for 20;
        printing "95 unresolvable" beside it would be a lie in the one place a
        boot log is read for the truth.
        """
        # "composed", not "shipped": the token counts what this module put in
        # the collection, and a later splice on the runtime path can replace
        # entries afterwards (it does - field_mobs' hostile bodies).
        self.assertEqual(
            identity.identity_console_token(108, 7),
            "identity=CLINE:108 composed,7 unresolvable",
        )
        self.assertEqual(
            identity.identity_console_token(20, None),
            "identity=CLINE:20 composed",
        )
        identity.identity_console_token(108, 7).encode("cp874")
        for bad in ("108", 108.0, None):
            with self.assertRaises(ValueError):
                identity.identity_console_token(bad, None)
        with self.assertRaises(ValueError):
            identity.identity_console_token(108, "7")


class CensusOnThisCrosswalkTests(unittest.TestCase):
    """The build a flagless boot makes out of the table above."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    def test_a_full_census_assembles_108_and_says_so_three_ways(self) -> None:
        """Assembled, on the wire, and on the console - all three, or none.

        These three numbers can move independently: what the module put in the
        list, what the collection header tells the client, and what the boot
        log prints.  A shortfall that only appears in one of them is the shape
        of failure CHARTER-02's pre-send count exists to prevent.
        """
        generation = world_population.build_world_population(
            self.legacy, self.spawn, scene_id=1,
            count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )
        self.assertEqual(generation.actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(len(generation.indices), SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            world_population.wire_actor_count(generation), SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            generation.count_source,
            world_population.COUNT_SOURCE_IDENTITY_RESOLVED,
        )

        line = world_population.census_console_line(generation)
        line.encode("cp874")
        self.assertNotIn("\n", line)
        self.assertIn(
            f"assembled={SHIPPED_CENSUS_COUNT}/{PORT_ROYAL_SOURCE_COUNT}", line)
        self.assertIn(f"shortfall=identity_resolved={SHIPPED_CENSUS_COUNT}", line)
        self.assertIn(
            "identity=CLINE:%d composed,%d unresolvable"
            % (SHIPPED_CENSUS_COUNT,
               PORT_ROYAL_SOURCE_COUNT - SHIPPED_CENSUS_COUNT),
            line,
        )
        self.assertIn("bodies=ok", line)

    def test_no_census_entry_carries_its_own_mob_set_number_on_the_wire(
        self,
    ) -> None:
        """The whole point, asserted against the bytes that would be sent.

        ``make_npc_attr`` writes the identity as ``u8tag(0x0B, npc_mask)``
        followed by ``u16tag(0x12, template_id)`` (v141:1196-1197), so this
        looks for that exact two-tag sequence rather than a bare u16 that could
        match any coincidental pair of bytes inside a coordinate.
        """
        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        generation = world_population.build_world_population(
            self.legacy, self.spawn, scene_id=1)
        npc_mask = self.legacy.u8tag(0x0B, 0x01 | 0x04)
        checked = 0
        for index in generation.indices:
            placement = placements[index]
            resolved = identity.resolve(placement.template_id)
            self.assertIn(
                npc_mask + self.legacy.u16tag(0x12, resolved.mobs_n_id),
                generation.pc,
            )
            self.assertNotIn(
                npc_mask + self.legacy.u16tag(0x12, placement.template_id),
                generation.pc,
            )
            checked += 1
        self.assertEqual(checked, SHIPPED_CENSUS_COUNT)

    def test_an_unshippable_placement_is_refused_rather_than_downgraded(
        self,
    ) -> None:
        """The fallback IS the bug, so there is no fallback.

        ``_entry`` never sees these placements on the census path, because
        ``census_order`` drops them first.  A caller that assembles a census
        some other way must get an exception naming the placement and the
        reason - not an actor built on the Mob-Set number GT-078 disproved.
        """
        from pirateforce_foundation.world_population import _entry

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        for placement_index in UNSHIPPABLE_PLACEMENT_INDICES:
            with self.assertRaises(ValueError) as caught:
                _entry(self.legacy, placements[placement_index])
            self.assertIn(str(placement_index), str(caught.exception))
            self.assertIn("no shippable identity", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
