"""LANE-B: the 35/35 pin COO-DECISION 20260829_0345 made mandatory, and the
five rows it does not cover.

The ruling that made ``cline`` the project's one identity rule attached a
condition: regenerating ``Bg0002`` under ``cline`` must come out identical,
"35/35", and a differing row stops the merge and goes to the owner.  It also
ordered the equality pinned by a test so nobody has to take a letter's word
for it.  This is that test, plus the part the letter got wrong.

WHAT IS PINNED HERE

  * the equality COO asked for, over the block it is actually true of
  * the size of the block, because "35 agree" is meaningless without it
  * the ten rows of the same CLINE type that do NOT agree
  * the five ``Bg0002`` placements that land on one of them, with what each
    reading makes them
  * that CLINE type 14 agrees on nothing at all, so the 35/35 cannot be
    carried to another scene by anyone quoting this file

THE RE-DERIVATION.  ``scene_identity_rule`` commits a copy of a table that
lives on the bridge clone.  Where that clone is present these tests re-mine
it and require an exact match including the digest; where it is not, they
skip through ``pf_preconditions.BRIDGE_GAMEDATA`` -- declared, tokenised and
pinned in ``docs/PYTEST_SKIP_PINS.json`` in this same commit, because a bare
``skipTest`` here is the exact defect the gate's skip census exists to catch
and has already caught three times in this lane.  A skip is not a pass.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import scene_identity_rule as sir
from pirateforce_foundation import field_mob_tables_bg0002 as bg0002


#: The bridge clone, if this machine has one beside the server repo.  Not a
#: configurable path: the two repositories are checked out side by side by
#: every runbook in this project, and a search would find a stale copy.
BRIDGE_TABLES = ROOT.parent / "pf_bridge" / "gamedata" / "tables"
CLINE_TSV = BRIDGE_TABLES / "CONSTDATA_TH__CLINE.tsv"
MOBS_TSV = BRIDGE_TABLES / "CONSTDATA_TH__MOBS.tsv"
MOBS_TIP_TSV = BRIDGE_TABLES / "TEXTDATA_TH__MOBS_TIP.tsv"
SCENE_NAME_TSV = BRIDGE_TABLES / "CONSTDATA_TH__SCENE_NAME.tsv"


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TheEqualityCooAskedFor(unittest.TestCase):
    """COO-DECISION 20260829_0345's mandatory condition, as an assertion."""

    def test_every_mob_set_number_in_the_agreeing_block_resolves_to_itself(self):
        """35/35.  The half of the condition that is true.

        Asserted per number rather than as a count, so a failure names the
        row that moved instead of saying 34.
        """
        block = sir.CLINE_BLOCKS[sir.AGREEING_BLOCK_SCENE_TYPE]
        for set_number in sir.AGREEING_BLOCK:
            with self.subTest(set_number=set_number):
                self.assertIn(set_number, block)
                self.assertEqual(
                    block[set_number], set_number,
                    "CLINE type %d maps Mob-Set %d to %d, not to itself.  "
                    "COO-DECISION 20260829_0345: a differing row means STOP "
                    "and ask the owner -- do not regenerate."
                    % (sir.AGREEING_BLOCK_SCENE_TYPE, set_number,
                       block[set_number]),
                )

    def test_the_block_is_exactly_thirty_five_numbers_wide(self):
        """So "35/35" cannot quietly become "35 of however many"."""
        self.assertEqual(len(sir.AGREEING_BLOCK), 35)

    def test_the_agreement_is_thirty_five_of_forty_five_not_thirty_five_of_thirty_five(self):
        """The half of the condition that is FALSE, pinned as a number.

        CLINE type 2 has 45 rows.  Ten of them are not identity.  A reader
        who only ever sees "35/35" quoted has been shown a true statement
        about a subset and will conclude something false about the table.
        """
        agreeing, total = sir.agreement(sir.AGREEING_BLOCK_SCENE_TYPE)
        self.assertEqual(agreeing, 35)
        self.assertEqual(total, 45)

    def test_the_ten_rows_outside_the_block_are_named_not_counted(self):
        """Every non-identity row of type 2, by value.

        These are where the next scene's placements land.  Pinned so a
        change to the mined copy has to be a deliberate edit to this list.
        """
        block = sir.CLINE_BLOCKS[2]
        self.assertEqual(
            {key: value for key, value in block.items() if key != value},
            {36: 360, 37: 230, 38: 231, 39: 742, 40: 743, 41: 914,
             101: 10003, 102: 10004, 103: 917, 104: 927},
        )


