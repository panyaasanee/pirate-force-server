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
import struct
import subprocess
import sys
import unittest
from decimal import Decimal, ROUND_FLOOR
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
                                   sp_multiplier=1.0)
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

    def test_a_float64_that_is_not_a_float32_is_returned_digit_for_digit(self):
        """Nothing to recover -> do not shorten it on a guess."""
        value = 0.1  # float64 0.1 is NOT the float32 in the mirror
        self.assertFalse(qc.is_exact_float32(value))
        self.assertEqual(qc.multiplier_decimal(value), Decimal(repr(value)))

    def test_only_one_point_four_cells_moved_and_exactly_fourteen_did(self):
        """The blast radius of this round's change, measured not asserted.

        Recomputes every plain-triple resolution both ways and requires
        that the naive float floor and the decimal floor differ ONLY on
        cells whose multiplier recovers to 1.4 -- 0.1/0.3/0.85 widen
        upward and never lost a unit, which is why this survived a round.
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
                naive = int(base * mult)
                if naive != amount.amount:
                    moved.append((row.quest_id, api, naive, amount.amount))
                    self.assertEqual(amount.amount, naive + 1)
                    self.assertEqual(qc.multiplier_decimal(mult),
                                     Decimal("1.4"))
        # 16 cells in the mirror carry 1.4; 14 of them had an integer
        # true product and so lost a unit to the binary floor.  The other
        # two were fractional either way, which is why the count is 14
        # and not 16 -- measured, not rounded off in prose.
        self.assertEqual(len(moved), 14)
        self.assertEqual({q for q, _, _, _ in moved},
                         {2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177})
        self.assertEqual({api for _, api, _, _ in moved},
                         {"AddCriteriaExp", "AddCriteriaSkillPoint"})

    def test_the_naive_float_floor_would_underpay_a_real_quest(self):
        """The concrete failure this round closed, spelled out.

        Quest 2170 at level 40 pays 15800 * 1.4 = 22120 experience.  The
        mirror's float32 1.4 makes that product 22119.9996..., so
        ``int(...)`` -- what this module did until round ``wn088m`` -- paid
        22119.  One unit, silently, on every 1.4 quest.
        """
        amount, reason = qc.resolve_for_api("AddCriteriaExp", 2170)
        self.assertIsNone(reason)
        self.assertEqual(amount.base, 15800)
        self.assertEqual(amount.amount, 22120)
        self.assertEqual(int(amount.raw), 22119)  # the bug, kept as evidence
        self.assertLess(amount.raw, 22120)

    def test_rounding_lives_at_one_place_and_that_place_is_floor(self):
        """COO-DECISION 20260907_0845, checkable rather than remembered."""
        self.assertIs(qc.ROUNDING_MODE, ROUND_FLOOR)
        self.assertEqual(qc.round_amount(Decimal("22.9")), 22)
        self.assertEqual(qc.round_amount(Decimal("22.0")), 22)
        source = (REPO_ROOT / "src" / "pirateforce_foundation" / "lua_api"
                  / "quest_criteria.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("to_integral_value"), 1)

    def test_every_resolution_is_its_own_exact_value_through_round_amount(self):
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
                self.assertEqual(amount.amount, qc.round_amount(amount.exact))

    def test_the_log_line_shows_the_authored_multiplier_not_the_widened_one(self):
        amount, _ = qc.resolve_for_api("AddCriteriaExp", 2170)
        line = amount.log_fields()
        self.assertIn("mult=1.4", line)
        self.assertNotIn("1.399999976158142", line)
        self.assertIn("amount=22120", line)
        # A whole-number product does not shout an exact= nobody needs.
        self.assertNotIn("exact=", line)
        line.encode("ascii")

    def test_a_fractional_reward_cannot_hide_behind_a_clean_integer(self):
        fractional = qc.resolve(qc.KIND_EXP, 1, 0.25)
        self.assertIn("exact=22.5", fractional.log_fields())
        self.assertIn("amount=22", fractional.log_fields())


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
