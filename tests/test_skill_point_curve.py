"""Pins for LANE-CS's reader of the client's level-indexed SP curve.

Every number asserted here was read off
``pf_bridge/gamedata/tables/CONSTDATA_TH__LEVEL_SP.tsv`` and is re-derivable
from the byte-identical copy this repo vendors.  The cross-table tests
deliberately go through ``persistence_standard_status``, which loads its OWN
file with its OWN hash pin, so "the SP curve is not the experience curve" is
checked against an independent reader rather than against a constant this
module also owns -- the tautology shape pf-adversary caught this lane writing
in round ``3f12wv``.
"""

import hashlib
import unittest

from pirateforce_foundation import persistence_standard_status
from pirateforce_foundation import skill_point_curve


class CommittedCopyTests(unittest.TestCase):
    def test_the_vendored_copy_hashes_to_the_pinned_digest(self):
        digest = hashlib.sha256(
            skill_point_curve._DATA_PATH.read_bytes()
        ).hexdigest()
        self.assertEqual(digest, skill_point_curve.SOURCE_SHA256)

    def test_the_table_carries_every_level_from_1_to_120_with_no_gap(self):
        self.assertEqual(
            skill_point_curve.levels(), tuple(range(1, 121))
        )
        self.assertEqual(skill_point_curve.TABLE_FIRST_LEVEL, 1)
        self.assertEqual(skill_point_curve.TABLE_LAST_LEVEL, 120)

    def test_n_sp_rises_at_every_one_of_the_119_steps(self):
        self.assertTrue(skill_point_curve.is_strictly_increasing())


class ShippedValueTests(unittest.TestCase):
    """Spot rows, chosen where the curve changes shape rather than at random.

    Level 1 and 2 are the rows the ``skill_points``-at-birth decision turns
    on; 11->12 is where the curve's step jumps from +5 to +50; 120 is the
    last row and the number LANE-CS wrongly called impossible.
    """

    def test_the_rows_the_birth_decision_turns_on(self):
        self.assertEqual(skill_point_curve.sp_at_level(1), 2)
        self.assertEqual(skill_point_curve.sp_at_level(2), 4)

    def test_the_row_where_the_step_size_jumps(self):
        self.assertEqual(skill_point_curve.sp_at_level(11), 47)
        self.assertEqual(skill_point_curve.sp_at_level(12), 97)

    def test_the_last_row(self):
        self.assertEqual(skill_point_curve.sp_at_level(120), 13645740)

    def test_row_for_level_returns_the_typed_record(self):
        row = skill_point_curve.row_for_level(60)
        self.assertEqual(row.level, 60)
        self.assertEqual(row.sp, 47125)


class NotTheExperienceCurveTests(unittest.TestCase):
    """The claim LANE-DB asked somebody to actually measure.

    Checked against ``persistence_standard_status``'s independently hashed
    copy of ``CONSTDATA_TH__STANDARD_STATUS.tsv``.
    """

    def _status(self, level):
        return persistence_standard_status.standard_status_row(level)

    def test_n_sp_never_equals_the_experience_value_at_the_same_level(self):
        collisions = [
            level for level in skill_point_curve.levels()
            if skill_point_curve.sp_at_level(level)
            == self._status(level).exp_currentlv
        ]
        self.assertEqual(collisions, [])

    def test_n_sp_never_equals_the_pvp_sp_or_pvp_exp_value(self):
        collisions = [
            level for level in skill_point_curve.levels()
            if skill_point_curve.sp_at_level(level)
            in (self._status(level).pvp_sp, self._status(level).pvp_exp)
        ]
        self.assertEqual(collisions, [])

    def test_n_sp_never_equals_the_per_level_experience_delta(self):
        collisions = []
        for level in skill_point_curve.levels():
            if level + 1 > skill_point_curve.TABLE_LAST_LEVEL:
                continue
            delta = (
                self._status(level + 1).exp_currentlv
                - self._status(level).exp_currentlv
            )
            if skill_point_curve.sp_at_level(level) == delta:
                collisions.append(level)
        self.assertEqual(collisions, [])

    def test_the_two_tables_do_not_even_cover_the_same_levels(self):
        """120 vs 255: they cannot be two views of one object."""
        self.assertEqual(skill_point_curve.TABLE_LAST_LEVEL, 120)
        self.assertEqual(
            persistence_standard_status.STANDARD_STATUS_MAX_LEVEL, 255
        )
        with self.assertRaises(skill_point_curve.SkillPointCurveError):
            skill_point_curve.sp_at_level(121)
        # ...and the level with no SP row still has a status row, so the
        # refusal above is this table ending, not a bad argument.
        self.assertIsNotNone(self._status(121))


