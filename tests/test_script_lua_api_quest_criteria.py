"""LANE-Q: the READ half of the quest reward-criteria seam.

Four levels, in the order a reader should doubt them:

  * ``VendoredMirrorShapeTests`` -- the two mirrors parse, and the numbers
    in them are the SHAPE the module claims (a multiplier column that is
    actually made of multipliers, a level column every value of which
    resolves to a curve row).  These are the DISPROOF tests: if someone
    ever re-points ``criteria_level`` at ``f_EXP``, or decides ``f_EXP``
    holds the amount after all, they go red.  No bridge checkout needed --
    they run on the Windows gate, which has none.
  * ``CorruptMirrorTests`` -- every way a vendored file can be wrong ends
    as a ``QuestCriteriaError`` naming the path, never as a half-parsed
    table that pays wrong rewards, and ``script_host`` classifies that
    error as OURS (``LUA_HOST``), not as a script's (pf-adversary D11).
  * ``ResolveTests`` -- the arithmetic, the refusals, and the one thing
    this module must never do: guess a level.
  * ``NamespaceWiringTests`` / ``VendoredMirrorMatchesTheRealTableTests``
    -- what a script actually sees, and (under BRIDGE_GAMEDATA) that the
    copy still equals the game's own tables.
"""
import subprocess
import sys
import unittest
from pathlib import Path

from pf_preconditions import BRIDGE_GAMEDATA, BRIDGE_LUA_SCRIPTS, SIBLING

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import quest, quest_criteria as qc

REPO_ROOT = Path(__file__).resolve().parents[1]


class VendoredMirrorShapeTests(unittest.TestCase):
    """The mirrors are complete, and they mean what the module says."""

    def test_both_mirrors_load_with_the_row_counts_their_headers_declare(self):
        for path, table in ((qc._CURVE_PATH, qc.load_curve()),
                            (qc._ROWS_PATH, qc.load_reward_rows())):
            with self.subTest(mirror=path.name):
                declared = [line for line in
                            path.read_text(encoding="ascii").splitlines()
                            if line.startswith("# source_rows: ")]
                self.assertEqual(len(declared), 1)
                self.assertEqual(int(declared[0][len("# source_rows: "):]),
                                 len(table))

    def test_the_curve_covers_every_level_from_1_with_no_gaps(self):
        curve = qc.load_curve()
        self.assertEqual(min(curve), qc.MIN_LEVEL)
        self.assertEqual(sorted(curve), list(range(min(curve), max(curve) + 1)))
        self.assertLessEqual(max(curve), qc.MAX_LEVEL)

    def test_the_curve_rises_with_level_for_all_three_kinds(self):
        # Not decoration: a reward table that did NOT rise with level would
        # mean this is some other table and the whole reading is wrong.
        curve = qc.load_curve()
        levels = sorted(curve)
        for field in ("cash", "exp", "skill_point"):
            values = [getattr(curve[level], field) for level in levels]
            with self.subTest(kind=field):
                self.assertEqual(values, sorted(values))
                self.assertGreater(values[-1], values[0])

    def test_f_exp_is_a_multiplier_not_an_amount(self):
        """The disproof of round 02mkqc's reading of this column.

        If ``exp_multiplier`` really held the exp a quest pays, the column
        would carry thousands of distinct large integers.  It carries a
        handful of small ratios.  Pinning both facts means a future change
        that re-points this field at an amount column cannot pass quietly.
        """
        rows = qc.load_reward_rows().values()
        values = {row.exp_multiplier for row in rows}
        self.assertLess(len(values), 20)
        self.assertLessEqual(max(values), 10.0)
        self.assertGreaterEqual(min(values), 0.0)

    def test_every_quest_rows_criteria_level_resolves_to_a_curve_row(self):
        """Zero orphans is what makes ``criteria_level`` an INDEX.

        One orphan would mean the column is something else and every
        amount this module resolves is arithmetic on a coincidence.
        """
        curve = qc.load_curve()
        orphans = [row.quest_id for row in qc.load_reward_rows().values()
                   if row.criteria_level not in curve]
        self.assertEqual(orphans, [])

    def test_no_multiplier_and_no_criteria_level_is_negative(self):
        for row in qc.load_reward_rows().values():
            with self.subTest(quest=row.quest_id):
                self.assertGreaterEqual(row.criteria_level, 0)
                self.assertGreaterEqual(row.exp_multiplier, 0.0)
                self.assertGreaterEqual(row.cash_multiplier, 0.0)
                self.assertGreaterEqual(row.sp_multiplier, 0.0)

    def test_the_body_digest_header_matches_the_body(self):
        # The one honesty check that needs NEITHER the source tables nor a
        # sibling checkout, i.e. the one the gate machine can run.
        for path in (qc._CURVE_PATH, qc._ROWS_PATH):
            with self.subTest(mirror=path.name):
                text = path.read_text(encoding="ascii")
                declared = [line[len(qc.BODY_DIGEST_PREFIX):].strip()
                            for line in text.splitlines()
                            if line.startswith(qc.BODY_DIGEST_PREFIX)]
                self.assertEqual(len(declared), 1)
                self.assertEqual(declared[0], qc.body_digest(text))

    def test_both_mirrors_are_pure_ascii_on_disk(self):
        # The bridge console is cp874; AGENTS.md section 7.
        for path in (qc._CURVE_PATH, qc._ROWS_PATH):
            with self.subTest(mirror=path.name):
                self.assertTrue(path.read_bytes().isascii())


