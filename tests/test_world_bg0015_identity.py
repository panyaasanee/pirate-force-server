"""LANE-A M3: Bg0015's crosswalk, and the controls that make it believable.

The four controls in ``world_bg0015_identity``'s docstring are prose there and
executable here.  Two things this file deliberately does NOT do:

* It does not re-derive the table from the client tables.  Those six files
  live in the pf_bridge clone, not in this repository, so a test here cannot
  open them; ``SOURCE_SHA256`` is recorded provenance for a bridge-side
  re-mine, and this file says so rather than pretending to check it.
* It does not claim any of these actors has been SEEN.  Nobody has been in
  this scene.  Everything below is wire/DB-layer and table-layer evidence;
  the client-observable layer is ``GT-134`` and it is empty today.
"""
from __future__ import annotations

import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_tables_bg0015  # noqa: E402
from pirateforce_foundation import world_bg0015_identity as identity  # noqa: E402


class Bg0015TableShape(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 14)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg0015")
        # A direct SCENE_NAME selector, not one of RE-128's 240 instance
        # scenes -- the whole reason M3 could start at this scene.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 14)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 41)
        self.assertEqual(len(identity.UNRESOLVED), 10)
        self.assertEqual(identity.PLACEMENT_COUNT, 91)
        self.assertEqual(len(identity.shippable_placements()), 81)
        self.assertEqual(len(identity.unshippable_placements()), 10)

    def test_control_1_scene_sets_and_cline_keys_are_the_same_51(self) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(len(table_sets), 51)
        self.assertEqual(scene_sets, table_sets)
        # And the 101..115 half really is there: a literal 1..N key block
        # could not produce it.
        self.assertTrue({101, 108, 115} <= table_sets)

    def test_control_2_is_recorded_with_every_row_including_the_five(
        self,
    ) -> None:
        # FOURTEEN scenes have a direct selector and a declared level, and
        # all fourteen are in the table.  The first draft carried eight and
        # called it "every scene that has both" -- selection on the
        # dependent variable, the exact mistake that killed this lane's
        # dense/sparse rule.  This test asserts the table is UNFILTERED
        # before anything is asserted about the result.
        self.assertEqual(len(identity.SCENE_LEVEL_CONTROL), 14)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 100)
        self.assertEqual(
            identity.SCENE_LEVEL_CONTROL["Bg0015"], (14, 100, 105.0, 20.0))

    def test_control_2_fails_on_five_of_the_fourteen_and_says_which(
        self,
    ) -> None:
        # The five that go against this module, asserted AS exceptions: if a
        # regeneration ever makes them quietly agree, that is a regeneration
        # to distrust, and this test is what notices.
        for scene in identity.SCENE_LEVEL_CONTROL_AGAINST:
            _type, declared, cline, set_number = (
                identity.SCENE_LEVEL_CONTROL[scene])
            with self.subTest(scene=scene):
                self.assertGreaterEqual(
                    abs(cline - declared), abs(set_number - declared))
        # BG0003 is the one that matters: not a 3000 scene, a plain island,
        # and Bg0015's closest structural twin (51 sets, exact key equality).
        self.assertIn("BG0003", identity.SCENE_LEVEL_CONTROL_AGAINST)
        self.assertEqual(
            identity.SCENE_LEVEL_CONTROL["BG0003"], (3, 25, 35.0, 20.0))

    def test_control_2_is_reproduced_without_any_placement_file(self) -> None:
        """NULL A, the control this round did not run and pf-adversary did.

        The CLINE-median column reproduces from the CLINE block alone, with
        no placements opened at all -- so control 2 measures which BLOCK was
        picked, not this scene's placements.  Pinned here so nobody can
        quote the control as per-placement evidence again.
        """
        for scene, (cline_type, declared, cline, set_number) in (
            identity.SCENE_LEVEL_CONTROL.items()
        ):
            null_a = identity.SCENE_LEVEL_CONTROL_NULL_A[cline_type]
            with self.subTest(scene=scene):
                # The placement-free column lands within 5 levels of the
                # placement-weighted one on every scene, and on Bg0015 it is
                # the same number.  Whatever control 2 measures, it is not
                # this scene's placements.
                self.assertLessEqual(abs(null_a - cline), 5.0)
                # And it beats the set-number reading in exactly the same
                # places the real column does -- same verdict, no placements.
                self.assertEqual(
                    abs(null_a - declared) < abs(set_number - declared),
                    abs(cline - declared) < abs(set_number - declared))
        self.assertEqual(identity.SCENE_LEVEL_CONTROL_NULL_A[14], 105.0)

    def test_the_half_of_the_finding_that_survives_everywhere(self) -> None:
        # The set-number reading carries no scene information on ANY of the
        # fourteen, sea or land: it sits near 20 whatever the scene declares.
        # This is an argument against the OLD reading, not for this one.
        for scene, row in identity.SCENE_LEVEL_CONTROL.items():
            with self.subTest(scene=scene):
                self.assertLess(row[3], 40.0)

    def test_control_3_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())
        for template_id, row in identity.IDENTITIES.items():
            self.assertNotEqual(template_id, row.mobs_n_id)

    def test_every_shipped_row_is_ascii_and_carries_a_body(self) -> None:
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                self.assertTrue(row.outfit.isascii() and row.outfit)
                self.assertTrue(row.name.isascii() and row.name)
                self.assertNotIn(";", row.outfit)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_the_ten_dropped_placements_each_name_a_reason(self) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["template_id"] for row in rows),
            [1, 101, 102, 103, 104, 105, 106, 107, 108, 115])
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
                self.assertGreater(row["leader_n_id"], 0)

    def test_identity_for_never_substitutes(self) -> None:
        # The ten unresolved sets come back as None, not as a fallback, and
        # never as the Mob-Set number GT-078 proved wrong on screen.
        for template_id in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(template_id))
        self.assertEqual(identity.identity_for(34).name, "Hell Ghoul")
        self.assertEqual(identity.identity_for(34).mobs_n_id, 354)
        # COO-DECISION 2026-08-28T22:50 condition (a): every value carries
        # its source line.  This is that line -- the CLINE row a second
        # party opens to check the pairing this module claims.
        self.assertEqual(identity.identity_for(34).cline_row_id, 3433)
        for row in identity.IDENTITIES.values():
            self.assertGreater(row.cline_row_id, 0)

    def test_multi_variant_outfits_ship_their_first_variant(self) -> None:
        # Ten sets list two avatar templates; the shipped column carries the
        # first and the whole string is kept.  [LANE-A ASSUMPTION]
        self.assertEqual(len(identity.MULTI_VARIANT_OUTFITS), 10)
        by_n_id = {row.mobs_n_id: row for row in identity.IDENTITIES.values()}
        for n_id, whole in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(n_id=n_id):
                self.assertIn(";", whole)
                self.assertEqual(by_n_id[n_id].outfit, whole.split(";")[0])
        # And it is not a corner case here the way it was for scene 1: this
        # is nearly half the island.
        affected = [p for p in identity.shippable_placements()
                    if p.n_id in identity.MULTI_VARIANT_OUTFITS]
        self.assertEqual(len(affected), 45)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_self_check_refuses_a_drifted_table(self) -> None:
        # The guard is not decoration: break the shape and import-time refuses.
        original = identity._RESOLVED_ROWS
        try:
            identity._RESOLVED_ROWS = original[:-1]
            with self.assertRaises(identity.Bg0015IdentityError):
                identity._self_check()
        finally:
            identity._RESOLVED_ROWS = original
        identity._self_check()


    def test_the_map_prop_row_is_recorded_rather_than_quietly_shipped(
        self,
    ) -> None:
        # Set 111 fails control 4's own smell test (a level-1, 106-HP map
        # prop on a level-100 volcano) and control 4 did not notice --
        # pf-adversary did.  It still ships, because a new drop rule with no
        # control under it is what this round was beaten for; what changed is
        # that it is named, here and in GT-134.
        self.assertEqual(sorted(identity.MAP_PROP_ROWS), [111])
        row = identity.IDENTITIES[111]
        self.assertEqual(row.mobs_n_id, 923)
        self.assertTrue(row.outfit.startswith("MAP"))
        self.assertEqual(row.level, 1)
        shipped = {p.template_id for p in identity.shippable_placements()}
        self.assertIn(111, shipped)


