"""LANE-A BUILD-001: the bg0001 census staircase.

The load-bearing test in this file is the first one.  Rung 3 must be BYTE-
IDENTICAL to what the runtime already sends today; if it is not, then a failing
higher rung could be blamed on the encoder instead of on the actor count, and
the whole staircase stops measuring anything.

The second load-bearing test is ``test_the_census_is_thin_everywhere``.  It
pins the measured fact that this table is map-wide and sparse, which is the
reason this module refuses to promise a crowded screen.  If the table ever
becomes dense, that promise can change - loudly, here, not quietly in prose.
"""

import dataclasses
import json
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population
from pirateforce_foundation import world_port_royal_identity
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    build_port_royal_initial_population,
    load_port_royal_placements,
)
from pirateforce_foundation.world_population import (
    CENSUS_COUNT,
    WorldPopulationGeneration,
    apply_identity_override,
    census_console_line,
    census_shortfall_reason,
    dispatch_report,
    DEFAULT_ACTOR_COUNT,
    INITIAL_REAPPLY_MS,
    SHIPPED_ISOLATED_INDICES,
    STAIRCASE_RUNGS,
    build_staircase,
    build_world_population,
    census_order,
    effective_actor_count,
    nesting_break,
    production_allowed,
    staircase_report,
    test_only,
    unshippable_placements,
)


# AMENDMENT 2026-08-28 (LANE-A, RE-128 / CLINE identities).  115 is still the
# size of the frozen placement table (``CENSUS_COUNT``), and this lane still
# reports it as the target on every console line.  108 is what ASSEMBLES: seven
# of those placements have a Mob-Set number whose CLINE leader has no
# ``CONSTDATA MOBS`` row (or is 0, or has no avatar template), so they have no
# identity that can be shipped without going back to the Mob-Set number GT-078
# proved wrong.  They are dropped, loudly, with a reason each - see
# ``world_port_royal_identity.UNRESOLVED`` and
# ``world_population.unshippable_placements``.  Every "115" below that meant
# "the whole census as built" became this number; every "115" that meant "the
# size of the source table" stayed ``CENSUS_COUNT``.
SHIPPED_CENSUS_COUNT = 108
UNSHIPPABLE_PLACEMENT_INDICES = (0, 75, 86, 87, 145, 147, 148)


class WorldPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            cls.legacy.V134_PLAYER_X,
            cls.legacy.V134_PLAYER_Y,
            cls.legacy.V134_PLAYER_Z,
        )
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.far = (
            cls.legacy.V112_PLAYER_X,
            cls.legacy.V112_PLAYER_Y,
            cls.legacy.V112_PLAYER_Z,
        )

    # --- the control -----------------------------------------------------

    def test_rung_three_ships_resolved_identities_the_frozen_default_never_had(
        self,
    ) -> None:
        """Was ``..._differs_from_the_shipped_default_by_exactly_the_two_added_names``.

        SUPERSEDED HISTORY, kept because this project strikes through rather
        than erases.  ~~Rung 3 was byte-identical to
        ``make_v112_monster_shop_population_state()``.~~  ~~Then GT-078
        OWNER-REJECTED made ``_entry()`` put every placement's own
        ``source_name`` on the wire, so the surviving invariant was narrower:
        the ONLY bytes rung 3 added, anywhere, were the two UTF-16LE name tags
        for P0 and P91, and the pinned sizes were 564/577.~~

        SUPERSEDED 2026-08-28 (RE-128 / CLINE identities).  Byte-comparability
        with that frozen snapshot is gone for good, in two independent ways:

        1.  The frozen snapshot sends each placement's MOB-SET NUMBER (1, 31,
            91) where ``make_npc_attr``'s own docstring wants "the MOBS/template
            u16 at +0x78", and it sends the scene file's Mob-Set-numbered
            preset with it.  That substitution is exactly what GT-078 put on
            the owner's screen and had rejected.  Rung 3 now sends the resolved
            ``MOBS.n_ID``, that MOBS row's own ``s_OUTFIT`` and its
            ``MOBS_TIP`` name, so a byte-delta against the frozen bytes would
            be a delta against identities this lane has stopped shipping.
        2.  The frozen control set is not even rung 3's membership any more.
            P0's Mob-Set 1 resolves to CLINE leader 155, which has no
            ``CONSTDATA MOBS`` row, so P0 has no shippable identity and is
            dropped; the third slot goes to the nearest resolvable placement.

        This project does not edit ``make_v112_monster_shop_population_state``,
        so it stays exactly as it is and stays correct for what it describes.
        What is asserted here instead is the new rule, per entry: every member
        carries its resolved MOBS id, that row's avatar template and its own
        MOBS_TIP name, and no member carries its Mob-Set number as an identity.
        """
        from pirateforce_foundation import world_port_royal_identity as identity_table
        from pirateforce_foundation.population import load_port_royal_placements

        shipped_pc, _shipped_frame, shipped_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        rung = build_world_population(self.legacy, self.anchor, 3, scene_id=1)

        # The frozen control set is still (0, 30, 91) - this module did not
        # touch it - and rung 3 is no longer that set, for a recorded reason.
        self.assertEqual(
            tuple(row[0] for row in shipped_rows), SHIPPED_ISOLATED_INDICES)
        self.assertEqual(rung.indices, (30, 91, 1))
        self.assertIsNotNone(
            identity_table.unresolved_reason(
                {
                    placement.placement_index: placement
                    for placement in load_port_royal_placements(self.legacy)
                }[0].template_id
            )
        )

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        # NPCAttr writes the identity as u8tag(0x0B, npc_mask) followed by
        # u16tag(0x12, template_id) (v141:1196-1197), so this looks for the
        # exact two-tag sequence rather than a bare u16 that could match any
        # coincidental pair of bytes in the payload.
        for index in rung.indices:
            placement = placements[index]
            identity = identity_table.resolve(placement.template_id)
            self.assertIsNotNone(identity)
            id_tags = (
                self.legacy.u8tag(0x0B, 0x01 | 0x04)
                + self.legacy.u16tag(0x12, identity.mobs_n_id)
            )
            set_number_tags = (
                self.legacy.u8tag(0x0B, 0x01 | 0x04)
                + self.legacy.u16tag(0x12, placement.template_id)
            )
            self.assertIn(id_tags, rung.pc)
            self.assertNotIn(set_number_tags, rung.pc)
            self.assertIn(self.legacy.wstr_tag(identity.outfit), rung.pc)
            self.assertIn(self.legacy.wstr_tag(identity.name), rung.pc)
            # ...and the frozen snapshot carries none of those names, which is
            # the shortest true statement of what the owner will see change.
            self.assertNotIn(self.legacy.wstr_tag(identity.name), shipped_pc)

        # Pinned so a future encoder change is caught here too, not only in
        # scenarios/world_population_full_001.json.  Was (564, 577) while rung
        # 3 was (P0, P30, P91) carrying the frozen table's own names.
        self.assertEqual((rung.pc_bytes, rung.frame_bytes), (550, 563))

    def test_the_control_rungs_first_two_members_are_anchor_invariant(self) -> None:
        """Was ``test_the_control_rung_is_anchor_invariant``.

        ~~The whole rung-3 collection is identical at every anchor, which is
        what makes it a control - and also its only limitation.~~  SUPERSEDED
        2026-08-28 (RE-128): the frozen V112 3-actor control rung is NO LONGER
        anchor-invariant, because its P0 member has no shippable identity
        (Mob-Set 1 -> CLINE leader 155, no MOBS row) and is dropped from the
        census.  Two pinned members survive the filter, so the third slot is
        filled by the nearest resolvable placement - which is a function of the
        anchor, and really does differ between the anchors below.

        The honest invariant is therefore narrower: the FIRST TWO members are
        (30, 91) at every anchor, in that order.  Anything wider than that
        would be asserting a control this lane no longer has.
        """
        anchors = (self.anchor, self.spawn, self.far, (0.0, 0.0, 0.0))
        thirds = set()
        for anchor in anchors:
            rung = build_world_population(self.legacy, anchor, 3, scene_id=1)
            self.assertEqual(rung.indices[:2], (30, 91))
            thirds.add(rung.indices[2])
        # Non-vacuous: the part that is no longer invariant demonstrably varies.
        self.assertGreater(len(thirds), 1)

    # --- the honesty pin -------------------------------------------------

    def test_the_census_is_thin_everywhere(self) -> None:
        """Sending 115 does not crowd a view; this is why the module says so."""
        placements = census_order(self.legacy, self.spawn)
        x, y, z = self.spawn
        distances = sorted(
            ((item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2) ** 0.5
            for item in placements
        )
        self.assertLessEqual(sum(1 for d in distances if d < 2000.0), 2)
        self.assertGreater(distances[AUTHORITATIVE_COUNT - 1], 10000.0)
        self.assertGreater(distances[-1], 35000.0)

    # --- the staircase ---------------------------------------------------

    def test_every_rung_is_a_prefix_of_the_next(self) -> None:
        """Was ``... == STAIRCASE_RUNGS``, i.e. (3, 20, 60, 115).

        SUPERSEDED 2026-08-28 (RE-128): the top rung ASKS for 115 and
        ASSEMBLES 108, because seven of the frozen placements have no
        shippable identity and ``census_order`` drops them.  The rung sizes
        below are what was built, not what was requested - which is the whole
        point of ``build_world_population`` taking its count from the
        assembled list (CHARTER-02: a shortfall arrives with its reason
        attached, never as a quietly rewritten target).
        """
        built = build_staircase(self.legacy, self.anchor)
        self.assertEqual(
            tuple(item.actor_count for item in built), (3, 20, 60, SHIPPED_CENSUS_COUNT))
        self.assertEqual(STAIRCASE_RUNGS[:3], (3, 20, 60))
        self.assertEqual(STAIRCASE_RUNGS[-1], CENSUS_COUNT)
        for lower, higher in zip(built, built[1:]):
            self.assertEqual(higher.indices[: lower.actor_count], lower.indices)
            self.assertGreater(higher.frame_bytes, lower.frame_bytes)
        self.assertIsNone(nesting_break(built))

    def test_nesting_break_catches_rungs_built_at_different_anchors(self) -> None:
        """The real threat: one boot per rung means one anchor per rung."""
        low = build_world_population(self.legacy, self.anchor, 20, scene_id=1)
        high_same = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        self.assertIsNone(nesting_break((low, high_same)))

        # An anchor on the far side of the table: at ~30,000 units away its
        # nearest-60 no longer contains the first anchor's nearest-20.
        elsewhere = (21694.0703125, -5071.00048828125, 0.0)
        high_elsewhere = build_world_population(self.legacy, elsewhere, 60, scene_id=1)
        dropped = nesting_break((low, high_elsewhere))
        self.assertIsNotNone(dropped)
        self.assertTrue(set(dropped) <= set(low.indices))
        self.assertTrue(set(dropped).isdisjoint(set(high_elsewhere.indices)))

    def test_nesting_break_refuses_input_it_cannot_read(self) -> None:
        low = build_world_population(self.legacy, self.anchor, 20, scene_id=1)
        high = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        for bad in ((), [low, high], None):
            with self.assertRaises(ValueError):
                nesting_break(bad)
        with self.assertRaises(ValueError):
            nesting_break((high, low))

    def test_top_rung_is_the_whole_census_minus_the_unshippable_seven(self) -> None:
        """Was ``test_top_rung_is_the_whole_census_without_repeats`` at 115.

        ~~top.actor_count == CENSUS_COUNT.~~  SUPERSEDED 2026-08-28 (RE-128):
        it is 108, and the seven that are missing are named here rather than
        left as a number, so a future drift in either direction is a failure
        with a list attached.
        """
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(top.actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(len(set(top.indices)), SHIPPED_CENSUS_COUNT)
        dropped = unshippable_placements(self.legacy)
        self.assertEqual(
            tuple(item[0] for item in dropped), UNSHIPPABLE_PLACEMENT_INDICES)
        self.assertEqual(
            len(top.indices) + len(dropped), CENSUS_COUNT)
        self.assertTrue(
            set(UNSHIPPABLE_PLACEMENT_INDICES).isdisjoint(set(top.indices)))

    def test_top_rung_carries_a_resolved_identity_the_frozen_golden_115_never_had(
        self,
    ) -> None:
        """Was ``..._differs_from_the_frozen_golden_115_by_every_members_own_name``.

        v141:1441 builds a 115-member snapshot and this one used to be that
        one, member for member.  ~~Was "by P30 alone", when P30's BasicAttr
        name was the only name this module put on the wire; then GT-078 widened
        it to the sum of every top-rung member's own frozen ``source_name``
        tag.~~

        SUPERSEDED 2026-08-28 (RE-128 / CLINE identities).  A byte-delta
        against ``make_v62_port_royal_population_snapshot`` cannot state
        anything true any more: that snapshot encodes each placement's Mob-Set
        number as its identity and the scene file's own preset with it, which
        is the pair the owner rejected on sight in GT-078, and it is seven
        members larger than this census because it does not know that seven of
        those Mob-Set numbers resolve to no MOBS row at all.  The frozen
        function is not edited and stays exactly correct for what it describes.

        The invariant asserted instead is the new rule, stated plainly: the top
        rung is the golden membership minus the seven unshippable placements,
        every entry carries the resolved ``MOBS.n_ID`` and that row's own
        ``MOBS_TIP`` name, and no entry reproduces its Mob-Set number as an
        identity.
        """
        from pirateforce_foundation import world_port_royal_identity as identity_table
        from pirateforce_foundation.population import load_port_royal_placements

        _label, golden_pc, _frame, chosen = (
            self.legacy.make_v62_port_royal_population_snapshot(*self.anchor)
        )
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(
            set(top.indices),
            {row[0] for row in chosen} - set(UNSHIPPABLE_PLACEMENT_INDICES),
        )

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        named = 0
        for index in top.indices:
            placement = placements[index]
            identity = identity_table.resolve(placement.template_id)
            self.assertIsNotNone(identity)
            self.assertNotEqual(identity.mobs_n_id, placement.template_id)
            id_tags = (
                self.legacy.u8tag(0x0B, 0x01 | 0x04)
                + self.legacy.u16tag(0x12, identity.mobs_n_id)
            )
            self.assertIn(id_tags, top.pc)
            if identity.name:
                named += 1
                self.assertIn(self.legacy.wstr_tag(identity.name), top.pc)
                # The golden snapshot names nobody, so every one of these tags
                # is a name line the player did not have yesterday.
                self.assertNotIn(self.legacy.wstr_tag(identity.name), golden_pc)
        # Exactly one census member ships without a name: placement 132, whose
        # Mob-Set 103 resolves to n_ID 917, which has a MOBS row (so it can be
        # raised) but no MOBS_TIP row (so it has no label).  It ships nameless
        # rather than borrowing a name - recorded, not papered over.
        self.assertEqual(named, SHIPPED_CENSUS_COUNT - 1)
        self.assertEqual(
            [
                index for index in top.indices
                if not identity_table.resolve(
                    placements[index].template_id).name
            ],
            [132],
        )

    def test_every_member_is_now_absent_from_the_golden_115_because_every_member_is_named(
        self,
    ) -> None:
        """Was "every member but P30 appears verbatim"; GT-078's fix widened this to all 115.

        Stronger than the frame-size delta above, and it can fail alone: a
        total-size comparison passes if two members drift in offsetting
        directions, so this looks for each census entry's exact bytes INSIDE
        the payload the frozen V62 builder produced.  Before the GT-078 name
        fix only P30 carried a name, so only P30's entry was absent from the
        nameless golden snapshot.  Now ``_entry()`` puts every placement's own
        ``source_name`` on the wire, and V62 never names anyone (not even
        P30), so EVERY entry this module builds now differs from its golden
        counterpart - "some absent" was the half-fixed world; "all absent" is
        the one after this fix.

        The comparison deliberately calls ``make_v62_port_royal_population_
        snapshot`` and searches its real output.  An earlier version of this
        test rebuilt a "golden" entry here using ``HEADINGS`` imported from the
        module under test, which made it agree with itself: zeroing HEADINGS
        changed 86 of 115 actors on the wire and the test still passed.

        NONCLAIM: a substring miss proves each entry's bytes are absent, not
        that the collection orders them the way V62 orders them.  Ordering is
        not compared here, and no other test compares it either.

        AMENDMENT 2026-08-28 (RE-128 / CLINE identities).  The reason every
        entry is absent got wider - it is no longer only the name tag, it is
        also the identity u16 and the avatar template, which now come from the
        resolved ``MOBS`` row instead of from the Mob-Set number V62 sends.
        The ITERATION had to change too: ``_entry()`` now REFUSES a placement
        with no shippable identity rather than falling back to its Mob-Set
        number, so this walks the census as ``census_order`` built it (108)
        instead of walking all 115 rows of the frozen table.  The seven it no
        longer walks are asserted to be exactly the ones that were dropped, so
        this cannot quietly shrink further.
        """
        from pirateforce_foundation.world_population import _entry

        _label, golden_pc, _frame, _chosen = (
            self.legacy.make_v62_port_royal_population_snapshot(*self.anchor)
        )
        placements = census_order(self.legacy, self.anchor)
        absent = [
            placement.placement_index
            for placement in placements
            if _entry(self.legacy, placement) not in golden_pc
        ]
        self.assertEqual(absent, [placement.placement_index for placement in placements])
        self.assertEqual(len(absent), SHIPPED_CENSUS_COUNT)
        from pirateforce_foundation.population import load_port_royal_placements

        self.assertEqual(
            set(absent) | set(UNSHIPPABLE_PLACEMENT_INDICES),
            {
                placement.placement_index
                for placement in load_port_royal_placements(self.legacy)
            },
        )

    def test_every_members_resolved_name_reaches_the_wire_as_a_utf16_basic_name_tag(
        self,
    ) -> None:
        """Was ``test_every_members_own_name_reaches_the_wire_...``.

        GT-078 OWNER-REJECTED, direct: no client screenshot ever showed a
        name line under any NPC in town, only a title line.  This is the test
        that would have caught it - there was none before this lane's fix
        (a static-RE grep of tests/test_population.py and
        tests/test_world_population.py for "basic_name"/"source_name" found
        no coverage of this path at all).

        Reuses the codebase's own frozen tag helper (``legacy.wstr_tag``)
        rather than hand-rolling UTF-16LE, the same way
        tests/test_field_mobs.py checks ``mob.display_name`` reaches the
        wire.

        SUPERSEDED 2026-08-28 (RE-128 / CLINE identities).  ~~The name on the
        wire is the frozen placement row's own ``source_name``, checked for
        P0, P91 and P35.~~  It is now the ``MOBS_TIP`` name of the RESOLVED
        ``MOBS.n_ID``, so that the id, the avatar template and the label in one
        entry all describe the same person; the placement's ``source_name`` is
        a Mob-Set-numbered label and is no longer sent.  P0 is not checkable at
        all any more - it has no shippable identity - so the three placements
        below are the two surviving pinned members (P30, P91) plus the owner's
        own confirmed anchor P65, which the owner named specifically: it used
        to ship as "Columbus" (the slave market's) and now ships as 802 Loie.
        """
        from pirateforce_foundation import world_port_royal_identity as identity_table
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import _entry

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        for index in (30, 91, 65):
            placement = placements[index]
            identity = identity_table.resolve(placement.template_id)
            self.assertIsNotNone(identity)
            self.assertTrue(identity.name)
            entry = _entry(self.legacy, placement)
            self.assertIn(self.legacy.wstr_tag(identity.name), entry)
            # ...and the Mob-Set-numbered label the table carries for the same
            # row does NOT reach the wire, which is the half the owner rejected.
            if placement.source_name != identity.name:
                self.assertNotIn(
                    self.legacy.wstr_tag(placement.source_name), entry)

    def test_p30_now_ships_its_resolved_identity_not_the_measured_override_name(
        self,
    ) -> None:
        """Was ``test_p30_uses_the_measured_override_name_not_the_tables_own``.

        THE OLD TEST'S REASONING, kept because the premise it guarded is gone
        rather than wrong: ~~pf-adversary (round pqx4fj-1): today
        ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS[30].source_name`` and
        ``V119_P30_TARGET_NAME`` happen to both be "Tornado Eagle", so the
        ``is_monster`` branch in ``_entry()`` is untestable coincidence, not a
        proven precedence - deleting the branch entirely passes every other
        test in this file unchanged.  This test forces the two values apart
        with a drifted legacy stand-in and proves the override wins.~~

        SUPERSEDED 2026-08-28 (RE-128 / CLINE identities).  There is no name
        branch left to guard: ``_entry()`` sends no ``V119_P30_TARGET_NAME``
        for anybody.  "Tornado Eagle" was P30's name UNDER THE MOB-SET
        NUMBERING, and P30's Mob-Set 31 resolves to ``MOBS.n_ID`` 248, Da
        Vinci, whom the owner filmed standing beside 904 Chalais - which is
        P91, 436 units away, the 0.1 percentile of this scene's pairwise
        distances.  So the new intended rule is the one pinned here: P30 ships
        248 / P_MALE_018_000_DAVINCI / "Da Vinci".

        The HP override is a different measurement and is deliberately
        untouched, so it is pinned here too - if a future edit collapses the
        ``is_monster`` branch entirely, this is what still catches it.
        """
        from pirateforce_foundation import world_port_royal_identity as identity_table
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import (
            DEFAULT_HP,
            SHIPPED_MONSTER_INDEX,
            _entry,
        )

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        p30 = placements[SHIPPED_MONSTER_INDEX]
        # The frozen table still says what it always said; this lane just
        # stopped treating that label as an identity.
        self.assertEqual(p30.source_name, self.legacy.V119_P30_TARGET_NAME)

        identity = identity_table.resolve(p30.template_id)
        self.assertEqual(
            (identity.mobs_n_id, identity.outfit, identity.name),
            (248, "P_MALE_018_000_DAVINCI", "Da Vinci"),
        )
        entry = _entry(self.legacy, p30)
        self.assertIn(self.legacy.wstr_tag("Da Vinci"), entry)
        self.assertIn(self.legacy.wstr_tag("P_MALE_018_000_DAVINCI"), entry)
        self.assertNotIn(
            self.legacy.wstr_tag(self.legacy.V119_P30_TARGET_NAME), entry)
        self.assertNotIn(
            self.legacy.u8tag(0x0B, 0x01 | 0x04)
            + self.legacy.u16tag(0x12, p30.template_id),
            entry,
        )

        # The HP override survives untouched: P30 is still the one member
        # built with the measured V117 hp instead of the default 100.
        drifted = types.SimpleNamespace(**vars(self.legacy))
        drifted.V117_P30_EXACT_HP = 4242
        drifted_entry = _entry(drifted, p30)
        self.assertIn(drifted.u32tag(0x14, 4242), drifted_entry)
        self.assertNotIn(drifted.u32tag(0x14, DEFAULT_HP), drifted_entry)
        self.assertIn(
            self.legacy.u32tag(0x14, self.legacy.V117_P30_EXACT_HP), entry)

    def test_identities_follow_the_frozen_actor_identity_rule(self) -> None:
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(
            top.actor_identities,
            tuple(0x2000 + index + 1 for index in top.indices),
        )

    def test_build_is_deterministic(self) -> None:
        first = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        second = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        self.assertEqual(first.pc, second.pc)
        self.assertEqual(first.indices, second.indices)

    def test_order_is_pinned_first_then_nearest_first(self) -> None:
        """Was ``placements[:3] == SHIPPED_ISOLATED_INDICES``.

        SUPERSEDED 2026-08-28 (RE-128): the pinned prefix is the pinned set
        MINUS whatever the identity filter dropped from it, which today is P0.
        So the prefix is (30, 91) and the nearest-first tail starts one place
        earlier.  The pinned set itself is unchanged and still refused if it
        drifts (``_pinned_indices``).
        """
        placements = census_order(self.legacy, self.anchor)
        self.assertEqual(
            tuple(item.placement_index for item in placements[:2]),
            tuple(
                index for index in SHIPPED_ISOLATED_INDICES
                if index not in UNSHIPPABLE_PLACEMENT_INDICES
            ),
        )
        x, y, z = self.anchor
        distances = [
            (item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2
            for item in placements[2:]
        ]
        self.assertEqual(distances, sorted(distances))

    def test_rung_twenty_now_differs_from_v94_by_the_placements_v94_cannot_name(
        self,
    ) -> None:
        """Was ``test_rung_twenty_membership_coincides_with_v94_at_this_anchor``.

        ~~A weak coincidence, recorded as one - not a second control.  At the
        V134 anchor the pinned three happen to fall inside V94's nearest-20, so
        the SETS match.~~  SUPERSEDED 2026-08-28 (RE-128): they no longer
        match, and the difference is exactly the interesting one.  Four of
        V94's nearest-20 (P0, P86, P87, P145) have no shippable identity, so
        this rung drops them and reaches four placements deeper into the
        nearest-first order to still send twenty actors.  Everything the old
        test said about frames and orders never matching is unchanged.
        """
        v94 = build_port_royal_initial_population(self.legacy, self.anchor)
        rung = build_world_population(self.legacy, self.anchor, AUTHORITATIVE_COUNT, scene_id=1)
        only_v94 = set(v94.current_indices) - set(rung.indices)
        only_rung = set(rung.indices) - set(v94.current_indices)
        self.assertEqual(only_v94, {0, 86, 87, 145})
        self.assertTrue(only_v94 <= set(UNSHIPPABLE_PLACEMENT_INDICES))
        self.assertEqual(len(only_rung), len(only_v94))
        self.assertTrue(
            only_rung.isdisjoint(set(UNSHIPPABLE_PLACEMENT_INDICES)))
        self.assertEqual(rung.actor_count, AUTHORITATIVE_COUNT)
        self.assertNotEqual(rung.pc, v94.pc)
        self.assertNotEqual(rung.indices, v94.current_indices)

    # --- the default this lane exists to ship ----------------------------

    def test_module_declares_itself_a_shipping_lane(self) -> None:
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        self.assertEqual(DEFAULT_ACTOR_COUNT, CENSUS_COUNT)

    def test_recording_a_measured_ceiling_actually_changes_what_callers_send(
        self,
    ) -> None:
        """The whole point of the constant: editing it must change behaviour."""
        original = world_population.MEASURED_CLIENT_ACTOR_CEILING
        try:
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = 20
            self.assertEqual(effective_actor_count(), 20)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = CENSUS_COUNT
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
        finally:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = original
        self.assertEqual(effective_actor_count(), CENSUS_COUNT)

    def test_effective_count_validates_an_explicit_ceiling(self) -> None:
        self.assertEqual(effective_actor_count(None), CENSUS_COUNT)
        self.assertEqual(effective_actor_count(60), 60)
        for bad in (0, -1, CENSUS_COUNT + 1, "60", 60.0, True):
            with self.assertRaises(ValueError):
                effective_actor_count(bad)

    def test_report_pins_sizes_and_membership(self) -> None:
        """``counts == list(STAIRCASE_RUNGS)`` until RE-128; see
        ``test_every_rung_is_a_prefix_of_the_next`` for why the top rung
        assembles 108 when 115 is asked for.  ``census_count`` stays 115: it is
        the size of the source table, which did not change.
        """
        report = staircase_report(self.legacy, self.anchor)
        self.assertEqual(report["census_count"], CENSUS_COUNT)
        self.assertEqual(report["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        counts = [rung["actor_count"] for rung in report["rungs"]]
        self.assertEqual(counts, [3, 20, 60, SHIPPED_CENSUS_COUNT])
        for rung in report["rungs"]:
            self.assertEqual(len(rung["indices"]), rung["actor_count"])
        sizes = [rung["frame_bytes"] for rung in report["rungs"]]
        self.assertEqual(sizes, sorted(sizes))

    def test_pin_file_still_describes_what_the_module_builds(self) -> None:
        """The scenario file is a PIN, not a switch: no flag reads it.

        Both anchors are pinned on purpose - the documented V134 anchor and the
        anchor a new character actually spawns at - so a tester comparing an
        observed frame to the pin is comparing against a position that exists.
        """
        pinned = json.loads(
            (ROOT / "scenarios" / "world_population_full_001.json")
            .read_text(encoding="ascii")
        )
        self.assertTrue(pinned["production_allowed"])
        self.assertFalse(pinned["test_only"])
        population = pinned["population"]
        self.assertEqual(population["default_actor_count"], CENSUS_COUNT)
        self.assertEqual(population["source_count"], CENSUS_COUNT)
        self.assertEqual(population["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        self.assertEqual(
            population["control_rung_indices"], list(SHIPPED_ISOLATED_INDICES)
        )
        from pirateforce_foundation.population import PORT_ROYAL_SOURCE_SHA256

        self.assertEqual(population["source_sha256"], PORT_ROYAL_SOURCE_SHA256)

        # AMENDMENT 2026-08-28 (RE-128).  The pin now has to describe the two
        # numbers that differ - what is ASKED for and what ASSEMBLES - and the
        # seven placements that account for the difference, by index, Mob-Set
        # number and reason.  Read from the module rather than from a second
        # hand-written list, so the file cannot drift away from the code.
        self.assertEqual(
            population["assembled_actor_count_at_default"], SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            population["count_source_when_short"],
            world_population.COUNT_SOURCE_IDENTITY_RESOLVED,
        )
        self.assertEqual(
            [
                (item["placement_index"], item["mob_set_number"], item["reason"])
                for item in population["unshippable_placements"]
            ],
            [tuple(item) for item in unshippable_placements(self.legacy)],
        )
        self.assertEqual(
            tuple(
                item["placement_index"]
                for item in population["unshippable_placements"]
            ),
            UNSHIPPABLE_PLACEMENT_INDICES,
        )

        anchors = pinned["staircase"]["reference_anchors"]
        self.assertEqual(len(anchors), 2)
        expected_anchors = {
            "v141_V134_PLAYER_XYZ": self.anchor,
            "v141_V135_PLAYER_XYZ_new_character_spawn": self.spawn,
        }
        for block in anchors:
            xyz = expected_anchors[block["label"]]
            self.assertEqual((block["x"], block["y"], block["z"]), xyz)
            report = staircase_report(self.legacy, xyz)
            self.assertEqual(
                [
                    {
                        "actor_count": rung["actor_count"],
                        "pc_bytes": rung["pc_bytes"],
                        "frame_bytes": rung["frame_bytes"],
                        "indices": rung["indices"],
                    }
                    for rung in report["rungs"]
                ],
                block["rungs"],
            )

    def test_pin_file_cannot_be_loaded_as_a_population_scenario(self) -> None:
        """It declares production_allowed; the loader only accepts test_only."""
        from pirateforce_foundation.population_scenario import (
            load_population_scenario,
        )

        with self.assertRaises(ValueError):
            load_population_scenario(
                ROOT / "scenarios" / "world_population_full_001.json"
            )

    # --- refusals --------------------------------------------------------

    def test_actor_count_is_bounded_by_the_census(self) -> None:
        for bad in (0, -1, CENSUS_COUNT + 1, 3.0, "3", None, True):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, self.anchor, bad, scene_id=1)

    def test_anchor_must_be_an_exact_finite_triple(self) -> None:
        for bad in (
            None, (), (0.0, 0.0), (0.0, 0.0, 0.0, 0.0), [0.0, 0.0, 0.0],
            (0.0, 0.0, float("nan")), (0.0, 0.0, float("inf")),
            (0.0, 0.0, "0"), (0.0, 0.0, 1e39),
        ):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, bad, 3, scene_id=1)

    def test_rungs_must_be_a_strictly_increasing_tuple_of_counts(self) -> None:
        for bad in (
            (), [3, 20], (20, 3), (3, 3), (3, 20, 20),
            (3, "20"), (3, None), (3, 3.0), (0, 20), (3, CENSUS_COUNT + 1),
        ):
            with self.assertRaises(ValueError):
                build_staircase(self.legacy, self.anchor, bad)

    def test_control_rung_refuses_to_measure_a_drifted_default(self) -> None:
        """If the shipped isolated set changes, rung 3 stops being the control."""
        drifted = types.SimpleNamespace(
            **{
                name: getattr(self.legacy, name)
                for name in (
                    "NPC_ATTR", "MOVEMENT_ATTR", "GSCN_RUNTIME_PROTOCOL_RES",
                    "V94_LOCAL_LIMIT", "V94_REFRESH_DISTANCE",
                    "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS",
                    "make_npc_attr", "make_remote_movement_attr",
                    "make_remote_actor_entry", "make_runtime_remote_actors",
                    "V112_MONSTER_INDEX", "V117_P30_EXACT_HP",
                    "V119_P30_TARGET_NAME",
                )
            }
        )
        drifted.V112_TEST_INDICES = (0, 30, 92)
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)
        drifted.V112_TEST_INDICES = self.legacy.V112_TEST_INDICES
        drifted.V112_MONSTER_INDEX = 31
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)


class CensusDispatchCountTests(unittest.TestCase):
    """CHARTER-02 replaced the staircase with a pre-send count.

    The ruling has a hard half: the number that goes out must never quietly
    become something other than the whole census.  "Quietly" includes a frame
    that SAYS 115 while carrying fewer bodies, which is why these tests care
    about the wire header and the body bytes and not only about the list this
    module built.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    def test_the_full_census_reports_its_shortfall_with_the_identity_reason(
        self,
    ) -> None:
        """Was ``test_the_full_census_reports_no_shortfall``.

        ~~A full-census build assembles 115, so there is nothing to report.~~
        SUPERSEDED 2026-08-28 (RE-128): it assembles 108, and CHARTER-02's hard
        half applies - the shortfall arrives with its reason attached, and the
        caller's stated ``full_census`` reason is REPLACED by the one that is
        actually true (``identity_resolved``) rather than left saying 115 went
        out.  The parts that still hold - wire count agrees with the assembled
        count, every body is intact - are asserted unchanged.
        """
        generation = build_world_population(
            self.legacy, self.spawn,
            scene_id=1, count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )
        report = dispatch_report(generation)
        self.assertEqual(report["assembled_count"], SHIPPED_CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], SHIPPED_CENSUS_COUNT)
        self.assertEqual(report["census_count"], CENSUS_COUNT)
        self.assertTrue(report["counts_agree"])
        self.assertTrue(report["bodies_intact"])
        self.assertEqual(
            report["count_source"], world_population.COUNT_SOURCE_IDENTITY_RESOLVED)
        self.assertEqual(
            report["shortfall_reason"], f"identity_resolved={SHIPPED_CENSUS_COUNT}")
        self.assertEqual(report["initial_reapply_ms"], INITIAL_REAPPLY_MS)

    def test_the_wire_count_is_read_back_out_of_the_bytes(self) -> None:
        """Not copied from the request - decoded from the header the client reads.

        AMENDMENT 2026-08-28 (RE-128): asking for ``CENSUS_COUNT`` (115) now
        puts 108 in the header, because 108 bodies follow.  That is the whole
        point of the count being read back out of the bytes: telling the client
        115 while sending 108 bodies is the stream-tail misalignment this
        client answers with ErrorData=28317.
        """
        for count in (1, 3, 20, SHIPPED_CENSUS_COUNT):
            generation = build_world_population(
                self.legacy, self.spawn, count, scene_id=1)
            self.assertEqual(
                world_population.wire_actor_count(generation), count)
        asked_for_everything = build_world_population(
            self.legacy, self.spawn, CENSUS_COUNT, scene_id=1)
        self.assertEqual(
            world_population.wire_actor_count(asked_for_everything),
            SHIPPED_CENSUS_COUNT,
        )
        # and it refuses bytes that are not that header rather than guessing
        broken = build_world_population(self.legacy, self.spawn, 3, scene_id=1)
        with self.assertRaises(ValueError):
            world_population.wire_actor_count(
                dataclasses.replace(broken, pc=b"\x00" * 8))

    def test_a_frame_that_lost_a_body_cannot_print_a_clean_line(self) -> None:
        """The defect this report exists to catch, reproduced end to end.

        A dropped actor body leaves the collection header saying N while N-1
        bodies follow - a RuntimeRes stream-tail misalignment, which is what
        ErrorData=28317 answers.  A report that counted only its own input
        would print 115/115 over exactly this frame.
        """
        honest = build_world_population(self.legacy, self.spawn, scene_id=1)
        last = honest.entry_bytes[-1]
        maimed = dataclasses.replace(honest, pc=honest.pc[:-last])
        report = dispatch_report(maimed)
        # 115 until RE-128; the default build now assembles 108 (seven
        # placements have no shippable identity).  The defect this test
        # reproduces is unchanged: header says N, N-1 bodies follow.
        self.assertEqual(report["assembled_count"], SHIPPED_CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], SHIPPED_CENSUS_COUNT)
        self.assertFalse(report["bodies_intact"])
        self.assertEqual(
            report["body_bytes"], report["entry_bytes_total"] - last)
        self.assertIn("bodies=SHORT", census_console_line(maimed))
        self.assertIn("bodies=ok", census_console_line(honest))

    def test_an_actor_that_encodes_to_nothing_is_refused_at_build(self) -> None:
        """The same defect one step earlier, where it can still be prevented."""
        original = world_population._entry
        calls = []

        def drop_one(legacy, placement):
            calls.append(placement.placement_index)
            if len(calls) == 2:
                return b""
            return original(legacy, placement)

        world_population._entry = drop_one
        try:
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, self.spawn, 3, scene_id=1)
        finally:
            world_population._entry = original

    def test_the_census_refuses_to_be_built_for_another_scene(self) -> None:
        """The acting half of the cross-build-order guard.

        world_scene_travel.population_source() reports which scene the census
        is true in; this refuses to build it anywhere else, so a caller that
        never asks still cannot deliver bg0001 dock NPCs into another map.
        """
        for scene in (2, 278, 0, None, "1"):
            with self.assertRaises(ValueError):
                build_world_population(
                    self.legacy, self.spawn, 3, scene_id=scene)
        with self.assertRaises(TypeError):
            build_world_population(self.legacy, self.spawn, 3)

    def test_the_reason_for_a_short_send_is_recorded_not_inferred(self) -> None:
        """One number, two meanings - so the caller states which one it meant."""
        deliberate = build_world_population(
            self.legacy, self.spawn, 20, scene_id=1,
            count_source=world_population.COUNT_SOURCE_CALLER,
        )
        self.assertEqual(
            dispatch_report(deliberate)["shortfall_reason"],
            "caller_requested=20",
        )
        capped = build_world_population(
            self.legacy, self.spawn, 20, scene_id=1,
            count_source=world_population.COUNT_SOURCE_MEASURED_CEILING,
        )
        self.assertEqual(
            dispatch_report(capped)["shortfall_reason"],
            "measured_client_ceiling=20",
        )
        self.assertIsNone(census_shortfall_reason(CENSUS_COUNT))
        with self.assertRaises(ValueError):
            census_shortfall_reason(20, "because_i_said_so")

    def test_the_dispatch_count_names_its_own_source(self) -> None:
        self.assertEqual(
            world_population.census_count_for_dispatch(),
            (CENSUS_COUNT, world_population.COUNT_SOURCE_FULL_CENSUS),
        )
        original = world_population.MEASURED_CLIENT_ACTOR_CEILING
        try:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = 60
            self.assertEqual(
                world_population.census_count_for_dispatch(),
                (60, world_population.COUNT_SOURCE_MEASURED_CEILING),
            )
        finally:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = original

    def test_the_console_line_is_one_ascii_line_carrying_the_count(self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn,
            scene_id=1, count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )
        line = census_console_line(generation)
        line.encode("ascii")
        self.assertNotIn("\n", line)
        # Was "assembled=115/115 wire=115 shortfall=none source=full_census".
        # SUPERSEDED 2026-08-28 (RE-128): the boot line now says what really
        # went out and why fewer than the target did, in one line a grep can
        # read - 108 of the 115-row source, dropped by the identity filter.
        self.assertIn(f"assembled={SHIPPED_CENSUS_COUNT}/{CENSUS_COUNT}", line)
        self.assertIn(f"wire={SHIPPED_CENSUS_COUNT}", line)
        self.assertIn(f"shortfall=identity_resolved={SHIPPED_CENSUS_COUNT}", line)
        self.assertIn("source=identity_resolved", line)
        self.assertIn(f"reapply_ms={INITIAL_REAPPLY_MS}", line)
        # The identity token names the crosswalk and both halves of the count,
        # so one grep for "identity=CLINE" finds every boot.
        self.assertIn(
            f"identity=CLINE:{SHIPPED_CENSUS_COUNT} composed,"
            f"{CENSUS_COUNT - SHIPPED_CENSUS_COUNT} unresolvable",
            line,
        )
        short = census_console_line(
            build_world_population(self.legacy, self.spawn, 3, scene_id=1))
        self.assertIn("assembled=3/115", short)
        self.assertIn("shortfall=caller_requested=3", short)
        # A rung SMALLER than the whole census is short because someone asked
        # for three, so the token names the source without claiming 112 are
        # unresolvable.
        # AMENDED 2026-08-29 (LANE-A, round mcxexp): the identity token is no
        # longer last on the line - the undressable roster is appended after
        # it - so this pins the token and its position relative to what
        # follows instead of pinning the end of the line to it.  The two
        # tokens say different things and a reader must not read one as the
        # other: "composed" counts what went into THIS rung, "undressable"
        # counts what NO rung of this scene can dress.
        self.assertIn("identity=CLINE:3 composed |", short)
        self.assertNotIn("unresolvable", short)
        # AMENDED AGAIN 2026-08-29 (LANE-A, round tz2eri): this assertion said
        # ``endswith`` while the comment above it said "position relative to
        # what follows", and the two stopped agreeing the moment a field was
        # appended after the roster (``ceiling=``, RE-149's verdict).  An
        # ``endswith`` on the last field of a line that is DESIGNED to be
        # extended by appending is a test that fails for the one change it
        # should be indifferent to, so it now pins what it always meant: the
        # roster is present, whole, and sits after the identity token.
        roster = world_population.undressable_console_token(
            build_world_population(self.legacy, self.spawn, 3, scene_id=1))
        self.assertIn(roster, short)
        self.assertLess(
            short.index("identity=CLINE:3 composed"), short.index(roster),
            f"undressable roster does not follow the identity token: {short!r}",
        )
        # A three-actor rung is short because a caller asked for three; the
        # undressable roster beside it is a property of the scene's table and
        # is the same seven on every rung, which is why it is worded as a
        # roster and not as this frame's shortfall.
        self.assertIn("undressable=7 ", short)

    def test_the_report_refuses_anything_that_is_not_a_generation(self) -> None:
        for bad in (None, 115, {"actor_count": 115}, [1, 2, 3]):
            with self.assertRaises(ValueError):
                dispatch_report(bad)

    # --- LANE-B / MOB-COMBAT-001: apply_identity_override -----------------
    #
    # Added round `sifsfg` as the pure half of the fix chief's escalation
    # (pf_bridge/notes_to_chief/20260827_0920_CHIEF-URGENT-...) asked lane B
    # to design: bar_frames/death_frames' one-entry collection is a confirmed
    # (RE-092) world-wipe on the flagless path.  Tested here, next to this
    # module's other generation-transforming functions, because it is a
    # world_population.py function; the caller it exists for is
    # mob_death.hostile_census_frames, tested against the real 115-actor
    # census in tests/test_mob_death.py.

    def test_apply_identity_override_replaces_only_named_identities(
            self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn, scene_id=1)
        target = generation.actor_identities[5]
        replacement = b"\x01\x02\x03"
        composed = apply_identity_override(
            self.legacy, generation, {target: replacement})
        self.assertIsInstance(composed, WorldPopulationGeneration)
        # The wire count and every other identity's bytes are unchanged.
        self.assertEqual(composed.actor_identities, generation.actor_identities)
        self.assertEqual(composed.actor_count, generation.actor_count)
        # Walk both collections in lockstep and check identity by identity.
        old_offset = world_population.WIRE_HEADER_BYTES
        new_offset = world_population.WIRE_HEADER_BYTES
        for identity, old_length, new_length in zip(
                generation.actor_identities, generation.entry_bytes,
                composed.entry_bytes):
            old_entry = generation.pc[old_offset:old_offset + old_length]
            new_entry = composed.pc[new_offset:new_offset + new_length]
            if identity == target:
                self.assertEqual(new_entry, replacement)
            else:
                self.assertEqual(new_entry, old_entry)
            old_offset += old_length
            new_offset += new_length
        self.assertEqual(composed.frame, self.legacy.frame_pc(composed.pc))

    def test_apply_identity_override_is_a_noop_on_an_empty_override(
            self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn, scene_id=1)
        composed = apply_identity_override(self.legacy, generation, {})
        self.assertIs(composed, generation)

    def test_apply_identity_override_ignores_identities_absent_from_the_rung(
            self) -> None:
        # A caller widening its override dict over time should not have to
        # filter it down to only the identities a particular rung encodes.
        generation = build_world_population(
            self.legacy, self.spawn, 3, scene_id=1)
        composed = apply_identity_override(
            self.legacy, generation, {0xFFFFFF: b"\x01"})
        self.assertEqual(composed.pc, generation.pc)
        self.assertEqual(composed.frame, generation.frame)

    def test_apply_identity_override_refuses_a_non_generation(self) -> None:
        with self.assertRaises(ValueError):
            apply_identity_override(self.legacy, None, {})

    def test_apply_identity_override_refuses_a_non_dict_override(self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn, 3, scene_id=1)
        with self.assertRaises(ValueError):
            apply_identity_override(self.legacy, generation, [(1, b"x")])

    def test_apply_identity_override_refuses_bad_keys_and_values(self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn, 3, scene_id=1)
        identity = generation.actor_identities[0]
        for bad_override in (
            {"not-an-int": b"x"},
            {True: b"x"},  # bool is an int subclass; must be refused anyway
            {identity: "not-bytes"},
            {identity: 5},
        ):
            with self.assertRaises(ValueError):
                apply_identity_override(self.legacy, generation, bad_override)


class UndressablePlacementNamingTests(unittest.TestCase):
    """The seven placements Port Royal loses are named on the boot line.

    BUILD-001's terms from the owner: a census that does not go out whole
    reports the real number AND the reason, and the 115 target is never
    quietly rewritten.  The count has been on the line since RE-128; these
    pin the part a log reader could not get before - WHICH placements, and
    who the client's own text table says they are.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.generation = world_population.build_world_population(
            cls.legacy, cls.spawn, world_population.CENSUS_COUNT, scene_id=1,
        )

    def test_the_named_report_is_the_same_seven_the_census_filter_dropped(
        self,
    ) -> None:
        named = world_population.undressable_placements_named(self.legacy)
        dropped = world_population.unshippable_placements(self.legacy)
        self.assertEqual(
            [(row[0], row[1]) for row in named],
            [(row[0], row[1]) for row in dropped],
        )
        # And the same seven the census actually left out, read from the
        # shipped membership rather than from a literal.
        shipped = set(self.generation.indices)
        every = {
            placement.placement_index
            for placement in load_port_royal_placements(self.legacy)
        }
        self.assertEqual(
            sorted(row[0] for row in named), sorted(every - shipped),
        )

    def test_every_named_row_carries_the_leader_its_refusal_recorded(
        self,
    ) -> None:
        for index, template_id, leader, name in (
            world_population.undressable_placements_named(self.legacy)
        ):
            recorded_leader, _ = world_port_royal_identity.UNRESOLVED[
                template_id]
            self.assertEqual(leader, recorded_leader)
            self.assertEqual(
                name,
                world_port_royal_identity.UNRESOLVED_CLIENT_NAMES[template_id],
            )
            self.assertIn(index, UNSHIPPABLE_PLACEMENT_INDICES)

    def test_the_census_line_names_the_seven_and_stays_printable(self) -> None:
        line = world_population.census_console_line(self.generation)
        self.assertIn("undressable=7 ", line)
        # The dock placement is the one an operator is most likely to be
        # standing next to when they wonder where everybody is.
        self.assertIn("P0/set1/lead155/Port_transportation", line)
        self.assertIn("P86/set86/lead0/NO_CREATURE", line)
        # 113's client name is CJK and the bridge console is cp874.
        self.assertIn("P148/set113/lead942/NON_ASCII", line)
        line.encode("ascii")
        line.encode("cp874")

    def test_a_generation_that_never_measured_says_so_and_not_zero(
        self,
    ) -> None:
        # "nobody asked" must not print as "nobody is missing" - the two
        # tokens are different strings on purpose.
        unmeasured = dataclasses.replace(self.generation, undressable=None)
        self.assertEqual(
            world_population.undressable_console_token(unmeasured),
            "undressable=not_recorded",
        )
        self.assertEqual(
            world_population.undressable_console_token(
                dataclasses.replace(self.generation, undressable=()),
            ),
            "undressable=0",
        )
        self.assertIn(
            "undressable=not_recorded",
            world_population.census_console_line(unmeasured),
        )

    def test_the_token_never_raises_inside_a_boots_own_log_line(self) -> None:
        for broken in (
            None,
            "not a generation",
            dataclasses.replace(self.generation, undressable=((1, 2), )),
            dataclasses.replace(self.generation, undressable=(("a",) * 4, )),
            dataclasses.replace(self.generation, undressable=(None, )),
        ):
            token = world_population.undressable_console_token(broken)
            self.assertTrue(token.startswith("undressable="))
            token.encode("cp874")

    def test_a_console_name_is_bounded_and_tells_its_three_absences_apart(
        self,
    ) -> None:
        name_of = world_population._console_name
        self.assertEqual(name_of(0, ""), "NO_CREATURE")
        self.assertEqual(name_of(0, "anything"), "NO_CREATURE")
        self.assertEqual(name_of(155, ""), "NO_NAME")
        self.assertEqual(name_of(942, "\u96f7\u9813"), "NON_ASCII")
        self.assertEqual(name_of(155, "Port transportation"),
                         "Port_transportation")
        long_name = name_of(155, "a" * 200)
        self.assertEqual(
            len(long_name), world_port_royal_identity.ASCII_NAME_LIMIT,
        )

    def test_the_names_table_covers_every_refusal_and_nothing_else(
        self,
    ) -> None:
        self.assertEqual(
            set(world_port_royal_identity.UNRESOLVED_CLIENT_NAMES),
            set(world_port_royal_identity.UNRESOLVED),
        )
        # A named Mob-Set number may never also be resolvable: that would be
        # a name for an actor that ships, recorded in the refusal table.
        for template_id in world_port_royal_identity.UNRESOLVED_CLIENT_NAMES:
            self.assertIsNone(world_port_royal_identity.resolve(template_id))


if __name__ == "__main__":
    unittest.main()
