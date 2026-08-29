"""LANE-B round wmomy7: the hostile census override, and the owner's refusal.

The claim under test, in one sentence: the monsters this lane ships in a
scene get the hostile-faction body in that scene's OWN census, and every
row this lane ships has a body in that census to get.

The second half is the one this round added, and it is not decoration.
Before this round scene 2 shipped 17 roster rows against a 97-actor census
that carried only 12 of them; the other five were placements the owner had
ruled "do not place", and the combat ledger opened on them anyway -- so the
server accepted strikes against a 38,728 HP monster no client had ever been
sent a body for.  Neither side is wrong on its own; only the comparison
shows it.  ``test_the_ledger_no_longer_opens_on_a_monster_with_no_body``
is the pin for that.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dataclasses import replace

from pirateforce_foundation import field_mob_tables_bg0002 as fmt2
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_census_hostility as mch
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_death
from pirateforce_foundation import scene2_prison_exile_tables as tables
from pirateforce_foundation import world_population
from pirateforce_foundation import world_population_bg0002 as wp2
from pirateforce_foundation.legacy_bridge import load_legacy

BG0002_SCENE_ID = 2
# The owner's whole ruling on the n_id 101-104 block.  This lane's table
# ships only the five in ``OWNER_REFUSED_SHIPPED_TODAY``; the other three
# are carried so a future regeneration cannot quietly start shipping them.
OWNER_REFUSED = (89, 90, 92, 93, 94, 95, 96, 97)
OWNER_REFUSED_SHIPPED_TODAY = (92, 93, 94, 95, 96)
# 0x2000 + placement_index + 1, the identity rule field_mobs documents.
GHOST_IDENTITY = 0x205D
SUBJECT_IDENTITY = 0x2033  # Tornado Eagle, placement 50


class OwnerRefusalTests(unittest.TestCase):
    """The filter at ``load_roster``, and the guard that keeps it honest."""

    def test_the_owner_refused_placements_are_not_shipped(self):
        shipped = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        indices = {mob.placement_index for mob in shipped}
        for refused in OWNER_REFUSED:
            self.assertNotIn(refused, indices)
        self.assertEqual(len(shipped), 12)

    def test_only_five_of_the_eight_ruled_placements_were_ever_shipped(self):
        # Keeps the two numbers from being conflated: the ruling is eight
        # placements wide, the table this lane generated resolves five of
        # them.  A future regeneration changing that is a real event, and
        # this pin is where it shows up.
        table = {row[0] for row in fmt2.SHIPPED_PLACEMENTS}
        self.assertEqual(
            table & set(OWNER_REFUSED), set(OWNER_REFUSED_SHIPPED_TODAY),
        )

    def test_the_generated_table_still_carries_all_seventeen_rows(self):
        # The filter narrows what this lane SHIPS.  It must not quietly
        # edit the generated data, which is the mining result and is
        # regenerated from the bridge clone.  These two numbers being
        # different is the point, not an inconsistency.
        self.assertEqual(len(fmt2.HOSTILE_PLACEMENTS), 17)
        parsed = field_mobs._parse_hostile_placements(fmt2)
        self.assertEqual(len(parsed), 17)

    def test_bg0001_has_no_refusal_and_is_byte_for_byte_unchanged(self):
        self.assertEqual(field_mobs.owner_refused_placements('bg0001'), ())
        roster = field_mobs.load_roster()
        self.assertEqual(
            roster, field_mobs._parse_hostile_placements(
                sys.modules['pirateforce_foundation.field_mob_tables']
            )
        )

    def test_the_refusal_literal_agrees_with_the_owners_own_table(self):
        mch.assert_owner_refusals_match_scene_source()

    def test_the_source_table_really_does_carry_the_owner_ruling(self):
        # Pin the join's far side.  Without this the guard above could pass
        # against a table that had lost the ruling entirely.
        ruled = {
            row[0] for row in tables.UNRESOLVED_PLACEMENTS
            if 'owner_says_do_not_place' in row[-1]
        }
        self.assertEqual(ruled, set(OWNER_REFUSED))

    def test_the_drift_guard_fires_when_this_lane_refuses_too_few(self):
        # A guard nobody has watched fail is not a guard.  Drive it.
        original = dict(field_mobs.OWNER_REFUSED_PLACEMENTS)
        field_mobs.OWNER_REFUSED_PLACEMENTS['Bg0002'] = (92, 93)
        try:
            with self.assertRaises(mch.CensusHostilityError) as caught:
                mch.assert_owner_refusals_match_scene_source()
            self.assertIn("owner-refusal drift", str(caught.exception))
        finally:
            field_mobs.OWNER_REFUSED_PLACEMENTS.clear()
            field_mobs.OWNER_REFUSED_PLACEMENTS.update(original)

    def test_the_drift_guard_fires_when_this_lane_refuses_too_many(self):
        original = dict(field_mobs.OWNER_REFUSED_PLACEMENTS)
        field_mobs.OWNER_REFUSED_PLACEMENTS['Bg0002'] = OWNER_REFUSED + (50,)
        try:
            with self.assertRaises(mch.CensusHostilityError):
                mch.assert_owner_refusals_match_scene_source()
        finally:
            field_mobs.OWNER_REFUSED_PLACEMENTS.clear()
            field_mobs.OWNER_REFUSED_PLACEMENTS.update(original)

    def test_a_filter_that_would_empty_a_roster_refuses_instead(self):
        original = dict(field_mobs.OWNER_REFUSED_PLACEMENTS)
        every = tuple(row[0] for row in fmt2.SHIPPED_PLACEMENTS)
        field_mobs.OWNER_REFUSED_PLACEMENTS['Bg0002'] = every
        try:
            with self.assertRaises(field_mobs.FieldMobContractError) as caught:
                field_mobs.load_roster('Bg0002')
            self.assertIn("removes every row", str(caught.exception))
        finally:
            field_mobs.OWNER_REFUSED_PLACEMENTS.clear()
            field_mobs.OWNER_REFUSED_PLACEMENTS.update(original)


class LedgerTests(unittest.TestCase):
    def test_the_ledger_no_longer_opens_on_a_monster_with_no_body(self):
        # THE defect of this round, pinned from both sides.
        unfiltered = field_mobs._parse_hostile_placements(fmt2)
        before = mob_combat.open_ledger(unfiltered)
        self.assertIn(GHOST_IDENTITY, set(before.identities()))
        self.assertEqual(before.balance_of(GHOST_IDENTITY).max_hp, 38728)

        after = mob_combat.open_ledger(
            field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        )
        self.assertNotIn(GHOST_IDENTITY, set(after.identities()))
        with self.assertRaises(mob_combat.MobCombatContractError) as caught:
            after.balance_of(GHOST_IDENTITY)
        self.assertIn("target_not_in_ledger", str(caught.exception))


class CensusHostilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            tables.SCENE2_REGISTRY_SPAWN_X,
            tables.SCENE2_REGISTRY_SPAWN_Y,
            1680.0,
        )
        cls.generation = wp2.build_bg0002_population(
            cls.legacy, cls.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )

    def _override(self):
        register = mob_death.DeathRegister()
        ledger = mob_combat.open_ledger(
            field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        )
        return mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, register, ledger=ledger,
        )

    def test_every_shipped_monster_has_a_census_body(self):
        report = mch.census_backing_report(
            BG0002_SCENE_ID, self.generation.actor_identities,
        )
        self.assertEqual(report["unbacked"], ())
        self.assertTrue(report["fully_backed"])
        self.assertEqual(report["roster_count"], 12)
        self.assertEqual(report["backed_count"], 12)
        self.assertEqual(report["census_count"], 97)

    def test_the_report_actually_detects_an_unbacked_row(self):
        # Same reasoning as the drift guard: prove the report can fail.
        short = tuple(
            i for i in self.generation.actor_identities
            if i != SUBJECT_IDENTITY
        )
        report = mch.census_backing_report(BG0002_SCENE_ID, short)
        self.assertEqual(report["unbacked"], (SUBJECT_IDENTITY,))
        self.assertFalse(report["fully_backed"])

    def test_the_override_covers_every_shipped_monster(self):
        override = self._override()
        self.assertEqual(len(override), 12)
        coverage = mob_death.roster_override_coverage(
            override, self.generation.actor_identities,
        )
        self.assertEqual(coverage["missing"], ())
        self.assertEqual(coverage["matched_count"], 12)

    def test_the_ledger_is_actually_forwarded_and_not_dropped(self):
        # A MUTANT THAT SURVIVED the first draft of this file: changing
        # ``ledger=ledger`` to ``ledger=None`` inside
        # ``hostile_override_for_scene_id`` left the whole suite green,
        # because every other test here passes a ledger in which nothing has
        # been hit -- so forwarding it and dropping it produce identical
        # bytes, and the pin could not tell them apart.
        #
        # Not a cosmetic gap.  Dropping the ledger is exactly the failure
        # MOB-DEATH-001's wiring note named: a census rebuilt while a monster
        # is wounded heals it back to its ceiling.  To catch it the pin has
        # to wound something first.
        register = mob_death.DeathRegister()
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        ledger = mob_combat.open_ledger(roster)
        full = ledger.balance_of(SUBJECT_IDENTITY)
        wounded = ledger.with_balance(
            mob_combat.MobBalance(
                actor_identity=SUBJECT_IDENTITY,
                max_hp=full.max_hp,
                current_hp=full.max_hp // 2,
            )
        )
        self.assertLess(
            wounded.balance_of(SUBJECT_IDENTITY).current_hp, full.current_hp,
        )

        with_ledger = mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, register, ledger=wounded,
        )
        without = mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, register, ledger=None,
        )
        self.assertNotEqual(
            with_ledger[SUBJECT_IDENTITY], without[SUBJECT_IDENTITY],
            "the ledger was not forwarded: a wounded monster is being sent "
            "to the client at full HP",
        )
        # ...and only the wounded one differs, so this cannot pass by the
        # override having changed wholesale.
        for identity in with_ledger:
            if identity != SUBJECT_IDENTITY:
                self.assertEqual(with_ledger[identity], without[identity])

    def test_an_unaddressed_scene_overrides_nothing_and_does_not_fall_back(self):
        register = mob_death.DeathRegister()
        override = mch.hostile_override_for_scene_id(
            self.legacy, 999, register,
        )
        self.assertEqual(override, {})
        # The point of the pin: {} must not be bg0001's roster.
        self.assertNotEqual(len(override), len(field_mobs.load_roster()))
        # And this now runs through the REAL composer -- the early return it
        # used to short-circuit was removed as dead code (self-mutation M2),
        # so an empty roster reaching mob_death and coming back {} is the
        # measured path, not a shortcut around it.
        self.assertEqual(field_mobs.roster_for_scene_id(999), ())

    def test_the_faction_splice_reaches_the_wire(self):
        override = self._override()
        offset = world_population.WIRE_HEADER_BYTES
        entries = []
        for identity, length in zip(
                self.generation.actor_identities,
                self.generation.entry_bytes):
            original = self.generation.pc[offset:offset + length]
            entries.append(override.get(identity, original))
            offset += length
        self.assertEqual(offset, len(self.generation.pc))

        index = list(self.generation.actor_identities).index(SUBJECT_IDENTITY)
        self.assertIn(field_mobs.FACTION_SPLICE_BYTES, entries[index])
        self.assertGreater(
            len(entries[index]), self.generation.entry_bytes[index],
        )

        pc, frame = self.legacy.make_runtime_remote_actors(entries)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        after = replace(
            self.generation, pc=pc, frame=frame,
            entry_bytes=tuple(len(entry) for entry in entries),
        )
        # The census still describes the same 97 actors; only bodies moved.
        self.assertEqual(after.actor_count, self.generation.actor_count)
        self.assertEqual(
            after.actor_identities, self.generation.actor_identities,
        )
        self.assertGreater(len(after.pc), len(self.generation.pc))

    def test_an_untouched_actor_keeps_the_bytes_the_census_built(self):
        # The splice must be surgical: a non-roster actor is not rewritten.
        override = self._override()
        offset = world_population.WIRE_HEADER_BYTES
        for identity, length in zip(
                self.generation.actor_identities,
                self.generation.entry_bytes):
            if identity not in override:
                original = self.generation.pc[offset:offset + length]
                self.assertEqual(override.get(identity, original), original)
            offset += length

    def test_the_ledger_is_actually_forwarded_and_not_dropped(self):
        # A MUTANT THAT SURVIVED the first draft of this file: changing
        # ``ledger=ledger`` to ``ledger=None`` inside
        # ``hostile_override_for_scene_id`` left the whole suite green,
        # because every test here passed a ledger in which nothing had been
        # hit -- so forwarding it and dropping it produced identical bytes.
        #
        # That is not a cosmetic gap.  Dropping the ledger is exactly the
        # failure MOB-DEATH-001's wiring note named: a census rebuilt while
        # a monster is wounded heals it back to its ceiling.  The pin has to
        # wound something first, or it cannot tell the two apart.
        register = mob_death.DeathRegister()
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        subject = next(
            m for m in roster if m.actor_identity == SUBJECT_IDENTITY
        )
        ledger = mob_combat.open_ledger(roster)
        full = ledger.balance_of(SUBJECT_IDENTITY).current_hp
        wounded_ledger = ledger.with_balance(
            mob_combat.MobBalance(
                actor_identity=SUBJECT_IDENTITY,
                max_hp=ledger.balance_of(SUBJECT_IDENTITY).max_hp,
                current_hp=full // 2,
            )
        )
        self.assertLess(
            wounded_ledger.balance_of(SUBJECT_IDENTITY).current_hp, full,
        )

        with_ledger = mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, register, ledger=wounded_ledger,
        )
        without = mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, register, ledger=None,
        )
        # The wounded monster's body must differ; everyone else's must not.
        self.assertNotEqual(
            with_ledger[SUBJECT_IDENTITY], without[SUBJECT_IDENTITY],
            "the ledger was not forwarded: a wounded monster is being sent "
            "at full HP",
        )
        for identity in with_ledger:
            if identity != SUBJECT_IDENTITY:
                self.assertEqual(with_ledger[identity], without[identity])
        self.assertIsNotNone(subject)

    def test_the_console_line_is_one_ascii_line_in_the_pinned_shape(self):
        lines = mch.describe_census_hostility(
            BG0002_SCENE_ID, self.generation.actor_identities,
        )
        self.assertEqual(len(lines), 1)
        line = lines[0]
        line.encode("ascii")
        self.assertEqual("\n", "\n")  # documents the single-line contract
        self.assertNotIn("\n", line)
        self.assertEqual(
            line,
            "MOB_CENSUS_HOSTILITY scene_id=2 scene=Bg0002 roster=12 "
            "backed=12 unbacked=none",
        )

    def test_the_console_line_names_an_unbacked_identity_rather_than_hiding_it(self):
        short = tuple(
            i for i in self.generation.actor_identities
            if i != SUBJECT_IDENTITY
        )
        line = mch.describe_census_hostility(BG0002_SCENE_ID, short)[0]
        self.assertIn("unbacked=0x2033", line)
        self.assertIn("backed=11", line)


if __name__ == "__main__":
    unittest.main()