class TheFiveRowsTheConditionDoesNotCover(unittest.TestCase):
    """Bg0002 places Mob-Set numbers the 35/35 measurement never saw."""

    def test_bg0002_ships_five_placements_outside_the_agreeing_block(self):
        outside = tuple(sorted(
            (index, set_number)
            for index, set_number in bg0002.SET_NUMBER_FOR_PLACEMENT.items()
            if set_number not in sir.AGREEING_BLOCK
        ))
        self.assertEqual(
            outside, sir.BG0002_PLACEMENTS_OUTSIDE_THE_AGREEING_BLOCK,
            "the set of Bg0002 placements outside Mob-Set 1..35 changed.  "
            "That set is the whole subject of the open question with the "
            "owner; update the letter before updating this test."
        )

    def test_the_two_readings_of_set_103_are_different_creatures(self):
        """Not a rename: a rank-1 level-58 hostile versus an INVISIBLE marker."""
        legacy = sir.DISPUTED_SET_103_READINGS[sir.LEGACY_IDENTITY_RULE]
        chosen = sir.DISPUTED_SET_103_READINGS[sir.PROJECT_IDENTITY_RULE]
        self.assertEqual(legacy[0], 103)
        self.assertEqual(chosen[0], 917)
        self.assertEqual((legacy[1], legacy[2]), (1, 332))
        self.assertEqual(
            (chosen[1], chosen[2]), (0, 0),
            "MOBS 917 was the reason cline drops these five placements: rank "
            "0 and no combat AI means the hostility predicate cannot select "
            "it.  If that changed, the open question changed with it."
        )
        self.assertEqual(chosen[3], "INVISIBLE")

    def test_bg0002_still_ships_under_the_legacy_rule_this_round(self):
        """The hold is a fact in the tree, not only a sentence in a letter.

        When the owner rules and this flips to ``cline``, this test fails --
        and the round that flips it must also cut the five rows out of
        ``SET_NUMBER_FOR_PLACEMENT`` and answer for the map going from
        seventeen hostiles to twelve.
        """
        self.assertEqual(bg0002.IDENTITY_RULE, sir.LEGACY_IDENTITY_RULE)
        self.assertEqual(len(bg0002.HOSTILE_PLACEMENTS), 17)

    def test_divergent_set_numbers_reports_exactly_those_five_numbers(self):
        self.assertEqual(
            sir.divergent_set_numbers(
                2, bg0002.SET_NUMBER_FOR_PLACEMENT.values()),
            (103,),
        )


class TheThirtyFiveDoesNotGeneralise(unittest.TestCase):
    """The failure mode this whole file is really guarding against."""

    def test_cline_type_14_agrees_with_the_legacy_rule_on_nothing(self):
        agreeing, total = sir.agreement(14)
        self.assertEqual(agreeing, 0)
        self.assertEqual(total, 51)

    def test_no_scene_type_may_be_resolved_by_guessing(self):
        with self.assertRaises(sir.IdentityRuleError):
            sir.resolve(1, 5, sir.PROJECT_IDENTITY_RULE)

    def test_an_unreadable_set_number_raises_rather_than_meaning_itself(self):
        with self.assertRaises(sir.IdentityRuleError):
            sir.resolve(2, 42, sir.PROJECT_IDENTITY_RULE)
        self.assertEqual(sir.resolve(2, 42, sir.LEGACY_IDENTITY_RULE), 42)

    def test_the_console_line_is_ascii_and_carries_the_block_size(self):
        line = sir.console_line(14)
        self.assertTrue(line.isascii(), "the bridge console is cp874")
        self.assertIn("block=51", line)
        self.assertIn("agree_with_setnum=0", line)


