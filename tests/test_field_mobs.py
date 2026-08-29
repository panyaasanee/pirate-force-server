"""LANE-B: named hostile monsters built from real MOBS rows.

The load-bearing tests in this file are the first three.

``test_the_hostile_body_is_the_frozen_body_plus_exactly_eight_bytes`` is the
one that matters most: the body this lane sends has never been on the wire in
this combination (named AND hostile AND leveled), so the only thing that
keeps it honest is that it differs from the frozen, client-rendered body by
exactly the GT-032 faction splice and the RE-117 level splice, and by nothing
else.  If that test starts passing for a body that is not the frozen body,
the lane is guessing.

``test_the_derived_columns_re_derive_two_frozen_constants`` pins the HP
derivation and the mined name against ``v141``'s own constants.  ~~which were
frozen from a live run rather than from a table join~~ -- WITHDRAWN, round
szdkgs (pf-adversary D11): that live run was a run of a server making the SAME
set-number read, so the two directions were never independent and this pin
could not have caught the reading being wrong.  It still holds, and is still
worth running, as a pin on the LEGACY reading that nine of these rows deliber-
ately still ship; it is one of the assertions the migration round has to move.  ``test_the_roster_is_a_
subset_of_the_census`` pins the integration hazard: these monsters ARE census
members, so anything that sends both collections duplicates identities.
"""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA
from pirateforce_foundation import (
    field_mob_tables,
    field_mob_tables_bg0002,
    field_mob_tables_bg0015,
    field_mobs,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    NPC_ATTR_ID,
    SCENE_ID,
    SCENE_SEQUENCE,
    load_port_royal_placements,
)
from pirateforce_foundation.field_mobs import (
    BASIC_BIT_FACTION,
    BASIC_BIT_LEVEL,
    BASIC_BIT_NAME,
    FACTION_SPLICE_BYTES,
    FACTION_TAG,
    FIELD_MOB_FACTION,
    FieldMob,
    FieldMobContractError,
    LEVEL_SPLICE_BYTES,
    LEVEL_TAG,
    PLAYER_PAIR_FACTION,
    assert_frozen_controls,
    build_field_mob_population,
    cross_scene_identity_collisions,
    describe_cross_scene_identity_collisions,
    hostile_actor_entry,
    hostile_npc_attr,
    hostile_placement_indices,
    load_roster,
    nearest_first,
    neighbour_census,
    overlapping_identities,
    production_allowed,
    roster_report,
    test_only,
)


class FieldMobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    # --- the three load-bearing tests ------------------------------------

    def test_the_hostile_body_is_the_frozen_body_plus_exactly_eight_bytes(self) -> None:
        for mob in load_roster():
            baseline = self.legacy.make_npc_attr(
                mob.template_id, mob.actor_identity, SCENE_ID, SCENE_SEQUENCE,
                mob.visual_preset, mob.max_hp, mob.max_hp,
                movement_speed=float(mob.speed_walk),
                basic_name=mob.display_name,
            )
            hostile = hostile_npc_attr(self.legacy, mob)
            self.assertEqual(
                len(hostile),
                len(baseline) + FACTION_SPLICE_BYTES + LEVEL_SPLICE_BYTES,
            )

            # Everything except the mask and the eight spliced bytes must be
            # untouched: five for the tagged faction u32 (RE-032/GT-032), and
            # three for the tagged level u16 (RE-117, this round).
            faction_bytes = bytes(
                self.legacy.u32tag(FACTION_TAG, FIELD_MOB_FACTION),
            )
            self.assertEqual(len(faction_bytes), FACTION_SPLICE_BYTES)
            level_bytes = bytes(self.legacy.u16tag(LEVEL_TAG, mob.level))
            self.assertEqual(len(level_bytes), LEVEL_SPLICE_BYTES)

            # The POSITION is the claim, not merely the presence: ascending
            # mask-bit order puts 0x0400 after the whole BasicAttr block and
            # before the NPCAttr block, so the splice offset is the length of
            # the body minus the length of the NPCAttr tail.  Derived here
            # from the legacy serializers, independently of the module.
            npc_mask = 0x01 | (0x04 if mob.visual_preset else 0)
            tail = (
                bytes(self.legacy.u8tag(0x0B, npc_mask))
                + bytes(self.legacy.u16tag(0x12, mob.template_id))
                + bytes(self.legacy.wstr_tag(mob.visual_preset))
            )
            offset = len(hostile) - len(tail) - FACTION_SPLICE_BYTES
            self.assertEqual(
                hostile[offset:offset + FACTION_SPLICE_BYTES], faction_bytes,
                "faction is not spliced at the ascending-mask-order position",
            )
            self.assertTrue(hostile.endswith(tail))
            # And the field immediately before it is the BasicAttr block's
            # last member, the tagged scene-sequence qword (bit 0x0200).
            scene_sequence = bytes(
                self.legacy.qwordtag(0x32, SCENE_SEQUENCE),
            )
            self.assertEqual(
                hostile[offset - len(scene_sequence):offset], scene_sequence,
            )
            rebuilt = hostile[:offset] + hostile[offset + FACTION_SPLICE_BYTES:]

            head = (
                bytes(self.legacy.u8tag(0x0B, 1))
                + bytes(self.legacy.qwordtag(0x32, mob.actor_identity))
            )
            mask_at = len(head) + 1

            # Ascending-mask-bit order also puts 0x0002 (level) right after
            # the mask value and the optional name, before HP -- the other
            # end of the body from faction.  Re-derived here independently of
            # the module, same as the faction splice above.
            name_bytes = bytes(self.legacy.wstr_tag(mob.display_name))
            level_at = mask_at + 2 + len(name_bytes)
            self.assertEqual(
                rebuilt[level_at:level_at + LEVEL_SPLICE_BYTES], level_bytes,
                "level is not spliced at the ascending-mask-order position",
            )
            rebuilt = (
                rebuilt[:level_at]
                + rebuilt[level_at + LEVEL_SPLICE_BYTES:]
            )

            baseline_mask = int.from_bytes(
                baseline[mask_at:mask_at + 2], "little",
            )
            hostile_mask = int.from_bytes(
                rebuilt[mask_at:mask_at + 2], "little",
            )
            self.assertEqual(
                hostile_mask,
                baseline_mask | BASIC_BIT_FACTION | BASIC_BIT_LEVEL,
            )
            self.assertTrue(baseline_mask & BASIC_BIT_NAME)
            self.assertFalse(baseline_mask & BASIC_BIT_FACTION)
            self.assertFalse(baseline_mask & BASIC_BIT_LEVEL)

            # With the mask restored, the rest is byte-identical.
            restored = (
                rebuilt[:mask_at]
                + baseline[mask_at:mask_at + 2]
                + rebuilt[mask_at + 2:]
            )
            self.assertEqual(restored, baseline)

    def test_the_speed_field_carries_the_mined_value_not_the_owners_pc_guess(
            self) -> None:
        # COO-DECISION 2026-08-28T01:46+07:00 told this lane to widen its own
        # ActorAttr composition toward PANYA-DECISION 2026-08-28T01:25+07:00's
        # table's "most complete" philosophy.  That table's own field 7 (Basic
        # 0x0040 +0x54 f32, move speed) is an explicit NONCLAIM: the owner's
        # 400 is a PC-actor screen guess, not sourced.  This test proves the
        # value this lane actually sends is NOT that guess -- it is
        # ``mob.speed_walk``, ``field_mob_tables``'s own mined MOBS column,
        # fed through a parameter ``legacy.make_npc_attr`` already carried
        # (and already statically RE'd: 0x45C103/0x464960/0x45D2EA/0x484580,
        # see that function's own docstring) before this round touched it.
        #
        # pf-adversary (this round) caught that an earlier draft of this test
        # only iterated ``load_roster()``'s bg0001 default, while its own
        # docstring/comment claimed "both live scenes" -- Bg0002 was never
        # actually exercised even though its mined speed_walk column exists.
        # Both scenes ``load_roster`` can load are iterated explicitly below
        # so the claim and the coverage cannot drift apart again; a future
        # third scene added to ``field_mobs._SCENE_TABLE_MODULES`` without an
        # entry here would silently narrow this test's scope back to the same
        # gap, so this list -- not ``_SCENE_TABLE_MODULES`` -- is the thing to
        # extend when that happens.
        for scene in (field_mob_tables.SCENE, field_mobs.BG0002_SCENE):
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            mined = {
                row[0]: row[11]
                for row in getattr(
                    module, "SHIPPED_PLACEMENTS", module.HOSTILE_PLACEMENTS,
                )
            }
            for mob in load_roster(scene=scene):
                # ~~self.assertEqual(mob.speed_walk, 100)~~ -- 100 was every
                # row's speed only while every row was a Prison Exile monster
                # read through the wrong column.  Round szdkgs's town target
                # (n_ID 916) carries 150 in the same MOBS column.
                # pf-adversary D10: comparing the parse against the same list
                # it parsed asserts that the parser is the identity function,
                # which is not what this test is for.  So BOTH: the parse is
                # faithful, AND the value is the LITERAL the MOBS table
                # carries for that actor -- 150 for the practice dummy, 100
                # for every row still read as a Prison Exile monster.
                self.assertEqual(mob.speed_walk, mined[mob.placement_index])
                self.assertEqual(
                    mob.speed_walk,
                    150 if mob.template_id == field_mobs.TOWN_TARGET_N_ID
                    else 100,
                )
                self.assertNotEqual(
                    mob.speed_walk, 400,
                    "this must be the mined MOBS speed, never the owner's "
                    "unsourced PC-actor guess",
                )
                hostile = hostile_npc_attr(self.legacy, mob)
                baseline_with_speed = self.legacy.make_npc_attr(
                    mob.template_id, mob.actor_identity, SCENE_ID,
                    SCENE_SEQUENCE, mob.visual_preset, mob.max_hp, mob.max_hp,
                    movement_speed=float(mob.speed_walk),
                    basic_name=mob.display_name,
                )
                baseline_without_speed = self.legacy.make_npc_attr(
                    mob.template_id, mob.actor_identity, SCENE_ID,
                    SCENE_SEQUENCE, mob.visual_preset, mob.max_hp, mob.max_hp,
                    basic_name=mob.display_name,
                )
                # Sending the speed field costs exactly one f32tag: 1 tag
                # byte + 4 float bytes, and nothing else on the wire moves.
                self.assertEqual(
                    len(baseline_with_speed),
                    len(baseline_without_speed) + 5,
                )
                self.assertEqual(
                    len(hostile),
                    len(baseline_with_speed)
                    + FACTION_SPLICE_BYTES + LEVEL_SPLICE_BYTES,
                )
                self.assertIn(
                    bytes(self.legacy.f32tag(float(mob.speed_walk))),
                    baseline_with_speed,
                )

    def test_the_level_field_carries_the_mined_value_not_a_bounded_guess(
            self) -> None:
        # RE-117 (this round) proved NPCAttr level uses the same base-object
        # bit/offset/tag (0x0002, +0x5E, u16 tag 0x12) the owner's PC-actor
        # probe found -- NPCAttr serializer 0x00466EB0 calls the common
        # BasicAttr serializer 0x004656F0 before its own derived fields, so
        # the base object's bits apply here too.  This test proves the value
        # sent is ``mob.level``, ``field_mob_tables``'s mined
        # ``MOBS.n_LEVEL_MIN``/``n_LEVEL_MAX`` column, never invented.
        for scene in (field_mob_tables.SCENE, field_mobs.BG0002_SCENE):
            for mob in load_roster(scene=scene):
                self.assertGreaterEqual(mob.level, 1)
                self.assertLessEqual(mob.level, 255)
                hostile = hostile_npc_attr(self.legacy, mob)
                self.assertIn(
                    bytes(self.legacy.u16tag(LEVEL_TAG, mob.level)),
                    hostile,
                )

    def test_the_derived_columns_re_derive_two_frozen_constants(self) -> None:
        assert_frozen_controls(self.legacy)
        # ROUND 8ftmbx: ~~a lookup in load_roster()~~.  Placement 30 is
        # withdrawn from what this lane ships (COO-DECISION
        # 2026-08-29T00:41+07:00), so the two frozen constants are re-derived
        # against the row the generated module PRESERVES for that reading --
        # they are still exact statements about it, and they are still what
        # makes the ``legacy`` argument mean something.
        control = field_mobs.gt035_observed_subject()
        self.assertEqual(control.placement_index, self.legacy.V112_MONSTER_INDEX)
        self.assertNotIn(
            control.placement_index,
            [mob.placement_index for mob in load_roster()])
        self.assertEqual(control.max_hp, self.legacy.V117_P30_EXACT_HP)
        self.assertEqual(control.display_name, self.legacy.V119_P30_TARGET_NAME)
        self.assertEqual(control.template_id, 31)
        self.assertEqual(control.level, 27)

    def test_the_roster_is_a_subset_of_the_census(self) -> None:
        census = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        for mob in load_roster():
            self.assertIn(mob.placement_index, census)
            placement = census[mob.placement_index]
            # Same row, mined twice by two different pipelines.  The census
            # pipeline still carries the scene file's Mob-SET number in its
            # ``template_id`` (that is v141's frozen table, and lane A's own
            # census resolves identity later); this roster carries the
            # RESOLVED n_ID for the rows it resolved.  So the comparison that
            # holds for every row is against the number the table itself says
            # each row came from.
            rule = field_mob_tables.IDENTITY_RULE_PER_PLACEMENT[
                mob.placement_index
            ]
            set_number = field_mob_tables.SET_NUMBER_FOR_PLACEMENT[
                mob.placement_index
            ]
            self.assertEqual(set_number, placement.template_id)
            if rule == "cline":
                self.assertNotEqual(mob.template_id, placement.template_id)
            else:
                self.assertEqual(mob.template_id, placement.template_id)
                self.assertEqual(mob.visual_preset, placement.visual_preset)
            self.assertEqual(mob.x, placement.x)
            self.assertEqual(mob.y, placement.y)
            self.assertEqual(mob.z, placement.z)
            self.assertEqual(mob.actor_identity, placement.actor_identity)
        shared = overlapping_identities(tuple(census))
        self.assertEqual(len(shared), len(load_roster()))

    # --- the roster ------------------------------------------------------

    def test_the_roster_is_the_four_practice_dummies_and_nothing_else(self):
        # ~~Thirteen monsters.~~  ~~Still thirteen placements, split by which
        # identity rule produced each one: four crosswalk dummies and nine
        # still carrying the legacy set-number reading.~~
        # ROUND 8ftmbx: FOUR, and they are all the same practice dummy.
        # COO-DECISION 2026-08-29T00:41+07:00 gave the nine set-number rows
        # one round and this is the round after it: they are withdrawn, and
        # who each of them really is stays readable per row in the generated
        # module's WITHDRAWN_UNDER_THIS_RULE.  ZERO placements in this town
        # satisfy the hostility predicate under the crosswalk -- Port Royal
        # is a town and has no monsters -- which is the finding, not a defect,
        # and HOSTILE_PLACEMENTS being empty is how the module says it.
        roster = load_roster()
        self.assertEqual(len(roster), 4)
        self.assertEqual({mob.template_id for mob in roster}, {916})
        self.assertEqual(hostile_placement_indices(), (103, 105, 107, 109))
        self.assertEqual(field_mob_tables.HOSTILE_PLACEMENTS, [])
        self.assertEqual(len(field_mob_tables.TOWN_TARGET_PLACEMENTS), 4)
        self.assertEqual(
            field_mob_tables.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION, [],
        )
        self.assertEqual(
            len(field_mob_tables.WITHDRAWN_UNDER_THIS_RULE), 9,
            "the nine withdrawn rows must stay named, not deleted")
        for mob in roster:
            self.assertGreater(mob.max_hp, 0)
            self.assertTrue(mob.display_name.isascii())
            self.assertTrue(mob.visual_preset.isascii())
            rule = field_mob_tables.IDENTITY_RULE_PER_PLACEMENT[
                mob.placement_index
            ]
            self.assertEqual(rule, "cline")
            self.assertEqual(mob.template_id, field_mobs.TOWN_TARGET_N_ID)
            self.assertEqual(mob.display_name, field_mobs.TOWN_TARGET_NAME)
            # A dummy, not a monster: this is the condition COO attached to
            # shipping 916 at all, asserted rather than only written down.
            self.assertEqual(mob.rank, 0)
            self.assertEqual(mob.ai_combat, 0)

    def test_the_withdrawn_row_guard_actually_raises(self) -> None:
        """The withdrawn-row guard, tripped rather than asserted.

        pf-adversary (same round, D11) mutated both to ``if False:`` and the
        whole suite stayed green: the tests around them asserted the
        CONDITION was false (assertNotIn) and never that the guard refuses.
        A guard nothing trips is a comment.  So this puts the withdrawn row
        back into the shipped roster and requires each one to raise.
        """
        returning = tuple(field_mob_tables.GT035_OBSERVED_SETNUM_ROW)
        original = field_mob_tables.SHIPPED_PLACEMENTS
        original_rules = field_mob_tables.IDENTITY_RULE_PER_PLACEMENT
        field_mob_tables.SHIPPED_PLACEMENTS = sorted(
            [returning] + list(original))
        field_mob_tables.IDENTITY_RULE_PER_PLACEMENT = {
            **original_rules, returning[0]: "cline"}
        try:
            # Guard 1: gt035_observed_subject refuses to hand back a row that
            # is shipped, so a pin cannot quietly change subject to a live
            # roster member.
            with self.assertRaises(FieldMobContractError) as caught:
                field_mobs.gt035_observed_subject()
            self.assertIn("shipped roster", str(caught.exception))
            # And the boot-time control refuses too -- by its SHAPE GATE,
            # which reaches the returning row before the guard above does.
            # Recorded as what actually catches it rather than assumed: this
            # is also why assert_frozen_controls carries ONE guard and not
            # two.  The second copy this round first wrote into it could
            # never execute (pf-adversary D11 mutation), and was removed
            # rather than left looking like a second line of defence.
            with self.assertRaises(FieldMobContractError) as caught:
                assert_frozen_controls(FieldMobTests.legacy)
            self.assertIn(
                str(field_mobs.LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX),
                str(caught.exception))
            self.assertIn("this lane ships", str(caught.exception))
        finally:
            field_mob_tables.SHIPPED_PLACEMENTS = original
            field_mob_tables.IDENTITY_RULE_PER_PLACEMENT = original_rules
        # And the tree is back where it started.
        assert_frozen_controls(FieldMobTests.legacy)

    def test_the_generator_never_places_two_monsters_on_one_spot(self) -> None:
        # ADDED this round: a duplicate PLACEMENT INDEX was already refused
        # (see the ``load_roster`` docstring's own duplicate check), but two
        # DIFFERENT placement indices sharing the exact same (x, y, z) were
        # not caught anywhere -- the shape a hand-edited or mis-mined table
        # could still produce, two identities visually stacked on one spot.
        # Both real mined tables (bg0001, Bg0002) already pass this by
        # construction (see the next test); this one proves the guard
        # actually FIRES rather than being an assertion nobody exercises,
        # using a synthetic two-row module (the same "any object with a
        # SCENE string and a HOSTILE_PLACEMENTS list" shape
        # ``cross_scene_identity_collisions`` already documents as this
        # package's own internal contract for a table module).
        import types
        row_a = (1, 31, 100.0, 200.0, 300.0, 'M011_000_000_SP3',
                  'Tornado Eagle', 27, 1, 16, 214, 100, 3857,
                  2701001, 5400001, 2802234)
        row_b = (2, 34, 100.0, 200.0, 300.0, 'M025_001_000_N',
                  'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138,
                  2701001, 5400001, 2802264)
        fake_module = types.SimpleNamespace(
            SCENE='TestOverlapScene',
            HOSTILE_PLACEMENTS=[row_a, row_b],
        )
        with self.assertRaises(FieldMobContractError) as caught:
            field_mobs._parse_hostile_placements(fake_module)
        self.assertIn('duplicate spawn position', str(caught.exception))

    def test_no_two_mobs_in_the_live_roster_share_a_spawn_position(
            self) -> None:
        # The real-data half of the guard above: both scenes
        # load_roster() can actually load today must have as many DISTINCT
        # (x, y, z) positions as they have mobs -- zero monsters standing
        # inside another one.  This is a measurement of the mined tables,
        # not a re-statement of the guard: it would still be true even if
        # ``_parse_hostile_placements`` never checked for it.
        for scene, expected_count in (
            # ROUND 8ftmbx: ~~13~~ -> 4 for bg0001 (COO-DECISION
            # 2026-08-29T00:41+07:00); Bg0002 is untouched by that ruling.
            (field_mob_tables.SCENE, 4),
            # ROUND wmomy7: ~~17~~ -> 12; the owner's
            # ``owner_says_do_not_place`` ruling on the n_id 101-104 block
            # keeps placements 92-96 out of what this lane ships.
            (field_mobs.BG0002_SCENE, 12),
        ):
            roster = load_roster(scene=scene)
            self.assertEqual(len(roster), expected_count)
            positions = {(mob.x, mob.y, mob.z) for mob in roster}
            self.assertEqual(
                len(positions), len(roster),
                "scene %r has two mobs sharing one spawn position" % scene,
            )

    def test_load_roster_defaults_to_bg0001_and_tags_every_mob_with_its_scene(
            self) -> None:
        # ADDED this round (PANYA-DECISION 2026-08-27T20:10+07:00): the
        # no-argument call must be byte-for-byte the same roster it always
        # was, and every returned mob must carry the SAME scene string the
        # generated module itself declares, not a hardcoded literal.
        roster = load_roster()
        self.assertEqual(len(roster), 4)  # ROUND 8ftmbx: ~~13~~ -> 4 (COO-DECISION 2026-08-29T00:41+07:00
        # withdrew the nine set-number rows; bg0001 ships four dummies)
        for mob in roster:
            self.assertEqual(mob.scene, field_mob_tables.SCENE)
            self.assertEqual(mob.scene, "bg0001")

    def test_load_roster_can_load_bg0002s_own_mined_roster(self) -> None:
        from pirateforce_foundation import field_mob_tables_bg0002
        bg0002_roster = load_roster(scene=field_mobs.BG0002_SCENE)
        self.assertEqual(field_mobs.BG0002_SCENE, "Bg0002")
        # ROUND wmomy7: ~~17 rows, 4 templates {31, 34, 35, 103}~~ -> 12
        # rows, 3 templates.  Template 103 ("Orc Chief") had all five of its
        # placements (92-96) inside the owner's
        # ``n_id_101_104_block ... owner_says_do_not_place`` ruling, so the
        # whole template leaves the shipped roster with them.  The generated
        # table still carries all 17 rows and all 4 templates.
        self.assertEqual(len(bg0002_roster), 12)
        self.assertEqual(
            len({mob.template_id for mob in bg0002_roster}), 3)
        self.assertEqual(
            {mob.template_id for mob in bg0002_roster}, {31, 34, 35})
        table_rows = field_mobs._parse_hostile_placements(
            field_mob_tables_bg0002)
        self.assertEqual(len(table_rows), 17)
        self.assertEqual(
            {mob.template_id for mob in table_rows}, {31, 34, 35, 103})
        for mob in bg0002_roster:
            self.assertEqual(mob.scene, field_mob_tables_bg0002.SCENE)
            self.assertEqual(mob.scene, "Bg0002")

    def test_bg0001_and_bg0002_actor_identities_no_longer_collide(
            self) -> None:
        # DISCOVERED this round, not fixed: FieldMob.actor_identity is
        # ``0x2000 + placement_index + 1`` with NO scene component (the same
        # rule world_population uses), and both scenes' placement indices are
        # small numbers assigned independently by their own .npc files -- so
        # four bg0001 mobs and four Bg0002 mobs land on the EXACT SAME actor
        # identity, four different monsters two-by-two: placement 58 (bg0001
        # Jungle Big Tiger / Bg0002 Fighting Fish soldier), 59 (Toxic Vine /
        # Fighting Fish soldier), 60 (Ancient Civilization Alert Weapon /
        # Fighting Fish soldier) and 95 (An Gebo Little Firebird / Orc
        # Chief). This is a SEPARATE hazard from the WIDENING_RULINGS
        # template/scene collision this round otherwise closes: it is about
        # the WIRE IDENTITY two different monsters would carry, not about
        # who is allowed to kill them. It is harmless today because nothing
        # sends both scenes' collections in the same generation (players
        # occupy one scene at a time, and load_roster() itself refuses to
        # merge them -- see assert_single_scene_tables) and mob_death's own
        # DeathRegister/CombatLedger are per-caller, not a cross-scene
        # global. It would stop being harmless the moment any single process
        # needs to reference BOTH scenes' mobs at once (a cross-scene admin
        # view, a shared in-memory registry, etc.) -- flagged here rather
        # than fixed, since fixing it means changing what actor_identity IS
        # (adding a scene component), which reaches world_population and the
        # wire format this project has not asked this round to touch.
        bg0001_identities = {mob.actor_identity for mob in load_roster()}
        bg0002_identities = {
            mob.actor_identity
            for mob in load_roster(scene=field_mobs.BG0002_SCENE)
        }
        shared = bg0001_identities & bg0002_identities
        # ROUND 8ftmbx: ~~{0x203B, 0x203C, 0x203D, 0x2060}~~ -> EMPTY.  The
        # four colliding bg0001 rows (placements 58, 59, 60, 95) were four of
        # the nine COO-DECISION 2026-08-29T00:41+07:00 withdrew, and what the
        # town still ships (103/105/107/109) meets nothing Bg0002 ships
        # (50..96).  THE HAZARD IS NOT FIXED, it is merely not realised: the
        # identity rule is still 0x2000 + placement_index + 1 with no scene
        # term, so the next roster either scene grows can bring it straight
        # back.  This assertion is what would say so.
        self.assertEqual(shared, set())

    def test_load_roster_never_merges_the_two_scenes_in_one_call(self) -> None:
        # The guard this round widened (assert_single_scene_tables) still
        # does its one job: a single load_roster() call for either scene
        # returns rows from ONLY that scene, never both.
        bg0001_scenes = {mob.scene for mob in load_roster()}
        bg0002_scenes = {
            mob.scene for mob in load_roster(scene=field_mobs.BG0002_SCENE)
        }
        self.assertEqual(bg0001_scenes, {"bg0001"})
        self.assertEqual(bg0002_scenes, {"Bg0002"})

    def test_load_roster_refuses_an_unregistered_scene(self) -> None:
        with self.assertRaises(FieldMobContractError):
            load_roster(scene="Bg9999")

    def test_the_generated_module_carries_its_sources_and_its_census(self) -> None:
        self.assertEqual(field_mob_tables.SCENE, "bg0001")
        self.assertEqual(
            sorted(field_mob_tables.SOURCE_DIGESTS),
            # cline + scene_name joined the list in round szdkgs: the identity
            # rule now reads two more committed tables, so two more digests
            # have to travel with the module that depends on them.
            ["cline", "mobs", "mobs_tip", "placements", "scene_name",
             "standard_mob"],
        )
        for digest in field_mob_tables.SOURCE_DIGESTS.values():
            self.assertEqual(len(digest), 64)
            int(digest, 16)
        self.assertEqual(field_mob_tables.IDENTITY_RULE, "cline")
        self.assertEqual(field_mob_tables.SCENE_CLINE_TYPE, 1)
        census = field_mob_tables.PREDICATE_CENSUS
        # ~~115 unambiguous, and the four hostility readings all agree at
        # 13.~~  Both numbers were counted over the SET-NUMBER reading.  Under
        # the crosswalk this scene resolves 140 placements unambiguously and
        # not one of them has a rank: Port Royal is a town.  The nine legacy
        # rows still shipped are counted in the module's own lists, not here.
        self.assertEqual(census["unambiguous"], 140)
        self.assertEqual(census["rank"], 0)
        self.assertEqual(census["rank_and_ai_combat"], 0)
        self.assertEqual(census["drops_normal"], 0)
        # Nine placements DO carry a combat AI at rank 0 (seven of them are
        # the Navy Private guards).  Named, not shipped -- see the module's
        # COMBAT_AI_AT_RANK_ZERO.
        self.assertEqual(census["ai_combat"], 9)
        self.assertEqual(len(field_mob_tables.COMBAT_AI_AT_RANK_ZERO), 9)
        self.assertEqual(census["town_target"], 4)

    def test_the_generated_module_is_pure_ascii(self) -> None:
        # Lesson 86: one character with no code page 874 mapping raises
        # UnicodeEncodeError inside print() and kills a tool mid-report.
        for name in (
            "field_mob_tables.py", "field_mob_tables_bg0002.py", "field_mobs.py",
        ):
            source = (ROOT / "src/pirateforce_foundation" / name).read_bytes()
            self.assertTrue(source.decode("utf-8").isascii(), name)
        tool = ROOT / "tools/pf_mine_scene_mob_roster.py"
        self.assertTrue(tool.read_bytes().decode("utf-8").isascii())

    # --- what this scene cannot deliver ----------------------------------

    def test_this_town_cannot_crowd_one_view(self) -> None:
        close = neighbour_census(1000.0)
        self.assertEqual(close["with_a_neighbour"], 0)
        wider = neighbour_census(2000.0)
        self.assertEqual(wider["best"], 103)
        self.assertEqual(wider["best_count"], 2)
        nearest = nearest_first(self.spawn)[0]
        distance = (
            (nearest.x - self.spawn[0]) ** 2
            + (nearest.y - self.spawn[1]) ** 2
            + (nearest.z - self.spawn[2]) ** 2
        ) ** 0.5
        self.assertGreater(distance, 12000.0)

    # --- the collection --------------------------------------------------

    def test_the_collection_is_nearest_first_and_reframes(self) -> None:
        generation = build_field_mob_population(self.legacy, self.spawn)
        self.assertEqual(generation.scene, "bg0001")
        self.assertEqual(generation.mob_count, 4)  # ROUND 8ftmbx: ~~13~~ -> 4 (COO-DECISION 2026-08-29T00:41+07:00
        # withdrew the nine set-number rows; bg0001 ships four dummies)
        self.assertEqual(generation.faction, FIELD_MOB_FACTION)
        self.assertEqual(len(set(generation.actor_identities)), 4)
        self.assertEqual(generation.frame, self.legacy.frame_pc(generation.pc))
        self.assertGreater(generation.frame_bytes, generation.pc_bytes)
        ordered = nearest_first(self.spawn)
        self.assertEqual(
            generation.placement_indices,
            tuple(mob.placement_index for mob in ordered),
        )

    def test_a_shorter_collection_is_a_prefix_of_the_full_one(self) -> None:
        full = build_field_mob_population(self.legacy, self.spawn)
        # ROUND 8ftmbx: ~~(1, 4, 12)~~ -- the roster is four rows now
        # (COO-DECISION 2026-08-29T00:41+07:00), and a count above its length
        # is refused by name, which is a different test.
        for count in (1, 2, 4):
            partial = build_field_mob_population(self.legacy, self.spawn, count)
            self.assertEqual(partial.mob_count, count)
            self.assertEqual(
                partial.placement_indices, full.placement_indices[:count],
            )

    def test_the_entry_carries_the_hostile_body_and_full_movement(self) -> None:
        mob = load_roster()[0]
        entry = hostile_actor_entry(self.legacy, mob)
        body = hostile_npc_attr(self.legacy, mob)
        self.assertIn(body, entry)
        movement = self.legacy.make_remote_movement_attr(
            mob.actor_identity, mob.x, mob.y, mob.z,
            field_mobs.HEADINGS[mob.placement_index & 3],
            mask=0xFF,
        )
        self.assertIn(bytes(movement), entry)
        expected = self.legacy.make_remote_actor_entry(
            4, mob.actor_identity,
            [(NPC_ATTR_ID, body), (0x2067, movement)],
        )
        self.assertEqual(entry, expected)

    def test_a_nameless_body_is_the_gt032_shape(self) -> None:
        # GT-032 shipped faction with no name bit at all.  Asking for that
        # shape here must still splice the faction and must not set 0x0001.
        mob = load_roster()[0]
        body = hostile_npc_attr(self.legacy, mob, with_name=False)
        head = (
            bytes(self.legacy.u8tag(0x0B, 1))
            + bytes(self.legacy.qwordtag(0x32, mob.actor_identity))
        )
        mask = int.from_bytes(body[len(head) + 1:len(head) + 3], "little")
        self.assertFalse(mask & BASIC_BIT_NAME)
        self.assertTrue(mask & BASIC_BIT_FACTION)
        self.assertLess(len(body), len(hostile_npc_attr(self.legacy, mob)))

    # --- refusals --------------------------------------------------------

    def test_it_refuses_the_neutral_pairing_and_a_zero_hp_spawn(self) -> None:
        mob = load_roster()[0]
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, mob, faction=0)
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, mob, current_hp=0)
        with self.assertRaises(FieldMobContractError):
            hostile_npc_attr(self.legacy, "not a mob")

    def test_it_refuses_a_bad_anchor_and_a_bad_count(self) -> None:
        for anchor in ((0.0, 0.0), [0.0, 0.0, 0.0], (0.0, 0.0, float("nan"))):
            with self.assertRaises(FieldMobContractError):
                build_field_mob_population(self.legacy, anchor)
        for count in (0, 14, True, 2.0):
            with self.assertRaises(FieldMobContractError):
                build_field_mob_population(self.legacy, self.spawn, count)

    def test_it_refuses_a_control_that_no_longer_re_derives(self) -> None:
        # ~~A drifted V117_P30_EXACT_HP.~~  That constant is no longer the
        # control (see assert_frozen_controls): it was produced by the same
        # reading it was checking.  What must refuse now is a shipped row that
        # stops matching the independently mined crosswalk table.
        row = list(field_mob_tables.TOWN_TARGET_PLACEMENTS[0])
        row[6] = "Not The Dummy"
        original = field_mob_tables.SHIPPED_PLACEMENTS
        field_mob_tables.SHIPPED_PLACEMENTS = [tuple(row)] + [
            item for item in original if item[0] != row[0]
        ]
        try:
            with self.assertRaises(FieldMobContractError):
                assert_frozen_controls(FieldMobTests.legacy)
        finally:
            field_mob_tables.SHIPPED_PLACEMENTS = original
        # ~~And the legacy rows are still held to the one thing their own
        # rule claims: the shipped id IS the scene file's Mob-Set number.~~
        # ROUND 8ftmbx: there are no legacy rows left to hold (COO-DECISION
        # 2026-08-29T00:41+07:00), and the check that replaces that one is
        # stronger: with EXPECTED_LEGACY_PLACEMENTS empty, a row that comes
        # BACK labelled as the set-number reading is refused outright rather
        # than merely held to its own weaker claim.  Proven by putting one
        # back, which is the regression this migration has to stay closed
        # against.
        self.assertEqual(field_mobs.EXPECTED_LEGACY_PLACEMENTS, frozenset())
        returning_row = tuple(field_mob_tables.GT035_OBSERVED_SETNUM_ROW)
        original_rules = field_mob_tables.IDENTITY_RULE_PER_PLACEMENT
        field_mob_tables.SHIPPED_PLACEMENTS = sorted(
            [returning_row] + list(original))
        field_mob_tables.IDENTITY_RULE_PER_PLACEMENT = {
            **original_rules, returning_row[0]: "setnum"}
        try:
            with self.assertRaises(FieldMobContractError) as caught:
                assert_frozen_controls(FieldMobTests.legacy)
            self.assertIn("setnum", str(caught.exception))
        finally:
            field_mob_tables.SHIPPED_PLACEMENTS = original
            field_mob_tables.IDENTITY_RULE_PER_PLACEMENT = original_rules

    def test_a_current_hp_below_max_is_allowed_and_changes_only_that_field(self) -> None:
        # M4 needs a body whose current HP is lower than its max; the shape
        # must not otherwise move.
        mob = load_roster()[0]
        full = hostile_npc_attr(self.legacy, mob)
        hurt = hostile_npc_attr(self.legacy, mob, current_hp=mob.max_hp // 2)
        self.assertEqual(len(full), len(hurt))
        self.assertNotEqual(full, hurt)

    # --- the lane's own conventions --------------------------------------

    def test_it_declares_itself_shippable_and_installs_nothing(self) -> None:
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        # NARROWED by MOB-COMBAT-001 (lane B, 2026-08-26).  The damage driver
        # builds its bar frame out of this module's hostile body, so "nothing
        # in src/ mentions field_mobs" stopped being true the moment the two
        # halves of M4 met.  What is still true, and is what this assertion is
        # for, is that nothing DISPATCHES it: the tripwire now names the
        # importers and separately pins that no dispatch file has picked either
        # module up.  When the chief wires the one line, this goes red and the
        # letter has to be rewritten - which is exactly the intent it had.
        source = (ROOT / "src/pirateforce_foundation").glob("*.py")
        importers = sorted(
            path.name for path in source
            if path.name != "field_mobs.py"
            and "field_mobs" in path.read_text(encoding="utf-8")
        )
        # WIDENED AGAIN by MOB-DEATH-001 (lane B, 2026-08-26, round 7ptoku):
        # the death half composes the corpse body out of this module's hostile
        # body too, and checks its own composer against it on every call.
        # WIDENED AGAIN by MOB-LOOT-001 (lane B, 2026-08-26, round g627j0):
        # the loot half rolls a dead monster's OWN drop sets, so it takes the
        # roster row (a typed FieldMob) as its input and refuses a dict.  It
        # still dispatches nothing -- the assertion below is what says so.
        # WIDENED AGAIN by the MOB-AGGRO-001 promotion (lane B, 2026-08-26,
        # round ywm4v1): the AI controller takes a typed FieldMob to look up
        # the monster's own AI_WANDER row and to anchor its leash origin at the
        # position the table placed it.  It still dispatches nothing.
        # THE TRIPWIRE FIRED, AS DESIGNED, on the CORE-REQUEST round that
        # wired MOB-COMBAT-001/MOB-DEATH-001 into runtime.py's dispatch (the
        # chief's file, per MOB_COMBAT_WIRING/MOB_DEATH_WIRING).  "nothing
        # dispatches this module" stopped being true for runtime.py on
        # purpose: it now calls mob_combat.attack_from_observed_action /
        # commit_step and mob_death.kill / commit_death / corpse_override on
        # an inbound EA7D ActionVital whose target resolves to a field-mob
        # identity, with no scenario flag.  app.py is untouched -- it needs
        # no new flag, because the whole point of this round is a path that
        # does not depend on one.
        # WIDENED AGAIN by PLAYER-HOSTILE-PAIRING-001 (lane B, 2026-08-27):
        # the player's half of the pairing reuses this module's
        # PLAYER_PAIR_FACTION / FACTION_SPLICE_BYTES constants (single
        # source of truth, so the two halves cannot drift apart) instead of
        # redefining them.  It still dispatches nothing -- runtime.py does
        # not call it yet; that is CORE-REQUEST-009, not this round.
        # WIDENED AGAIN by GT-DIAG-MULTI-OBJECT-001 (lane B, 2026-08-27,
        # PANYA-ORDER 18:55/ADDENDUM 19:05): the diagnostic module reads a
        # real roster row for its control body and reuses
        # ``hostile_actor_entry``/``hostile_npc_attr`` for four of its five
        # objects.  It dispatches nothing itself -- runtime.py's own mention
        # of field_mobs/mob_combat/mob_death is the wiring pinned above, not
        # anything this module added; wiring the diagnostic in is a separate
        # CORE-REQUEST, not this round.
        # WIDENED AGAIN by the GT-DIAG-MULTI-OBJECT-001 WIRING round (lane B,
        # 2026-08-27): diag_multi_object_wiring.py is the runtime-facing half
        # of that diagnostic and it takes this module's FIELD_MOB_FACTION as
        # the default for the two composers it forwards to (mob_death's own
        # signature default, mirrored rather than re-guessed) and FieldMob as
        # the type it widens a roster with.  IT STILL DISPATCHES NOTHING: it
        # composes and returns bytes, and every one of its functions is a
        # pass-through when the diagnostic gate is off.  runtime.py's mention
        # of field_mobs is the MOB-COMBAT/MOB-DEATH wiring already pinned
        # above, not anything this round added -- wiring THIS module into
        # runtime.py is a CORE-REQUEST that has not landed at the time this
        # line is written.
        self.assertEqual(
            importers,
            # ROUND wmomy7 adds mob_census_hostility.py: it reads
            # ``roster_for_scene_id``/``scene_for_scene_id`` and the
            # ``OWNER_REFUSED_PLACEMENTS`` literal.  It dispatches nothing
            # -- runtime.py does not call it yet; that is this round's
            # one-line wiring ask, not a landed call site.
            # ROUND jop8ph adds mob_ledger_admission.py: it reads
            # ``roster_for_scene_id``/``scene_for_scene_id`` to answer
            # whether a combat ledger speaks for a scene.  It dispatches
            # nothing either -- runtime.py reaches it only through
            # mob_census_hostility, and the keyword that would let it
            # matter is this round's wiring ask.
            # ROUND y9s0xo adds mob_scene_recompose.py: it reads
            # ``roster_for_scene_id``/``scene_for_scene_id`` to compose the
            # mid-session recompose census for whichever scene the hit
            # happened in, and takes ``FIELD_MOB_FACTION`` as the default it
            # forwards (mob_death's own signature default, mirrored rather
            # than re-guessed).  IT DISPATCHES NOTHING: runtime.py does not
            # call it, and the two call sites that would are this round's
            # wiring ask (mob_scene_recompose.SCENE_RECOMPOSE_WIRING).
            ["diag_multi_object_wiring.py", "mob_ai_control.py",
             "mob_census_hostility.py",
             "mob_combat.py", "mob_death.py",
             "mob_diag_multi_object.py",
             "mob_ledger_admission.py", "mob_loot.py",
             "mob_scene_recompose.py",
             "player_hostile_pairing.py", "runtime.py"],
            "field_mobs importers changed; update the letter")
        runtime_body = (
            ROOT / "src/pirateforce_foundation/runtime.py"
        ).read_text(encoding="utf-8")
        for needle in ("field_mobs", "mob_combat", "mob_death"):
            self.assertIn(needle, runtime_body)
        app_body = (ROOT / "src/pirateforce_foundation/app.py").read_text(
            encoding="utf-8")
        for needle in ("field_mobs", "mob_combat", "mob_death"):
            self.assertNotIn(needle, app_body)
        self.assertEqual(PLAYER_PAIR_FACTION, 1)
        self.assertEqual(FIELD_MOB_FACTION, 6)

    def test_the_wire_constants_are_the_gt032_ones(self) -> None:
        # Pinned as literals on purpose.  Every other test in this file reads
        # these through the module, so only a literal here can catch the case
        # where the constant itself moves and the assertions move with it.
        self.assertEqual(BASIC_BIT_FACTION, 0x0400)
        self.assertEqual(BASIC_BIT_NAME, 0x0001)
        self.assertEqual(FACTION_TAG, 0x14)
        self.assertEqual(FACTION_SPLICE_BYTES, 5)
        # RE-117 (this round), pinned as a literal for the same reason.
        self.assertEqual(BASIC_BIT_LEVEL, 0x0002)
        self.assertEqual(LEVEL_TAG, 0x12)
        self.assertEqual(LEVEL_SPLICE_BYTES, 3)

    def test_the_committed_pin_is_what_the_code_produces(self) -> None:
        path = ROOT / "scenarios/field_mobs_hostile_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        self.assertEqual(committed, field_mobs.pin_document(self.legacy))
        self.assertTrue(committed["production_allowed"])
        self.assertFalse(committed["test_only"])
        self.assertEqual(
            committed["selection"], "none_default_behaviour_no_scenario_flag",
        )
        # ROUND 8ftmbx: ~~13~~ -> 4 (COO-DECISION 2026-08-29T00:41+07:00
        # withdrew the nine set-number rows; bg0001 ships four dummies).
        self.assertEqual(len(committed["roster"]), 4)
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_report_is_ascii_safe(self) -> None:
        report = roster_report(self.legacy, self.spawn)
        # ROUND 8ftmbx: ~~13 mobs / 10 templates~~ -> four placements of one
        # template (COO-DECISION 2026-08-29T00:41+07:00 withdrew the nine
        # set-number rows; what Port Royal ships is four practice dummies).
        self.assertEqual(report["mob_count"], 4)
        self.assertEqual(report["distinct_templates"], 1)
        self.assertTrue(repr(report).isascii())


class FieldMobTypeTests(unittest.TestCase):
    def test_actor_identity_follows_the_census_rule(self) -> None:
        mob = FieldMob(
            30, 31, 0.0, 0.0, 0.0, "P", "N", 27, 1, 0, 1, 100, 3857, 0, 0, 0,
        )
        self.assertEqual(mob.actor_identity, 0x2000 + 30 + 1)


class CrossSceneIdentityCollisionTests(unittest.TestCase):
    # round `k25cur`: turns the prose already on record (this module's
    # ``load_roster`` docstring, and
    # ``test_bg0001_and_bg0002_actor_identities_are_NOT_disjoint_a_real_
    # collision`` above) into a reusable, reproducible report.  Also
    # extends the MEASUREMENT (not the default, and not any import in
    # ``src/``) to Bg0015, a third mined-but-still-COO-gated-dormant scene
    # table nothing previously compared against the other two -- see
    # ``test_bg0015_is_measurable_...`` below for why that stays an
    # explicit, test-only argument rather than joining the default set.

    def test_default_set_is_the_two_live_known_scenes_only(self) -> None:
        # Bg0015 is deliberately NOT in the default: COO-DECISION
        # 2026-08-26T12:46+07:00 keeps field_mob_tables_bg0015 unimported
        # anywhere under src/pirateforce_foundation/, so this function's own
        # module-level default cannot reference it either.
        # ROUND 8ftmbx: ~~four bg0001 x Bg0002 pairs~~ -> none.  All four
        # were bg0001 rows COO-DECISION 2026-08-29T00:41+07:00 withdrew.  The
        # report is not broken by having nothing to report; that is what a
        # report does when there is nothing there, and the tests below still
        # exercise it on data that does collide.
        collisions = cross_scene_identity_collisions()
        self.assertEqual(collisions, ())

    def test_bg0001_vs_bg0002_matches_the_identities_the_load_roster_test_pins(
            self) -> None:
        # cross-check against the OTHER test's independently-computed set
        # (test_bg0001_and_bg0002_actor_identities_no_longer_collide
        # above (renamed round 8ftmbx: it now pins the empty set)) rather than trusting one number twice.
        # ROUND 8ftmbx: both sides now compute the empty set, and they are
        # still computed independently -- that is still the point.  The four
        # names this used to pin (Jungle Big Tiger / Fighting Fish soldier /
        # An Gebo Little Firebird / Orc Chief) were bg0001 rows read through
        # the set-number column, and every one of them is withdrawn; naming
        # them here as if they were still shipped would be the exact thing
        # the withdrawal was for.
        collisions = cross_scene_identity_collisions(
            (field_mob_tables, field_mob_tables_bg0002))
        found = {row["actor_identity"] for row in collisions}
        independent = (
            {mob.actor_identity for mob in load_roster()}
            & {mob.actor_identity
               for mob in load_roster(scene=field_mobs.BG0002_SCENE)})
        self.assertEqual(found, independent)
        self.assertEqual(found, set())
        # NOT VACUOUS, and pf-adversary (round 8ftmbx, D10) is why this is
        # spelled out: with both sides empty, `assertEqual(set(), set())`
        # passes for a function replaced by `return ()`.  So the same report
        # is run on a pair that DOES collide, built from the same real rows,
        # and has to find it.  Agreement on nothing is only evidence when the
        # thing agreeing can still say something.
        overlapping = type(
            "_OverlappingScene", (), {
                "SCENE": "OverlapProbe",
                "HOSTILE_PLACEMENTS": list(
                    field_mob_tables.SHIPPED_PLACEMENTS),
            })
        probe = cross_scene_identity_collisions(
            (field_mob_tables, overlapping))
        self.assertEqual(
            {row["actor_identity"] for row in probe},
            {mob.actor_identity for mob in load_roster()})

    def test_bg0015_is_measurable_even_though_load_roster_refuses_it(self) -> None:
        # field_mob_tables_bg0015 is deliberately NOT in
        # field_mobs._SCENE_TABLE_MODULES (still unwired, still COO-gated
        # out of src/) -- this function must still be able to read it for a
        # caller-supplied report, without that meaning load_roster() can
        # load it, and without field_mobs.py itself ever importing it (this
        # test file is under tests/, not src/pirateforce_foundation/, so its
        # own import of field_mob_tables_bg0015 above does not trip
        # test_field_mob_tables_bg0015.py's src-only AST guard).
        with self.assertRaises(FieldMobContractError):
            load_roster(scene=field_mob_tables_bg0015.SCENE)
        # ROUND 8ftmbx: ~~3~~ -> 0 for this pair too; the three were
        # withdrawn bg0001 rows.  What this test is actually about -- that a
        # COO-gated dormant table can still be MEASURED without becoming
        # loadable -- is unchanged and is the assertion above.
        collisions = cross_scene_identity_collisions(
            (field_mob_tables, field_mob_tables_bg0015))
        self.assertEqual(collisions, ())

    def test_all_three_known_tables_together_find_one_pairwise_collision(
            self) -> None:
        # The full picture across every scene table this project has mined
        # so far (bg0001 live, Bg0002 about to be wired per this round's
        # letter, Bg0015 COO-gated dormant) -- passed explicitly, never the
        # default, for the reason the two tests above document.
        collisions = cross_scene_identity_collisions(
            (field_mob_tables, field_mob_tables_bg0002, field_mob_tables_bg0015))
        by_pair: dict[tuple[str, str], list[dict]] = {}
        for row in collisions:
            by_pair.setdefault((row["scene_a"], row["scene_b"]), []).append(row)
        # ROUND 8ftmbx: ~~ten pairs across three scenes~~ -> three, all of
        # them Bg0002 x Bg0015.  The seven that went were every pair with a
        # bg0001 side, and they went because bg0001's colliding rows were
        # withdrawn, not because anything about the identity rule changed.
        # ROUND ua236k: ~~three~~ -> ONE, and this time it IS the identity
        # rule.  Bg0015 was re-mined through the crosswalk
        # (COO-DECISION 20260829_0345), so its templates are no longer Port
        # Royal's; two of the three collisions were two scenes agreeing on a
        # template only because the set-number reading gave both the same
        # wrong answer.  This is the report doing the job lane A's letter
        # 20260829_0014 asked it to do, measured rather than asserted.
        #
        # WHAT THE SURVIVOR IS, AND WHY IT MUST NOT BE "FIXED" HERE.
        # Placement index 87 exists in BOTH scenes, and the wire identity is
        # 0x2000 + index + 1, so the two rows collide on 0x2058 no matter
        # who stands there: Bg0002 template 34 (Fighting Fish soldier) vs
        # Bg0015 template 924 (Carlos).  That is a placement-index collision,
        # not an identity-rule one -- it is the per-scene identity space lane
        # A proposed as option 3 and COO declined for this lane (it touches
        # world_population).  Re-mining cannot remove it and this test must
        # keep reporting it until someone widens the identity space.
        self.assertEqual(sorted(by_pair), [("Bg0002", "Bg0015")])
        self.assertEqual(len(by_pair[("Bg0002", "Bg0015")]), 1)
        self.assertEqual(len(collisions), 1)
        survivor = collisions[0]
        self.assertEqual(survivor["placement_index"], 87)
        self.assertEqual(survivor["actor_identity"], 0x2000 + 87 + 1)
        self.assertEqual(
            (survivor["template_a"], survivor["template_b"]), (34, 924))

    def test_two_disjoint_scenes_report_zero_collisions(self) -> None:
        # bg0002 vs a hand-built single-mob table sharing no placement index
        # with it: the function must not manufacture a false positive.
        class _FakeModule:
            SCENE = "FakeSceneNoOverlap"
            HOSTILE_PLACEMENTS = [
                (9001, 31, 0.0, 0.0, 0.0, "P", "N", 1, 1, 0, 1, 1, 1, 0, 0, 0),
            ]
        collisions = cross_scene_identity_collisions(
            (field_mob_tables_bg0002, _FakeModule))
        self.assertEqual(collisions, ())

    # -- same-scene collisions (LANE-A letter 20260829_0014, round 8ftmbx) --

    @staticmethod
    def _second_table_for(scene, rows):
        """A second table module naming a scene another module already names.

        This is the shape lane A's letter reported and this function exists
        for: two committed tables for ONE scene, disagreeing about who stands
        at a placement.  Built by hand here because the real second table for
        that scene belongs to lane A and lives outside this package -- and
        because a synthetic pair is the only way to prove the report FIRES
        rather than merely returns an empty tuple today.
        """
        class _SecondTable:
            SCENE = scene
            HOSTILE_PLACEMENTS = list(rows)
        return _SecondTable

    def test_same_scene_collisions_are_found_where_the_old_report_was_blind(
            self) -> None:
        # THE REGRESSION THIS CLOSES, proven by execution rather than by the
        # docstring: cross_scene_identity_collisions keyed its rosters by
        # SCENE and skipped a repeat, so the second table was dropped in
        # silence and the report said "nothing".
        rows = [
            row for row in field_mob_tables_bg0002.HOSTILE_PLACEMENTS[:2]
        ]
        disagreeing = [
            (row[0], 916) + row[2:5] + ("M016_000_000_N", "Training Iron Man")
            + row[7:]
            for row in rows
        ]
        second = self._second_table_for(
            field_mob_tables_bg0002.SCENE, disagreeing)
        found = field_mobs.same_scene_identity_collisions(
            (field_mob_tables_bg0002, second))
        self.assertEqual(len(found), 2)
        for collision, row in zip(found, rows):
            self.assertTrue(collision["same_scene"])
            self.assertEqual(collision["scene_a"], collision["scene_b"])
            self.assertEqual(collision["placement_index"], row[0])
            self.assertEqual(
                collision["actor_identity"], 0x2000 + row[0] + 1)
            self.assertEqual(collision["template_a"], row[1])
            self.assertEqual(collision["template_b"], 916)
            self.assertNotEqual(collision["name_a"], collision["name_b"])
        # And the OLD report still says nothing about them, which is the
        # whole reason a second function exists rather than a wider one.
        self.assertEqual(
            cross_scene_identity_collisions(
                (field_mob_tables_bg0002, second)),
            (),
        )

    def test_the_same_module_passed_twice_is_not_a_collision_with_itself(
            self) -> None:
        # The trap in keying by module instead of by scene: comparing a table
        # with itself would report EVERY one of its own rows as a clash.
        self.assertEqual(
            field_mobs.same_scene_identity_collisions(
                (field_mob_tables_bg0002, field_mob_tables_bg0002)),
            (),
        )

    def test_two_tables_of_one_scene_that_agree_report_nothing(self) -> None:
        # A collision is a DISAGREEMENT about a placement, but this report
        # keys on the placement index alone -- so two tables that agree still
        # collide, and it says so rather than pretending to compare bodies.
        # Recorded as the report's real contract, not asserted away.
        same = self._second_table_for(
            field_mob_tables_bg0002.SCENE,
            field_mob_tables_bg0002.HOSTILE_PLACEMENTS[:1])
        found = field_mobs.same_scene_identity_collisions(
            (field_mob_tables_bg0002, same))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["template_a"], found[0]["template_b"])

    def test_same_scene_describe_is_ascii_and_names_the_scene_once(
            self) -> None:
        second = self._second_table_for(
            field_mob_tables_bg0002.SCENE,
            field_mob_tables_bg0002.HOSTILE_PLACEMENTS[:1])
        lines = field_mobs.describe_same_scene_identity_collisions(
            (field_mob_tables_bg0002, second))
        self.assertEqual(
            lines[0], "FIELD_MOB_SAME_SCENE_IDENTITY_COLLISIONS count=1")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1].count(field_mob_tables_bg0002.SCENE), 1)
        for line in lines:
            self.assertTrue(line.isascii())
            self.assertTrue(line.encode("cp874"))

    def test_the_default_set_reports_no_same_scene_collision(self) -> None:
        # Two modules, two different scenes: nothing for this report to find,
        # and it says zero by name rather than by absence.
        self.assertEqual(field_mobs.same_scene_identity_collisions(), ())
        self.assertEqual(
            field_mobs.describe_same_scene_identity_collisions()[0],
            "FIELD_MOB_SAME_SCENE_IDENTITY_COLLISIONS count=0")

    def test_same_scene_report_refuses_the_same_way_its_sibling_does(
            self) -> None:
        with self.assertRaises(FieldMobContractError):
            field_mobs.same_scene_identity_collisions((field_mob_tables,))

        class _NoScene:
            HOSTILE_PLACEMENTS = []
        with self.assertRaises(FieldMobContractError):
            field_mobs.same_scene_identity_collisions(
                (field_mob_tables, _NoScene))

    def test_refuses_fewer_than_two_modules(self) -> None:
        with self.assertRaises(FieldMobContractError):
            cross_scene_identity_collisions((field_mob_tables,))

    def test_refuses_a_module_missing_its_scene_constant(self) -> None:
        class _NoScene:
            HOSTILE_PLACEMENTS = []
        with self.assertRaises(FieldMobContractError):
            cross_scene_identity_collisions((field_mob_tables, _NoScene))

    def test_describe_is_ascii_and_carries_the_same_count(self) -> None:
        collisions = cross_scene_identity_collisions()
        lines = describe_cross_scene_identity_collisions()
        # ROUND 8ftmbx: ~~count=4~~ -> count=0; the four were withdrawn
        # bg0001 rows.  The line still has to be PRINTED, which is what
        # test_describe_reports_zero_by_name_not_by_absence is about.
        self.assertEqual(
            lines[0], "FIELD_MOB_CROSS_SCENE_IDENTITY_COLLISIONS count=0")
        self.assertEqual(len(lines), 1 + len(collisions))
        for line in lines:
            self.assertTrue(line.isascii())
            self.assertTrue(line.encode("cp874"))

    def test_describe_reports_zero_by_name_not_by_absence(self) -> None:
        lines = describe_cross_scene_identity_collisions(
            (field_mob_tables_bg0002, field_mob_tables_bg0015))
        # These two DO collide (measured above) -- exercise the true
        # zero-collision shape explicitly instead, mirroring
        # test_two_disjoint_scenes_report_zero_collisions.
        class _FakeModule:
            SCENE = "FakeSceneNoOverlap2"
            HOSTILE_PLACEMENTS = [
                (9002, 34, 0.0, 0.0, 0.0, "P", "N", 1, 1, 0, 1, 1, 1, 0, 0, 0),
            ]
        zero_lines = describe_cross_scene_identity_collisions(
            (field_mob_tables_bg0002, _FakeModule))
        self.assertEqual(
            zero_lines, ("FIELD_MOB_CROSS_SCENE_IDENTITY_COLLISIONS count=0",))
        self.assertNotEqual(lines[0], zero_lines[0])




