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
  * ``Float32RoundingTests`` -- the floor is taken of the RIGHT number.
    ``f_EXP`` is a float32 column, so ``1.4`` reaches the mirror as
    ``1.399999976158142`` and ``int(base * that)`` pays one short on the
    sixteen 1.4 cells.  These tests pin the recovered decimal, name the 14
    shipped resolutions that changed, and go red if anyone floors a binary
    float again (COO-DECISION ``20260907_0845``: floor, but the raw
    product stays and the rounding lives at one place).
  * ``NamespaceWiringTests`` / ``VendoredMirrorMatchesTheRealTableTests``
    -- what a script actually sees, and (under BRIDGE_GAMEDATA) that the
    copy still equals the game's own tables.
"""
import shutil
import struct
import subprocess
import tempfile
import sys
import unittest
from unittest import mock
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR
from pathlib import Path

from pf_preconditions import (BRIDGE_GAMEDATA, BRIDGE_LUA_SCRIPTS,
                             LUA_CORPUS_RUNNABLE, SIBLING)

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import (dispatch, quest,
                                            quest_criteria as qc,
                                            reward,
                                            spec as api_spec)

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
        types = script_host._host_side_error_types()
        self.assertTrue(issubclass(qc.QuestCriteriaError, types))
        # And by construction, not by anyone remembering a list: the next
        # vendored mirror inherits the classification (pf-adversary, this
        # round -- the previous hand-maintained tuple had no completeness
        # test, which is the same door D11 was raised to close).
        from pirateforce_foundation.lua_api.vendored import VendoredDataError
        self.assertEqual(types, (VendoredDataError,))
        self.assertTrue(issubclass(qc.QuestCriteriaError, VendoredDataError))


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
        # the module hands every view up instead of choosing for callers.
        amount = qc.resolve(qc.KIND_EXP, 1, 0.25)
        self.assertEqual(amount.base, 90)
        self.assertEqual(amount.raw, 22.5)
        self.assertEqual(amount.exact, Decimal("22.5"))
        self.assertIsInstance(amount.exact, Decimal)
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

    def test_a_quest_row_level_off_the_curve_refuses_instead_of_paying(self):
        """`REFUSE_LEVEL_OUT_OF_RANGE` is the QUEST-ROW side of the check.

        A player level outside 1..255 is refused earlier and by name
        (`bad_player_level`, added this round), so the only way to reach
        this reason is a quest row whose own `criteria_level` has no curve
        entry -- which no shipped row does today
        (`test_every_quest_rows_criteria_level_resolves_to_a_curve_row`),
        so it is exercised here against a synthetic row rather than left
        as a branch nothing runs.
        """
        rows = dict(qc.load_reward_rows())
        broken = qc.QuestRewardRow(quest_id=999999, criteria_level=100000,
                                   cash_multiplier=1.0, exp_multiplier=1.0,
                                   sp_multiplier=1.0, script="Q_NOWHERE")
        rows[broken.quest_id] = broken
        original = qc._ROWS_CACHE
        qc._ROWS_CACHE = rows
        try:
            self.assertEqual(
                qc.resolve_for_api("AddCriteriaExp", broken.quest_id)[1],
                qc.REFUSE_LEVEL_OUT_OF_RANGE)
        finally:
            qc._ROWS_CACHE = original

    def test_a_boolean_player_level_is_refused_not_read_as_level_1(self):
        """`True` is an `int` in Python, and `curve[True]` is level 1.

        Without this guard an `AddLvCriteria*` grant handed a truthy
        sentinel pays a level-90 player the level-1 reward and nothing
        looks broken (pf-adversary, round xlk7hl).
        """
        row = next(iter(qc.load_reward_rows().values()))
        amount, reason = qc.resolve_for_api(
            "AddLvCriteriaExp", row.quest_id, player_level=True)
        self.assertIsNone(amount)
        self.assertEqual(reason, qc.REFUSE_BAD_PLAYER_LEVEL)

    def test_a_lua_style_whole_number_float_level_is_accepted(self):
        # lupa hands every Lua number across as a float; this house already
        # settled the same question for Quest.CheckOpenTime (900.0 is 900).
        row = next(iter(qc.load_reward_rows().values()))
        amount, reason = qc.resolve_for_api(
            "AddLvCriteriaExp", row.quest_id, player_level=30.0)
        self.assertIsNone(reason)
        self.assertEqual(amount.level, 30)

    def test_a_fractional_or_out_of_range_or_non_numeric_level_is_refused(self):
        row = next(iter(qc.load_reward_rows().values()))
        for bad in (30.5, -1, 0, 10 ** 9, "30", object()):
            with self.subTest(level=repr(bad)):
                amount, reason = qc.resolve_for_api(
                    "AddLvCriteriaExp", row.quest_id, player_level=bad)
                self.assertIsNone(amount)
                self.assertEqual(reason, qc.REFUSE_BAD_PLAYER_LEVEL)

    def test_every_refusal_reason_comes_from_the_declared_closed_set(self):
        # pf-adversary D7 shape: a reason assembled from runtime data is an
        # unbounded key for anything downstream that counts reasons.
        declared = {qc.REFUSE_NO_QUEST_ROW, qc.REFUSE_NO_PLAYER_LEVEL,
                    qc.REFUSE_LEVEL_OUT_OF_RANGE, qc.REFUSE_UNKNOWN_API,
                    qc.REFUSE_BAD_PLAYER_LEVEL}
        seen = set()
        for api in list(qc.LEVEL_SOURCE) + ["SetFlag", ""]:
            for quest_id in (-1, 0, 26, 10 ** 9):
                for level in (None, 0, 30, 30.0, 30.5, True, "30", 10 ** 9):
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
        # And ACTUALLY check the arity this test is named after: "no
        # arguments means the amount is in the tables" is the premise the
        # whole module rests on, and the previous version of this test
        # never read an arity column at all (pf-adversary, round xlk7hl).
        by_name = {fn.method: fn for fn in api_spec.API_FUNCTIONS
                   if fn.namespace == "Quest"}
        for name in qc.LEVEL_SOURCE:
            with self.subTest(method=name):
                self.assertEqual(by_name[name].arity_min, 0)
                self.assertEqual(by_name[name].arity_max, 0)

    def test_lv_and_plain_split_three_and_three_one_kind_each(self):
        by_source = {qc.LEVEL_SOURCE_QUEST: set(), qc.LEVEL_SOURCE_PLAYER: set()}
        for name, source in qc.LEVEL_SOURCE.items():
            by_source[source].add(qc.API_KIND[name])
        self.assertEqual(by_source[qc.LEVEL_SOURCE_QUEST], set(qc.KINDS))
        self.assertEqual(by_source[qc.LEVEL_SOURCE_PLAYER], set(qc.KINDS))


class Float32RoundingTests(unittest.TestCase):
    """Floor is fine; flooring the wrong float is not.

    Every number here is measured off the shipped mirrors by the test
    itself -- nothing is a literal copied out of a round file.
    """

    #: The one thing in this class that IS a literal: what a human reading
    #: ``QUESTDATA_TH__QUEST.tsv`` would say the multiplier column holds.
    #: If the mirror ever carries a value not in this list, the recovery
    #: is being asked to read a column nobody has looked at.
    AUTHORED = ("0", "0.1", "0.25", "0.3", "0.5", "0.85",
                "1", "1.4", "1.5", "2", "3", "5")

    @classmethod
    def _multipliers(cls):
        rows = qc.load_reward_rows().values()
        return sorted({m for row in rows for m in (row.cash_multiplier,
                                                   row.exp_multiplier,
                                                   row.sp_multiplier)})

    def test_every_shipped_multiplier_is_exactly_a_float32(self):
        """The evidence the recovery reads a float32 and invents nothing.

        A False here means the source column is NOT float32, and
        ``multiplier_decimal`` would be shortening a float64 on a guess.
        """
        for value in self._multipliers():
            with self.subTest(value=value):
                self.assertTrue(qc.is_exact_float32(value))
                self.assertEqual(
                    struct.unpack("<f", struct.pack("<f", value))[0], value)

    def test_the_recovered_decimals_are_exactly_the_authored_ones(self):
        recovered = [str(qc.multiplier_decimal(v)) for v in self._multipliers()]
        self.assertEqual(recovered, list(self.AUTHORED))

    def test_a_recovered_decimal_round_trips_back_to_the_stored_bits(self):
        """Recovery is lossless in the direction that matters."""
        for value in self._multipliers():
            with self.subTest(value=value):
                back = float(qc.multiplier_decimal(value))
                self.assertEqual(struct.pack("<f", back),
                                 struct.pack("<f", value))

    def test_a_non_finite_multiplier_cell_is_refused_at_the_cell(self):
        """An inf would otherwise die as OverflowError in int(Infinity),
        which script_host prints against innocent scripts (adversary D4)."""
        for cell in ("inf", "-inf", "nan", "1e400"):
            with self.subTest(cell=cell):
                with self.assertRaises(qc.QuestCriteriaError) as caught:
                    qc._parse_float(Path("mirror.tsv"), "exp_multiplier", cell)
                self.assertIn("not finite", str(caught.exception))

    def test_a_multiplier_that_is_not_a_number_at_all_names_this_module(self):
        """struct.error is neither OverflowError nor ValueError, and a raw
        struct.error out of here would not be classified as ours."""
        with self.assertRaises(qc.QuestCriteriaError):
            qc.is_exact_float32("1.4")

    def test_the_multiplier_memo_cannot_grow_without_bound(self):
        """resolve() is public and takes an arbitrary float (adversary D8)."""
        qc.load_reward_rows()
        for step in range(qc._MULTIPLIER_CACHE_MAX + 50):
            qc.multiplier_decimal(1.0 + step * 1e-6)
        self.assertLessEqual(len(qc._MULTIPLIER_DECIMALS),
                             qc._MULTIPLIER_CACHE_MAX)
        # ...and it still answers correctly once full.
        self.assertEqual(qc.multiplier_decimal(1.399999976158142),
                         Decimal("1.4"))
        qc.reset_caches()
        self.assertEqual(len(qc._MULTIPLIER_DECIMALS), 0)

    def test_a_float64_that_is_not_a_float32_is_returned_digit_for_digit(self):
        """Nothing to recover -> do not shorten it on a guess."""
        value = 0.1  # float64 0.1 is NOT the float32 in the mirror
        self.assertFalse(qc.is_exact_float32(value))
        self.assertEqual(qc.multiplier_decimal(value), Decimal(repr(value)))

    def test_the_fourteen_cells_wn088m_moved_up_are_moved_back_down(self):
        """The blast radius of THIS round's change, measured not asserted.

        Round ``wn088m`` could not read the width of the client's multiply
        and bet on single precision, implemented as a decimal recovery of
        the authored multiplier; that bet paid 14 shipped resolutions one
        MORE than the client does.  RE-295 read the multiply (``mulsd``,
        double) so the bet is settled and those 14 come back down.  This
        test recomputes both readings over the whole corpus and requires
        the disagreement to be exactly those cells -- a fifteenth means
        the two readings differ somewhere nobody looked.
        """
        curve = qc.load_curve()
        moved = []
        for row in qc.load_reward_rows().values():
            base_row = curve.get(row.criteria_level)
            if base_row is None:
                continue
            for api, base, mult in (
                    ("AddCriteriaCash", base_row.cash, row.cash_multiplier),
                    ("AddCriteriaExp", base_row.exp, row.exp_multiplier),
                    ("AddCriteriaSkillPoint", base_row.skill_point,
                     row.sp_multiplier)):
                amount, reason = qc.resolve_for_api(api, row.quest_id)
                self.assertIsNone(reason)
                authored = int((Decimal(base) * qc.multiplier_decimal(mult))
                               .to_integral_value(rounding=ROUND_FLOOR))
                if authored != amount.amount:
                    moved.append((row.quest_id, api, authored, amount.amount))
                    # The client pays one LESS than the table's decimal.
                    self.assertEqual(amount.amount, authored - 1)
                    self.assertEqual(qc.multiplier_decimal(mult),
                                     Decimal("1.4"))
        # The same 14 cells and the same eight quests round wn088m named,
        # walked in the other direction.
        self.assertEqual(len(moved), 14)
        self.assertEqual({q for q, _, _, _ in moved},
                         {2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177})
        self.assertEqual({api for _, api, _, _ in moved},
                         {"AddCriteriaExp", "AddCriteriaSkillPoint"})

    def test_the_multiply_is_double_and_a_single_multiply_would_show(self):
        """The one instruction the whole round turns on (RE-295).

        ``15800 * float32(1.4)`` is the case that separates the readings:
        at double it is ``22119.999623298645`` and truncates to 22119; a
        product kept in single rounds UP to exactly ``22120.0`` and
        truncates to 22120.  A single-precision multiply therefore fails
        here, which is what makes this pin worth having.
        """
        widened = qc.widen_float32(1.4)
        product = qc.client_product(15800, widened)
        self.assertEqual(product, 22119.999623298645)
        self.assertEqual(qc.round_amount(Decimal(product)), 22119)
        single = qc.widen_float32(qc.widen_float32(15800.0) * widened)
        self.assertEqual(single, 22120.0)
        self.assertNotEqual(int(single), qc.round_amount(Decimal(product)))

    def test_the_base_goes_through_float32_before_the_multiply(self):
        """``cvtsi2ss`` at 0x00608DC7, which no shipped row exercises.

        Every base in the curve is under 2**24 so float32 holds it exactly
        (pinned below); this uses a hand-made base because the module
        reproduces the instruction, not the corpus.
        """
        self.assertEqual(qc.client_product(16777217, 1.0), 16777216.0)
        self.assertNotEqual(qc.client_product(16777217, 1.0),
                            float(16777217) * 1.0)
        curve = qc.load_curve()
        biggest = max(max(row.cash, row.exp, row.skill_point)
                      for row in curve.values())
        self.assertEqual(biggest, 14252800)
        self.assertLess(biggest, 2 ** 24)
        # ...so on shipped data the step is the identity, and saying so is
        # not the same as saying the step is not there.
        for row in curve.values():
            for base in (row.cash, row.exp, row.skill_point):
                self.assertEqual(qc.widen_float32(float(base)), float(base))

    def test_an_operand_no_float32_can_hold_is_named_not_an_overflowerror(self):
        """script_host blames the running script for a foreign exception
        type (pf-adversary D11), so this module names itself -- and names
        WHICH operand, since the base goes through float32 too now."""
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.client_product(10 ** 400, 1.0)
        self.assertIn("base", str(caught.exception))
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc.client_product(1, 1e300)
        self.assertIn("multiplier", str(caught.exception))

    def test_the_client_underpays_its_own_table_and_we_pay_what_it_pays(self):
        """The concrete number this round moved, spelled out.

        Quest 2170 at level 40: the designer typed 1.4 against a base of
        15800 and meant 22120 experience.  The client stores 1.4 in a
        float32 column, multiplies at double and truncates, so it pays
        22119.  This server pays 22119 -- and keeps the 22120 on the
        result, because a reward that differs from its own table is worth
        seeing, not worth hiding.
        """
        amount, reason = qc.resolve_for_api("AddCriteriaExp", 2170)
        self.assertIsNone(reason)
        self.assertEqual(amount.base, 15800)
        self.assertEqual(amount.amount, 22119)
        self.assertEqual(amount.raw, 22119.999623298645)
        self.assertEqual(amount.exact, Decimal("22120.0"))  # what 1.4 meant

    def test_rounding_lives_at_one_place_and_that_place_truncates(self):
        """RE-295's ``cvttsd2si``, checkable rather than remembered.

        The first draft of this test counted the string
        ``to_integral_value`` and nothing else.  pf-adversary (D3, round
        ``wn088m``) mutation-proved that useless: replacing
        ``round_amount(exact)`` in ``resolve`` with ``int(exact)`` left the
        whole module green, because the token still appeared once and the
        two functions agree on every non-negative input.  So the pin is now
        BEHAVIOURAL -- move the constant and every resolution must move
        with it -- and the token count is kept only as a cheap second
        signal beside it.
        """
        self.assertIs(qc.ROUNDING_MODE, ROUND_DOWN)
        self.assertEqual(qc.round_amount(Decimal("22.9")), 22)
        self.assertEqual(qc.round_amount(Decimal("22.0")), 22)
        # Truncate toward zero, not floor: identical on everything the
        # mirror can produce (all operands >= 0) and different below zero,
        # which only the public `resolve` can reach.  The module claims
        # exactly that, so exactly that is pinned.
        self.assertEqual(qc.round_amount(Decimal("-22.5")), -22)
        self.assertEqual(Decimal("-22.5").to_integral_value(
            rounding=ROUND_FLOOR), Decimal("-23"))
        self.assertEqual(qc.resolve(qc.KIND_EXP, 1, -0.25).amount, -22)
        self.assertEqual(qc.resolve(qc.KIND_EXP, 1, 0.25).amount, 22)
        original = qc.ROUNDING_MODE
        try:
            qc.ROUNDING_MODE = ROUND_CEILING
            self.assertEqual(qc.round_amount(Decimal("22.1")), 23)
            self.assertEqual(qc.resolve(qc.KIND_EXP, 1, 0.25).amount, 23)
        finally:
            qc.ROUNDING_MODE = original
        self.assertEqual(qc.resolve(qc.KIND_EXP, 1, 0.25).amount, 22)
        source = (REPO_ROOT / "src" / "pirateforce_foundation" / "lua_api"
                  / "quest_criteria.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("to_integral_value"), 1)

    def test_every_resolution_is_its_own_client_product_through_round(self):
        """No second rounding path can creep in beside the first."""
        curve = qc.load_curve()
        for row in list(qc.load_reward_rows().values())[:200]:
            base_row = curve.get(row.criteria_level)
            if base_row is None:
                continue
            amount, reason = qc.resolve_for_api("AddCriteriaExp", row.quest_id)
            self.assertIsNone(reason)
            with self.subTest(quest_id=row.quest_id):
                self.assertEqual(
                    amount.exact,
                    Decimal(base_row.exp)
                    * qc.multiplier_decimal(row.exp_multiplier))
                self.assertEqual(
                    amount.raw,
                    qc.client_product(base_row.exp, row.exp_multiplier))
                self.assertEqual(amount.amount,
                                 qc.round_amount(Decimal(amount.raw)))

    def test_the_log_line_shows_the_authored_multiplier_not_the_widened_one(self):
        amount, _ = qc.resolve_for_api("AddCriteriaExp", 2170)
        line = amount.log_fields()
        self.assertIn("mult=1.4", line)
        self.assertIn("amount=22119", line)
        # The product the cast truncated, and the number the table's own
        # decimal would have paid: the only operator-visible sign that the
        # client and its designer disagree (pf-adversary D9, round
        # wn088m, re-aimed by RE-295).
        self.assertIn("product=22119.999623298645", line)
        self.assertIn("authored=22120 ", line)
        self.assertNotIn("22120.0", line)  # _plain, not str(Decimal)
        line.encode("ascii")

        # A resolution the client pays exactly says neither.
        clean = qc.resolve(qc.KIND_EXP, 15, 1.5).log_fields()
        self.assertNotIn("product=", clean)
        self.assertNotIn("authored=", clean)
        self.assertIn("amount=1050", clean)
        clean.encode("ascii")

    def test_a_fractional_reward_cannot_hide_behind_a_clean_integer(self):
        fractional = qc.resolve(qc.KIND_EXP, 1, 0.25)
        line = fractional.log_fields()
        self.assertIn("product=22.5", line)
        self.assertIn("amount=22", line)
        # ...and `authored=` stays quiet here, because the table's own
        # decimal pays the SAME 22.  Printing it on every fractional
        # product made it 171 false positives against 14 real ones
        # (pf-adversary D3, round na0ftg).
        self.assertNotIn("authored=", line)
        line.encode("ascii")

    def test_authored_prints_only_where_the_paid_integer_actually_differs(self):
        """The 12:1 signal-to-noise pf-adversary D3 measured, closed.

        Counted over every shipped plain-triple resolution: `authored=`
        must appear exactly on the 14 cells where the client's integer and
        the table's integer differ, not on the 185 where the two Decimals
        differ at all.
        """
        curve = qc.load_curve()
        printed = differ = 0
        for row in qc.load_reward_rows().values():
            base_row = curve.get(row.criteria_level)
            if base_row is None:
                continue
            for kind, base, mult in (
                    (qc.KIND_CASH, base_row.cash, row.cash_multiplier),
                    (qc.KIND_EXP, base_row.exp, row.exp_multiplier),
                    (qc.KIND_SKILL_POINT, base_row.skill_point,
                     row.sp_multiplier)):
                amount = qc.resolve(kind, row.criteria_level, mult)
                if "authored=" in amount.log_fields():
                    printed += 1
                if amount.exact != amount.amount:
                    differ += 1
        self.assertEqual(printed, 14)
        self.assertEqual(differ, 185)

    def test_the_log_line_never_grows_an_exponent_on_a_round_number(self):
        """``_plain``: ``22120``, not ``2.212E+4`` and not ``22120.0``."""
        self.assertEqual(qc._plain(Decimal("22120.0")), "22120")
        self.assertEqual(qc._plain(Decimal("22.50")), "22.5")
        self.assertEqual(qc._plain(Decimal("0.00")), "0")
        self.assertEqual(qc._plain(Decimal("-22.50")), "-22.5")
        self.assertEqual(qc._plain(Decimal("1E+9")), "1000000000")

    def test_the_log_formatter_cannot_raise_after_the_grant_is_made(self):
        """pf-adversary D2, round na0ftg: `quantize` raised
        InvalidOperation past the decimal context's 28 digits, and
        `log_fields` runs AFTER `store.add_typed_attribute` returns -- so
        the reward was paid and the line blamed a quest script."""
        self.assertEqual(qc._plain(Decimal("1E+40")), "1" + "0" * 40)
        self.assertEqual(qc._plain(Decimal("-1E+40")), "-1" + "0" * 40)
        # Specials never come out of a product; a formatter that raises on
        # them is still a formatter that raises.
        self.assertEqual(qc._plain(Decimal("NaN")), "NaN")
        self.assertEqual(qc._plain(Decimal("Infinity")), "Infinity")
        line = qc.resolve(qc.KIND_EXP, 255, 1e21).log_fields()
        self.assertIn("amount=", line)
        line.encode("ascii")

    def test_a_base_the_client_could_not_load_is_refused_not_wrapped(self):
        """`cvtsi2ss` reads a SIGNED DWORD (pf-adversary D4, na0ftg).

        The client would wrap 2**31 to -2**31 and pay a negative reward.
        Nobody has observed that paying out, so this refuses rather than
        inventing it -- and the message names the int32 boundary, not the
        float32 one 12 orders of magnitude away.
        """
        self.assertEqual(qc.client_product(qc.INT32_MAX, 0.0), 0.0)
        for bad in (qc.INT32_MAX + 1, qc.INT32_MIN - 1, 10 ** 400):
            with self.subTest(base=bad):
                with self.assertRaises(qc.QuestCriteriaError) as caught:
                    qc.client_product(bad, 1.0)
                self.assertIn("int32", str(caught.exception))
                # ...and it does not dump 401 digits into a cp874 console.
                self.assertLess(len(str(caught.exception)), 100)
                str(caught.exception).encode("ascii")
        for bad in (1.5, None, "90", True):
            with self.subTest(base=bad):
                with self.assertRaises(qc.QuestCriteriaError) as caught:
                    qc.client_product(bad, 1.0)
                self.assertIn("must be an int", str(caught.exception))

    def test_a_multiplier_that_is_not_a_float_is_refused_by_name(self):
        """The guard used to be `isinstance(multiplier, float)`, so a
        Decimal walked past it and died as decimal.InvalidOperation deep
        inside multiplier_decimal (pf-adversary D6, round na0ftg)."""
        self.assertEqual(qc.resolve(qc.KIND_EXP, 40, Decimal("1.4")).amount,
                         qc.resolve(qc.KIND_EXP, 40, 1.4).amount)
        for bad in (Decimal("Infinity"), float("inf"), float("nan")):
            with self.subTest(multiplier=bad):
                with self.assertRaises(qc.QuestCriteriaError):
                    qc.resolve(qc.KIND_EXP, 40, bad)
        for bad in (None, "1.4", object()):
            with self.subTest(multiplier=bad):
                with self.assertRaises(qc.QuestCriteriaError) as caught:
                    qc.resolve(qc.KIND_EXP, 40, bad)
                self.assertIn("not a number", str(caught.exception))

    def test_a_negative_zero_multiplier_cannot_poison_the_memo(self):
        """pf-adversary D8, round na0ftg: the memo was keyed by the float,
        and `hash(-0.0) == hash(0.0)`, so one resolution with a negative
        zero made every later zero-multiplier line read `mult=-0`."""
        qc.reset_caches()
        self.assertIn("mult=-0 ", qc.resolve(qc.KIND_EXP, 40, -0.0).log_fields())
        self.assertIn("mult=0 ", qc.resolve(qc.KIND_EXP, 40, 0.0).log_fields())
        qc.reset_caches()
        self.assertIn("mult=0 ", qc.resolve(qc.KIND_EXP, 40, 0.0).log_fields())



class QuestDispatchTests(unittest.TestCase):
    """The missing argument, supplied: a script loaded AS a quest.

    Every criteria call site in the corpus has been logging
    ``refused=no_quest_row`` for one reason -- nothing said which quest was
    running.  ``s_LUASCRIPT`` is now mirrored, so quest id -> script is a
    function this server can evaluate.  These tests do NOT need lupa: they
    exercise the resolution and the context, which is where the refusal
    came from.  The one test that actually runs Lua is guarded and lives
    at the bottom.
    """

    def test_a_quest_id_names_exactly_one_script(self):
        self.assertEqual(qc.script_for_quest(2170), "Q_ARCH1")
        self.assertIsNone(qc.script_for_quest(0))
        for row in qc.load_reward_rows().values():
            with self.subTest(quest_id=row.quest_id):
                self.assertTrue(row.script)
                row.script.encode("ascii")

    def test_the_reverse_direction_is_not_a_function_and_says_so(self):
        """Why a running script can never be asked which quest it is."""
        self.assertEqual(len(qc.quests_for_script("Q_CON1")), 160)
        self.assertEqual(qc.quests_for_script("q_con1"),
                         qc.quests_for_script("Q_CON1"))
        self.assertEqual(qc.quests_for_script("no such script"), ())
        rows = qc.load_reward_rows()
        self.assertEqual(len({r.script for r in rows.values()}), 209)
        self.assertEqual(len(rows), 1544)

    def test_an_empty_script_cell_is_refused_not_defaulted(self):
        """An empty name would resolve to the corpus root itself."""
        with self.assertRaises(qc.QuestCriteriaError) as caught:
            qc._parse_script(Path("mirror.tsv"), "   ")
        self.assertIn("empty script name", str(caught.exception))

    def test_a_dispatched_context_stops_the_refusal_the_lane_measured(self):
        """The whole point, on a real quest id and a real amount."""
        context = quest.QuestContext(character_id=7, quest_id=2170)
        calls = []
        ns = quest.build_namespace(
            api_spec.NAMESPACE_METHODS["Quest"], calls.append, context=context)
        ns["AddCriteriaExp"]()
        self.assertIn("LUA_QUEST_CRITERIA Quest.AddCriteriaExp quest=2170",
                      calls[0])
        self.assertIn("amount=22119", calls[0])
        self.assertNotIn("refused", calls[0])
        # The default context still refuses, for the same honest reason.
        default_calls = []
        default_ns = quest.build_namespace(
            api_spec.NAMESPACE_METHODS["Quest"], default_calls.append)
        default_ns["AddCriteriaExp"]()
        self.assertIn("refused=%s" % qc.REFUSE_NO_QUEST_ROW, default_calls[0])

    def test_an_lv_name_still_refuses_even_with_a_quest_id(self):
        """A quest id is not a player level, and one may not stand in for
        the other (COO-DECISION 20260907_0845 item 2)."""
        amount, reason = qc.resolve_for_api("AddLvCriteriaExp", 2170)
        self.assertIsNone(amount)
        self.assertEqual(reason, qc.REFUSE_NO_PLAYER_LEVEL)

    @LUA_CORPUS_RUNNABLE.skip_unless_present()
    def test_a_real_shipped_script_loads_as_its_quest_and_names_the_number(self):
        root = SIBLING / "pf_bridge" / "gamedata" / "lua"
        calls = []
        host = dispatch.load_quest_script(root, 2170, character_id=7,
                                             log=calls.append)
        self.assertIn("LUA_QUEST_DISPATCH quest=2170 character=7 "
                      "script=q_arch1", calls[0])
        # The entry points are the ones q_arch1.lua actually defines --
        # Accept_Run / Report_Run, NOT "Accept"/"Report" (pf-adversary D1,
        # round wn088m: the first draft called two names that do not exist
        # and one that has no criteria call, so the assertion below could
        # never have fired, and lupa's absence here hid that).  The three
        # criteria calls of this script live in Report_Run.
        self.assertTrue(host.has_function("Report_Run"))
        for entry in ("Accept_Check", "Accept_Run", "Report_Check",
                      "Report_Run"):
            if host.has_function(entry):
                host.call(entry)
        criteria = [line for line in calls if "LUA_QUEST_CRITERIA" in line]
        self.assertEqual(len(criteria), 3)
        self.assertFalse([line for line in criteria
                          if "refused=%s" % qc.REFUSE_NO_QUEST_ROW in line])

    def test_an_unknown_quest_id_and_a_missing_corpus_each_say_which(self):
        with self.assertRaises(dispatch.QuestDispatchError) as no_row:
            dispatch.script_path_for_quest(REPO_ROOT, 999999)
        self.assertIn("no row in the vendored quest mirror",
                      str(no_row.exception))
        with self.assertRaises(dispatch.QuestDispatchError) as no_corpus:
            dispatch.script_path_for_quest(
                REPO_ROOT / "no_such_corpus_dir", 2170)
        self.assertIn("no lua corpus at", str(no_corpus.exception))


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
        """THREE lines since round `8ou0zg`, not two, and each says one thing.

        `LUA_QUEST_CRITERIA` is what the game's tables resolve;
        `LUA_QUEST_PAYOUT` is what happened to that number (here: refused,
        no reward store is bound to the default namespace); `LUA_API_STUB`
        is what the script got back, and is unchanged. The payout line was
        added deliberately -- a resolved reward that nothing pays is the
        fact this lane most needs visible in a log, not the fact it most
        needs hidden.
        """
        # A row whose Exp criteria is actually POSITIVE. The first row in
        # the mirror (quest 12) carries multiplier 0.0, so it resolves to a
        # reward of nothing and is refused as `amount_is_zero` before the
        # store is ever considered -- a true statement about that quest, but
        # not the one this test is about.
        quest_id = next(
            qid for qid in sorted(qc.load_reward_rows())
            if (qc.resolve_for_api("AddCriteriaExp", qid)[0] or
                type("", (), {"amount": 0})).amount > 0)
        ns, calls = self._namespace(quest_id)
        row = qc.load_reward_rows()[quest_id]
        self.assertEqual(ns["AddCriteriaExp"](), quest.STUB_DEFAULT)
        self.assertEqual(len(calls), 3)
        self.assertTrue(calls[0].startswith(
            "LUA_QUEST_CRITERIA Quest.AddCriteriaExp quest=%d " % row.quest_id))
        self.assertIn("amount=", calls[0])
        self.assertTrue(calls[1].startswith("LUA_QUEST_PAYOUT AddCriteriaExp"))
        self.assertIn("refused=%s" % reward.REFUSE_NO_STORE, calls[1])
        # The stub line itself is UNCHANGED: still stubbed, still says so.
        self.assertEqual(calls[2], "LUA_API_STUB Quest.AddCriteriaExp")

    def test_nothing_is_paid_without_a_reward_store(self):
        """The default namespace must not invent a payment out of nowhere."""
        row = next(iter(qc.load_reward_rows().values()))
        ns, calls = self._namespace(row.quest_id)
        ns["AddCriteriaExp"]()
        self.assertEqual(
            [line for line in calls
             if "LUA_QUEST_PAYOUT" in line and "refused=" not in line], [])

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
        """ASCII only: the bridge console is cp874 and dies on anything else.

        Line count differs by NAME, on purpose: an `AddLvCriteria*` call
        refuses at resolution and is logged ONCE (the payment layer never
        gets a number to report on), while a plain `AddCriteria*` call
        resolves and so gets a payout line too.
        """
        row = next(iter(qc.load_reward_rows().values()))
        for name in qc.LEVEL_SOURCE:
            with self.subTest(method=name):
                ns, calls = self._namespace(row.quest_id)
                ns[name]()
                expected = 2 if qc.LEVEL_SOURCE[name] == \
                    qc.LEVEL_SOURCE_PLAYER else 3
                self.assertEqual(len(calls), expected)
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

    def test_each_mirrored_column_came_from_the_source_column_it_names(self):
        """The one tie the rest of this module could not make.

        Every other check here -- `# source_sha256`, `# source_rows`,
        `# body_sha256`, even `--check` -- verifies "the mirror equals what
        the tool produced from that FILE".  None of them verifies the tool
        read the right COLUMN, and `n_LEVEL_QUEST` sits next to
        `n_LEVEL_EXP` with the same 1..120 domain, so re-pointing the
        regenerator at it changed 647 of 1039 rewards and left all 38 tests
        green (pf-adversary, round xlk7hl, mutation-proven).  This reads
        both source tables BY COLUMN NAME and compares cell by cell.
        """
        import csv
        tables = SIBLING / "pf_bridge" / "gamedata" / "tables"
        with (tables / "QUESTDATA_TH__QUEST.tsv").open(
                encoding="utf-8", newline="") as handle:
            source = {int(r["n_ID"]): r for r in csv.DictReader(
                handle, delimiter="\t")}
        rows = qc.load_reward_rows()
        self.assertEqual(set(rows), set(source))
        for quest_id, row in rows.items():
            raw = source[quest_id]
            with self.subTest(quest=quest_id):
                self.assertEqual(row.criteria_level, int(raw["n_LEVEL_EXP"]))
                self.assertEqual(row.exp_multiplier, float(raw["f_EXP"]))
                self.assertEqual(row.cash_multiplier, float(raw["f_CASH"]))
                self.assertEqual(row.sp_multiplier, float(raw["f_SP"]))

        with (tables / "CONSTDATA_TH__STANDARD_QUEST.tsv").open(
                encoding="utf-8", newline="") as handle:
            curve_source = {int(r["n_ID"]): r for r in csv.DictReader(
                handle, delimiter="\t")}
        curve = qc.load_curve()
        self.assertEqual(set(curve), set(curve_source))
        for level, entry in curve.items():
            raw = curve_source[level]
            with self.subTest(level=level):
                self.assertEqual(entry.exp, int(raw["n_QUEST_EXP"]))
                self.assertEqual(entry.cash, int(raw["n_QUEST_CASH"]))
                self.assertEqual(entry.skill_point, int(raw["n_QUEST_SP"]))

    @BRIDGE_LUA_SCRIPTS.skip_unless_present()
    def test_the_path_is_resolved_by_stem_not_by_gluing_a_table_cell_on(self):
        root = SIBLING / "pf_bridge" / "gamedata" / "lua"
        path = dispatch.script_path_for_quest(root, 2170)
        self.assertEqual(path.name, "q_arch1.lua")
        self.assertEqual(path.parent.name, "Quest")
        self.assertTrue(path.is_file())

    @BRIDGE_LUA_SCRIPTS.skip_unless_present()
    def test_every_script_a_quest_names_exists_on_disk_exactly_once(self):
        root = SIBLING / "pf_bridge" / "gamedata" / "lua"
        for name in sorted({r.script for r in qc.load_reward_rows().values()}):
            with self.subTest(script=name):
                matches = [p for p in root.rglob("*.lua")
                           if p.stem.lower() == name.lower()]
                self.assertEqual(len(matches), 1)

    @BRIDGE_LUA_SCRIPTS.skip_unless_present()
    def test_how_much_of_the_corpus_the_dispatcher_actually_unblocks(self):
        """The measurement this round is allowed to claim, computed here.

        1213 of the 1544 quest rows dispatch a script that calls at least
        one criteria name; 1039 of those now resolve a real amount.  The
        remaining 174 are the ``Lv`` triple, which refuses for want of a
        player level and is NOT counted as unblocked.
        """
        root = SIBLING / "pf_bridge" / "gamedata" / "lua"
        text = {p.stem.lower(): p.read_text(encoding="latin-1")
                for p in root.rglob("*.lua")}
        with_calls = resolving = 0
        for row in qc.load_reward_rows().values():
            body = text.get(row.script.lower(), "")
            used = [n for n in qc.LEVEL_SOURCE if ("Quest." + n) in body]
            if not used:
                continue
            with_calls += 1
            if any(qc.resolve_for_api(n, row.quest_id)[1] is None
                   for n in used):
                resolving += 1
        self.assertEqual(with_calls, 1213)
        self.assertEqual(resolving, 1039)

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



import pytest as _pytest_for_mirror_health_isolation
from pirateforce_foundation.lua_api import vendored as _vendored_for_isolation
from pirateforce_foundation import script_host as _script_host_for_isolation


@_pytest_for_mirror_health_isolation.fixture(autouse=True)
def _keep_the_published_mirror_health_clean():
    """Every test in this module gets its own counter, not the real one.

    pf-adversary D5, round `h20x7g`. Round `h20x7g` wrapped the lazy
    mirror loaders so a broken copy is COUNTED -- which means every test
    in this module that points `_CURVE_PATH`/`_ROWS_PATH`/`_CATALOG_PATH`
    at a temp fixture now writes a failure into the process-wide
    `MIRROR_HEALTH`, naming a path that no longer exists. Measured before
    this fixture: a finished run left `mirror_failures=12` and, depending
    on test order, `broken_now=true broken="criteria_curve"` -- the one
    object the counter exists to publish, asserting that a perfectly
    healthy shipped mirror is broken right now.

    BOTH NAMES are swapped: `script_host` imported `MIRROR_HEALTH` by
    value, so `script_host.MIRROR_HEALTH` and `vendored.MIRROR_HEALTH` are
    two names for one object, and the two halves that record read
    different names.
    """
    fresh = _vendored_for_isolation.MirrorHealth()
    vendored_original = _vendored_for_isolation.MIRROR_HEALTH
    host_original = _script_host_for_isolation.MIRROR_HEALTH
    _vendored_for_isolation.MIRROR_HEALTH = fresh
    _script_host_for_isolation.MIRROR_HEALTH = fresh
    try:
        yield
    finally:
        _vendored_for_isolation.MIRROR_HEALTH = vendored_original
        _script_host_for_isolation.MIRROR_HEALTH = host_original


#: A quest id whose `s_LUASCRIPT` cell names a script, picked from the
#: vendored mirror at import time rather than typed in, so a re-vendor that
#: renumbers the rows moves this test instead of making it lie.
_A_DISPATCHABLE_QUEST = next(
    quest_id for quest_id in sorted(qc.load_reward_rows())
    if qc.script_for_quest(quest_id)
)


class DispatchStemIndexTests(unittest.TestCase):
    """Dispatch resolves against the corpus AS IT IS NOW, not a snapshot.

    Round `8ou0zg` first answered pf-adversary D11 ("616 files re-walked on
    every dispatch") with a per-root index built once. The adversary then
    measured D11's actual cost -- 0.06 ms per dispatch -- and measured what
    the index cost: a corpus that changes under a live index (pf_bridge
    takes `sync: N file(s) from the Windows bridge` commits) gives two
    silent wrong answers. The index was removed in the same round it was
    added. These tests are what hold that decision: they pass only if the
    walk is live.
    """

    def setUp(self):
        from pirateforce_foundation.lua_api import dispatch

        dispatch.reset_caches()
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.script = qc.script_for_quest(_A_DISPATCHABLE_QUEST)
        self.assertIsNotNone(self.script)

    def _write(self, relative: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("-- test corpus\n", encoding="ascii")
        return path

    def test_a_file_that_lands_after_the_first_dispatch_is_seen(self):
        """pf-adversary finding 3: the index stopped seeing new files.

        With the index in place this returned `Quest/<script>.lua` happily
        on the second call -- the duplicate-stem guard, the whole point of
        which is to refuse an ambiguous corpus, had gone blind.
        """
        from pirateforce_foundation.lua_api import dispatch

        self._write("Quest/%s.lua" % self.script.lower())
        first = dispatch.script_path_for_quest(self.root,
                                               _A_DISPATCHABLE_QUEST)
        self.assertEqual(first.name, "%s.lua" % self.script.lower())
        self._write("%s.lua" % self.script.lower())
        with self.assertRaises(dispatch.QuestDispatchError) as caught:
            dispatch.script_path_for_quest(self.root, _A_DISPATCHABLE_QUEST)
        self.assertIn("2 files", str(caught.exception))

    def test_a_file_deleted_after_a_dispatch_refuses_by_name(self):
        """pf-adversary finding 3, second half.

        With the index in place the stale path survived and
        `load_script_file` raised a bare `FileNotFoundError` -- neither a
        `QuestDispatchError` nor a `VendoredDataError`, so `load_corpus`
        filed it as `LUA_SCRIPT <file> ERR` against an innocent script:
        D11's original mis-attribution, re-opened by D11's own fix.
        """
        from pirateforce_foundation.lua_api import dispatch

        path = self._write("Quest/%s.lua" % self.script.lower())
        dispatch.script_path_for_quest(self.root, _A_DISPATCHABLE_QUEST)
        path.unlink()
        with self.assertRaises(dispatch.QuestDispatchError):
            dispatch.script_path_for_quest(self.root, _A_DISPATCHABLE_QUEST)

    def test_the_module_holds_no_shared_state(self):
        """TWO_SESSIONS_SAME_SCENE, held as a test rather than a sentence."""
        from pirateforce_foundation.lua_api import dispatch

        shared = [name for name, value in vars(dispatch).items()
                  if isinstance(value, (dict, list, set))
                  and not name.startswith("__")]
        self.assertEqual(shared, [],
                         "lua_api.dispatch grew module-level mutable state; "
                         "two sessions in one scene share this process")

    def test_a_duplicate_stem_refuses_and_names_both_files(self):
        """The refusal, through a root spelled with `..`.

        This bug predates the round and survived on the pre-round base: the
        message built its paths with `relative_to(root)` against the
        CALLER's spelling while the paths came from the resolved root, so a
        root containing `..` raised a bare `ValueError` out of the error
        path instead of the refusal that names the duplicates.
        """
        from pirateforce_foundation.lua_api import dispatch

        self._write("Quest/%s.lua" % self.script.lower())
        self._write("%s.lua" % self.script.lower())
        spelled_with_dotdot = self.root / ".." / self.root.name
        with self.assertRaises(dispatch.QuestDispatchError) as caught:
            dispatch.script_path_for_quest(spelled_with_dotdot,
                                           _A_DISPATCHABLE_QUEST)
        message = str(caught.exception)
        self.assertIn("Quest/%s.lua" % self.script.lower(), message)
        self.assertIn("2 files", message)

    def test_a_missing_script_still_refuses_by_name(self):
        from pirateforce_foundation.lua_api import dispatch

        self._write("Quest/not_the_one.lua")
        with self.assertRaises(dispatch.QuestDispatchError) as caught:
            dispatch.script_path_for_quest(self.root, _A_DISPATCHABLE_QUEST)
        self.assertIn(self.script.lower(), str(caught.exception))


if __name__ == "__main__":
    unittest.main()