class UndecidedReadingTests(unittest.TestCase):
    """The module must not quietly pick one of the two readings.

    A future round that adds ``starting_skill_points()`` returning 2 (or 0)
    to this module makes this test red on purpose: the number is not the
    problem, publishing it as a fact is.
    """

    def test_both_readings_are_published_and_neither_is_preferred(self):
        self.assertEqual(
            skill_point_curve.UNDECIDED_READINGS,
            (
                skill_point_curve.READING_HOLDING,
                skill_point_curve.READING_THRESHOLD,
            ),
        )
        self.assertEqual(len(set(skill_point_curve.UNDECIDED_READINGS)), 2)

    def test_the_module_exports_no_birth_value_under_any_spelling(self):
        forbidden = [
            name for name in dir(skill_point_curve)
            if not name.startswith("_")
            and ("starting" in name.lower() or "birth" in name.lower()
                 or "default" in name.lower())
        ]
        self.assertEqual(forbidden, [])


class RefusalTests(unittest.TestCase):
    def test_a_level_below_the_table_is_refused_by_name(self):
        with self.assertRaises(skill_point_curve.SkillPointCurveError) as caught:
            skill_point_curve.sp_at_level(0)
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_LEVEL_OFF_TABLE,
        )

    def test_a_level_above_the_table_is_refused_by_name(self):
        with self.assertRaises(skill_point_curve.SkillPointCurveError) as caught:
            skill_point_curve.sp_at_level(255)
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_LEVEL_OFF_TABLE,
        )

    def test_a_bool_is_not_a_level(self):
        with self.assertRaises(skill_point_curve.SkillPointCurveError) as caught:
            skill_point_curve.sp_at_level(True)
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_LEVEL_NOT_AN_INT,
        )

    def test_a_float_that_equals_a_level_is_still_not_a_level(self):
        with self.assertRaises(skill_point_curve.SkillPointCurveError) as caught:
            skill_point_curve.sp_at_level(60.0)
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_LEVEL_NOT_AN_INT,
        )


class HeadlessSummaryTests(unittest.TestCase):
    def test_the_console_line_is_ascii_and_carries_the_measured_fields(self):
        line = skill_point_curve.headless_summary()
        self.assertEqual(line.encode("ascii").decode("ascii"), line)
        self.assertIn("SKILL_POINT_CURVE rows=120 levels=1..120", line)
        self.assertIn("sp_first=2", line)
        self.assertIn("sp_last=13645740", line)
        self.assertIn("strictly_increasing=yes", line)

    def test_the_summary_reads_the_loaded_rows_not_a_constant(self):
        """Mutation pin: blank the loaded table and the line must change.

        Written because this lane shipped a headless token last round that
        printed a constant while claiming to report the frame (pf-adversary
        D3, round ``3f12wv``).
        """
        original = dict(skill_point_curve._ROWS)
        try:
            skill_point_curve._ROWS[1] = skill_point_curve.SkillPointRow(
                level=1, sp=999
            )
            self.assertIn("sp_first=999", skill_point_curve.headless_summary())
        finally:
            skill_point_curve._ROWS.clear()
            skill_point_curve._ROWS.update(original)
        self.assertIn("sp_first=2", skill_point_curve.headless_summary())