@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0001RegenerateAndDiffTest(unittest.TestCase):
    """The control bg0002 and bg0015 have had all along and bg0001 did not.

    pf-adversary (round szdkgs, D6): the one scene this round REWROTE was the
    one scene with no re-derivation test, so every new table in it -- the
    per-placement rule labels, the Mob-Set numbers, the withdrawn rows, the
    unresolved rows -- rested on the author having run the tool by hand.  It
    reproduces byte-for-byte; now something says so on every run.

    ROUND 0n9inw: ~~a bare ``unittest.SkipTest`` in ``setUpClass``~~ IS STRUCK.
    Lane A's status letter of 2026-08-29T10:50+07:00 (section 3) measured it on
    a fresh Linux clone: ``tools/pf_pytest_precondition_census.py`` reported
    these two tests as an UNDECLARED SKIP and the census as ``RESULT: FAIL``.
    Lane A said plainly they could not reproduce a red GATE and did not claim
    one, and that is still true -- but the skip was undeclared either way, and
    ``pf_preconditions``' own header names this exact shape as the thing it
    exists to stop.  It is the same defect that closed pull requests in rounds
    ctflxc, 2vxlx2, y7koj9 and vyi2ud, which is why every note in the pin file
    says "pinned in the same commit as the test": this one is too.
    """

    def test_regenerating_reproduces_the_committed_bg0001_module(self) -> None:
        import importlib.util

        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        spec = importlib.util.spec_from_file_location(
            "pf_mine_scene_mob_roster",
            ROOT / "tools" / "pf_mine_scene_mob_roster.py",
        )
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)

        rule = tool.IDENTITY_RULE_CLINE
        sources = tool.Sources(gamedata, "bg0001")
        controls = tool.check_crosswalk_controls(sources)
        roster = tool.hostile_roster(sources, rule)
        town = tool.town_target_roster(sources, rule)
        withdrawn = tool.withdrawn_under_rule(sources, rule)
        # ROUND 8ftmbx: ~~pending = the withdrawn rows, kept one more round~~.
        # COO-DECISION 2026-08-29T00:41+07:00 ended that round, so the module
        # is regenerated WITHOUT --keep-withdrawn-rows and pending is empty.
        # The GT-035 row the tool now preserves is the set-number reading of
        # the control placement, and it is passed here the same way the tool's
        # own main() computes it -- so this stays a re-derivation, not a copy.
        pending = []
        legacy_control_row = next(
            row for row in tool.hostile_roster(
                sources, tool.IDENTITY_RULE_SETNUM)
            if row["placement_index"] == tool.LEGACY_CONTROL_PLACEMENT_INDEX
        )
        regenerated = tool.render_module(
            "bg0001", roster, sources.digests(),
            tool.predicate_census(sources, rule),
            rule=rule, cline_type=sources.cline_type, town=town,
            withdrawn=withdrawn, controls=controls, pending=pending,
            legacy_control_row=legacy_control_row,
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(sources, rule)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
            unresolved=tool.unresolved_placements(sources, rule),
        )
        committed = (
            ROOT / "src/pirateforce_foundation/field_mob_tables.py"
        ).read_text(encoding="ascii")
        self.assertEqual(
            regenerated, committed,
            "field_mob_tables.py is stale - regenerate it with "
            "tools/pf_mine_scene_mob_roster.py --identity-rule cline",
        )

    def test_the_scene_is_fully_accounted_for(self) -> None:
        # pf-adversary D8: "zero hostiles" is a claim about the placements the
        # rule resolves, so the denominator has to be visible.  140 read + 9
        # unreadable = the scene's whole 149.
        self.assertEqual(
            field_mob_tables.PREDICATE_CENSUS["unambiguous"]
            + len(field_mob_tables.UNRESOLVED_PLACEMENTS),
            149,
        )
        for _index, _set_number, reason in (
                field_mob_tables.UNRESOLVED_PLACEMENTS):
            self.assertTrue(reason, "an unreadable placement with no reason")


if __name__ == "__main__":
    unittest.main()
