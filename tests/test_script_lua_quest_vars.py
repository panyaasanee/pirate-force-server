"""``Quest.VarN`` and the per-column signedness table (LANE-Q, COO `0042`).

Four layers, and they are kept apart on purpose because they fail for
different reasons and on different machines:

  1. THE MIRRORS PARSE (gate-runnable, no bridge checkout).  Shape, digest
     header, refusals.  This is what the Windows gate can see.
  2. THE TABLE SAYS WHAT IT SAYS (gate-runnable).  Five rows, two kinds,
     every row's provenance pointing at a real corpus line, every row's
     evidence actually present in the row mirror.
  3. THE JOIN BEHAVES (gate-runnable).  Signed columns unwrap; unsigned
     columns holding a wrapped cell are REFUSED by name; unknown quest ids
     are refused by a different name; `Quest.Var4` on a live namespace
     hands a script -15000 where it handed 0 yesterday.
  4. THE MIRRORS MATCH THE GAME (needs ../pf_bridge, skipped on the gate).
     Regenerating is byte-identical AND the derivation re-runs from the
     source table by COLUMN NAME -- the tie `api_spec.tsv` never had, which
     pf-adversary F2 of round `5qtaqy` measured as this lane's standing
     hole: a mirror checked only against itself.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pf_preconditions import (BRIDGE_GAMEDATA, BRIDGE_LUA_SCRIPTS,
                             LUA_CORPUS_RUNNABLE, SIBLING)

from pirateforce_foundation.lua_api import (quest, quest_criteria as qc,
                                            quest_rewards, quest_vars as qv,
                                            vendored)
from pirateforce_foundation.lua_api.quest_criteria import QuestCriteriaError

REPO_ROOT = Path(__file__).resolve().parents[1]
MIRROR_DIR = (REPO_ROOT / "src" / "pirateforce_foundation" / "lua_api")

#: The five (script, column) pairs the derivation finds in the shipped
#: table, spelled out here so a change to the mirror has to be a change to
#: this list too.  Re-derive with:
#:     python3 tools/pf_regen_lua_quest_vars.py --explain
EXPECTED_SIGNED = {
    ("q_class", 4): ("signed_money", "Player.AddCash",
                     "Quest/q_class.lua:60"),
    ("q_guild_boss2", 8): ("signed_money", "Player.AddCash",
                           "Quest/q_guild_boss2.lua:59"),
    ("q_kill_skxyz", 10): ("signed_coordinate", "Player.CastSkillXYZ",
                           "Quest/q_kill_skxyz.lua:85"),
    ("q_kill_skxyz", 11): ("signed_coordinate", "Player.CastSkillXYZ",
                           "Quest/q_kill_skxyz.lua:85"),
    ("q_kill_skxyz", 12): ("signed_coordinate", "Player.CastSkillXYZ",
                           "Quest/q_kill_skxyz.lua:85"),
}

#: One row of each kind, with the number a designer typed.  `Q_CLASS` 3200
#: is the class-change quest that round `2euu94` nearly credited with
#: 4,294,952,296 instead of charging 15,000.
CHARGE_QUEST_ID = 3200
CHARGE_RAW = 4294952296
CHARGE_SIGNED = -15000


def _grant_home():
    """The home position ``create_character`` needs -- same shape
    ``tests/test_script_lua_api_player.py`` builds, for the same reason:
    only its type matters to a money grant."""
    from pirateforce_foundation.model import Position

    return Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)


class MirrorsParseTests(unittest.TestCase):
    """Layer 1: what the gate can check without a bridge checkout."""

    def setUp(self):
        qv.reset_caches()
        self.addCleanup(qv.reset_caches)

    def test_row_mirror_has_one_entry_per_shipped_quest(self):
        rows = qv.load_rows()
        self.assertEqual(len(rows), 1544)
        self.assertTrue(all(len(cells) == qv.VAR_COUNT
                            for cells in rows.values()))

    def test_every_cell_is_inside_the_unsigned_32_bit_range(self):
        for quest_id, cells in qv.load_rows().items():
            for index, cell in enumerate(cells, start=1):
                self.assertGreaterEqual(cell, 0, "quest %d var%d" % (quest_id, index))
                self.assertLess(cell, 1 << 32, "quest %d var%d" % (quest_id, index))

    def test_both_mirrors_are_registered_under_their_own_health_keys(self):
        """A broken mirror must be counted as ITSELF, not as `unnamed`."""
        self.assertIn(vendored.MIRROR_QUEST_VAR_ROWS, vendored.KNOWN_MIRRORS)
        self.assertIn(vendored.MIRROR_QUEST_VAR_SIGNEDNESS,
                      vendored.KNOWN_MIRRORS)

    def test_both_mirrors_are_pure_ascii_on_disk(self):
        """The bridge console is cp874; a stray byte kills the tool there."""
        for name in ("quest_var_rows.tsv", "quest_var_signedness.tsv"):
            (MIRROR_DIR / name).read_text(encoding="ascii")

    def test_a_hand_edited_body_is_refused_rather_than_half_read(self):
        """One digit changed, digest header untouched -> refused, not believed.

        This is the failure mode the header exists for: somebody opens the
        mirror, "fixes" a number, and every consumer quietly pays the new
        one.  The mutation is applied to a COPY and the module pointed at
        it, so the shipped file is never written to by a test.
        """
        text = (MIRROR_DIR / "quest_var_rows.tsv").read_text(encoding="ascii")
        tampered = text.replace("\n12\t34\t2\t", "\n12\t35\t2\t", 1)
        self.assertNotEqual(tampered, text, "the fixture row moved")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quest_var_rows.tsv"
            path.write_text(tampered, encoding="ascii", newline="\n")
            with mock.patch.object(qv, "_ROWS_PATH", path):
                qv.reset_caches()
                with self.assertRaises(QuestCriteriaError) as caught:
                    qv.load_rows()
        self.assertIn("body digest mismatch", str(caught.exception))


class SignednessTableTests(unittest.TestCase):
    """Layer 2: the table is the authority, and it says exactly this."""

    def setUp(self):
        qv.reset_caches()
        self.addCleanup(qv.reset_caches)

    def test_the_table_names_five_columns_and_no_others(self):
        table = qv.load_signedness()
        self.assertEqual(set(table), set(EXPECTED_SIGNED))

    def test_each_row_carries_the_kind_api_and_call_site_it_was_derived_from(self):
        for key, (kind, api, call_site) in EXPECTED_SIGNED.items():
            column = qv.load_signedness()[key]
            self.assertEqual(column.kind, kind, key)
            self.assertEqual(column.api_name, api, key)
            self.assertEqual(column.call_site, call_site, key)

    def test_every_kind_is_one_of_the_two_the_corpus_exhibits(self):
        for column in qv.load_signedness().values():
            self.assertIn(column.kind, qv.KNOWN_KINDS)

    def test_every_row_of_evidence_really_holds_that_raw_value(self):
        """Provenance that does not check out is decoration.

        Each signedness row names the quest ids and the raw cells that made
        it; this walks back into the row mirror and demands the cell is
        still there.  Re-point the derivation at the wrong column and this
        fails without any bridge checkout present.
        """
        rows = qv.load_rows()
        for column in qv.load_signedness().values():
            self.assertEqual(len(column.evidence_quest_ids),
                             len(column.evidence_raw))
            for quest_id, raw in zip(column.evidence_quest_ids,
                                     column.evidence_raw):
                self.assertIn(quest_id, rows)
                self.assertEqual(rows[quest_id][column.var_index - 1], raw,
                                 "%s quest %d var%d"
                                 % (column.script, quest_id, column.var_index))
                self.assertTrue(qv.is_wrapped(raw))

    def test_every_evidence_row_dispatches_the_script_the_row_names(self):
        """The (script, column) key has to agree with the OTHER mirror."""
        for column in qv.load_signedness().values():
            for quest_id in column.evidence_quest_ids:
                self.assertEqual(qc.script_for_quest(quest_id).lower(),
                                 column.script.lower())

    def test_the_gap_between_ordinary_and_wrapped_cells_is_still_enormous(self):
        """The threshold is safe because there is nothing near it.

        Largest ordinary cell 2,608,007; smallest wrapped 4,294,917,296.
        Three orders of magnitude of empty space is the entire reason "at
        or above 2**31 means a stored negative" cannot misfile a legitimate
        big number.  The day the game ships a cell in between, this fails
        and a person decides -- rather than the scan quietly guessing.
        """
        cells = [cell for row in qv.load_rows().values() for cell in row]
        ordinary = [cell for cell in cells if not qv.is_wrapped(cell)]
        wrapped = [cell for cell in cells if qv.is_wrapped(cell)]
        self.assertEqual(len(cells), 1544 * 20)
        self.assertEqual(len(wrapped), 13)
        self.assertEqual(max(ordinary), qv.LARGEST_ORDINARY_CELL)
        self.assertEqual(min(wrapped), qv.SMALLEST_WRAPPED_CELL)
        self.assertLess(max(ordinary) * 1000, min(wrapped))

    def test_the_two_mirrors_of_one_source_table_cover_the_same_quests(self):
        """Two files, one source: a row in one and not the other is drift.

        `quest_var_rows.tsv` and `quest_criteria_rows.tsv` are generated
        from the same 1544-row table by two different tools, and
        `quest_var` reads the script name out of the second while reading
        the cells out of the first.  Nothing else would notice if one of
        them were regenerated and the other left behind.
        """
        self.assertEqual(set(qv.load_rows()), set(qc.load_reward_rows()))


class TheJoinTests(unittest.TestCase):
    """Layer 3: what a running script gets back."""

    def setUp(self):
        qv.reset_caches()
        self.addCleanup(qv.reset_caches)

    def test_a_signed_money_column_comes_back_negative(self):
        value, reason = qv.quest_var(CHARGE_QUEST_ID, 4)
        self.assertIsNone(reason)
        self.assertEqual(value, CHARGE_SIGNED)

    def test_a_signed_coordinate_column_comes_back_negative(self):
        self.assertEqual(qv.quest_var(1071, 10), (-23754, None))
        self.assertEqual(qv.quest_var(1071, 12), (-800, None))
        self.assertEqual(qv.quest_var(997, 11), (-18008, None))

    def test_an_ordinary_cell_is_handed_over_untouched(self):
        """The 30,867 cells that are not wrapped go through unchanged."""
        rows = qv.load_rows()
        for quest_id in (12, 13, CHARGE_QUEST_ID):
            for index in range(1, qv.VAR_COUNT + 1):
                raw = rows[quest_id][index - 1]
                if qv.is_wrapped(raw):
                    continue
                self.assertEqual(qv.quest_var(quest_id, index), (raw, None))

    def test_a_wrapped_cell_in_an_unclassified_column_is_refused_by_name(self):
        """The rollback behaviour, and the reason the table is the authority.

        `Q_CLASS` var4 is signed BECAUSE the table says so.  Ask the same
        question about the same raw value under a column the table does not
        name and the answer is a refusal, not a decode -- so a future signed
        column has to be derived and written down, never inferred at read
        time.
        """
        signed = dict(qv.load_signedness())
        signed.pop(("q_class", 4))
        with mock.patch.object(qv, "_SIGNEDNESS_CACHE", signed):
            self.assertEqual(qv.quest_var(CHARGE_QUEST_ID, 4),
                             (None, qv.REFUSE_WRAPPED_UNSIGNED))

    def test_an_unknown_quest_id_is_a_different_refusal_from_a_bad_column(self):
        value, reason = qv.quest_var(999999, 1)
        self.assertIsNone(value)
        self.assertEqual(reason, qv.REFUSE_NO_QUEST_ROW)
        self.assertNotEqual(reason, qv.REFUSE_WRAPPED_UNSIGNED)

    def test_every_refusal_reason_is_in_the_closed_set(self):
        self.assertIn(qv.REFUSE_NO_QUEST_BOUND, qv.REFUSAL_REASONS)
        self.assertIn(qv.REFUSE_NO_QUEST_ROW, qv.REFUSAL_REASONS)
        self.assertIn(qv.REFUSE_NO_SCRIPT, qv.REFUSAL_REASONS)
        self.assertIn(qv.REFUSE_WRAPPED_UNSIGNED, qv.REFUSAL_REASONS)
        self.assertEqual(len(qv.REFUSAL_REASONS), 4)

    def test_an_unbound_run_is_a_different_answer_from_an_unknown_quest(self):
        """Quest id 0 is nobody's row AND nobody's mistake.

        The corpus sweep, a spike and half the tests in this repository run
        a script with no quest bound to it at all.  That is not a data
        fault -- there is no id to have got wrong -- so it gets its own
        reason, and `quest_var` never even opens the row mirror for it.
        """
        self.assertEqual(qv.quest_var(qv.UNBOUND_QUEST_ID, 1),
                         (None, qv.REFUSE_NO_QUEST_BOUND))
        self.assertNotIn(qv.UNBOUND_QUEST_ID, qv.load_rows())
        self.assertEqual(min(qv.load_rows()), 12)
        self.assertIn(qv.REFUSE_NO_QUEST_BOUND, qv.REPORT_ONCE_REASONS)
        self.assertNotIn(qv.REFUSE_NO_QUEST_ROW, qv.REPORT_ONCE_REASONS)

    def test_a_column_number_outside_1_to_20_is_a_programming_error(self):
        """Not a refusal: no script can produce it, so it is OUR bug."""
        for bad in (0, 21, -1):
            with self.assertRaises(ValueError):
                qv.quest_var(CHARGE_QUEST_ID, bad)

    def test_unwrap_is_two_s_complement_and_nothing_cleverer(self):
        self.assertEqual(qv.unwrap(CHARGE_RAW), CHARGE_SIGNED)
        self.assertEqual(qv.unwrap(0), 0)
        self.assertEqual(qv.unwrap((1 << 31) - 1), (1 << 31) - 1)
        self.assertEqual(qv.unwrap(1 << 31), -(1 << 31))
        self.assertEqual(qv.unwrap((1 << 32) - 1), -1)


class NamespaceTests(unittest.TestCase):
    """Layer 3, at the seam a Lua script actually touches."""

    def setUp(self):
        qv.reset_caches()
        self.addCleanup(qv.reset_caches)

    def _namespace(self, quest_id):
        lines = []
        namespace = quest.build_namespace(
            frozenset(), lines.append,
            context=quest.QuestContext(character_id=7, quest_id=quest_id))
        return namespace, lines

    def test_the_join_still_reads_the_charge_the_designer_typed(self):
        """`quest_var` -- the UNGATED join -- still answers -15000.

        Round `joa0u6` built this and round `l0rbyx` did not take it away:
        the cell is still decoded, the table still says the column is
        signed, and `quest_vars.quest_var` still returns the number.  What
        changed is who is allowed to SPEND it (see
        `TheHalfTransactionGateTests`): the namespace now asks
        `quest_rewards` first, and that is where the refusal lives.
        Asserting the join here keeps the two facts apart -- a gate that
        was silently deleting the value would pass a test written only
        against the namespace.
        """
        value, reason = qv.quest_var(CHARGE_QUEST_ID, 4)
        self.assertIsNone(reason)
        self.assertEqual(value, CHARGE_SIGNED)

    def test_the_value_survives_the_money_door_that_used_to_refuse_it(self):
        """The tie between this round and round `2euu94`'s i32 ceiling."""
        from pirateforce_foundation.lua_api import player as lua_player
        value, _reason = qv.quest_var(CHARGE_QUEST_ID, 4)
        self.assertEqual(
            lua_player._coerce_signed_int(value,
                                          lua_player._MAX_SIGNED_STAT_MAGNITUDE),
            CHARGE_SIGNED)
        self.assertIsNone(
            lua_player._coerce_signed_int(CHARGE_RAW,
                                          lua_player._MAX_SIGNED_STAT_MAGNITUDE),
            "the RAW cell must still be refused; only the decoded one passes")

    def test_a_var_of_an_unknown_quest_logs_its_refusal_and_stubs(self):
        namespace, lines = self._namespace(999999)
        self.assertEqual(namespace["Var1"], quest.STUB_DEFAULT)
        self.assertEqual(
            lines,
            ["LUA_QUEST_VAR_BAD_VALUE Quest.Var1 quest=999999 raw=? "
             "refused=no_row_for_quest_id (said once per script run)"])

    def test_names_that_are_not_columns_still_fall_through_silently(self):
        """`Var21`/`Var0`/`Var01`/`VarX` are not columns of any quest row."""
        namespace, lines = self._namespace(CHARGE_QUEST_ID)
        for name in ("Var21", "Var0", "Var01", "VarX", "Var", "Var4x"):
            self.assertEqual(namespace[name], quest.STUB_DEFAULT, name)
        self.assertEqual(lines, [], "a non-column must not log a refusal")

    def test_the_status_constants_still_win_over_the_var_lookup(self):
        namespace, _lines = self._namespace(CHARGE_QUEST_ID)
        self.assertEqual(namespace["Finish"], 2)
        self.assertNotEqual(namespace["None"], namespace["Active"])

    def test_an_unbound_run_says_so_once_and_then_stops_repeating_itself(self):
        """The default context: inert, honest, and not 12,653 log lines.

        Every script in the corpus sweep runs with no quest bound, and the
        corpus reads `VarN` thousands of times.  One line per read would
        make the host log unreadable, which is the practical way a "never
        silent" rule turns into a log nobody opens -- so the reason is said
        once per namespace and the reads after it are quiet.
        """
        lines = []
        namespace = quest.build_namespace(frozenset(), lines.append)
        for name in ("Var1", "Var2", "Var1", "Var20"):
            self.assertEqual(namespace[name], quest.STUB_DEFAULT)
        self.assertEqual(len(lines), 1)
        self.assertIn("refused=no_quest_bound_to_this_script", lines[0])
        self.assertIn("said once per script run", lines[0])

    def test_a_second_script_gets_its_own_line(self):
        """Once per namespace, not once per process."""
        lines = []
        for _ in range(2):
            quest.build_namespace(frozenset(), lines.append)["Var1"]
        self.assertEqual(len(lines), 2)

    def test_a_bound_run_says_each_column_once_however_often_it_is_read(self):
        """pf-adversary D9: 35,078 lines over one dispatch, all duplicates.

        The quest binding cannot change inside one namespace, so `VarN` has
        exactly one answer for the whole run.  Reading Var4 a hundred times
        is one fact, and the log says it once -- which caps a script at 20
        lines and loses nothing, unlike the alternative this module's own
        docstring already argued against for the refusal case.
        """
        namespace, lines = self._namespace(CHARGE_QUEST_ID)
        for _ in range(100):
            self.assertEqual(namespace["Var2"], 1)
            self.assertEqual(namespace["Var5"], 3201)
        self.assertEqual(len(lines), 2)
        self.assertEqual(sorted(lines), [
            "LUA_QUEST_VAR Quest.Var2 quest=3200 value=1",
            "LUA_QUEST_VAR Quest.Var5 quest=3200 value=3201",
        ])

    def test_a_gated_column_is_also_said_once_however_often_it_is_read(self):
        """The same cap on the refusal the half-transaction gate produces.

        Var4 of quest 3200 is the take side of a group whose give side is
        not implemented, so it never resolves -- and a hundred reads of it
        must still be ONE line, for the reason above.  Written as its own
        test rather than folded into the one above because it exercises a
        different code path (`quest_rewards`, not `quest_vars`) and a
        single test covering both would go green if either lost its cap.
        """
        namespace, lines = self._namespace(CHARGE_QUEST_ID)
        for _ in range(100):
            # `quest_rewards.REFUSED_CELL`, not the 0 every other stub
            # answers with: round `ad7t6n` measured that a refused charge
            # cell handed back as 0 satisfies a REAL `CheckItemNum`.
            self.assertEqual(namespace["Var4"], quest_rewards.REFUSED_CELL)
        self.assertEqual(len(lines), 1)
        self.assertIn("LUA_QUEST_GROUP_REFUSED n_VARI_4 quest=3200", lines[0])