class AdversaryPaidTests(unittest.TestCase):
    """Pins added to answer pf-adversary findings on this round's first draft.

    Each test names the finding it closes so a later round can tell a pin
    that was reasoned about from a pin that was added to feel thorough.
    """

    def test_d3_more_rows_are_named_than_the_digest_alone_protects(self):
        """D3: the hash is self-signed -- a coordinated edit passes it.

        These value pins do not fix that.  They raise its cost: a coordinated
        edit now has to move fourteen named rows spread across the table as
        well as the digest.  114 rows remain covered by the digest alone.
        """
        spread = {
            1: 2, 2: 4, 11: 47, 12: 97, 26: 1462, 27: 3403,
            40: 8422, 41: 8903, 60: 47125, 61: 62437,
            90: 470613, 100: 920014, 110: 2556816, 120: 13645740,
        }
        measured = {
            level: skill_point_curve.sp_at_level(level) for level in spread
        }
        self.assertEqual(measured, spread)

    def test_d4_the_ratio_bounds_quoted_in_the_module_header_are_real(self):
        """D4: the header's ratio claim had no test and two wrong numbers.

        Computed here rather than in the module: naming the STANDARD_STATUS
        reader inside `src/` enrols that file in its sole-caller pin, which
        is what turned this round's first full suite red.
        """
        ratios = {}
        for level in skill_point_curve.levels():
            exp = persistence_standard_status.standard_status_row(
                level
            ).exp_currentlv
            if exp:
                ratios[level] = skill_point_curve.sp_at_level(level) / exp
        # Level 1 has no ratio at all: exp is 0 there while n_SP is 2.
        self.assertNotIn(1, ratios)
        self.assertEqual(len(ratios), 119)
        low = min(ratios, key=ratios.get)
        high = max(ratios, key=ratios.get)
        self.assertEqual((low, high), (2, 61))
        self.assertAlmostEqual(ratios[low], 0.05063, places=5)
        self.assertAlmostEqual(ratios[high], 0.17857, places=5)
        band = [ratios[lv] for lv in range(13, 41)]
        self.assertAlmostEqual(min(band), 0.05942, places=5)
        self.assertAlmostEqual(max(band), 0.05952, places=5)

    def test_d6_is_strictly_increasing_is_not_a_constant(self):
        """D6: `return True` survived as a mutant of that function."""
        original = dict(skill_point_curve._ROWS)
        try:
            skill_point_curve._ROWS[60] = skill_point_curve.SkillPointRow(
                level=60, sp=skill_point_curve._ROWS[61].sp + 1
            )
            self.assertFalse(skill_point_curve.is_strictly_increasing())
        finally:
            skill_point_curve._ROWS.clear()
            skill_point_curve._ROWS.update(original)
        self.assertTrue(skill_point_curve.is_strictly_increasing())

    def test_d6_the_summary_reads_every_field_it_prints(self):
        """D6: only `sp_first` was covered; `rows`, `levels`, `sp_last` and
        `strictly_increasing` could all be hardcoded and survive."""
        original = dict(skill_point_curve._ROWS)
        try:
            skill_point_curve._ROWS[120] = skill_point_curve.SkillPointRow(
                level=120, sp=7
            )
            line = skill_point_curve.headless_summary()
            self.assertIn("sp_last=7", line)
            # 120 now sits below 119, so the ordering field must flip too.
            self.assertIn("strictly_increasing=no", line)
            skill_point_curve._ROWS[121] = skill_point_curve.SkillPointRow(
                level=121, sp=99
            )
            self.assertIn("rows=121", skill_point_curve.headless_summary())
        finally:
            skill_point_curve._ROWS.clear()
            skill_point_curve._ROWS.update(original)
        line = skill_point_curve.headless_summary()
        self.assertIn("rows=120", line)
        self.assertIn("sp_last=13645740", line)
        self.assertIn("strictly_increasing=yes", line)

    def test_d11_the_last_level_is_covered_by_the_delta_check_too(self):
        """D11: the delta pin skipped level 120 although STANDARD_STATUS has
        a row 121.  Checked in both directions."""
        forward = (
            persistence_standard_status.standard_status_row(121).exp_currentlv
            - persistence_standard_status.standard_status_row(
                120
            ).exp_currentlv
        )
        backward = (
            persistence_standard_status.standard_status_row(120).exp_currentlv
            - persistence_standard_status.standard_status_row(
                119
            ).exp_currentlv
        )
        self.assertNotEqual(skill_point_curve.sp_at_level(120), forward)
        self.assertNotEqual(skill_point_curve.sp_at_level(120), backward)


if __name__ == "__main__":
    unittest.main()