class CorruptMirrorTests(unittest.TestCase):
    """Every corruption is OUR error, named, and never a partial table."""

    def setUp(self):
        self._curve, self._rows = qc._CURVE_PATH, qc._ROWS_PATH
        qc.reset_caches()
        self.addCleanup(self._restore)

    def _restore(self):
        qc._CURVE_PATH, qc._ROWS_PATH = self._curve, self._rows
        qc.reset_caches()

    def _point_curve_at(self, text):
        import tempfile
        directory = tempfile.mkdtemp()
        self.addCleanup(
            lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        path = Path(directory) / "quest_criteria_curve.tsv"
        if text is not None:
            path.write_text(text, encoding="ascii", newline="\n")
        qc._CURVE_PATH = path
        qc.reset_caches()
        return path

    @staticmethod
    def _good_curve_text(body_lines):
        body = "\n".join(["\t".join(qc.CURVE_COLUMNS)] + body_lines) + "\n"
        return ("# VENDORED MIRROR -- do not hand-edit.\n"
                "%s%s\n" % (qc.BODY_DIGEST_PREFIX, qc.body_digest(body))) + body

    def test_a_missing_mirror_names_the_path(self):
        path = self._point_curve_at(None)
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn(str(path), str(caught.exception))

    def test_a_mirror_with_no_digest_header_is_refused(self):
        self._point_curve_at("level\tcash\texp\tskill_point\n1\t2\t90\t45\n")
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("body_sha256", str(caught.exception))

    def test_a_hand_edited_row_is_caught_by_the_digest(self):
        good = self._good_curve_text(["1\t2\t90\t45", "2\t4\t120\t60"])
        self._point_curve_at(good.replace("90", "9000"))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("digest mismatch", str(caught.exception))

    def test_a_wrong_header_is_refused_before_any_row_is_parsed(self):
        body = "level\tcash\texp\n1\t2\t90\n"
        self._point_curve_at("%s%s\n%s"
                             % (qc.BODY_DIGEST_PREFIX, qc.body_digest(body), body))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("header", str(caught.exception))

    def test_a_short_line_names_its_line_number(self):
        self._point_curve_at(self._good_curve_text(["1\t2\t90\t45", "2\t4\t120"]))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("line 3", str(caught.exception))

    def test_a_non_numeric_cell_is_refused_not_coerced(self):
        self._point_curve_at(self._good_curve_text(["1\t2\tlots\t45"]))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("not an integer", str(caught.exception))

    def test_a_duplicate_level_is_refused_not_silently_overwritten(self):
        self._point_curve_at(
            self._good_curve_text(["1\t2\t90\t45", "1\t9\t99\t99"]))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("duplicate level", str(caught.exception))

    def test_a_header_only_mirror_is_refused(self):
        self._point_curve_at(self._good_curve_text([]))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.load_curve()
        self.assertIn("no rows", str(caught.exception))

    def test_script_host_calls_this_error_ours_not_the_scripts(self):
        # pf-adversary D11: a broken file of OURS must not print as up to
        # 616 accusations against innocent quest scripts.
        self.assertIn(qc.QuestCriteriaError, script_host._host_side_error_types())


class ResolveTests(unittest.TestCase):
    """The arithmetic, and the refusals that are not arithmetic."""

    def test_the_amount_is_the_curve_times_the_multiplier(self):
        curve = qc.load_curve()
        amount = qc.resolve(qc.KIND_EXP, 15, 1.5)
        self.assertEqual(amount.base, curve[15].exp)
        self.assertEqual(amount.raw, curve[15].exp * 1.5)
        self.assertEqual(amount.amount, int(curve[15].exp * 1.5))

    def test_a_fractional_product_keeps_both_the_exact_and_the_floored_value(self):
        # Which one the client uses is UNVERIFIED (module docstring), so
        # the module hands both up instead of choosing for its callers.
        amount = qc.resolve(qc.KIND_EXP, 1, 0.25)
        self.assertEqual(amount.base, 90)
        self.assertEqual(amount.raw, 22.5)
        self.assertEqual(amount.amount, 22)

    def test_a_zero_multiplier_pays_zero_and_is_not_a_refusal(self):
        amount = qc.resolve(qc.KIND_CASH, 20, 0.0)
        self.assertEqual(amount.amount, 0)

    def test_a_level_with_no_curve_row_is_none_not_zero(self):
        self.assertIsNone(qc.resolve(qc.KIND_EXP, 0, 1.0))
        self.assertIsNone(qc.resolve(qc.KIND_EXP, 100000, 1.0))

    def test_an_unknown_kind_raises_rather_than_defaulting_to_exp(self):
        with self.assertRaises(qc.QuestCriteriaError):
            qc.resolve("Reputation", 10, 1.0)

    def test_the_plain_triple_reads_the_level_off_the_quest_row(self):
        row = next(iter(qc.load_reward_rows().values()))
        amount, reason = qc.resolve_for_api("AddCriteriaExp", row.quest_id)
        self.assertIsNone(reason)
        self.assertEqual(amount.level, row.criteria_level)

    def test_the_lv_triple_refuses_rather_than_guess_a_level(self):
        """The single most important refusal in this module.

        Falling back to the quest row's level here would pay a level-15
        reward to a level-90 player on every daily quest in the game, and
        nothing would look broken.
        """
        row = next(iter(qc.load_reward_rows().values()))
        amount, reason = qc.resolve_for_api("AddLvCriteriaExp", row.quest_id)
        self.assertIsNone(amount)
        self.assertEqual(reason, qc.REFUSE_NO_PLAYER_LEVEL)

    def test_the_lv_triple_uses_the_player_level_when_it_is_given(self):
        row = next(iter(qc.load_reward_rows().values()))
        amount, reason = qc.resolve_for_api(
            "AddLvCriteriaExp", row.quest_id, player_level=30)
        self.assertIsNone(reason)
        self.assertEqual(amount.level, 30)

    def test_an_unknown_quest_id_refuses_by_name(self):
        self.assertEqual(qc.resolve_for_api("AddCriteriaExp", -1)[1],
                         qc.REFUSE_NO_QUEST_ROW)

    def test_a_name_outside_the_six_refuses_by_name(self):
        self.assertEqual(qc.resolve_for_api("SetFlag", 26)[1],
                         qc.REFUSE_UNKNOWN_API)

    def test_a_player_level_off_the_curve_refuses_instead_of_paying(self):
        row = next(iter(qc.load_reward_rows().values()))
        self.assertEqual(
            qc.resolve_for_api("AddLvCriteriaExp", row.quest_id,
                               player_level=99999)[1],
            qc.REFUSE_LEVEL_OUT_OF_RANGE)

    def test_every_refusal_reason_comes_from_the_declared_closed_set(self):
        # pf-adversary D7 shape: a reason assembled from runtime data is an
        # unbounded key for anything downstream that counts reasons.
        declared = {qc.REFUSE_NO_QUEST_ROW, qc.REFUSE_NO_PLAYER_LEVEL,
                    qc.REFUSE_LEVEL_OUT_OF_RANGE, qc.REFUSE_UNKNOWN_API}
        seen = set()
        for api in list(qc.LEVEL_SOURCE) + ["SetFlag", ""]:
            for quest_id in (-1, 0, 26, 10 ** 9):
                for level in (None, 0, 30, 10 ** 9):
                    reason = qc.resolve_for_api(api, quest_id, level)[1]
                    if reason is not None:
                        seen.add(reason)
        self.assertTrue(seen)
        self.assertEqual(seen - declared, set())

    def test_the_six_names_are_exactly_the_zero_arity_reward_names(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        self.assertEqual(set(qc.LEVEL_SOURCE), set(qc.API_KIND))
        self.assertEqual(len(qc.LEVEL_SOURCE), 6)
        quest_methods = api_spec.NAMESPACE_METHODS["Quest"]
        self.assertEqual(set(qc.LEVEL_SOURCE) - set(quest_methods), set())

    def test_lv_and_plain_split_three_and_three_one_kind_each(self):
        by_source = {qc.LEVEL_SOURCE_QUEST: set(), qc.LEVEL_SOURCE_PLAYER: set()}
        for name, source in qc.LEVEL_SOURCE.items():
            by_source[source].add(qc.API_KIND[name])
        self.assertEqual(by_source[qc.LEVEL_SOURCE_QUEST], set(qc.KINDS))
        self.assertEqual(by_source[qc.LEVEL_SOURCE_PLAYER], set(qc.KINDS))


class NamespaceWiringTests(unittest.TestCase):
    """What a script running against ``Quest`` actually sees."""

    def _namespace(self, quest_id):
        from pirateforce_foundation.lua_api import spec as api_spec
        calls = []
        ns = quest.build_namespace(
            api_spec.NAMESPACE_METHODS["Quest"], calls.append,
            context=quest.QuestContext(character_id=1, quest_id=quest_id))
        return ns, calls

    def test_a_plain_criteria_call_logs_the_number_it_would_have_paid(self):
        row = next(iter(qc.load_reward_rows().values()))
        ns, calls = self._namespace(row.quest_id)
        self.assertEqual(ns["AddCriteriaExp"](), quest.STUB_DEFAULT)
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith(
            "LUA_QUEST_CRITERIA Quest.AddCriteriaExp quest=%d " % row.quest_id))
        self.assertIn("amount=", calls[0])
        # The stub line itself is UNCHANGED: still stubbed, still says so.
        self.assertEqual(calls[1], "LUA_API_STUB Quest.AddCriteriaExp")

    def test_an_lv_criteria_call_logs_a_refusal_and_no_number(self):
        row = next(iter(qc.load_reward_rows().values()))
        ns, calls = self._namespace(row.quest_id)
        ns["AddLvCriteriaExp"]()
        self.assertIn("refused=%s" % qc.REFUSE_NO_PLAYER_LEVEL, calls[0])
        self.assertNotIn("amount=", calls[0])

    def test_an_unknown_quest_id_refuses_rather_than_inventing_a_reward(self):
        ns, calls = self._namespace(0)
        ns["AddCriteriaCash"]()
        self.assertIn("refused=%s" % qc.REFUSE_NO_QUEST_ROW, calls[0])

    def test_every_criteria_line_is_ascii_and_one_line(self):
        row = next(iter(qc.load_reward_rows().values()))
        for name in qc.LEVEL_SOURCE:
            with self.subTest(method=name):
                ns, calls = self._namespace(row.quest_id)
                ns[name]()
                self.assertEqual(len(calls), 2)
                for line in calls:
                    self.assertTrue(line.isascii())
                    self.assertNotIn("\n", line)

    def test_a_non_criteria_stub_still_logs_exactly_one_line(self):
        ns, calls = self._namespace(26)
        ns["GetWeekDay"]()
        self.assertEqual(calls, ["LUA_API_STUB Quest.GetWeekDay"])


@BRIDGE_GAMEDATA.skip_unless_present()
class VendoredMirrorMatchesTheRealTableTests(unittest.TestCase):
    """Only runs where the bridge tables are; the gate has none."""

    def test_regenerating_produces_byte_identical_mirrors(self):
        result = subprocess.run(
            [sys.executable, "tools/pf_regen_lua_quest_criteria.py", "--check"],
            cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0,
                         "%s%s" % (result.stdout, result.stderr))

    @BRIDGE_LUA_SCRIPTS.skip_unless_present()
    def test_the_two_triples_of_call_sites_are_disjoint_in_the_corpus(self):
        """The measurement ``LEVEL_SOURCE`` rests on.

        166 files call the plain triple, 59 call the ``Lv`` triple, and no
        file calls both.  If that ever stops being true, the prefix is not
        the discriminator and the mapping needs re-deriving, not patching.
        """
        corpus = SIBLING / "pf_bridge" / "gamedata" / "lua"
        texts = {path: path.read_text(encoding="utf-8", errors="replace")
                 for path in corpus.rglob("*.lua")}
        plain = {p for p, t in texts.items() if "Quest.AddCriteriaExp" in t}
        lv = {p for p, t in texts.items() if "Quest.AddLvCriteriaExp" in t}
        self.assertEqual(len(plain), 166)
        self.assertEqual(len(lv), 59)
        self.assertEqual(plain & lv, set())


if __name__ == "__main__":
    unittest.main()
