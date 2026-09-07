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
     which is the negative result that says the gate reads the ROW; and
     the moment ``Player.AddItem`` becomes real the group opens by itself.
  4. THE MIRRORS MATCH THE GAME (needs ../pf_bridge, skipped on the gate).

WHAT THIS ROUND DELIBERATELY UNDID.  Round `joa0u6` made
``Quest/q_class.lua`` take 15,000 off the player for real.  Four lines
later the same function is supposed to hand over three items through
``Player.AddItem``, which is a stub.  COO-DECISION ``20260908_0242`` item
4 chose the free quest over the robbed player, so the tests that pinned
the charge now pin the refusal, and the join underneath them is asserted
separately in ``test_script_lua_quest_vars`` so that a gate quietly
deleting the value cannot pass both.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pf_preconditions import BRIDGE_GAMEDATA, BRIDGE_LUA_SCRIPTS, SIBLING

from pirateforce_foundation.lua_api import (player as lua_player, quest,
                                            quest_criteria as qc,
                                            quest_rewards as qr,
                                            quest_vars as qv, vendored)
from pirateforce_foundation.lua_api.quest_criteria import QuestCriteriaError

REPO_ROOT = Path(__file__).resolve().parents[1]
MIRROR_DIR = REPO_ROOT / "src" / "pirateforce_foundation" / "lua_api"

#: The class-change quest: charges 15,000 (`n_VARI_4`) and names three
#: reward items in the SAME `Report_Run`.  The whole reason this module
#: exists.
GATED_QUEST_ID = 3200
GATED_ITEMS = (2480010, 2480011, 2480012)

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
EXPECTED_GROUPS = {
    ("q_class", "Report_Run"): ("n_VARI_4", "Quest/q_class.lua:60"),
    ("q_guild_boss2", "Report_Run"): ("n_VARI_8",
                                      "Quest/q_guild_boss2.lua:59"),
    ("q_boat_health", "Accept_Run"): ("n_VARI_2",
                                      "Quest/q_boat_health.lua:21"),
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

    def test_exactly_the_three_coupled_scripts_are_in_the_table(self):
        groups = qr.load_groups()
        found = {(script, group.group)
                 for script, entries in groups.items() for group in entries}
        self.assertEqual(found, set(EXPECTED_GROUPS))

    def test_every_group_names_both_sides_with_provenance(self):
        for script, entries in qr.load_groups().items():
            for group in entries:
                take = group.side(qr.TAKE)
                give = group.side(qr.GIVE)
                self.assertTrue(take, script)
                self.assertTrue(give, script)
                expected_column, expected_site = EXPECTED_GROUPS[
                    (script, group.group)]
                self.assertEqual([member.column for member in take],
                                 [expected_column])
                self.assertEqual(take[0].call_site, expected_site)
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
                        self.assertIn(member.api_name, ("Player.AddCash",))
                        self.assertTrue(member.call_site.endswith(
                            EXPECTED_GROUPS[(script, group.group)][1]
                            .rsplit("/", 1)[-1]), member.call_site)
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
        self.assertEqual(namespace["Var4"], quest.STUB_DEFAULT)
        self.assertEqual(namespace["RewardItem1"], quest.STUB_DEFAULT)
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
        self.assertEqual(namespace["Var8"], quest.STUB_DEFAULT)
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
        """
        body = ("Q_CLASS\tReport_Run\ttake\tn_VARI_4\t"
                "Player.AddCash\tQuest/q_class.lua:60\n"
                "Q_CLASS\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                "Player.AddItem\tQuest/q_class.lua:64\n"
                "Q_GUILD_BOSS2\tReport_Run\ttake\tn_VARI_8\t"
                "Player.AddCash\tQuest/q_guild_boss2.lua:59\n"
                "Q_GUILD_BOSS2\tReport_Run\tgive\tn_REWARD_ITEM1\t"
                "Player.AddItem\tQuest/q_guild_boss2.lua:62\n")
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
            self.assertEqual(gated["Var4"], quest.STUB_DEFAULT,
                             "3200 DOES name a reward item, so the same "
                             "column-only table gates it and not 8061")

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
            self.assertEqual(namespace["Var4"], quest.STUB_DEFAULT)
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
        """`Quest.RewardItemSelect` real and `Player.AddItem` not is still
        a half transaction -- the group waits on ALL of its give side."""
        with mock.patch.object(quest, "REAL_METHODS",
                               quest.REAL_METHODS | {"RewardItemSelect"}):
            namespace, lines = self._namespace(GATED_QUEST_ID)
            self.assertEqual(namespace["Var4"], quest.STUB_DEFAULT)
        blocked = [line for line in lines
                   if line.startswith("LUA_QUEST_GROUP_REFUSED")]
        self.assertEqual(len(blocked), 1, blocked)
        self.assertIn("blocked_on=Player.AddItem", blocked[0])
        self.assertNotIn("Quest.RewardItemSelect", blocked[0].split(
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
        self.assertEqual(checked, 169,
                         "RE-DERIVED round `yzdgx1` (pf-adversary D7 "
                         "against round `kkuqzo`, which left a wrong "
                         "arithmetic string on the one assertion whose "
                         "job is to be re-read): 5 Q_CLASS rows x 17 "
                         "members (16 + Player.AddPpClass, new this "
                         "round) + 5 Q_GUILD_BOSS2 rows x 16 + 2 "
                         "Q_BOAT_HEALTH rows x 2 = 85 + 80 + 4 = 169. If "
                         "this number moves, a group or a row appeared "
                         "and the assertion above has to be read again")


def _lua_name_for(source_column: str) -> str:
    """The ``Quest.<name>`` that reads a shipped reward column."""
    for name, column in qr._LUA_NAME_TO_SOURCE.items():
        if column == source_column:
            return name
    raise AssertionError("no Lua name reads %s" % source_column)


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
