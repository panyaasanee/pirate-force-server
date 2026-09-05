"""LANE-B: Bg0015's own hostile entry-byte composer, pre-wire.

Three tests carry this file's weight:

``test_actor_identities_match_lane_As_measured_numbers`` cross-checks this
module's ``0x2000 + placement_index + 1`` output against the EXACT twelve
numbers lane A's letter
(``pf_bridge/notes_to_chief/20260831_2007_LANE-A-TO-LANE-B-scene14-hostile-
splice-design-proposal-re092.md``) measured independently, so the two lanes'
readings of the same formula cannot silently drift apart.

``test_overrides_reuse_hostile_actor_entry_byte_for_byte`` proves this module
does not re-derive the encoding: calling ``field_mobs.hostile_actor_entry``
directly on the same mob must produce bytes identical to what
``scene14_hostile_overrides`` puts in its dict.

``test_splice_proof_changes_exactly_the_twelve_identities_and_nothing_else``
is the end-to-end proof lane A's letter asked for: build a synthetic civilian
census, splice in this module's override, and show that exactly (and only)
the twelve hostile identities changed.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_hostile_bg0015 as hostile_bg0015
from pirateforce_foundation import field_mob_tables_bg0015
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_scene_recompose
from pirateforce_foundation.legacy_bridge import load_legacy


# Measured independently by LANE-A's letter (20260831_2007), reproduced here
# so the two lanes' readings of "0x2000 + placement_index + 1" are checked
# against each other rather than trusted once and copied.
LANE_A_MEASURED_IDENTITIES = {
    22: 0x2017, 24: 0x2019, 27: 0x201C, 29: 0x201E, 31: 0x2020, 44: 0x202D,
    45: 0x202E, 46: 0x202F, 47: 0x2030, 51: 0x2034, 70: 0x2047, 87: 0x2058,
}

# ROUND j5v7mu.  COO-DECISION 20260905_0545 withheld placement 87 (template
# 924, Carlos) from what this lane SHIPS, so the table above -- which is
# LANE-A's independent reading of the identity formula and stays whole
# because that is what it is for -- is no longer the same set as the
# override dict.  DERIVED from field_mobs rather than a second hand-typed
# eleven-entry literal, so the day the ruling is lifted this file follows.
WITHHELD_PLACEMENTS = set(field_mobs.lane_withheld_placements("Bg0015"))
SHIPPED_MEASURED_IDENTITIES = {
    index: identity
    for index, identity in LANE_A_MEASURED_IDENTITIES.items()
    if index not in WITHHELD_PLACEMENTS
}


class FieldMobHostileBg0015Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_module_flags_follow_the_project_convention(self) -> None:
        self.assertIs(hostile_bg0015.production_allowed, True)
        self.assertIs(hostile_bg0015.test_only, False)

    def test_roster_is_exactly_the_twelve_hostile_placements(self) -> None:
        roster = hostile_bg0015.scene14_hostile_roster()
        self.assertEqual(len(roster), 12)
        self.assertEqual(hostile_bg0015.scene14_hostile_count(), 12)
        self.assertEqual(
            sorted(mob.placement_index for mob in roster),
            sorted(row[0] for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS),
        )
        for mob in roster:
            self.assertEqual(mob.scene, "Bg0015")

    def test_default_placement_indices_are_the_shipped_eleven_sorted(
            self) -> None:
        # ~~the full twelve~~ IS STRUCK, ROUND j5v7mu: the default is the
        # table's twelve MINUS what field_mobs withholds, which is placement
        # 87 today (COO-DECISION 20260905_0545).  The literal below is what
        # the value must actually be -- a derived-only assertion would pass
        # against an empty tuple -- and the two-sided pin under it is what
        # says WHY the twelfth is gone.
        self.assertEqual(
            hostile_bg0015.DEFAULT_HOSTILE_PLACEMENT_INDICES,
            (22, 24, 27, 29, 31, 44, 45, 46, 47, 51, 70),
        )
        self.assertEqual(WITHHELD_PLACEMENTS, {87})
        self.assertEqual(
            set(hostile_bg0015.DEFAULT_HOSTILE_PLACEMENT_INDICES)
            | WITHHELD_PLACEMENTS,
            {row[0] for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS},
        )

    def test_the_default_and_the_live_roster_shrink_together(self) -> None:
        """The wmomy7 lesson, pinned across the two modules that must agree.

        A hostile body spliced into the census for a placement the combat
        ledger does not carry is a monster on a screen that no strike can
        reach; the reverse is a ledger row for a body nobody was sent.  The
        override default and ``load_roster`` are the two ends of that, so
        they are compared rather than each pinned to its own literal.
        """
        self.assertEqual(
            set(hostile_bg0015.DEFAULT_HOSTILE_PLACEMENT_INDICES),
            {mob.placement_index
             for mob in field_mobs.load_roster(scene="Bg0015")},
        )

    def test_actor_identities_match_lane_As_measured_numbers(self) -> None:
        roster = {
            mob.placement_index: mob
            for mob in hostile_bg0015.scene14_hostile_roster()
        }
        self.assertEqual(set(roster), set(LANE_A_MEASURED_IDENTITIES))
        for placement_index, expected_identity in LANE_A_MEASURED_IDENTITIES.items():
            mob = roster[placement_index]
            self.assertEqual(mob.actor_identity, expected_identity)
            # Same formula every other scene in this project already uses --
            # not a scene-14-specific rule.
            self.assertEqual(mob.actor_identity, 0x2000 + placement_index + 1)

    def test_overrides_reuse_hostile_actor_entry_byte_for_byte(self) -> None:
        overrides = hostile_bg0015.scene14_hostile_overrides(self.legacy)
        self.assertEqual(len(overrides), len(SHIPPED_MEASURED_IDENTITIES))
        self.assertEqual(len(overrides), 11)
        for mob in hostile_bg0015.scene14_hostile_roster():
            direct = field_mobs.hostile_actor_entry(self.legacy, mob)
            if mob.placement_index in WITHHELD_PLACEMENTS:
                # The encoder still produces his body on request -- the
                # gates module asks for exactly that -- he is simply not in
                # the default dict any more.
                self.assertNotIn(mob.actor_identity, overrides)
                continue
            self.assertEqual(overrides[mob.actor_identity], direct)

    def test_overrides_keys_are_exactly_the_shipped_measured_identities(
            self) -> None:
        overrides = hostile_bg0015.scene14_hostile_overrides(self.legacy)
        self.assertEqual(
            set(overrides), set(SHIPPED_MEASURED_IDENTITIES.values()),
        )
        # AND THE WITHHELD ONE IS NAMED, not merely absent from a set that
        # would also be satisfied by an override dict missing something else.
        self.assertNotIn(0x2058, overrides)

    def test_narrowing_placement_indices_narrows_the_dict_without_error(self) -> None:
        overrides = hostile_bg0015.scene14_hostile_overrides(
            self.legacy, placement_indices=(22, 87),
        )
        self.assertEqual(set(overrides), {0x2017, 0x2058})

    def test_an_unknown_placement_index_is_refused_by_name(self) -> None:
        with self.assertRaises(hostile_bg0015.FieldMobHostileBg0015Error):
            hostile_bg0015.scene14_hostile_overrides(
                self.legacy, placement_indices=(22, 999),
            )

    def test_empty_placement_indices_is_refused_by_name(self) -> None:
        with self.assertRaises(hostile_bg0015.FieldMobHostileBg0015Error):
            hostile_bg0015.scene14_hostile_overrides(
                self.legacy, placement_indices=(),
            )

    def test_splice_proof_changes_exactly_the_shipped_identities_and_nothing_else(
            self) -> None:
        # ~~the twelve~~ IS STRUCK, ROUND j5v7mu.  The synthetic census this
        # proof builds still carries all TWELVE placements as civilians --
        # that half is about the recompose plumbing and is unchanged -- but
        # the override dict is the shipped eleven, so the withheld row stays
        # a civilian body through the splice.  That is the whole visible
        # effect of COO-DECISION 20260905_0545 in one assertion.
        proof = hostile_bg0015.scene14_civilian_then_hostile_splice_proof(
            self.legacy,
        )
        civilian = proof["civilian"]
        spliced = proof["spliced"]
        self.assertEqual(
            proof["override_count"], len(SHIPPED_MEASURED_IDENTITIES))
        self.assertEqual(proof["override_count"], 11)
        self.assertEqual(
            set(proof["changed_identities"]),
            set(SHIPPED_MEASURED_IDENTITIES.values()),
        )
        # The collection is still the same 12 identities, in the same order.
        self.assertEqual(spliced.actor_identities, civilian.actor_identities)
        self.assertEqual(len(spliced.actor_identities), 12)
        # Every entry actually changed bytes (civilian body != hostile body):
        # decompose both pc buffers the same way splice_identity_override
        # does internally, entry by entry, and diff them.
        offset_civ = 0
        offset_spliced = 0
        civilian_entries = []
        spliced_entries = []
        for length in civilian.entry_bytes:
            civilian_entries.append(
                civilian.pc[offset_civ:offset_civ + length])
            offset_civ += length
        for length in spliced.entry_bytes:
            spliced_entries.append(
                spliced.pc[offset_spliced:offset_spliced + length])
            offset_spliced += length
        # ROUND j5v7mu: the withheld identity's entry must be UNCHANGED and
        # every other one changed -- pinned from both sides, so neither "he
        # was spliced after all" nor "nothing was spliced" can pass here.
        withheld_identities = {
            LANE_A_MEASURED_IDENTITIES[index]
            for index in WITHHELD_PLACEMENTS
        }
        untouched = 0
        for identity, civ_entry, spliced_entry in zip(
                civilian.actor_identities, civilian_entries, spliced_entries):
            if identity in withheld_identities:
                self.assertEqual(civ_entry, spliced_entry)
                untouched += 1
            else:
                self.assertNotEqual(civ_entry, spliced_entry)
        self.assertEqual(untouched, len(withheld_identities))
        self.assertEqual(
            spliced.frame, self.legacy.frame_pc(spliced.pc),
        )

    def test_splice_proof_is_reachable_through_the_generic_recompose_splice(
            self) -> None:
        # Not a second implementation: this calls the SAME function the
        # proof above calls, confirming the module this file exercises is
        # not shadowing mob_scene_recompose with a private copy.
        overrides = hostile_bg0015.scene14_hostile_overrides(self.legacy)
        proof = hostile_bg0015.scene14_civilian_then_hostile_splice_proof(
            self.legacy,
        )
        spliced_again = mob_scene_recompose.splice_identity_override(
            self.legacy, proof["civilian"], overrides,
        )
        self.assertEqual(spliced_again.pc, proof["spliced"].pc)


if __name__ == "__main__":
    unittest.main()
