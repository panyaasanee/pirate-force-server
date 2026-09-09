"""``Quest.Reward*`` and the half-transaction gate (LANE-Q, COO ``0242``).

Four layers, kept apart for the same reason
``test_script_lua_quest_vars`` keeps its four apart -- they fail for
different reasons and on different machines:

  1. THE MIRRORS PARSE (gate-runnable, no bridge checkout).  Shape, digest
     header, and the refusals a corrupt mirror has to produce -- including
     the one this table exists for: a group with only one side.
  2. THE TABLE SAYS WHAT IT SAYS (gate-runnable).  THREE groups (this
     sentence said "two" for two rounds after the third arrived --
     pf-adversary D7, round `yzdgx1`), each keyed on the entry point that
     performs both halves, every member carrying a ``file:line``.
  3. THE GATE BEHAVES (gate-runnable).  The q_class row is refused whole;
     the q_guild_boss2 row -- same script shape, no reward cells -- is NOT,
     which is the negative result that says the gate reads the ROW.

     ROUND `6gc0zk` MEASURED THE CLAIM THIS SECTION USED TO MAKE HERE AND
     FOUND IT FALSE: it used to say "the moment ``Player.AddItem`` becomes
     real the group opens by itself".  ``Player.AddItem`` went real that
     round (``store.mint_backpack_item`` landed), and ``Q_CLASS.Report_Run``
     stayed SHUT -- it has five give-side members, not one
     (``Player.AddItem``, ``Player.AddPpClass``,
     ``Quest.AddCriteriaCash``, ``Quest.AddCriteriaExp``,
     ``Quest.AddCriteriaSkillPoint``), and the gate correctly waits on
     ALL of them, exactly as ``test_a_real_give_does_not_open_a_group_
     whose_take_is_still_a_stub`` already proved for the take side.  The
     corrected claim: the group opens only once EVERY member of it is
     real, and going real one name at a time is expected to leave it
     shut for several rounds yet.
  4. THE MIRRORS MATCH THE GAME (needs ../pf_bridge, skipped on the gate).

WHAT AN EARLIER ROUND DELIBERATELY UNDID.  Round `joa0u6` made
``Quest/q_class.lua`` take 15,000 off the player for real.  Four lines
later the same function is supposed to hand over three items through
``Player.AddItem``, which was a stub then.  COO-DECISION ``20260908_0242``
item 4 chose the free quest over the robbed player, so the tests that
pinned the charge pinned the refusal instead, and the join underneath them
is asserted separately in ``test_script_lua_quest_vars`` so that a gate
quietly deleting the value cannot pass both.  ``Player.AddItem`` itself
went real in round `6gc0zk` (``lua_api.reward.mint``, against
``store.mint_backpack_item``); ``Quest/q_class.lua``'s own group stays
refused regardless, for the reason layer 3 above now measures.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pf_preconditions import BRIDGE_GAMEDATA, BRIDGE_LUA_SCRIPTS, SIBLING

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import (player as lua_player, quest,
                                            quest_criteria as qc,
                                            quest_rewards as qr,
                                            quest_vars as qv, spec, vendored)
from pirateforce_foundation.lua_api.quest_criteria import QuestCriteriaError

#: What a refused ``Quest.VarN`` would hand back if the gate let it fall
#: through to the namespace's own bare-name default -- imported by value so
#: this file's assertions say which of the two answers they mean.
STUB_DEFAULT = quest.STUB_DEFAULT

REPO_ROOT = Path(__file__).resolve().parents[1]
MIRROR_DIR = REPO_ROOT / "src" / "pirateforce_foundation" / "lua_api"

#: The class-change quest: charges 15,000 (`n_VARI_4`) and names three
#: reward items in the SAME `Report_Run`.  The whole reason this module
#: exists.
GATED_QUEST_ID = 3200
GATED_ITEMS = (2480010, 2480011, 2480012)

#: A row of `q_ocean_gather1`, the flagship of the 56 groups
#: `Player.RemoveItem` opens in round `ad7t6n`.  Its `Report_Run` removes
#: `n_VARI_2` x `n_VARI_3` (the shipped cells: ten of item 2500533) via
#: `Player.RemoveItem`, still a stub, and pays with `Player.AddItem`,
#: real since round `6gc0zk` -- so the group is STILL unpayable (the take
#: side, not the give side, is what is missing now) and both charge cells
#: are still refused; see `test_a_real_give_does_not_open_a_group_whose_
#: take_is_still_a_stub`.  `n_VARI_4`/`n_VARI_5` are the teleport scene and
#: the countdown `Accept_Run` reads, in no group, and must still resolve
#: -- and both ship NON-ZERO, so the assertion cannot pass by accidentally
#: agreeing with a stub default.
GATHER_QUEST_ID = 4501
GATHER_ITEM = 2500533
GATHER_COUNT = 10
GATHER_UNGATED = {"Var4": 126, "Var5": 600}

#: Same script SHAPE, different rows: `q_guild_boss2.lua` carries the
#: identical `Player.AddItem` block, but rows 8061..8065 put nothing in a
#: reward cell, so their charge is a complete transaction on its own and
#: must NOT be gated.  This is the measurement that decides the gate is
#: per row, not per script.
UNGATED_CHARGE_QUEST_ID = 8061
UNGATED_CHARGE_SIGNED = -10000

#: A row with reward items whose script takes nothing: no group, so the
#: cells resolve straight through.
FREE_REWARD_QUEST_ID = 26
FREE_REWARD_ITEMS = (2608007, 2401006)

#: The three groups the derivation finds, spelled out so a change to the
#: mirror has to be a change to this list too.  Re-derive with:
#:     python3 tools/pf_regen_lua_quest_rewards.py --explain
#:
#: `q_boat_health` JOINED THIS ROUND (pf-adversary D3, round `l0rbyx`:
#: "the take side must stop coming from the signedness table alone").  Its
#: charge is `Player.AddCash(Quest.Var2 * -1)` -- the shipped cell is
#: POSITIVE and the SCRIPT carries the minus sign, so the signedness table
#: classified `n_VARI_2` as an ordinary number and the take was invisible
#: to a scan that only read that table.  The give it is charged for,
#: `Player.BoatHealth(Quest.Var3)` on the line above, is a stub, so the
#: group is unpayable and the charge is refused: boat repair can no longer
#: take the money without repairing the boat.
#: `q_day_hunt` AND `q_repeat_hunt` JOINED IN ROUND `5a3x47`
#: (pf-adversary D3 against round `kkuqzo`).  Their charge is not money at
#: all -- `Player.Addmoralized(-Quest.Var4)` spends MORALE, in the same
#: `Report_Run` that hands over the reward items -- and the take scan read
#: only `Player.AddCash`, so nothing in this repository could see it.  The
#: same shape appears at eleven call sites the shipped table reaches on 72
#: rows; these two are the two where the give is in the SAME function, so
#: they are the two that form a group.  The other nine charge morale at
#: `Accept_Run` and hand over nothing there, which is not a half
#: transaction and correctly stays out of this table.
#: ROUND `ad7t6n` SPLITS THIS LIST IN TWO, because the take side stopped
#: being one kind of thing.  `EXPECTED_CHARGE_GROUPS` still pins, by hand
#: and exactly, every group whose charge is money or morale -- the takes
#: whose only evidence is a SIGN.  `Player.RemoveItem` is the other kind:
#: the name is the charge, it is the most common one in the corpus (367
#: call sites), and it opens 56 more groups, which are pinned by the
#: derived facts below plus three spelled-out flagships rather than by
#: 56 hand-copied lines nobody would re-derive.
EXPECTED_CHARGE_GROUPS = {
    ("q_class", "Report_Run"): ("n_VARI_4", "Quest/q_class.lua:60",
                                "Player.AddCash"),
    ("q_guild_boss2", "Report_Run"): ("n_VARI_8",
                                      "Quest/q_guild_boss2.lua:59",
                                      "Player.AddCash"),
    ("q_boat_health", "Accept_Run"): ("n_VARI_2",
                                      "Quest/q_boat_health.lua:21",
                                      "Player.AddCash"),
    ("q_day_hunt", "Report_Run"): ("n_VARI_4", "Quest/q_day_hunt.lua:55",
                                   "Player.Addmoralized"),
    ("q_repeat_hunt", "Report_Run"): ("n_VARI_4",
                                      "Quest/q_repeat_hunt.lua:54",
                                      "Player.Addmoralized"),
}

#: Every group `Player.RemoveItem` opens, counted.  RE-DERIVE with
#: ``python3 tools/pf_regen_lua_quest_rewards.py --explain``.
EXPECTED_ITEM_GROUP_COUNT = 56

#: Three of those 56, spelled out to the cell and the line, so a change
#: to the item scan has to be a change to this file too.  Chosen for the
#: three shapes that exist: both cells at one call site, a script that
#: charges FOUR separate items, and a script whose removals are spread
#: over three call sites in one entry point.
EXPECTED_ITEM_GROUPS = {
    ("q_ocean_gather1", "Report_Run"): (
        ("n_VARI_2", "Quest/q_ocean_gather1.lua:55"),
        ("n_VARI_3", "Quest/q_ocean_gather1.lua:55"),
    ),
    ("q_other1", "Report_Run"): (
        ("n_VARI_2", "Quest/q_other1.lua:59"),
        ("n_VARI_3", "Quest/q_other1.lua:60"),
        ("n_VARI_4", "Quest/q_other1.lua:61"),
        ("n_VARI_5", "Quest/q_other1.lua:62"),
    ),
    ("q_week2_gather3", "Report_Run"): (
        ("n_VARI_2", "Quest/q_week2_gather3.lua:53"),
        ("n_VARI_3", "Quest/q_week2_gather3.lua:53"),
        ("n_VARI_4", "Quest/q_week2_gather3.lua:54"),
        ("n_VARI_5", "Quest/q_week2_gather3.lua:54"),
        ("n_VARI_6", "Quest/q_week2_gather3.lua:55"),
        ("n_VARI_7", "Quest/q_week2_gather3.lua:55"),
    ),
}


class MirrorShapeTests(unittest.TestCase):
    """Layer 1.  Everything the Windows gate can check without the game."""

    def setUp(self):
        qr.reset_caches()
        self.addCleanup(qr.reset_caches)

    def test_every_shipped_quest_row_has_its_reward_cells(self):
        rewards = qr.load_rewards()
        self.assertEqual(len(rewards), len(qv.load_rows()),
                         "the two mirrors are two views of the SAME 1544 "
                         "rows; a row in one and not the other is a "
                         "hand-edit, not a feature")
        for quest_id, cells in rewards.items():
            self.assertEqual(len(cells), len(qr.SOURCE_COLUMNS), quest_id)

    def test_no_reward_cell_is_a_wrapped_negative(self):
        """The `n_VARI_*` bug must not have a twin here, and cannot get one.

        `quest_vars` needs a signedness table because a designer's -15000
        is stored as 4294952296.  Nothing in the 37,056 reward cells is
        anywhere near that: the largest is 3,509,557.  So this module has
        no signedness reading to make -- and the day one appears, this
        test fails and a person decides, instead of the server granting
        4.29 billion of an item.
        """
        cells = [cell for row in qr.load_rewards().values() for cell in row]
        self.assertEqual(len(cells), len(qr.load_rewards()) * 24)
        self.assertEqual(max(cells), qr.LARGEST_REWARD_CELL)
        self.assertEqual(
            sum(1 for cell in cells if cell >= 1 << 31),
            qr.WRAPPED_REWARD_CELLS)

    def test_the_lua_name_map_covers_all_four_kinds_and_nothing_else(self):
        """`RewardItemNum3 -> n_REWARD_NUM3` is the asymmetry that bites."""
        self.assertEqual(len(qr._LUA_NAME_TO_SOURCE), 24)
        self.assertEqual(qr._LUA_NAME_TO_SOURCE["RewardItemNum3"],
                         "n_REWARD_NUM3")
        self.assertEqual(qr._LUA_NAME_TO_SOURCE["RewardChooseNum3"],
                         "n_REWARD_CHOOSENUM3")
        self.assertIsNone(qr.lua_name_of("RewardItem7"))
        self.assertIsNone(qr.lua_name_of("RewardItem0"))
        self.assertIsNone(qr.lua_name_of("Reward"))
        with self.assertRaises(ValueError):
            qr.reward_cell(GATED_QUEST_ID, "RewardItem7")

    def test_both_mirrors_carry_a_body_digest_header(self):
        for name in ("quest_reward_rows.tsv", "quest_column_groups.tsv"):
            text = (MIRROR_DIR / name).read_text(encoding="ascii")
            self.assertIn(qc.BODY_DIGEST_PREFIX, text, name)
            body = text.split("\n", 8)[8]
            digest = [line for line in text.splitlines()
                      if line.startswith(qc.BODY_DIGEST_PREFIX)][0]
            self.assertEqual(
                digest[len(qc.BODY_DIGEST_PREFIX):], qc.body_digest(body),
                "%s: the header digest must match the body it heads" % name)


class CorruptGroupTableTests(unittest.TestCase):
    """Layer 1, the refusals.  A group table that lies is worse than none."""

    def setUp(self):
        qr.reset_caches()
        self.addCleanup(qr.reset_caches)

    def _write(self, body):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "quest_column_groups.tsv"
        header = (MIRROR_DIR / "quest_column_groups.tsv"
                  ).read_text(encoding="ascii").split("\n")[:8]
        rendered = "\t".join(qr.GROUP_COLUMNS) + "\n" + body
        header[6] = "%s%s" % (qc.BODY_DIGEST_PREFIX, qc.body_digest(rendered))
        path.write_text("\n".join(header) + "\n" + rendered, encoding="ascii")
        return path

    def _load(self, body):
        path = self._write(body)
        with mock.patch.object(qr, "_GROUPS_PATH", path):
            qr.reset_caches()
            return qr.load_groups()

    def test_a_group_with_only_a_take_side_is_refused(self):
        """The failure this table exists to make impossible.

        A group listing the charge and no give is not a transaction; it is
        a licence to take.  Parsing it as "nothing to wait for" would open
        exactly the charge COO's rule closes, so it stops the load.
        """
        with self.assertRaises(QuestCriteriaError) as caught:
            self._load("Q_CLASS\tReport_Run\ttake\tn_VARI_4\t"
                       "Player.AddCash\tQuest/q_class.lua:60\n")
        self.assertIn("only one side", str(caught.exception))

    def test_a_group_with_only_a_give_side_is_refused_too(self):
        with self.assertRaises(QuestCriteriaError) as caught:
            self._load("Q_CLASS\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                       "Player.AddItem\tQuest/q_class.lua:64\n")
        self.assertIn("only one side", str(caught.exception))

    def test_a_member_with_no_provenance_is_refused(self):
        with self.assertRaises(QuestCriteriaError) as caught:
            self._load("Q_CLASS\tReport_Run\ttake\tn_VARI_4\t"
                       "Player.AddCash\tq_class.lua\n"
                       "Q_CLASS\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                       "Player.AddItem\tQuest/q_class.lua:64\n")
        self.assertIn("not a file:line", str(caught.exception))

    def test_an_unknown_side_is_refused_rather_than_ignored(self):
        with self.assertRaises(QuestCriteriaError) as caught:
            self._load("Q_CLASS\tReport_Run\trefund\tn_VARI_4\t"
                       "Player.AddCash\tQuest/q_class.lua:60\n")
        self.assertIn("unknown side", str(caught.exception))

    def test_a_give_column_the_table_does_not_ship_is_refused(self):
        """A give side naming a column the game has no cell for cannot be
        exercised, so it would make its group permanently unexercised --
        a silently open charge."""
        with self.assertRaises(QuestCriteriaError) as caught:
            self._load("Q_CLASS\tReport_Run\ttake\tn_VARI_4\t"
                       "Player.AddCash\tQuest/q_class.lua:60\n"
                       "Q_CLASS\tReport_Run\tgive\tn_REWARD_ITEM9\t"
                       "Player.AddItem\tQuest/q_class.lua:64\n")
        self.assertIn("not one of the shipped reward columns",
                      str(caught.exception))

    def test_a_broken_mirror_is_counted_under_its_own_key(self):
        """The call-time half of pf-adversary D3/D6 (`95aw54`), for the two
        mirrors this module adds."""
        for key in (vendored.MIRROR_QUEST_REWARD_ROWS,
                    vendored.MIRROR_QUEST_COLUMN_GROUPS):
            self.assertIn(key, vendored.KNOWN_MIRRORS)


class TheTableSaysWhatItSaysTests(unittest.TestCase):
    """Layer 2."""

    def setUp(self):
        qr.reset_caches()
        self.addCleanup(qr.reset_caches)

    def test_exactly_the_measured_coupled_scripts_are_in_the_table(self):
        """Five charge groups, 56 item groups, and nothing else.

        The five are named; the 56 are counted and then characterised by
        the assertion below, which is the only honest way to pin a set
        this size: a hand-copied list of 56 lines is a list nobody
        re-derives, and a bare count would let one group swap for
        another.
        """
        groups = qr.load_groups()
        found = {(script, group.group)
                 for script, entries in groups.items() for group in entries}
        self.assertTrue(set(EXPECTED_CHARGE_GROUPS) <= found)
        self.assertTrue(set(EXPECTED_ITEM_GROUPS) <= found)
        self.assertEqual(len(found) - len(EXPECTED_CHARGE_GROUPS),
                         EXPECTED_ITEM_GROUP_COUNT)

    def test_every_item_group_is_a_removeitem_take_in_a_report_run(self):
        """What the 56 unnamed groups all are, asserted rather than trusted.

        Every group that is not one of the five named charges exists
        because `Player.RemoveItem` takes something, and every one of them
        is in `Report_Run` -- the entry point that also hands the reward
        over.  A group appearing anywhere else, or with a take this lane
        has not classified, fails here instead of arriving unremarked in
        a mirror of 1087 rows.
        """
        for script, entries in qr.load_groups().items():
            for group in entries:
                if (script, group.group) in EXPECTED_CHARGE_GROUPS:
                    continue
                self.assertEqual(group.group, "Report_Run", script)
                self.assertEqual(
                    {member.api_name for member in group.side(qr.TAKE)},
                    {"Player.RemoveItem"}, script)

    def test_the_three_spelled_out_item_groups_are_exactly_right(self):
        """The cell AND the line, for one group of each shape.

        Deleting the second member of `q_ocean_gather1` (the COUNT cell of
        a single call) or the third call site of `q_week2_gather3` leaves
        a mirror that still has the right number of groups, so the count
        above cannot catch it and this does.
        """
        groups = qr.load_groups()
        for (script, entry), expected in EXPECTED_ITEM_GROUPS.items():
            found = [group for group in groups[script]
                     if group.group == entry]
            self.assertEqual(len(found), 1, script)
            self.assertEqual(
                tuple((member.column, member.call_site)
                      for member in found[0].side(qr.TAKE)), expected)

    def test_every_group_names_both_sides_with_provenance(self):
        for script, entries in qr.load_groups().items():
            for group in entries:
                take = group.side(qr.TAKE)
                give = group.side(qr.GIVE)
                self.assertTrue(take, script)
                self.assertTrue(give, script)
                expected = EXPECTED_CHARGE_GROUPS.get((script, group.group))
                if expected is not None:
                    expected_column, expected_site, expected_api = expected
                    charge = [member for member in take
                              if member.api_name == expected_api]
                    self.assertEqual([member.column for member in charge],
                                     [expected_column])
                    self.assertEqual(charge[0].call_site, expected_site)
                for member in group.members:
                    self.assertIn(":", member.call_site)
                    self.assertIn(".lua:", member.call_site)

    def test_the_give_side_is_the_twelve_ids_plus_the_three_curve_payouts(self):
        """Six `RewardItem`, six `RewardChoose`, three column-less payouts.

        The NUM columns are not members, because no script tests a NUM
        before giving anything.  The three criteria calls ARE members even
        though they read no cell: pf-adversary D1 measured what leaving
        them out costs (a 15,000-per-run gift), and they are addressed by
        API name instead of by column.
        """
        for script, entries in qr.load_groups().items():
            for group in entries:
                give = group.side(qr.GIVE)
                columns = sorted(member.column for member in give
                                 if member.column != qr.NO_COLUMN)
                names = sorted(member.api_name for member in give
                               if member.column == qr.NO_COLUMN)
                if script == "q_boat_health":
                    # THE ONE PURCHASE GROUP.  It pays no reward cell and
                    # runs no criteria payout: the whole give side is the
                    # single `Player.BoatHealth(Quest.Var3)` the charge on
                    # the next line is FOR.  Spelled as its own branch
                    # rather than loosened out of the assertion above, so
                    # a reward group that quietly lost its twelve columns
                    # still fails.
                    self.assertEqual(columns, [])
                    self.assertEqual(names, ["Player.BoatHealth"])
                    continue
                if script == "q_instance_gather2":
                    # THE ONE SCRIPT THAT PAYS TWICE, and a corpus fact
                    # rather than a scan defect: `Report_Run` calls every
                    # `Player.AddItem`/`Quest.RewardItemSelect` once
                    # UNCONDITIONALLY at lines 60-71 and then AGAIN
                    # behind `if (Quest.RewardItemK > 0)` from line 74.
                    # A group member is a CALL SITE, so twelve columns
                    # arrive as twenty-four members with twenty-four
                    # distinct lines.  Asserted as its own branch, and by
                    # count as well as by set, so the day the scan starts
                    # collapsing call sites this fails instead of
                    # quietly agreeing.
                    self.assertEqual(sorted(set(columns)),
                                     sorted(qr.GIVE_ID_COLUMNS))
                    self.assertEqual(len(columns),
                                     2 * len(qr.GIVE_ID_COLUMNS))
                    self.assertEqual(
                        len({member.call_site for member in give
                             if member.column != qr.NO_COLUMN}),
                        2 * len(qr.GIVE_ID_COLUMNS))
                    continue
                self.assertEqual(sorted(qr.GIVE_ID_COLUMNS), columns)
                # THE THREE CURVE PAYOUTS, PLUS -- for `q_class` only --
                # the thing the charge BUYS.  Round `yzdgx1`
                # (pf-adversary D2) read `Player.AddPpClass(Quest.Var2)`
                # at `q_class.lua:59` as a give for exactly the reason
                # `Player.BoatHealth` is one: a stubbed delivery on the
                # line above the charge, taking a `Quest.VarN`.  Branched
                # rather than loosened for the same reason the purchase
                # group above is -- `q_guild_boss2`, which buys nothing,
                # must still hold at three or this assertion says nothing.
                purchases = [name for name in names
                             if not name.startswith("Quest.Add")]
                if script == "q_class":
                    self.assertEqual(purchases, ["Player.AddPpClass"])
                else:
                    self.assertEqual(purchases, [], script)
                criteria = [name for name in names if name not in purchases]
                self.assertEqual(len(criteria), 3, names)
                for name in criteria:
                    self.assertTrue(name.startswith("Quest.Add"), name)
                    self.assertIn("Criteria", name)
                # TWO CURVE FAMILIES, never mixed inside one group.  The
                # shipped scripts call either the three `AddCriteria*` or
                # the three `AddLvCriteria*` (round `ad7t6n`, measured:
                # 40 groups take the first, 19 the second, 0 take some of
                # each).  A group holding a mix would mean the scan had
                # merged two entry points, which is the failure this
                # assertion exists to catch.
                self.assertIn(
                    sorted(criteria),
                    [["Quest.AddCriteriaCash", "Quest.AddCriteriaExp",
                      "Quest.AddCriteriaSkillPoint"],
                     ["Quest.AddLvCriteriaCash", "Quest.AddLvCriteriaExp",
                      "Quest.AddLvCriteriaSkillPoint"]], names)

    def test_the_take_side_agrees_with_the_signedness_table(self):
        """One fact, two files, and they have to match.

        The take column of each group is a `signed_money` column of
        `quest_var_signedness.tsv`.  Nothing enforces that at write time
        beyond the tool reading one to build the other, so it is checked
        here rather than assumed.
        """
        signed = qv.load_signedness()
        for script, entries in qr.load_groups().items():
            for group in entries:
                for member in group.side(qr.TAKE):
                    index = int(member.column.rsplit("_", 1)[1])
                    column = signed.get((script, index))
                    if column is None:
                        # A SCRIPT-NEGATED TAKE (pf-adversary D3, round
                        # `l0rbyx`).  `Player.AddCash(Quest.Var2 * -1)`
                        # spends a cell the shipped table stores as a
                        # POSITIVE number, so `quest_var_signedness.tsv`
                        # has nothing to say about it and this cross-check
                        # cannot be the one that holds it.  Its provenance
                        # is held instead by the assertion below: the call
                        # site must be a real line of the real corpus file,
                        # and `EXPECTED_GROUPS` pins which line.
                        # ROUND `5a3x47` ADDS THE SECOND NAME.  A morale
                        # charge is script-negated in every one of its
                        # eleven call sites -- the cell is ordinary, the
                        # minus sign is in the script -- so the signedness
                        # table has nothing to say about any of them
                        # either.  The list stays CLOSED rather than
                        # becoming "whatever the table lacks": a take-side
                        # name arriving here without a person adding it is
                        # the thing this branch must not wave through.
                        # ROUND `ad7t6n` ADDS THE THIRD NAME, and it is
                        # here for a DIFFERENT reason than the first two.
                        # `Player.AddCash`/`Player.Addmoralized` are
                        # absent from the signedness table when the SIGN
                        # is in the script.  `Player.RemoveItem` is
                        # absent from it always: it moves an ITEM, so
                        # `quest_var_signedness.tsv` -- which is about
                        # whether a MONEY cell is stored negative -- has
                        # no opinion about any of its 367 call sites and
                        # never will.  The list stays CLOSED for both
                        # reasons: a take-side name arriving here without
                        # a person adding it is the thing this branch
                        # must not wave through.
                        self.assertIn(member.api_name,
                                      ("Player.AddCash",
                                       "Player.Addmoralized",
                                       "Player.RemoveItem"))
                        expected = EXPECTED_CHARGE_GROUPS.get(
                            (script, group.group))
                        if (expected is not None
                                and member.api_name == expected[2]):
                            self.assertTrue(member.call_site.endswith(
                                expected[1].rsplit("/", 1)[-1]),
                                member.call_site)
                        continue
                    self.assertEqual(column.kind, qv.KIND_MONEY)
                    self.assertEqual(column.api_name.split("@")[0],
                                     member.api_name)
                    self.assertEqual(column.call_site, member.call_site)


class TheGateBehavesTests(unittest.TestCase):
    """Layer 3.  What a running script gets."""

    def setUp(self):
        qr.reset_caches()
        qv.reset_caches()
        self.addCleanup(qr.reset_caches)
        self.addCleanup(qv.reset_caches)

    def _namespace(self, quest_id):
        lines = []
        namespace = quest.build_namespace(
            frozenset(), lines.append,
            context=quest.QuestContext(character_id=7, quest_id=quest_id))
        return namespace, lines

    def test_the_charged_row_refuses_both_halves(self):
        namespace, lines = self._namespace(GATED_QUEST_ID)
        self.assertEqual(namespace["Var4"], qr.REFUSED_CELL)
        self.assertLess(qr.REFUSED_CELL, 0,
                        "a refused CHARGE cell is NEGATIVE: every "
                        "`_coerce_int` door in this package refuses a "
                        "value outside [0, ceiling], so no real API "
                        "accepts it as data -- see qr.REFUSED_CELL")
        self.assertFalse(qr.REFUSED_CELL > 0,
                         "and it must still be a NUMBER, so a shipped "
                         "`if (Quest.VarN > 0)` skips its branch instead "
                         "of raising half way through an entry point "
                         "(pf-adversary D3, round `ad7t6n`)")
        self.assertEqual(namespace["RewardItem1"], quest.STUB_DEFAULT,
                         "a refused REWARD cell stays 0: that is what the "
                         "shipped `if (Quest.RewardItem1 > 0)` tests, and "
                         "0 there correctly skips the payout")
        self.assertTrue(any(line.startswith("LUA_QUEST_GROUP_REFUSED")
                            for line in lines))
        self.assertTrue(any("refused=%s" % qr.REFUSE_GROUP_UNPAYABLE in line
                            for line in lines))

    def test_the_uncharged_column_of_the_same_row_still_resolves(self):
        """The gate is a group, not a quarantine of the row.

        `n_VARI_2` is the class id `Player.AddPpClass` reads: no take/give
        counterpart, so it is in no group and this module has no opinion
        about it.  Refusing it too would be the blunt reading of COO's rule
        that the rule itself rules out.
        """
        namespace, _lines = self._namespace(GATED_QUEST_ID)
        self.assertEqual(namespace["Var2"], 1)

    def test_the_guild_boss_fee_is_gated_too(self):
        """pf-adversary D2, round `l0rbyx`, MEASURED and closed here.

        Rows 8061..8065 put nothing in a reward cell, so the first draft of
        this module called their group "not exercised" and let the 10,000
        charge through -- exactly the take-with-no-give COO's rule
        forbids, on one of the only two scripts the table names.  The
        adversary measured it: `cash 20000 -> 10000`, `LUA_API_STUB`
        everywhere else.  What the draft was not reading is that
        `q_guild_boss2.lua:55-57` calls `AddLvCriteriaExp/SkillPoint/Cash`
        UNCONDITIONALLY: a give that needs no cell is owed on every row, so
        the group is always exercised and the fee waits with it.
        """
        namespace, lines = self._namespace(UNGATED_CHARGE_QUEST_ID)
        self.assertEqual(namespace["Var8"], qr.REFUSED_CELL)
        refusals = [line for line in lines
                    if line.startswith("LUA_QUEST_GROUP_REFUSED")]
        self.assertEqual(len(refusals), 1, refusals)
        self.assertIn("group=Q_GUILD_BOSS2.Report_Run", refusals[0])

    def test_a_group_of_columns_alone_is_exercised_by_the_row(self):
        """The per-row half of the rule, on its own.

        No shipped group needs this today -- both carry an unconditional
        payout, so both are always exercised (the test above) -- but the
        rule is what stops a future group from refusing rows that owe
        nothing, and a rule with no test is a comment.  Same script, same
        row, a group table holding ONLY column members: row 8061 has no
        reward id, so its charge stands.

        The give side is deliberately `Player.RemoveItem`, not
        `Player.AddItem`: `AddItem` went real in round `6gc0zk`, and this
        test's whole point is a group held shut by a still-stubbed
        member, not by which specific name that is.
        """
        body = ("Q_CLASS\tReport_Run\ttake\tn_VARI_4\t"
                "Player.AddCash\tQuest/q_class.lua:60\n"
                "Q_CLASS\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                "Player.RemoveItem\tQuest/q_class.lua:64\n"
                "Q_GUILD_BOSS2\tReport_Run\ttake\tn_VARI_8\t"
                "Player.AddCash\tQuest/q_guild_boss2.lua:59\n"
                "Q_GUILD_BOSS2\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                "Player.RemoveItem\tQuest/q_guild_boss2.lua:62\n")
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "quest_column_groups.tsv"
        header = (MIRROR_DIR / "quest_column_groups.tsv"
                  ).read_text(encoding="ascii").split("\n")[:8]
        rendered = "\t".join(qr.GROUP_COLUMNS) + "\n" + body
        header[6] = "%s%s" % (qc.BODY_DIGEST_PREFIX, qc.body_digest(rendered))
        path.write_text("\n".join(header) + "\n" + rendered, encoding="ascii")
        with mock.patch.object(qr, "_GROUPS_PATH", path):
            qr.reset_caches()
            namespace, lines = self._namespace(UNGATED_CHARGE_QUEST_ID)
            self.assertEqual(namespace["Var8"], UNGATED_CHARGE_SIGNED)
            self.assertFalse([line for line in lines
                              if line.startswith("LUA_QUEST_GROUP_REFUSED")])
            gated, _lines = self._namespace(GATED_QUEST_ID)
            self.assertEqual(gated["Var4"], qr.REFUSED_CELL,
                             "3200 DOES name a reward item, so the same "
                             "column-only table gates it and not 8061")

    def test_a_real_give_does_not_open_a_group_whose_take_is_still_a_stub(self):
        """pf-adversary D2, round `ad7t6n`, the highest finding it raised.

        `group_state` computed `blocking` over `group.side(GIVE)` alone,
        so a group became payable the moment its GIVE side went real --
        whatever the take side was doing.  `Player.AddItem` and
        `Player.RemoveItem` are both stubs today and both carry the same
        reason in `player.STILL_STUBBED`, so they are expected to land
        together; nothing made them.  The day `AddItem` alone went real,
        the adversary measured 452 of the 1544 shipped rows across 57
        scripts in which the player would receive the reward AND KEEP the
        turn-in items, repeatably -- the module's own rule broken by the
        module, in the one direction it never looked.

        A transaction is payable when EVERY member can be honoured.  A
        take that no-ops is a member that cannot.
        """
        with mock.patch.object(
                lua_player, "REAL_METHODS",
                lua_player.REAL_METHODS | {"AddItem"}), \
                mock.patch.object(
                    quest, "REAL_METHODS",
                    quest.REAL_METHODS | {"RewardItemSelect",
                                          "AddCriteriaExp",
                                          "AddCriteriaSkillPoint",
                                          "AddCriteriaCash"}):
            states = qr.group_state(GATHER_QUEST_ID)
            self.assertEqual(len(states), 1)
            self.assertFalse(states[0].payable,
                             "the give side is real and the take side is "
                             "not; that is still half a transaction")
            self.assertEqual(states[0].blocking, ("Player.RemoveItem",))
            namespace, _lines = self._namespace(GATHER_QUEST_ID)
            self.assertEqual(namespace["Var2"], qr.REFUSED_CELL)
            self.assertEqual(namespace["RewardItem1"], quest.STUB_DEFAULT)

    def test_the_group_opens_when_both_sides_are_real_together(self):
        """The other half of the mutant above: the take side is a GATE,
        not a permanent hold.  Same row, same table; `Player.RemoveItem`
        joins its namespace's `REAL_METHODS` alongside the give side and
        both halves come back at once."""
        with mock.patch.object(
                lua_player, "REAL_METHODS",
                lua_player.REAL_METHODS | {"AddItem", "RemoveItem"}), \
                mock.patch.object(
                    quest, "REAL_METHODS",
                    quest.REAL_METHODS | {"RewardItemSelect",
                                          "AddCriteriaExp",
                                          "AddCriteriaSkillPoint",
                                          "AddCriteriaCash"}):
            states = qr.group_state(GATHER_QUEST_ID)
            self.assertEqual(states[0].blocking, ())
            self.assertTrue(states[0].payable)
            namespace, lines = self._namespace(GATHER_QUEST_ID)
            self.assertEqual(namespace["Var2"], GATHER_ITEM)
            self.assertEqual(namespace["Var3"], GATHER_COUNT)
        self.assertFalse([line for line in lines
                          if line.startswith("LUA_QUEST_GROUP_REFUSED")])

    def test_a_refused_charge_cell_cannot_be_read_as_a_met_requirement(self):
        """pf-adversary D8 of round `5a3x47`, PAID -- and the reason the
        item charge could be turned on at all.

        `q_ocean_gather1.lua:43` guards the report with
        `Player.CheckItemNum(Quest.Var2,Quest.Var3)`, and quest 4501 ships
        those cells as "ten of item 2500533".  `Player.CheckItemNum` is
        REAL: it reads the player's actual backpack.  So what the gate
        hands back for a refused charge cell is not a private matter
        between two of this lane's modules -- it goes straight into a
        real requirement check.

        `0` is a catastrophic answer there: it asks whether the player
        holds at least ZERO of template id ZERO, which is true of an
        EMPTY BACKPACK.  Every one of the 57 scripts this round couples
        would have told a player carrying nothing "you may report this
        quest", and then refused the reward -- the quest burned, nothing
        received.  `nil` runs into the `_coerce_int` door every namespace
        in this package already has, and the check REFUSES.

        Both halves are asserted: that the requirement now refuses, and
        that the old value would have satisfied it.  Without the second
        line the first one passes for the wrong reason the day someone
        changes the backpack fixture.
        """
        from pirateforce_foundation.lua_api import spec as api_spec
        empty_backpack = lua_player.PlayerContext()
        namespace = lua_player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], lambda _line: None,
            context=empty_backpack)
        check = namespace["CheckItemNum"]
        quest_namespace, _lines = self._namespace(GATHER_QUEST_ID)
        self.assertEqual(quest_namespace["Var2"], qr.REFUSED_CELL)
        self.assertEqual(quest_namespace["Var3"], qr.REFUSED_CELL)
        self.assertFalse(check(quest_namespace["Var2"],
                               quest_namespace["Var3"]),
                         "a refused charge cell must not satisfy a real "
                         "requirement check")
        self.assertTrue(check(quest.STUB_DEFAULT, quest.STUB_DEFAULT),
                        "this is what the gate used to hand the script: "
                        "`CheckItemNum(0, 0)` is TRUE for an empty "
                        "backpack, which is why REFUSED_CELL is not 0")
        self.assertFalse(qr.REFUSED_CELL > 0,
                         "and the refusal must not raise on the way out "
                         "of a guard it was never decided for: 87 of the "
                         "88 item take cells are read in some OTHER "
                         "entry point of their own script")
        self.assertTrue(check(GATHER_ITEM, 0),
                        "and 0 as a COUNT alone is true as well, so it is "
                        "not only the id position that mattered")

    def test_the_ungated_cells_of_a_gated_gather_row_still_resolve(self):
        """The gate is still a group, not a quarantine of the row.

        `q_ocean_gather1` charges `n_VARI_2`/`n_VARI_3` at `Report_Run`;
        the teleport scene and the countdown `Accept_Run` reads are in no
        group.  Refusing them too would be the blunt reading of COO's
        rule that the rule itself rules out -- and with 56 new groups
        covering many cells each, this is where a blunt reading would
        first show.  Both pinned values are NON-ZERO on purpose: against
        a stub default of 0 an assertion about a zero cell would pass
        whether the gate was blunt or not.
        """
        namespace, _lines = self._namespace(GATHER_QUEST_ID)
        for name, value in sorted(GATHER_UNGATED.items()):
            with self.subTest(cell=name):
                self.assertEqual(namespace[name], value)

    def test_a_reward_row_with_no_take_side_resolves_straight_through(self):
        """206 of the 209 scripts couple nothing; they must not pay for
        the three that do.

        RE-DERIVED round `yzdgx1` (pf-adversary D7): this said "204 ...
        the two" and was wrong in both halves -- `load_groups()` has
        THREE scripts in it (`q_boat_health`, `q_class`,
        `q_guild_boss2`), and 209 - 3 = 206.
        """
        namespace, lines = self._namespace(FREE_REWARD_QUEST_ID)
        self.assertEqual(namespace["RewardItem1"], FREE_REWARD_ITEMS[0])
        self.assertEqual(namespace["RewardItem2"], FREE_REWARD_ITEMS[1])
        self.assertEqual(namespace["RewardItemNum2"], 5)
        self.assertIn("LUA_QUEST_REWARD Quest.RewardItem1 quest=%d value=%d"
                      % (FREE_REWARD_QUEST_ID, FREE_REWARD_ITEMS[0]), lines)

    def test_additem_alone_is_not_enough_because_the_class_change_is_a_give(self):
        """ROUND `yzdgx1`, pf-adversary D2 against round `kkuqzo`.

        Before `Player.AddPpClass` was a member, THIS EXACT PATCH SET
        opened the group: the player was charged 15,000, received the
        reward items, and `Player.AddPpClass(Quest.Var2)` -- the class
        change the 15,000 buys, `q_class.lua:59`, one line ABOVE the
        charge -- silently no-opped.  A half transaction on the flagship
        script, produced by the module built to prevent it.

        So this is the same mutant, kept as a NEGATIVE now: realness is
        still what the gate reads, and the group correctly stays shut
        while ANY give member is a stub.
        """
        with mock.patch.object(lua_player, "REAL_METHODS",
                               lua_player.REAL_METHODS | {"AddItem"}), \
                mock.patch.object(
                    quest, "REAL_METHODS",
                    quest.REAL_METHODS | {"RewardItemSelect",
                                          "AddCriteriaExp",
                                          "AddCriteriaSkillPoint",
                                          "AddCriteriaCash"}):
            namespace, lines = self._namespace(GATED_QUEST_ID)
            self.assertEqual(namespace["Var4"], qr.REFUSED_CELL)
            refusals = [line for line in lines
                        if line.startswith("LUA_QUEST_GROUP_REFUSED")]
            self.assertTrue(refusals, lines)
            self.assertTrue(any("blocked_on=Player.AddPpClass" in line
                                for line in refusals), refusals)

    def test_the_group_opens_by_itself_the_day_every_give_becomes_real(self):
        """The mutant that proves the gate is reading REALNESS, not a date.

        Nothing else changes: same mirror, same table, same row.  The only
        edit is every give-side API of the group joining its namespace's
        `REAL_METHODS`, and both halves come back at once -- the charge
        AND the item ids.  That is what "opened together" has to mean, and
        it is why the blocking API is named in the log rather than
        described in a comment.
        """
        with mock.patch.object(lua_player, "REAL_METHODS",
                               lua_player.REAL_METHODS | {"AddItem",
                                                          "AddPpClass"}), \
                mock.patch.object(
                    quest, "REAL_METHODS",
                    quest.REAL_METHODS | {"RewardItemSelect",
                                          "AddCriteriaExp",
                                          "AddCriteriaSkillPoint",
                                          "AddCriteriaCash"}):
            namespace, lines = self._namespace(GATED_QUEST_ID)
            self.assertEqual(namespace["Var4"], -15000)
            self.assertEqual(namespace["RewardItem1"], GATED_ITEMS[0])
            self.assertEqual(namespace["RewardItem3"], GATED_ITEMS[2])
        self.assertFalse([line for line in lines
                          if line.startswith("LUA_QUEST_GROUP_REFUSED")])

    def test_one_stubbed_give_api_is_enough_to_hold_the_whole_group(self):
        """Four of `Q_CLASS.Report_Run`'s five give-side members real and
        `Player.AddPpClass` not is still a half transaction -- the group
        waits on ALL of its give side.

        `Player.AddItem` was this test's own example of that one stub
        until round `6gc0zk`, when it went real -- it needs no mocking
        here any more, and `Player.AddPpClass` (still a stub) takes its
        place as the single name this test isolates; see
        `test_additem_alone_is_not_enough_because_the_class_change_is_a_
        give`, which pins the same group with a different subset real.
        """
        with mock.patch.object(
                quest, "REAL_METHODS",
                quest.REAL_METHODS | {"RewardItemSelect", "AddCriteriaExp",
                                      "AddCriteriaSkillPoint",
                                      "AddCriteriaCash"}):
            namespace, lines = self._namespace(GATED_QUEST_ID)
            self.assertEqual(namespace["Var4"], qr.REFUSED_CELL)
        blocked = [line for line in lines
                   if line.startswith("LUA_QUEST_GROUP_REFUSED")]
        self.assertEqual(len(blocked), 1, blocked)
        self.assertIn("blocked_on=Player.AddPpClass", blocked[0])
        self.assertNotIn("Player.AddItem", blocked[0].split(
            "call_site=")[0])

    def test_an_unbound_run_refuses_a_reward_name_by_its_own_reason(self):
        lines = []
        namespace = quest.build_namespace(frozenset(), lines.append)
        self.assertEqual(namespace["RewardItem1"], quest.STUB_DEFAULT)
        self.assertEqual(len(lines), 1)
        self.assertIn("refused=%s" % qv.REFUSE_NO_QUEST_BOUND, lines[0])

    def test_a_reward_name_of_an_unknown_quest_is_refused_by_name(self):
        namespace, lines = self._namespace(999999)
        self.assertEqual(namespace["RewardItem1"], quest.STUB_DEFAULT)
        self.assertEqual(len(lines), 1)
        self.assertIn("refused=%s" % qv.REFUSE_NO_QUEST_ROW, lines[0])

    def test_no_shipped_row_can_open_half_a_group(self):
        """COO `0242`: "a test that no script opens half a group".

        Every row of every coupled script, every member column, one
        assertion: the row either answers ALL of its group's columns or
        NONE of them.  A group that answered its take side and refused its
        give side is the state the rule forbids, and this is the check
        that says no row anywhere is in it.
        """
        checked = 0
        for script, entries in qr.load_groups().items():
            for quest_id in sorted(qc.quests_for_script(script)):
                for group in entries:
                    answered = set()
                    for member in group.members:
                        if member.column == qr.NO_COLUMN:
                            refused = qr.unpayable_group_for(
                                quest_id, member.api_name) is not None
                        elif member.side == qr.TAKE:
                            refused = qr.unpayable_group_for(
                                quest_id, member.column) is not None
                        else:
                            _value, reason = qr.reward_cell(
                                quest_id, _lua_name_for(member.column))
                            refused = reason is not None
                        answered.add(not refused)
                        checked += 1
                    self.assertEqual(
                        len(answered), 1,
                        "quest %d opened half of %s.%s"
                        % (quest_id, script, group.group))
        self.assertEqual(checked, 7816,
                         "RE-DERIVED round `ad7t6n`, which put "
                         "`Player.RemoveItem` on the take side and with "
                         "it 56 more groups, all in `Report_Run`, on the "
                         "gather/send/set quests the shipped table names "
                         "on many rows each -- so this number is now "
                         "dominated by rows, not by groups.  Re-derive "
                         "it, do not adjust it: sum over every coupled "
                         "script of (rows naming that script) x (members "
                         "of each of its groups).  If it moves, a group "
                         "or a row appeared and the assertion above has "
                         "to be read again")


def _lua_name_for(source_column: str) -> str:
    """The ``Quest.<name>`` that reads a shipped reward column."""
    for name, column in qr._LUA_NAME_TO_SOURCE.items():
        if column == source_column:
            return name
    raise AssertionError("no Lua name reads %s" % source_column)


class TheScannerSeesEveryCallTests(unittest.TestCase):
    """Layer 2b: the SCANNER, on scripts this file writes.

    GATE-RUNNABLE ON PURPOSE (pf-adversary D8, round `yzdgx1`: the give
    side is checked only where a `pf_bridge` checkout exists, so on the
    Windows gate none of it runs).  Everything here feeds the tool bytes
    from `tempfile` instead of the corpus, so the rules the tool applies
    are held by a machine that has never seen the game -- and the two
    holes pf-adversary D3 named are pinned as the tool REFUSING rather
    than as the corpus happening not to contain them.
    """

    def _tool(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import pf_regen_lua_quest_rewards as regen
        finally:
            sys.path.pop(0)
        return regen

    def _script(self, body: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".lua", delete=False, encoding="ascii")
        handle.write(body)
        handle.close()
        path = Path(handle.name)
        self.addCleanup(path.unlink)
        return path

    def test_removeitem_charges_with_both_of_its_cells(self):
        """The item charge reads the id AND the count, at one call.

        `Player.RemoveItem(item, count)` takes the player's item whatever
        the cells hold, so both cells are part of that charge -- unlike
        `Player.AddCash`, where only a SIGN says the player pays at all.
        Asserted on a script written here, so the rule is held on a
        machine with no corpus.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.RemoveItem(Quest.Var2,Quest.Var3)\n"
            "end\n")
        self.assertEqual(
            [(index, api) for _function, index, api, _number
             in regen.take_sites(path)],
            [(2, "Player.RemoveItem"), (3, "Player.RemoveItem")])

    def test_removeitem_charges_from_the_count_alone(self):
        """A literal item id and a cell COUNT is still a charge.

        The shape `Player.RemoveItem(2600392, Quest.Var3)` -- the corpus
        has exactly one, at `q_sea_reward.lua:100`, on a script no
        shipped row names -- is why argument 1 is read and not only
        argument 0.  A scan that read the id position alone would report
        no take here, form no group, and leave the transaction as
        unguarded as `q_ship.lua` was.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.RemoveItem(2600392,Quest.Var3)\n"
            "end\n")
        self.assertEqual(
            [(index, api) for _function, index, api, _number
             in regen.take_sites(path)],
            [(3, "Player.RemoveItem")])

    def test_removeitem_walks_past_an_argument_that_reads_no_cell(self):
        """`delItem[1]`, `mySet_1[i]` and bare literals are not this
        lane's business: 49 of the 367 call sites hand `RemoveItem`
        something that is not a quest cell at one position or both, and a
        take with no cell to name is one this table must not carry."""
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.RemoveItem(Quest.Var2,delItem[1])\n"
            "    Player.RemoveItem(mySet_1[i],mySet_2[i])\n"
            "    Player.RemoveItem(2200225,2)\n"
            "end\n")
        self.assertEqual(
            [(index, api) for _function, index, api, _number
             in regen.take_sites(path)],
            [(2, "Player.RemoveItem")])

    def test_an_unclassified_removeitem_argument_stops_the_tool(self):
        """The shape nobody has read is LOUD, not skipped.

        Every one of the 367 shipped call sites hands `RemoveItem` a BARE
        `Quest.VarN` at any cell-reading position.  The day one is
        shipped that does arithmetic on a cell, this tool must name the
        line rather than report no take -- because no take means no
        group, no refusal, a green run and a player charged for an
        undelivered reward.  That is the same contract
        `UnclassifiedTakeSite` already carries for the money shapes.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.RemoveItem(Quest.Var2 + 1,Quest.Var3)\n"
            "end\n")
        with self.assertRaises(regen.UnclassifiedTakeSite) as caught:
            regen.take_sites(path)
        self.assertIn("Quest.Var2 + 1", str(caught.exception))
        self.assertIn("Player.RemoveItem", str(caught.exception))

    def test_a_bare_cell_is_a_take_for_removeitem_and_not_for_addcash(self):
        """One spelling, two meanings, decided by the API not the shape.

        `Player.AddCash(Quest.Var3)` is NOT reported: the sign is the only
        thing that says the player pays, and where the shipped cell is
        negative `quest_var_signedness.tsv` already carries it with its
        own provenance.  The identical argument to `Player.RemoveItem`
        IS reported.  Reading both under one rule is what left one of the
        two kinds of charge invisible.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.AddCash(Quest.Var3)\n"
            "    Player.RemoveItem(Quest.Var3,1)\n"
            "end\n")
        self.assertEqual(
            [(index, api) for _function, index, api, _number
             in regen.take_sites(path)],
            [(3, "Player.RemoveItem")])

    def test_a_second_charge_on_the_same_line_is_read_too(self):
        """The hole itself: `line.find` once meant one call per line.

        Two `Player.AddCash` calls on one line used to produce ONE take
        site -- the second charge read by nothing, the mirror green and
        `--check` clean.  The corpus has no such line today (measured: six
        `AddCash` call sites, six lines), which is why this is asserted
        against a script written here rather than against the game.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.AddCash(-Quest.Var3) Player.AddCash(Quest.Var5 * -1)\n"
            "end\n")
        found = regen.take_sites(path)
        self.assertEqual([(function, index, api) for function, index, api,
                          _number in found],
                         [("Report_Run", 3, "Player.AddCash"),
                          ("Report_Run", 5, "Player.AddCash")])

    def test_a_second_reward_give_on_the_same_line_is_read_too(self):
        """The same hole on the give side, which is the worse direction.

        A give the scan cannot see does not open a group, so the take it
        was paired with is never refused.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.AddItem(Quest.RewardItem1,1) "
            "Player.AddItem(Quest.RewardItem2,1)\n"
            "end\n")
        slots = sorted(entry[1] for entry in regen.give_sites(path))
        self.assertEqual(slots, [1, 2])

    def test_an_unclassified_negation_stops_the_tool_instead_of_passing(self):
        """D3, said as the tool behaving rather than as four regexes.

        `-1 * Quest.VarN` is not one of the two spellings the corpus uses.
        The old scan walked past it without a word: no take, no group, no
        refusal, and a player charged for an undelivered thing with every
        test green.  Now the run STOPS and the message names the line.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.AddCash(-1 * Quest.Var3)\n"
            "end\n")
        with self.assertRaises(regen.UnclassifiedTakeSite) as caught:
            regen.take_sites(path)
        self.assertIn(":2", str(caught.exception))
        self.assertIn("Player.AddCash", str(caught.exception))

    def test_each_of_the_four_shapes_pf_adversary_named_is_refused(self):
        """All four, so removing the stop for one of them fails here."""
        regen = self._tool()
        for argument in ("-1 * Quest.Var3", "-(Quest.Var3)",
                         "Quest.Var3 * -2", "0 - Quest.Var3"):
            path = self._script(
                "function Report_Run()\n"
                "    Player.AddCash(%s)\n"
                "end\n" % argument)
            with self.assertRaises(regen.UnclassifiedTakeSite, msg=argument):
                regen.take_sites(path)

    def test_the_bare_read_is_not_a_script_negated_take(self):
        """The refund half of the same API name, and why shape decides.

        `q_day_business.lua:105` gives `Quest.Var7` BACK in `Delete_Run`,
        one bare read of the same cell `Accept_Run` spent.  A rule that
        keyed on the NAME would call the refund a charge; the shape is
        what tells them apart, and the bare read is the signedness
        table's business, not this scan's.
        """
        regen = self._tool()
        path = self._script(
            "function Delete_Run()\n"
            "    Player.Addmoralized(Quest.Var7)\n"
            "end\n")
        self.assertEqual(regen.take_sites(path), [])

    def test_an_argument_that_reads_no_cell_is_nobody_s_business(self):
        """A literal amount is not a column, so it is passed over quietly.

        SAID OUT LOUD BECAUSE IT IS A LIMIT, not a result: this table
        gates COLUMNS, so a charge that names no cell cannot be a member
        of a group and the scan has nothing to record.  No corpus call
        site is in this shape today.
        """
        regen = self._tool()
        path = self._script(
            "function Report_Run()\n"
            "    Player.AddCash(-15000)\n"
            "end\n")
        self.assertEqual(regen.take_sites(path), [])