@BRIDGE_GAMEDATA.skip_unless_present()
class TheCommittedCopyIsTheRealTable(unittest.TestCase):
    """Re-mine the bridge clone where it exists; skip loudly where it does not.

    Nine tests, and the pin in ``docs/PYTEST_SKIP_PINS.json`` says nine.
    On a machine without the bridge clone every number in
    ``scene_identity_rule`` is TRUSTED, not verified, and the skip census
    is where that shows up.
    """

    def test_the_source_digest_matches_the_file_the_blocks_came_from(self):
        self.assertEqual(_digest(CLINE_TSV), sir.SOURCE_DIGESTS["cline"])

    def test_both_blocks_re_derive_exactly(self):
        rows = _rows(CLINE_TSV)
        for cline_type, committed in sorted(sir.CLINE_BLOCKS.items()):
            with self.subTest(cline_type=cline_type):
                mined = {
                    int(row["n_CREATURE_TYPE"]): int(row["n_LEADER_BK1"])
                    for row in rows
                    if int(row["n_CLINE_TYPE"]) == cline_type
                }
                self.assertEqual(mined, committed)

    def test_the_two_readings_of_set_103_re_derive_from_mobs(self):
        # Not a second skip: BRIDGE_GAMEDATA guards the tables DIRECTORY, and
        # a clone that has the directory without CONSTDATA_TH__MOBS.tsv is a
        # broken clone, which is red rather than skipped.
        self.assertTrue(
            MOBS_TSV.is_file(),
            "the bridge tables directory is present but %s is missing"
            % (MOBS_TSV.name,),
        )
        self.assertEqual(_digest(MOBS_TSV), sir.SOURCE_DIGESTS["mobs"])
        mobs = {int(row["n_ID"]): row for row in _rows(MOBS_TSV)}
        for rule, expected in sorted(sir.DISPUTED_SET_103_READINGS.items()):
            with self.subTest(rule=rule):
                row = mobs[expected[0]]
                self.assertEqual(int(row["n_RANK"]), expected[1])
                self.assertEqual(int(row["n_AI_COMBAT"]), expected[2])
                self.assertEqual(row["s_OUTFIT"], expected[3])
                self.assertEqual(int(row["n_LEVEL_MIN"]), expected[4])

    def test_the_display_names_re_derive_from_the_TIP_table_not_from_mobs(self):
        """The sixth field, which the first version of this file never checked.

        pf-adversary's finding: the constant was labelled "straight from
        CONSTDATA_TH__MOBS" and its last element is not from that table.
        MOBS.s_NAME for 103 is the original-language string; the English
        name is MOBS_TIP.s_NAME, and 917 has no MOBS_TIP row at all.  Both
        halves are asserted here so the label and the value stay honest
        together.
        """
        self.assertEqual(_digest(MOBS_TIP_TSV), sir.SOURCE_DIGESTS["mobs_tip"])
        tips = {int(row["n_ID"]): row["s_NAME"] for row in _rows(MOBS_TIP_TSV)}
        legacy = sir.DISPUTED_SET_103_READINGS[sir.LEGACY_IDENTITY_RULE]
        chosen = sir.DISPUTED_SET_103_READINGS[sir.PROJECT_IDENTITY_RULE]
        self.assertEqual(tips[legacy[0]].strip(), legacy[5])
        self.assertNotIn(
            chosen[0], tips,
            "MOBS 917 has a MOBS_TIP name now, so '(no MOBS_TIP name)' is "
            "wrong and the disputed reading needs restating",
        )
        mobs = {int(row["n_ID"]): row for row in _rows(MOBS_TSV)}
        self.assertNotEqual(
            mobs[legacy[0]]["s_NAME"], legacy[5],
            "MOBS.s_NAME now equals the English name, so the two-source note "
            "on DISPUTED_SET_103_READINGS is no longer the reason it says "
            "what it says",
        )

    def test_the_scene_cline_type_re_derives_from_scene_name(self):
        """The crosswalk's entry point, which nothing checked before.

        Case-insensitively on s_MODLE_ID, because the table spells BG0002 in
        upper case and Bg0015 in mixed case -- and SCENE_MODEL_ID's exact
        spellings are asserted here too, so the inconsistency is pinned
        rather than worked around silently.
        """
        self.assertEqual(_digest(SCENE_NAME_TSV),
                         sir.SOURCE_DIGESTS["scene_name"])
        rows = {row["s_MODLE_ID"].strip().lower(): row
                for row in _rows(SCENE_NAME_TSV)}
        for scene, cline_type in sorted(sir.SCENE_CLINE_TYPE.items()):
            with self.subTest(scene=scene):
                row = rows[scene.lower()]
                self.assertEqual(int(row["n_CLINE_TYPE"]), cline_type)
                self.assertEqual(row["s_MODLE_ID"].strip(),
                                 sir.SCENE_MODEL_ID[scene])

    def test_the_cline_type_column_is_not_the_id_column_in_general(self):
        """Why SCENE_CLINE_TYPE cannot validate itself, as a measurement.

        Both entries sit among the rows where n_ID == n_CLINE_TYPE, so a
        module that read the wrong column would look identical over them.
        Over the whole table the two columns disagree on almost every row,
        and that is the fact a future scene depends on.
        """
        rows = _rows(SCENE_NAME_TSV)
        same = [r for r in rows
                if int(r["n_ID"]) == int(r["n_CLINE_TYPE"])]
        self.assertEqual((len(same), len(rows)), (12, 271))
        for scene in sir.SCENE_CLINE_TYPE:
            with self.subTest(scene=scene):
                self.assertIn(sir.SCENE_MODEL_ID[scene],
                              [r["s_MODLE_ID"].strip() for r in same])

    def test_the_rules_reach_is_nineteen_scenes_of_two_hundred_seventy_one(self):
        """The scope of "one rule for every scene", measured not assumed."""
        blocks = {int(row["n_CLINE_TYPE"]) for row in _rows(CLINE_TSV)}
        rows = _rows(SCENE_NAME_TSV)
        readable = [r for r in rows if int(r["n_CLINE_TYPE"]) in blocks]
        self.assertEqual(
            (len(readable), len(rows)), sir.SCENES_THE_RULE_CAN_READ)

    def test_no_shipped_control_was_measured_on_the_scene_it_ships_under(self):
        """Bg0015's module records controls that are about other scene types.

        Not a failure of the table -- a gap in the generator, stated here so
        it cannot be mistaken for validation.  This test asserts the gap
        EXISTS; the round that closes it (a control measured on the scene
        being mined) deletes this test and says so.
        """
        from pirateforce_foundation import field_mob_tables_bg0015 as bg0015

        self.assertEqual(bg0015.SCENE_CLINE_TYPE, 14)
        self.assertEqual(
            sorted(bg0015.CONTROL_FINDINGS),
            ["prison_exile_identity", "town_target_916_hp"],
            "the controls this module ships changed; if one of them is now "
            "measured on CLINE type 14, this test has done its job and "
            "should be replaced by an assertion that it passed",
        )
        # prison_exile_identity is CLINE type 2.  This module is type 14, and
        # the two agree on nothing -- which is exactly why the control
        # carries no information here.
        self.assertEqual(sir.agreement(2)[0], 35)
        self.assertEqual(sir.agreement(14)[0], 0)

    def test_cline_resolves_set_103_to_the_id_this_module_committed(self):
        self.assertEqual(sir.resolve(2, 103, sir.PROJECT_IDENTITY_RULE), 917)


if __name__ == "__main__":
    unittest.main()