class CollidesWithACommittedTableTest(unittest.TestCase):
    """The overlap with field_mob_tables_bg0015, which is already at HEAD.

    Asserted rather than described, because the first draft of this round
    did not open that file at all -- the repo's own artifact for this exact
    scene.  Both modules derive actor_identity = 0x2000 + index + 1 for
    scene 14, so on the day both are sent the later collection replaces the
    earlier by omission (RE-092) and one identity silently wins.  This test
    exists so that day cannot arrive unannounced.
    """

    @staticmethod
    def _conflicts():
        # Computed HERE, not in src/: COO-DECISION 2026-08-26T12:46 keeps
        # field_mob_tables_bg0015 unimported from src/ and a guard test
        # enforces it.  Lane B's own tests import it the same way.
        mine = {p.placement_index: p
                for p in identity.shippable_placements()}
        out = {}
        for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS:
            index, template_id = row[0], row[1]
            placement = mine.get(index)
            if placement is None:
                continue
            out[index] = {
                "actor_identity": placement.actor_identity,
                "theirs": (template_id, row[6]),
                "ours": (placement.n_id, placement.display_name),
                # Added by LANE-A round 8ubiku when confirming lane B's
                # rewrite: rows 2..4 of their tuple are the placement XYZ.
                "theirs_xyz": (row[2], row[3], row[4]),
                "ours_xyz": (placement.x, placement.y, placement.z),
            }
        return out

    def test_the_scene_is_the_same_scene(self) -> None:
        self.assertEqual(field_mob_tables_bg0015.SCENE, "Bg0015")
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg0015")

    # ~~test_sixteen_placements_have_two_committed_identities~~ and
    # ~~test_the_other_tables_reading_is_the_one_gt078_rejected~~ --
    # ~~[LANE-B แก้ไฟล์ของสาย A - รอสาย A ยืนยัน]~~ **CONFIRMED BY LANE-A,
    # round 8ubiku (2026-08-29T07:4x+07:00)** -- EDITED BY LANE-B, round
    # ua236k, and this note is here because this file is lane A's.
    #
    # Lane A re-measured the claim at HEAD before accepting it, rather than
    # accepting a letter that said this lane's problem was solved: the two
    # tables share 12 placements, agree on n_ID, name AND XYZ at all 12, and
    # exactly one member of COLLIDING_PLACEMENTS (70) is still in lane B's
    # table.  The rewrite is kept as lane B wrote it, with one addition
    # below (the XYZ leg), because lane B pinned the identity agreement and
    # not the position agreement - and two tables that name the same monster
    # at two different points would still be a collision.
    #
    # Both tests asserted that field_mob_tables_bg0015 disagreed with this
    # module: sixteen placements with two committed identities, theirs read
    # as a raw Mob-Set number.  That disagreement was real and this file was
    # right to pin it.  It is GONE, and not because anybody edited around
    # it: COO-DECISION 20260829_0345 made cline the project's one identity
    # rule, and lane B re-mined its table through the crosswalk in round
    # ua236k.  The two tables now agree on every placement they share.
    #
    # Asserting a disagreement that no longer exists is a red that means
    # "the good outcome happened", so the tests below assert the AGREEMENT
    # instead -- which is the stronger pin, and the one lane A's letter
    # 20260829_0014 was really asking for.  If lane A wants this stated
    # differently, this is the paragraph to rewrite; lane B changed no other
    # line of this file, and no line of world_bg0015_identity.py.

    def test_the_two_committed_tables_now_agree_on_every_shared_placement(
            self) -> None:
        conflicts = self._conflicts()
        self.assertEqual(
            sorted(conflicts),
            [22, 24, 27, 29, 31, 44, 45, 46, 47, 51, 70, 87],
            "the set of placements the two tables share moved; that is a "
            "roster change in one of them, not an identity-rule question",
        )
        for index, row in sorted(conflicts.items()):
            with self.subTest(placement=index):
                self.assertEqual(
                    row["theirs"], row["ours"],
                    "field_mob_tables_bg0015 and world_bg0015_identity "
                    "disagree about placement %d again.  Two independently "
                    "mined tables for one scene are only worth having while "
                    "they are derived the same way (COO-DECISION "
                    "20260829_0345: cline, one rule for every scene)."
                    % (index,),
                )
                self.assertEqual(row["actor_identity"], 0x2000 + index + 1)
                # LANE-A round 8ubiku.  Agreeing on WHO is at a placement is
                # not agreeing on WHERE it stands: two tables naming one
                # monster at two points would still put two actors on the
                # wire at one identity, which is the collision this class
                # exists for.  Measured equal to the float at all 12 today.
                self.assertEqual(
                    row["theirs_xyz"], row["ours_xyz"],
                    "the two tables agree on the identity of placement %d "
                    "but not on its position" % (index,),
                )

    def test_both_readings_are_the_crosswalk_and_neither_is_the_raw_set_number(
            self) -> None:
        # ~~Their template_id IS the Mob-Set number, read straight as a
        # MOBS.n_ID.  Ours is the CLINE-resolved leader.~~  Both are the
        # CLINE-resolved leader now.  A Mob-Set number for this scene is in
        # 1..115; a type-14 leader id is not, so the bound below is what
        # tells the two readings apart, and it is the reading GT-078
        # rejected that must NOT come back.
        for index, row in self._conflicts().items():
            with self.subTest(placement=index):
                self.assertGreater(row["theirs"][0], 115)
                self.assertGreater(row["ours"][0], 115)

    def test_the_overlap_is_held_back_by_a_withdrawal_not_by_agreement(
            self) -> None:
        """LANE-A round 8ubiku, after pf-adversary D4.

        The round's first correction said the collision was GONE.  It is
        not: all sixteen recorded placements are still in lane B's module,
        fifteen of them parked in WITHDRAWN/UNRESOLVED with the reason
        ``not carried: ..._avatar_is_a_variant_list``.  The overlap is held
        back by lane B declining to ship them, and the identity question for
        those fifteen was never answered.  This test fails the day that
        withdrawal is lifted - which is the day the collision returns and
        the day someone needs to read this class again.
        """
        shipped = {row[0] for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS}
        withdrawn = {
            row[0] for row in field_mob_tables_bg0015.WITHDRAWN_UNDER_THIS_RULE
        }
        unresolved = {
            row[0] for row in field_mob_tables_bg0015.UNRESOLVED_PLACEMENTS
        }
        recorded = set(identity.COLLIDING_PLACEMENTS)

        # Still all present, somewhere in lane B's module.
        self.assertEqual(recorded - (shipped | withdrawn | unresolved), set())
        # Only one of them is a live overlap today.
        self.assertEqual(recorded & shipped, {70})
        # The other fifteen are withheld, and for the same stated reason.
        for index in sorted(recorded - shipped):
            with self.subTest(placement=index):
                self.assertIn(index, withdrawn | unresolved)
        # pf-adversary, round 8ubiku2, E14: the first version read reasons
        # only from WITHDRAWN_UNDER_THIS_RULE.  That was harmless only
        # because the fifteen sit in BOTH lists today - a duplication, not a
        # partition - so a future split would have left half unchecked.
        reasons = [
            row[-1]
            for source in (field_mob_tables_bg0015.WITHDRAWN_UNDER_THIS_RULE,
                           field_mob_tables_bg0015.UNRESOLVED_PLACEMENTS)
            for row in source
            if row[0] in recorded - shipped
        ]
        self.assertTrue(reasons)
        for reason in reasons:
            self.assertIn("variant_list", reason)

    def test_the_modules_own_collision_list_is_now_history_not_state(
            self) -> None:
        """COLLIDING_PLACEMENTS still names what the collision WAS.

        Left alone on purpose: it is lane A's constant and it records a real
        past disagreement.  This test only pins that it no longer describes
        the tables as they stand, so nobody reads it as current state.
        """
        self.assertEqual(
            sorted(identity.COLLIDING_PLACEMENTS),
            [30, 59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74])
        live = set(self._conflicts())
        self.assertEqual(
            sorted(set(identity.COLLIDING_PLACEMENTS) & live), [70],
            "placement 70 is the only one of the recorded sixteen that both "
            "tables still ship, and they now agree on it (MOBS 355, Horror "
            "butcher Lasa)",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