@BRIDGE_GAMEDATA.skip_unless_present()
@BRIDGE_LUA_SCRIPTS.skip_unless_present()
class MirrorsMatchTheGameTests(unittest.TestCase):
    """Layer 4: only where the bridge checkout is.  The gate has none."""

    def test_regenerating_produces_byte_identical_mirrors(self):
        result = subprocess.run(
            [sys.executable, "tools/pf_regen_lua_quest_vars.py", "--check"],
            cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0,
                         "%s%s" % (result.stdout, result.stderr))

    def test_every_mirrored_cell_came_from_the_column_it_names(self):
        """The tie a `body_sha256` cannot make (pf-adversary F2, `5qtaqy`).

        A digest proves the mirror is the file the tool wrote.  It does not
        prove the tool read `n_VARI_4` rather than `n_VARI_5`, and the
        twenty columns are interchangeable in shape.  This reads the source
        BY COLUMN NAME, cell by cell, all 30,880 of them.
        """
        import csv
        source_path = (SIBLING / "pf_bridge" / "gamedata" / "tables"
                       / "QUESTDATA_TH__QUEST.tsv")
        with source_path.open(encoding="utf-8", newline="") as handle:
            source = {int(row["n_ID"]): row
                      for row in csv.DictReader(handle, delimiter="\t")}
        mirrored = qv.load_rows()
        self.assertEqual(set(mirrored), set(source))
        for quest_id, cells in mirrored.items():
            for index, cell in enumerate(cells, start=1):
                self.assertEqual(
                    cell, int(source[quest_id]["n_VARI_%d" % index]),
                    "quest %d n_VARI_%d" % (quest_id, index))

    def test_the_derivation_reruns_to_the_same_five_columns(self):
        """The signedness table, re-derived from scratch, not re-read."""
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import pf_regen_lua_quest_vars as regen
        finally:
            sys.path.pop(0)
        rows = regen.read_rows(SIBLING / "pf_bridge" / "gamedata" / "tables"
                               / "QUESTDATA_TH__QUEST.tsv")
        derived = regen.scan_signedness(
            rows, SIBLING / "pf_bridge" / "gamedata" / "lua")
        self.assertEqual(
            {(script.lower(), index): (kind, api, call_site)
             for script, index, kind, api, call_site, _ids, _raws in derived},
            EXPECTED_SIGNED)

    def _regen(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import pf_regen_lua_quest_vars as regen
        finally:
            sys.path.pop(0)
        return regen

    def _rows_with(self, regen, quest_id, var_index, value):
        source = (SIBLING / "pf_bridge" / "gamedata" / "tables"
                  / "QUESTDATA_TH__QUEST.tsv")
        out = []
        for identifier, script, cells in regen.read_rows(source):
            if identifier == quest_id:
                mutated = list(cells)
                mutated[var_index - 1] = value
                cells = tuple(mutated)
            out.append((identifier, script, cells))
        return out

    def test_an_id_beside_three_coordinates_stops_the_tool(self):
        """pf-adversary D3: position, not "the api name is on this line".

        `q_kill_skxyz.lua:85` passes `Quest.Var9` -- a SKILL ID -- to
        `Player.CastSkillXYZ` alongside the three coordinates.  A classifier
        that matched the api name anywhere in the line would file a wrapped
        id as `signed_coordinate` and hand the game a negative id, which is
        the exact `n_VARI_13 = mob id` case ASK-COO `0015` gave as the
        reason this table has to exist.
        """
        regen = self._regen()
        rows = self._rows_with(regen, 997, 9, (1 << 32) - 8106)
        with self.assertRaises(regen.UnclassifiedColumn) as caught:
            regen.scan_signedness(
                rows, SIBLING / "pf_bridge" / "gamedata" / "lua")
        self.assertIn("Player.CastSkillXYZ@arg0", str(caught.exception))

    def test_a_sign_the_script_already_flips_stops_the_tool(self):
        """pf-adversary D4: the sign can live in the EXPRESSION.

        `q_boat_health.lua:21` is `Player.AddCash(Quest.Var2 * -1)`.  Decode
        a wrapped cell there as signed too and the two flips cancel: the
        player is PAID 100 for repairing their own boat.  Only a bare
        `Quest.VarN` argument is classified -- an allow-list of one shape,
        not a blocklist of the two negations that exist today.
        """
        regen = self._regen()
        rows = self._rows_with(regen, 3189, 2, (1 << 32) - 100)
        with self.assertRaises(regen.UnclassifiedColumn) as caught:
            regen.scan_signedness(
                rows, SIBLING / "pf_bridge" / "gamedata" / "lua")
        self.assertIn("Q_BOAT_HEALTH n_VARI_2", str(caught.exception))

    def test_the_scan_finds_a_new_signed_column_when_the_data_shows_one(self):
        """The other direction: silence must be about DATA, not blindness.

        pf-adversary D8 measured that `Q_CLASS2` (quests 3195-3199) is
        `Q_CLASS`'s twin and reads the same column at
        `q_class2.lua`, but holds a plain 0 today, so the derivation cannot
        see it.  Give it the twin's cell and the tool finds it unaided --
        which is what says the five-row table is a fact about the shipped
        data and not about the scanner's reach.
        """
        regen = self._regen()
        rows = self._rows_with(regen, 3195, 4, 4294952296)
        derived = regen.scan_signedness(
            rows, SIBLING / "pf_bridge" / "gamedata" / "lua")
        found = [row for row in derived if row[0] == "Q_CLASS2"]
        self.assertEqual(len(found), 1, derived)
        self.assertEqual(found[0][1], 4)
        self.assertEqual(found[0][2], qv.KIND_MONEY)
        self.assertEqual(found[0][3], "Player.AddCash")

    def test_every_call_site_line_really_reads_that_var(self):
        """Open the corpus file at the pinned line and look.

        Read as BYTES: `q_kill_skxyz.lua` carries Big5 comment bytes three
        lines above its call site, and decoding the file as text raises
        `UnicodeDecodeError` on exactly the file this table needs most
        (pf-adversary D12, round `yfeauz` -- paid here).
        """
        corpus = SIBLING / "pf_bridge" / "gamedata" / "lua"
        for column in qv.load_signedness().values():
            relative, _, number = column.call_site.rpartition(":")
            data = (corpus / relative).read_bytes().split(b"\n")
            line = data[int(number) - 1]
            self.assertIn(b"Quest.Var%d" % column.var_index, line,
                          column.call_site)
            self.assertIn(column.api_name.encode("ascii"), line,
                          column.call_site)


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class TheShippedScriptChargesARealRowTests(unittest.TestCase):
    """The whole point of the round, run as the game ships it.

    ONE key, not two stacked guards: `LUA_CORPUS_RUNNABLE` already is
    "the corpus AND lupa", and stacking `BRIDGE_LUA_SCRIPTS` outside it
    would make unittest record the outer reason and hide the fact that
    these four need a Lua runtime -- the exact mistake
    `tests/pf_preconditions.py` documents beside that key.

    `Quest/q_class.lua:60` is `Player.AddCash(Quest.Var4)` inside
    `Report_Run`, and quest 3200 is the class change whose `n_VARI_4` cell
    holds 4294952296 -- a designer's -15000.  Yesterday that expression
    evaluated to 0 and changing class was free.  This runs the SHIPPED FILE
    through real Lua, with quest 3200 bound and a real `SQLiteStore` on
    disk, and reads the money back off the row.

    Deliberately NOT asserted from the namespace's return value or from a
    log line: the two evidence layers stay apart, and the row is the one
    that decides.
    """

    def setUp(self):
        import tempfile

        from pirateforce_foundation.store import SQLiteStore

        qv.reset_caches()
        self.addCleanup(qv.reset_caches)
        migrations = REPO_ROOT / "migrations"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = SQLiteStore(Path(directory.name) / "state.sqlite3",
                                 migrations)
        self.store.migrate()
        account_id = self.store.ensure_account("acct-classchange")
        self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "Classer01", "classer01", "fp-classer",
            lambda selector: (b"wire", b"avatar", 4242, 0),
            _grant_home(),
        )
        self.store.write_typed_attributes(self.character.id, {"cash": 20000})

    def _run_report(self, quest_id):
        from pirateforce_foundation import script_host
        from pirateforce_foundation.lua_api import player as lua_player

        path = (SIBLING / "pf_bridge" / "gamedata" / "lua" / "Quest"
                / "q_class.lua")
        lines = []
        host = script_host.load_script_file(
            path, log=lines.append,
            quest_context=quest.QuestContext(
                character_id=self.character.id, quest_id=quest_id),
            player_context=lua_player.PlayerContext(
                character_id=self.character.id),
            payout_store=self.store)
        host.call("Report_Run")
        return lines

    def _cash(self):
        return self.store.read_typed_attributes(self.character.id)["cash"]

    def test_the_class_change_takes_nothing_while_it_can_give_nothing(self):
        """20000 -> 20070, and NOT 5070.  The whole point of the round.

        Round `joa0u6` made `Report_Run` take 15,000 off this row for real.
        The SAME entry point, four lines later, is supposed to hand over
        items 2480010/2480011/2480012 through `Player.AddItem`, which is
        still a stub -- so the state that round reached was "charged and
        given nothing", which COO-DECISION `20260908_0242` item 4 names as
        worse than either end.  The gate closes the whole group: no charge,
        no items, and -- pf-adversary D1 of this round, MEASURED -- not
        the three criteria payouts either.  Refusing the charge while
        `AddCriteriaExp/SkillPoint/Cash` kept paying moved the player from
        -14,930 to +70 cash plus 19,350 exp and 6,450 skill points, every
        run: a gate that gives money away is not a gate.  A transaction is
        not a set of columns, so a give that reads no cell is a member of
        the group addressed by its API name.

        Both halves are asserted separately, on purpose: the console line
        proves WHICH column was refused and the row proves the money did
        not move.  A total on its own would let a wrong charge hide behind
        a right balance.
        """
        lines = self._run_report(CHARGE_QUEST_ID)
        self.assertNotIn(
            "LUA_PLAYER_CHARGE Player.AddCash character=%d column=cash "
            "charged=15000 balance_after=5000" % self.character.id, lines)
        self.assertTrue(
            [line for line in lines
             if line.startswith("LUA_QUEST_GROUP_REFUSED n_VARI_4 quest=3200 "
                                "group=Q_CLASS.Report_Run")],
            "the refusal has to name the column, the row and the group")
        self.assertEqual(self._cash(), 20000,
                         "not 5070 (the charge landed) and not 20070 (the "
                         "charge refused while the curve still paid): the "
                         "whole transaction stands still")

    def test_the_console_names_the_api_the_whole_group_is_waiting_on(self):
        """The other evidence layer, read on its own terms.

        The reader of this line is whoever has to decide to go and build
        the missing half, so it names it.  `Player.AddItem` was that name
        until round `6gc0zk` (`store.mint_backpack_item` landed, see
        `docs/SCRIPT_LANE.md`); the group -- five give-side members, not
        one -- stayed shut, and the console now names the next one
        alphabetically: `Player.AddPpClass`.
        """
        lines = self._run_report(CHARGE_QUEST_ID)
        refusals = [line for line in lines
                    if line.startswith("LUA_QUEST_GROUP_REFUSED")]
        self.assertEqual(
            len(refusals), 4, refusals)
        self.assertEqual(
            sorted(line.split()[1] for line in refusals),
            ["Quest.AddCriteriaCash", "Quest.AddCriteriaExp",
             "Quest.AddCriteriaSkillPoint", "n_VARI_4"],
            "one line per member the run actually reached: the charge and "
            "the three curve payouts")
        for line in refusals:
            self.assertIn("blocked_on=Player.AddPpClass,", line)
            self.assertNotIn("Player.AddItem", line.split("call_site=")[0])
            self.assertIn("call_site=Quest/q_class.lua:", line)
        self.assertFalse([line for line in lines
                          if line.startswith("LUA_QUEST_PAYOUT")],
                         "nothing may be paid out of the curve either")

    def test_the_reward_names_the_script_tests_are_refused_not_zeroed(self):
        """`if (Quest.RewardItem1 > 0)` must be false, and say why.

        The failure mode this test exists to catch is the quiet one: the
        cells land, the branch fires, and the item goes out anyway even
        though the GROUP is still short a member.  Under the gate the name
        refuses INSTEAD of answering 2480010, and the log says which group
        is holding it.  `Player.AddItem` itself went real in round
        `6gc0zk`; the group's other four give-side members did not, so the
        assertion below now covers both worlds the closure could have
        logged through (the old stub line, and the new real one) rather
        than a line that can no longer appear.
        """
        lines = self._run_report(CHARGE_QUEST_ID)
        refusals = [line for line in lines
                    if line.startswith("LUA_QUEST_REWARD_BAD_VALUE "
                                       "Quest.RewardItem1 ")]
        self.assertEqual(len(refusals), 1, refusals)
        self.assertIn("refused=transaction_group_give_side_not_implemented",
                      refusals[0])
        self.assertNotIn("LUA_API_STUB Player.AddItem", lines,
                         "the give branch must not even be entered")
        self.assertFalse(
            [line for line in lines if line.startswith(
                "LUA_PLAYER_MINT Player.AddItem")],
            "the give branch must not even be entered, and that still "
            "holds now that Player.AddItem is real: the group is not")

    def test_the_same_script_under_an_unbound_quest_still_charges_nothing(self):
        """The mutant that says this test is measuring the join, not luck.

        Same file, same store, same call -- only the quest binding removed.
        `Quest.Var4` falls back to 0, `AddCash(0)` moves no money, and the
        row is untouched.  If the charge above came from anywhere other
        than quest 3200's row, this would move too.
        """
        self._run_report(qv.UNBOUND_QUEST_ID)
        self.assertEqual(self._cash(), 20000)

    def test_a_quest_whose_var4_is_not_wrapped_charges_nothing_either(self):
        """`Q_CLASS2` rows 3195-3199 hold a plain 0 in the same column.

        A second binding of the SAME script, so the difference between the
        two runs is the quest row and nothing else.  Var4 resolves to 0,
        `AddCash` refuses `amount_is_zero`, and this quest's own criteria
        cash multiplier is 0.0 as well -- the row does not move at all.
        """
        self.assertEqual(qv.quest_var(3195, 4), (0, None))
        lines = self._run_report(3195)
        self.assertIn("LUA_QUEST_VAR Quest.Var4 quest=3195 value=0", lines)
        self.assertEqual(self._cash(), 20000)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
