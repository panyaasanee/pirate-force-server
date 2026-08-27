"""LANE-B: named hostile monsters built from real MOBS rows.

The load-bearing tests in this file are the first three.

``test_the_hostile_body_is_the_frozen_body_plus_exactly_five_bytes`` is the one
that matters most: the body this lane sends has never been on the wire in this
combination (named AND hostile), so the only thing that keeps it honest is that
it differs from the frozen, client-rendered body by exactly the GT-032 splice
and by nothing else.  If that test starts passing for a body that is not the
frozen body, the lane is guessing.

``test_the_derived_columns_re_derive_two_frozen_constants`` pins the HP
derivation and the mined name against ``v141``'s own constants, which were
frozen from a live run rather than from a table join.  ``test_the_roster_is_a_
subset_of_the_census`` pins the integration hazard: these monsters ARE census
members, so anything that sends both collections duplicates identities.
"""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
    BASIC_BIT_NAME,
    FACTION_SPLICE_BYTES,
    FACTION_TAG,
    FIELD_MOB_FACTION,
    FieldMob,
    FieldMobContractError,
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

    def test_the_hostile_body_is_the_frozen_body_plus_exactly_five_bytes(self) -> None:
        for mob in load_roster():
            baseline = self.legacy.make_npc_attr(
                mob.template_id, mob.actor_identity, SCENE_ID, SCENE_SEQUENCE,
                mob.visual_preset, mob.max_hp, mob.max_hp,
                basic_name=mob.display_name,
            )
            hostile = hostile_npc_attr(self.legacy, mob)
            self.assertEqual(len(hostile), len(baseline) + FACTION_SPLICE_BYTES)

            # Everything except the mask and the five spliced bytes must be
            # untouched, and the splice must be the tagged faction u32.
            faction_bytes = bytes(
                self.legacy.u32tag(FACTION_TAG, FIELD_MOB_FACTION),
            )
            self.assertEqual(len(faction_bytes), FACTION_SPLICE_BYTES)

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
            baseline_mask = int.from_bytes(
                baseline[mask_at:mask_at + 2], "little",
            )
            hostile_mask = int.from_bytes(
                rebuilt[mask_at:mask_at + 2], "little",
            )
            self.assertEqual(hostile_mask, baseline_mask | BASIC_BIT_FACTION)
            self.assertTrue(baseline_mask & BASIC_BIT_NAME)
            self.assertFalse(baseline_mask & BASIC_BIT_FACTION)

            # With the mask restored, the rest is byte-identical.
            restored = (
                rebuilt[:mask_at]
                + baseline[mask_at:mask_at + 2]
                + rebuilt[mask_at + 2:]
            )
            self.assertEqual(restored, baseline)

    def test_the_derived_columns_re_derive_two_frozen_constants(self) -> None:
        assert_frozen_controls(self.legacy)
        control = {
            mob.placement_index: mob for mob in load_roster()
        }[self.legacy.V112_MONSTER_INDEX]
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
            # Same row, mined twice by two different pipelines.
            self.assertEqual(mob.template_id, placement.template_id)
            self.assertEqual(mob.visual_preset, placement.visual_preset)
            self.assertEqual(mob.x, placement.x)
            self.assertEqual(mob.y, placement.y)
            self.assertEqual(mob.z, placement.z)
            self.assertEqual(mob.actor_identity, placement.actor_identity)
        shared = overlapping_identities(tuple(census))
        self.assertEqual(len(shared), len(load_roster()))

    # --- the roster ------------------------------------------------------

    def test_the_roster_is_the_mined_thirteen(self) -> None:
        roster = load_roster()
        self.assertEqual(len(roster), 13)
        self.assertEqual(len({mob.template_id for mob in roster}), 10)
        self.assertEqual(
            hostile_placement_indices(),
            (12, 30, 33, 58, 59, 60, 63, 95, 103, 105, 107, 109, 132),
        )
        for mob in roster:
            self.assertGreater(mob.max_hp, 0)
            self.assertGreater(mob.rank, 0)
            self.assertGreater(mob.ai_combat, 0)
            self.assertTrue(mob.display_name.isascii())
            self.assertTrue(mob.visual_preset.isascii())

    def test_load_roster_defaults_to_bg0001_and_tags_every_mob_with_its_scene(
            self) -> None:
        # ADDED this round (PANYA-DECISION 2026-08-27T20:10+07:00): the
        # no-argument call must be byte-for-byte the same roster it always
        # was, and every returned mob must carry the SAME scene string the
        # generated module itself declares, not a hardcoded literal.
        roster = load_roster()
        self.assertEqual(len(roster), 13)
        for mob in roster:
            self.assertEqual(mob.scene, field_mob_tables.SCENE)
            self.assertEqual(mob.scene, "bg0001")

    def test_load_roster_can_load_bg0002s_own_mined_roster(self) -> None:
        from pirateforce_foundation import field_mob_tables_bg0002
        bg0002_roster = load_roster(scene=field_mobs.BG0002_SCENE)
        self.assertEqual(field_mobs.BG0002_SCENE, "Bg0002")
        self.assertEqual(len(bg0002_roster), 17)
        self.assertEqual(
            len({mob.template_id for mob in bg0002_roster}), 4)
        self.assertEqual(
            {mob.template_id for mob in bg0002_roster}, {31, 34, 35, 103})
        for mob in bg0002_roster:
            self.assertEqual(mob.scene, field_mob_tables_bg0002.SCENE)
            self.assertEqual(mob.scene, "Bg0002")

    def test_bg0001_and_bg0002_actor_identities_are_NOT_disjoint_a_real_collision(
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
        self.assertEqual(shared, {0x203B, 0x203C, 0x203D, 0x2060})

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
            ["mobs", "mobs_tip", "placements", "standard_mob"],
        )
        for digest in field_mob_tables.SOURCE_DIGESTS.values():
            self.assertEqual(len(digest), 64)
            int(digest, 16)
        census = field_mob_tables.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], 115)
        # On THIS scene the four readings agree.  They do not agree over the
        # whole MOBS table, which is why the census is carried at all.
        self.assertEqual(census["rank"], 13)
        self.assertEqual(census["ai_combat"], 13)
        self.assertEqual(census["drops_normal"], 13)
        self.assertEqual(census["rank_and_ai_combat"], 13)

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
        self.assertEqual(generation.mob_count, 13)
        self.assertEqual(generation.faction, FIELD_MOB_FACTION)
        self.assertEqual(len(set(generation.actor_identities)), 13)
        self.assertEqual(generation.frame, self.legacy.frame_pc(generation.pc))
        self.assertGreater(generation.frame_bytes, generation.pc_bytes)
        ordered = nearest_first(self.spawn)
        self.assertEqual(
            generation.placement_indices,
            tuple(mob.placement_index for mob in ordered),
        )

    def test_a_shorter_collection_is_a_prefix_of_the_full_one(self) -> None:
        full = build_field_mob_population(self.legacy, self.spawn)
        for count in (1, 4, 12):
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
        class Drifted:
            def __getattr__(self, name):
                return getattr(FieldMobTests.legacy, name)
            V117_P30_EXACT_HP = 1

        with self.assertRaises(FieldMobContractError):
            assert_frozen_controls(Drifted())

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
        self.assertEqual(
            importers,
            ["mob_ai_control.py", "mob_combat.py", "mob_death.py",
             "mob_diag_multi_object.py", "mob_loot.py",
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
        self.assertEqual(len(committed["roster"]), 13)
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_report_is_ascii_safe(self) -> None:
        report = roster_report(self.legacy, self.spawn)
        self.assertEqual(report["mob_count"], 13)
        self.assertEqual(report["distinct_templates"], 10)
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
        collisions = cross_scene_identity_collisions()
        by_pair: dict[tuple[str, str], list[dict]] = {}
        for row in collisions:
            by_pair.setdefault((row["scene_a"], row["scene_b"]), []).append(row)
        self.assertEqual(sorted(by_pair), [("bg0001", "Bg0002")])
        self.assertEqual(len(by_pair[("bg0001", "Bg0002")]), 4)
        self.assertEqual(len(collisions), 4)

    def test_bg0001_vs_bg0002_matches_the_identities_the_load_roster_test_pins(
            self) -> None:
        # cross-check against the OTHER test's independently-computed set
        # (test_bg0001_and_bg0002_actor_identities_are_NOT_disjoint_a_real_
        # collision above) rather than trusting one number twice.
        collisions = cross_scene_identity_collisions(
            (field_mob_tables, field_mob_tables_bg0002))
        found = {row["actor_identity"] for row in collisions}
        self.assertEqual(found, {0x203B, 0x203C, 0x203D, 0x2060})
        by_placement = {row["placement_index"]: row for row in collisions}
        self.assertEqual(by_placement[58]["name_a"], "Jungle Big Tiger")
        self.assertEqual(by_placement[58]["name_b"], "Fighting Fish soldier")
        self.assertEqual(by_placement[95]["name_a"], "An Gebo Little Firebird")
        self.assertEqual(by_placement[95]["name_b"], "Orc Chief")

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
        collisions = cross_scene_identity_collisions(
            (field_mob_tables, field_mob_tables_bg0015))
        self.assertEqual(len(collisions), 3)
        for row in collisions:
            self.assertEqual({row["scene_a"], row["scene_b"]}, {"bg0001", "Bg0015"})

    def test_all_three_known_tables_together_find_ten_pairwise_collisions(
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
        self.assertEqual(
            sorted(by_pair),
            [("Bg0002", "Bg0015"), ("bg0001", "Bg0002"), ("bg0001", "Bg0015")],
        )
        self.assertEqual(len(by_pair[("bg0001", "Bg0002")]), 4)
        self.assertEqual(len(by_pair[("bg0001", "Bg0015")]), 3)
        self.assertEqual(len(by_pair[("Bg0002", "Bg0015")]), 3)
        self.assertEqual(len(collisions), 10)

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
        self.assertEqual(lines[0], "FIELD_MOB_CROSS_SCENE_IDENTITY_COLLISIONS count=4")
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


if __name__ == "__main__":
    unittest.main()