@BRIDGE_GAMEDATA.skip_unless_present()
@BRIDGE_LUA_SCRIPTS.skip_unless_present()
class MirrorsMatchTheGameTests(unittest.TestCase):
    """Layer 4: only where the bridge checkout is.  The gate has none."""

    def test_regenerating_produces_byte_identical_mirrors(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools"
                                 / "pf_regen_lua_quest_rewards.py"), "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)

    def _tool(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import pf_regen_lua_quest_rewards as regen
        finally:
            sys.path.pop(0)
        return regen

    def test_every_morale_charge_in_the_corpus_is_read_as_a_take(self):
        """The eleven, by name, so a lost one fails here (round `5a3x47`).

        `Player.Addmoralized(-Quest.VarN)` is the charge; the same name
        with a BARE argument is the refund, and there are ten of those.
        Both halves are asserted, because a scan that started reading the
        refund as a charge would gate cells the player is owed.
        """
        regen = self._tool()
        corpus = SIBLING / "pf_bridge" / "gamedata" / "lua"
        charges, refunds = [], 0
        for path in sorted(corpus.rglob("*.lua")):
            data = path.read_bytes()
            if b"Addmoralized" not in data:
                continue
            takes = {(number, index) for _function, index, api, number
                     in regen.take_sites(path) if api == "Player.Addmoralized"}
            for number, line in enumerate(data.split(b"\n"), start=1):
                for args in regen.argument_lists_of(line,
                                                    b"Player.Addmoralized"):
                    argument = args[0].strip()
                    if argument.startswith(b"-"):
                        charges.append((path.name, number))
                        self.assertIn(
                            (number, int(argument.rsplit(b"Var", 1)[1])),
                            takes, "%s:%d" % (path.name, number))
                    else:
                        refunds += 1
                        self.assertNotIn(
                            number, {entry[0] for entry in takes},
                            "%s:%d is the refund" % (path.name, number))
        self.assertEqual(
            sorted(charges),
            [("q_day_business.lua", 26), ("q_day_hunt.lua", 55),
             ("q_ocean_checkbuff.lua", 24), ("q_ocean_con.lua", 24),
             ("q_ocean_gather1.lua", 24), ("q_ocean_gather2.lua", 24),
             ("q_ocean_guard.lua", 24), ("q_ocean_kill1.lua", 26),
             ("q_ocean_kill2.lua", 25), ("q_ocean_kill3.lua", 27),
             ("q_repeat_hunt.lua", 54)])
        self.assertEqual(refunds, 10)

    def test_the_ship_purchase_is_classified_even_though_no_row_reaches_it(self):
        """pf-adversary D1, round `yzdgx1`, ANSWERED RATHER THAN DELETED.

        `Player.ChangeShip` and the `-Quest.VarN` spelling live in the
        tool for `q_ship.lua` alone, and the shipped quest table names
        `q_ship` on ZERO of its 1544 rows -- so no group is ever built
        from either and a mutant deleting them changes no mirror.  The
        answer is not to delete a true reading of the corpus; it is to
        assert the reading directly, on the file, where deleting either
        one fails.
        """
        regen = self._tool()
        corpus = SIBLING / "pf_bridge" / "gamedata" / "lua"
        path = regen.corpus_file_for(corpus, "q_ship")
        self.assertIsNotNone(path)
        self.assertEqual(
            [(index, api, number) for _function, index, api, number
             in regen.take_sites(path)],
            [(3, "Player.AddCash", 50),
             (8, "Player.RemoveItem", 51),
             (4, "Player.RemoveItem", 51)],
            "round `ad7t6n`: the ship is not only paid for, it is "
            "TRADED for -- `Player.RemoveItem(Quest.Var8,Quest.Var4)` on "
            "the line after the charge takes an item too, and both cells "
            "of that one call are members of the same charge")
        self.assertIn(
            ("Report_Run", 0, None, "Player.ChangeShip", 49),
            [entry[:5] for entry in regen.give_sites(path)])
        source = (SIBLING / "pf_bridge" / "gamedata" / "tables"
                  / "QUESTDATA_TH__QUEST.tsv")
        named = {script.strip().lower()
                 for _identifier, script, _cells in regen.read_rows(source)}
        self.assertNotIn("q_ship", named,
                         "a row now names q_ship: the group table should "
                         "have grown a fourth script, and this test is the "
                         "one that says why it had not")

    def test_every_reward_cell_matches_the_source_by_column_name(self):
        """The tie a mirror checked only against itself never has.

        Read the shipped table again, by COLUMN NAME, and compare cell by
        cell -- so a tool that wrote the right shape from the wrong columns
        is caught here rather than believed forever (pf-adversary F2,
        round `5qtaqy`).
        """
        import csv
        source = (SIBLING / "pf_bridge" / "gamedata" / "tables"
                  / "QUESTDATA_TH__QUEST.tsv")
        mirror = qr.load_rewards()
        seen = 0
        with source.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                cells = mirror[int(row["n_ID"])]
                for index, name in enumerate(qr.SOURCE_COLUMNS):
                    self.assertEqual(cells[index], int(row[name]),
                                     "%s %s" % (row["n_ID"], name))
                seen += 1
        self.assertEqual(seen, len(mirror))

    def test_the_call_site_of_every_member_reads_that_column(self):
        """Provenance that points at a line which does not mention the
        column is provenance nobody checked.

        NO `lua_corpus_runnable` GUARD, deliberately: this reads corpus
        BYTES and executes no Lua, so demanding `lupa` would stop it on
        exactly the bridge machines that can run it -- the mistake
        pf-adversary D2 of round `joa0u6` caught in the sibling module.
        The class's `bridge_lua_scripts` guard is the one that applies.
        """
        corpus = SIBLING / "pf_bridge" / "gamedata" / "lua"
        for entries in qr.load_groups().values():
            for group in entries:
                for member in group.members:
                    relative, _, number = member.call_site.rpartition(":")
                    data = (corpus / relative).read_bytes().split(b"\n")
                    line = data[int(number) - 1]
                    self.assertIn(member.api_name.split(".")[1].encode("ascii"),
                                  line, member.call_site)


class TheRefusalKnowsWhichEntryPointIsRunningTests(unittest.TestCase):
    """pf-adversary D8 (round `5a3x47`): a group is one entry point's fact.

    A group is DEFINED as the take and give one Lua entry point performs
    together -- it is even keyed that way in the mirror -- but until this
    round the refusal was delivered through ``Quest.VarN``, keyed only on
    ``(quest_id, column)``, and therefore imposed on every OTHER top-level
    function of the same script as well.

    ``Q_BOAT_HEALTH`` (quest 3189) is the whole defect in one shipped file,
    which is why it is the fixture here rather than a hand-written one: its
    single group belongs to ``Accept_Run`` (blocked on ``Player.BoatHealth``,
    still a stub), and ``n_VARI_2`` is the 100-cash price the repair costs.
    """

    QUEST = 3189
    OWNER = "Accept_Run"
    PRICE = 100

    def test_the_owning_entry_point_still_has_its_cells_refused(self):
        state = qr.unpayable_group_for(self.QUEST, "n_VARI_2", self.OWNER)
        self.assertIsNotNone(state)
        self.assertEqual(state.group.group, self.OWNER)
        self.assertEqual(
            qr.resolve_var_for_namespace(lambda _line: None, self.QUEST, 2,
                                         STUB_DEFAULT, None, self.OWNER),
            qr.REFUSED_CELL)

    def test_another_entry_point_of_the_same_script_reads_the_real_cell(self):
        # D8 itself.  `Report_Check`/`Delete_Run`/`Accept_Check` are not
        # part of the repair transaction and were being handed -1 for it.
        for entry_point in ("Accept_Check", "Report_Check", "Report_Run",
                            "Delete_Run", "OpenAcceptUI_Run"):
            with self.subTest(entry_point=entry_point):
                self.assertIsNone(qr.unpayable_group_for(self.QUEST,
                                                         "n_VARI_2",
                                                         entry_point))
                self.assertEqual(
                    qr.resolve_var_for_namespace(lambda _line: None,
                                                 self.QUEST, 2, STUB_DEFAULT,
                                                 None, entry_point),
                    self.PRICE)

    def test_an_unnamed_entry_point_refuses_exactly_as_much_as_before(self):
        # FAIL-CLOSED, and the pin that says so.  If unknown ever scoped to
        # "no group", every caller that forgets to name its entry point
        # would silently disarm the gate -- the state COO `0242` item 4
        # forbids.  Both spellings of unknown, and the default, must refuse.
        for unknown in (qr.UNKNOWN_ENTRY_POINT, ""):
            with self.subTest(unknown=unknown):
                self.assertIsNotNone(qr.unpayable_group_for(self.QUEST,
                                                            "n_VARI_2",
                                                            unknown))
        self.assertIsNotNone(qr.unpayable_group_for(self.QUEST, "n_VARI_2"))
        self.assertEqual(
            qr.resolve_var_for_namespace(lambda _line: None, self.QUEST, 2,
                                         STUB_DEFAULT),
            qr.REFUSED_CELL)

    def test_only_the_owner_is_refused_as_a_whole_entry_point(self):
        owner = qr.unpayable_group_of_entry_point(self.QUEST, self.OWNER)
        self.assertIsNotNone(owner)
        self.assertEqual(owner.group.script, "Q_BOAT_HEALTH")
        self.assertEqual(owner.blocking, ("Player.BoatHealth",))
        for other in ("Accept_Check", "Report_Check", "Report_Run",
                      "Delete_Run", "Script_Start", qr.UNKNOWN_ENTRY_POINT):
            with self.subTest(other=other):
                self.assertIsNone(
                    qr.unpayable_group_of_entry_point(self.QUEST, other))

    def test_a_row_whose_groups_are_all_payable_refuses_no_entry_point(self):
        # The negative result: entry-point scoping must not invent a
        # refusal for a row that had none.
        #
        # DRIVEN BY MAKING THE APIS REAL, not by looking for such a row in
        # the shipped table.  pf-adversary D3 of round `0ldyk7` measured
        # that the first version of this test did the latter and was
        # VACUOUS: today zero of the 452 rows with a group have all their
        # groups payable (Player.AddItem/RemoveItem are stubs, so every
        # group blocks), the list was empty, the loop body never ran, and
        # the test was green for the one reason a test must never be green.
        # It could not falsify `not state.payable` -- deleting that clause
        # left the whole suite passing.
        with mock.patch.object(qr, "_default_api_is_real",
                               return_value=True):
            for quest_id in (self.QUEST, 39, 42, 44):
                states = qr.group_state(quest_id)
                self.assertTrue(states, quest_id)
                self.assertTrue(all(state.payable for state in states))
                for entry_point in ("Accept_Run", "Report_Run",
                                    "Delete_Run"):
                    self.assertIsNone(
                        qr.unpayable_group_of_entry_point(quest_id,
                                                          entry_point))
                self.assertIsNone(qr.unpayable_group_for(quest_id,
                                                         "n_VARI_2"))
        # And back, on the real table, without the patch.
        self.assertIsNotNone(
            qr.unpayable_group_of_entry_point(self.QUEST, self.OWNER))

    def test_the_host_call_ACTS_on_the_refusal_and_does_not_merely_log_it(self):
        """``ScriptHost.call`` refuses, WITHOUT a Lua runtime to prove it.

        pf-adversary D2 of round `0ldyk7`: every other test of the acting
        half is in `tests/test_script_host_spike.py`, guarded by
        `LUPA_PACKAGE`, so on a cloud clone -- where this lane does all its
        work -- replacing the `raise` in `ScriptHost.call` with nothing at
        all left the entire suite green.  The gate reported and did not
        act, and nothing said so.

        So this drives the REAL `ScriptHost.call` against a stand-in
        `self`: the method is called unbound, with an object carrying only
        the four attributes it touches.  Not a mock of the gate -- the gate
        itself, line for line, including `_refuse_if_degraded`'s real
        ordering.  `runtime` raises if it is ever reached, which is the
        assertion that matters: a `call` that only logged would fall
        through to it.
        """
        class _RuntimeThatMustNotBeReached:
            def globals(self):  # pragma: no cover - reaching this is the bug
                raise AssertionError("call() ran the script after refusing")

        class _HostStandIn:
            _refuse_if_degraded = script_host.ScriptHost._refuse_if_degraded
            call = script_host.ScriptHost.call
            degraded = False
            mirror_failure = None

            def __init__(self, namespace, log):
                self.namespaces = {"Quest": namespace}
                self.log = log
                self.runtime = _RuntimeThatMustNotBeReached()

        lines = []
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lines.append,
            context=quest.QuestContext(character_id=1, quest_id=self.QUEST))
        host = _HostStandIn(namespace, lines.append)
        with self.assertRaises(script_host.EntryPointRefused) as raised:
            host.call(self.OWNER)
        self.assertIn("Player.BoatHealth", str(raised.exception))
        self.assertIn("LUA_QUEST_ENTRY_REFUSED script=Q_BOAT_HEALTH "
                      "entry=Accept_Run quest=3189 "
                      "blocked_on=Player.BoatHealth", lines)
        # The entry point BESIDE it is not refused, so `call` goes on to
        # the runtime -- which is how this test knows the refusal above was
        # the gate and not the stand-in refusing everything.
        with self.assertRaises(AssertionError):
            host.call("Report_Check")

    def test_the_namespace_carries_the_entry_point_and_puts_it_back(self):
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lambda _line: None,
            context=quest.QuestContext(character_id=1, quest_id=self.QUEST))
        self.assertEqual(namespace.context.entry_point,
                         qr.UNKNOWN_ENTRY_POINT)
        self.assertEqual(namespace["Var2"], qr.REFUSED_CELL)
        with namespace.entering("Report_Check") as entered:
            self.assertIs(entered, namespace)
            self.assertEqual(namespace.context.entry_point, "Report_Check")
            self.assertEqual(namespace["Var2"], self.PRICE)
        # RESTORED, and restored to unknown rather than left open: a host
        # someone reads cells off of outside a call gets the conservative
        # answer back, not the last entry point that happened to run.
        self.assertEqual(namespace.context.entry_point,
                         qr.UNKNOWN_ENTRY_POINT)
        self.assertEqual(namespace["Var2"], qr.REFUSED_CELL)

    def test_the_scope_is_restored_even_when_the_entry_point_raises(self):
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lambda _line: None,
            context=quest.QuestContext(character_id=1, quest_id=self.QUEST))
        with self.assertRaises(ZeroDivisionError):
            with namespace.entering("Report_Check"):
                raise ZeroDivisionError("the script blew up mid entry point")
        self.assertEqual(namespace.context.entry_point,
                         qr.UNKNOWN_ENTRY_POINT)

    def test_the_context_cannot_be_swapped_behind_the_gates_back(self):
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lambda _line: None,
            context=quest.QuestContext(character_id=1, quest_id=self.QUEST))
        with self.assertRaises(AttributeError):
            namespace.context = quest.QuestContext(character_id=1, quest_id=1)

    def test_the_gate_reads_the_namespace_and_refuses_the_owner(self):
        # `quest.entry_point_refusal` is module level, and lives in
        # `lua_api` rather than in `script_host`, precisely so this runs
        # where `lupa` does not -- which is every cloud clone this lane
        # works from.  Both sentences are asserted, because the log line is
        # the only thing a reader of a live server will ever see.
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lambda _line: None,
            context=quest.QuestContext(character_id=1, quest_id=self.QUEST))
        refused = quest.entry_point_refusal(namespace, self.OWNER)
        self.assertIsNotNone(refused)
        self.assertEqual(refused.log_line,
                         "LUA_QUEST_ENTRY_REFUSED script=Q_BOAT_HEALTH "
                         "entry=Accept_Run quest=3189 "
                         "blocked_on=Player.BoatHealth")
        self.assertIn("Player.BoatHealth", refused.message)
        for other in ("Accept_Check", "Report_Run", "Delete_Run"):
            self.assertIsNone(quest.entry_point_refusal(namespace, other))

    def test_a_namespace_with_no_context_refuses_no_entry_point(self):
        self.assertIsNone(quest.entry_point_refusal(None, "Accept_Run"))
        self.assertIsNone(quest.entry_point_refusal(object(), "Accept_Run"))

    def test_an_unbound_row_refuses_no_entry_point(self):
        # Why the corpus sweep cannot raise EntryPointRefused: it never
        # passes a context, so every host it builds is bound to row 0,
        # which has no script and therefore no group.  The sweep's numbers
        # are untouched by this gate, stated here rather than trusted in a
        # comment.
        namespace = quest.build_namespace(
            spec.NAMESPACE_METHODS["Quest"], lambda _line: None)
        self.assertEqual(namespace.context.quest_id, 0)
        for entry_point in script_host.STANDARD_ENTRY_POINTS:
            self.assertIsNone(quest.entry_point_refusal(namespace,
                                                        entry_point))

    def test_every_group_in_the_mirror_is_owned_by_a_known_entry_point(self):
        # The census this scoping stands on, pinned so a regen that moves a
        # group to an entry point the host never calls is seen HERE and not
        # as a gate that silently stopped refusing anything.  Today: 61
        # groups, 60 in Report_Run and one in Accept_Run (Q_BOAT_HEALTH).
        owners = {}
        for entries in qr.load_groups().values():
            for group in entries:
                owners[group.group] = owners.get(group.group, 0) + 1
        self.assertEqual(owners, {"Report_Run": 60, "Accept_Run": 1})
        self.assertLessEqual(set(owners), set(script_host.STANDARD_ENTRY_POINTS))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
