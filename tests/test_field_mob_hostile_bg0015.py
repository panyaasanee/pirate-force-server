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

    def test_default_placement_indices_are_the_full_twelve_sorted(self) -> None:
        self.assertEqual(
            hostile_bg0015.DEFAULT_HOSTILE_PLACEMENT_INDICES,
            (22, 24, 27, 29, 31, 44, 45, 46, 47, 51, 70, 87),
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
        self.assertEqual(len(overrides), 12)
        for mob in hostile_bg0015.scene14_hostile_roster():
            direct = field_mobs.hostile_actor_entry(self.legacy, mob)
            self.assertEqual(overrides[mob.actor_identity], direct)

    def test_overrides_keys_are_exactly_the_measured_identities(self) -> None:
        overrides = hostile_bg0015.scene14_hostile_overrides(self.legacy)
        self.assertEqual(
            set(overrides), set(LANE_A_MEASURED_IDENTITIES.values()),
        )

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

    def test_splice_proof_changes_exactly_the_twelve_identities_and_nothing_else(
            self) -> None:
        proof = hostile_bg0015.scene14_civilian_then_hostile_splice_proof(
            self.legacy,
        )
        civilian = proof["civilian"]
        spliced = proof["spliced"]
        self.assertEqual(proof["override_count"], 12)
        self.assertEqual(
            set(proof["changed_identities"]),
            set(LANE_A_MEASURED_IDENTITIES.values()),
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
        for civ_entry, spliced_entry in zip(civilian_entries, spliced_entries):
            self.assertNotEqual(civ_entry, spliced_entry)
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
