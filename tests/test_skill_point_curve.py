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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Same line `test_class_starting_gear.py` carries.  Without it this file
# only imports when some EARLIER test module in the same run happened to
# put `src/` on the path, so `pytest tests/test_skill_point_curve.py` on
# its own has never worked -- which is a poor way to hand a lane a file it
# is meant to iterate on.
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_standard_status
from pirateforce_foundation import skill_point_curve


class TheRefusalsNobodyHadEverRunTests(unittest.TestCase):
    """The three ``REFUSE_TABLE_*`` branches, driven for the first time.

    pf-adversary finding D9 of round ``2o69yt``: ``_load_rows`` has three
    raises that no test had ever reached, so the messages could have been
    wrong, the constants unreachable, or the whole check inverted, and the
    suite would not have noticed.  They are the only thing standing between
    a corrupted vendored table and five classes being handed silently wrong
    skill points, so "never executed" was not an acceptable state for them.

    Each case stages a COPY of the package (the vendored table lives inside
    it), damages the copy in exactly one way, and imports the module in a
    real interpreter -- because these raise at IMPORT, which is the property
    the module's own docstring sells and which an in-process patch could not
    demonstrate.  Nothing under ``src/`` is touched.
    """

    def _staged(self, tmp):
        package = Path(tmp) / "pirateforce_foundation"
        shutil.copytree(
            ROOT / "src" / "pirateforce_foundation",
            package,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        return package

    def _import_it(self, tmp):
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "from pirateforce_foundation import skill_point_curve",
            ],
            cwd=str(ROOT),
            env={"PYTHONPATH": str(tmp), "PATH": "/usr/bin:/bin"},
            capture_output=True,
        )

    def _repin(self, package, table_bytes):
        """Rewrite the copy's SOURCE_SHA256 to match `table_bytes`.

        Without this every damaged table would trip REFUSE_TABLE_DRIFTED
        first and the two MALFORMED branches would stay unreachable -- the
        exact blindness D9 is about.
        """
        digest = hashlib.sha256(table_bytes).hexdigest()
        source = (package / "skill_point_curve.py").read_text(encoding="utf-8")
        self.assertIn(skill_point_curve.SOURCE_SHA256, source)
        source = source.replace(skill_point_curve.SOURCE_SHA256, digest)
        (package / "skill_point_curve.py").write_text(source, encoding="utf-8")

    def test_a_drifted_table_refuses_at_import_and_names_the_two_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self._staged(tmp)
            table = package / "data" / "level_sp.tsv"
            damaged = table.read_bytes() + b"121\t999\n"
            table.write_bytes(damaged)
            result = self._import_it(tmp)
        self.assertNotEqual(result.returncode, 0)
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertIn(skill_point_curve.REFUSE_TABLE_DRIFTED, stderr)
        # Both digests, so an operator can tell "I edited the table" from
        # "the pin is stale" without opening the file.
        self.assertIn(skill_point_curve.SOURCE_SHA256, stderr)
        self.assertIn(hashlib.sha256(damaged).hexdigest(), stderr)

    def test_a_table_with_other_columns_refuses_as_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self._staged(tmp)
            table = package / "data" / "level_sp.tsv"
            damaged = table.read_bytes().replace(b"n_SP", b"n_EXP", 1)
            self.assertNotEqual(damaged, table.read_bytes())
            table.write_bytes(damaged)
            self._repin(package, damaged)
            result = self._import_it(tmp)
        self.assertNotEqual(result.returncode, 0)
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertIn(skill_point_curve.REFUSE_TABLE_MALFORMED, stderr)
        self.assertIn("n_EXP", stderr)
        # ...and NOT as a drift: the hash matched, so this is the second
        # branch, not the first one wearing the second one's name.
        self.assertNotIn(skill_point_curve.REFUSE_TABLE_DRIFTED, stderr)

    def test_a_table_with_a_hole_in_the_levels_refuses_as_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = self._staged(tmp)
            table = package / "data" / "level_sp.tsv"
            lines = table.read_bytes().split(b"\n")
            # Drop one data row from the middle.  A gap, not a short table:
            # a reader that only counted rows would still be fooled by
            # renumbering, so the levels themselves must be what is checked.
            kept = [line for line in lines if not line.startswith(b"60\t")]
            self.assertEqual(len(kept), len(lines) - 1)
            damaged = b"\n".join(kept)
            table.write_bytes(damaged)
            self._repin(package, damaged)
            result = self._import_it(tmp)
        self.assertNotEqual(result.returncode, 0)
        stderr = result.stderr.decode("utf-8", "replace")
        self.assertIn(skill_point_curve.REFUSE_TABLE_MALFORMED, stderr)
        self.assertIn("119 rows", stderr)

    def test_an_undamaged_copy_of_the_same_staging_imports_cleanly(self):
        """The control.  Without it all three tests above could be passing
        because the staging itself is broken -- a package copy that cannot
        import at all would satisfy every assertion about a non-zero exit.
        """
        with tempfile.TemporaryDirectory() as tmp:
            self._staged(tmp)
            result = self._import_it(tmp)
        self.assertEqual(
            result.returncode, 0, result.stderr.decode("utf-8", "replace")[-2000:]
        )


class TheRefusalTypeIsSwallowableTests(unittest.TestCase):
    """Recorded, not fixed: pf-adversary D12 of round ``2o69yt``.

    ``SkillPointCurveError`` derives from ``KeyError``, so a caller written
    as ``try: ... except KeyError: return default`` swallows a refusal that
    means "the committed table is corrupt" and hands back a default skill
    point count instead.  The base class is not changed here because this
    module has no production caller yet and the fix belongs in the same
    commit as the first one -- but the shape is pinned so the day a caller
    appears, this test is what it is read against.
    """

    def test_a_bare_except_keyerror_swallows_a_corrupt_table_refusal(self):
        swallowed = False
        try:
            raise skill_point_curve.SkillPointCurveError(
                skill_point_curve.REFUSE_TABLE_DRIFTED, "staged"
            )
        except KeyError:
            swallowed = True
        self.assertTrue(
            swallowed,
            "if this ever fails the base class changed; the caller-side "
            "hazard D12 describes is gone and this test should be replaced "
            "by one that pins the new base",
        )
        self.assertTrue(issubclass(skill_point_curve.SkillPointCurveError, KeyError))


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

    def test_the_only_birth_names_are_the_four_the_owner_ordered(self):
        """This test used to demand ZERO birth names, and that was right
        until 2026-09-08 14:41.

        ``COO-DECISION 20260908_1341`` forbade a birth value while nothing
        consumed one; ``COO-DECISION 20260908_1441`` point 3 lifted the ban
        for exactly one constant, because a consumer arrived -- LANE-DB's
        birth pin, which can only grade the VALUE of ``skill_points`` if some
        module in ``src/`` declares it.  So the test keeps its teeth and
        changes its shape: an allowlist, not a ban.  A fifth birth name, or a
        ``starting_skill_points()`` under any other spelling, is still red.
        """
        allowed = {
            "BIRTH_SKILL_POINTS",
            "BIRTH_SKILL_POINTS_PROVENANCE",
            "BIRTH_SKILL_POINTS_SOURCE",
            "OWNER_ORDERED_BIRTH_SKILL_POINTS",
            "birth_skill_points",
            "REFUSE_BIRTH_PROVENANCE_UNKNOWN",
            "REFUSE_BIRTH_ASSUMPTION_NOT_AS_ORDERED",
            "REFUSE_BIRTH_MEASURED_WITHOUT_SOURCE",
            "REFUSE_BIRTH_ASSUMPTION_WITH_SOURCE",
        }
        found = {
            name for name in dir(skill_point_curve)
            if not name.startswith("_")
            and ("starting" in name.lower() or "birth" in name.lower()
                 or "default" in name.lower())
        }
        self.assertEqual(found - allowed, set())
        # And the four that carry the value must all still be there: a round
        # that deletes the provenance label and keeps the number is the other
        # way this can go wrong.
        self.assertLessEqual(
            {
                "BIRTH_SKILL_POINTS",
                "BIRTH_SKILL_POINTS_PROVENANCE",
                "BIRTH_SKILL_POINTS_SOURCE",
                "OWNER_ORDERED_BIRTH_SKILL_POINTS",
            },
            found,
        )


class BirthSkillPointsTests(unittest.TestCase):
    """The one number this module names.

    ``COO-DECISION 20260908_1441`` point 3 made this lane the owner of the
    skill points a character is born holding, so that LANE-DB's birth pin can
    grade the value instead of only the column.  These tests grade the two
    things that can rot: the number, and the honesty of the label on it.
    """

    def setUp(self):
        self._saved = {
            name: getattr(skill_point_curve, name)
            for name in (
                "BIRTH_SKILL_POINTS",
                "BIRTH_SKILL_POINTS_PROVENANCE",
                "BIRTH_SKILL_POINTS_SOURCE",
                "OWNER_ORDERED_BIRTH_SKILL_POINTS",
            )
        }

    def tearDown(self):
        for name, value in self._saved.items():
            setattr(skill_point_curve, name, value)

    def test_the_shipped_value_is_the_zero_the_owner_ordered(self):
        self.assertEqual(skill_point_curve.BIRTH_SKILL_POINTS, 0)
        self.assertEqual(
            skill_point_curve.OWNER_ORDERED_BIRTH_SKILL_POINTS, 0
        )
        self.assertEqual(skill_point_curve.birth_skill_points(), 0)

    def test_the_label_is_assumption_and_names_no_source(self):
        """Not decoration.  ``COO-DECISION 20260908_1441`` point 3 says to
        write MEASURED only if a shipped table declares the number, and this
        round's header scan of every ``gamedata/tables/*.tsv`` found none."""
        self.assertEqual(
            skill_point_curve.BIRTH_SKILL_POINTS_PROVENANCE,
            skill_point_curve.PROVENANCE_ASSUMPTION,
        )
        self.assertEqual(skill_point_curve.BIRTH_SKILL_POINTS_SOURCE, "")
        self.assertEqual(
            skill_point_curve.PROVENANCE_LABELS,
            ("MEASURED", "ASSUMPTION"),
        )

    def test_the_number_does_not_come_from_the_table(self):
        """Mutation pin for the coincidence the header calls out: under
        reading (b) level 1 holds 0 too, so a reader could think this value
        is read off the curve.  Blank the whole curve and the birth value
        must not move."""
        original = dict(skill_point_curve._ROWS)
        try:
            for level in list(skill_point_curve._ROWS):
                skill_point_curve._ROWS[level] = (
                    skill_point_curve.SkillPointRow(level=level, sp=777)
                )
            self.assertEqual(skill_point_curve.birth_skill_points(), 0)
        finally:
            skill_point_curve._ROWS.clear()
            skill_point_curve._ROWS.update(original)

    def test_an_unknown_provenance_label_is_refused_by_name(self):
        skill_point_curve.BIRTH_SKILL_POINTS_PROVENANCE = "probably"
        with self.assertRaises(
            skill_point_curve.SkillPointCurveError
        ) as caught:
            skill_point_curve.birth_skill_points()
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_BIRTH_PROVENANCE_UNKNOWN,
        )

    def test_an_unmeasured_number_other_than_the_ordered_one_is_refused(self):
        """The guessed-number door.  A later round that quietly writes the
        table's own ``2`` into the birth constant, still labelled
        ASSUMPTION, gets refused rather than shipped."""
        skill_point_curve.BIRTH_SKILL_POINTS = 2
        with self.assertRaises(
            skill_point_curve.SkillPointCurveError
        ) as caught:
            skill_point_curve.birth_skill_points()
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_BIRTH_ASSUMPTION_NOT_AS_ORDERED,
        )
        self.assertIn("20260908_1218", caught.exception.args[1])

    def test_claiming_measured_without_naming_a_table_is_refused(self):
        skill_point_curve.BIRTH_SKILL_POINTS_PROVENANCE = (
            skill_point_curve.PROVENANCE_MEASURED
        )
        with self.assertRaises(
            skill_point_curve.SkillPointCurveError
        ) as caught:
            skill_point_curve.birth_skill_points()
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_BIRTH_MEASURED_WITHOUT_SOURCE,
        )

    def test_naming_a_table_under_an_assumption_label_is_refused(self):
        skill_point_curve.BIRTH_SKILL_POINTS_SOURCE = "CONSTDATA_TH__LEVEL_SP"
        with self.assertRaises(
            skill_point_curve.SkillPointCurveError
        ) as caught:
            skill_point_curve.birth_skill_points()
        self.assertEqual(
            caught.exception.args[0],
            skill_point_curve.REFUSE_BIRTH_ASSUMPTION_WITH_SOURCE,
        )

    def test_a_measured_value_with_a_named_source_is_allowed_through(self):
        """The door has to OPEN the day an RE answers, or the guard is just
        a wall.  Measured here rather than assumed: relabel, name a table,
        and any number passes."""
        skill_point_curve.BIRTH_SKILL_POINTS = 2
        skill_point_curve.BIRTH_SKILL_POINTS_PROVENANCE = (
            skill_point_curve.PROVENANCE_MEASURED
        )
        skill_point_curve.BIRTH_SKILL_POINTS_SOURCE = "RE-xxx table row"
        self.assertEqual(skill_point_curve.birth_skill_points(), 2)

    def test_the_console_line_reports_the_birth_value_and_its_label(self):
        line = skill_point_curve.headless_summary()
        self.assertEqual(line.encode("ascii").decode("ascii"), line)
        self.assertIn("birth_sp=0", line)
        self.assertIn("birth_sp_provenance=ASSUMPTION", line)

    def test_the_console_line_reads_the_door_not_a_constant(self):
        """Mutation pin of the same shape D3/D6 forced on the other fields:
        move the number (and the order behind it) and the line must move."""
        skill_point_curve.OWNER_ORDERED_BIRTH_SKILL_POINTS = 5
        skill_point_curve.BIRTH_SKILL_POINTS = 5
        line = skill_point_curve.headless_summary()
        self.assertIn("birth_sp=5", line)
        skill_point_curve.BIRTH_SKILL_POINTS_PROVENANCE = (
            skill_point_curve.PROVENANCE_MEASURED
        )
        skill_point_curve.BIRTH_SKILL_POINTS_SOURCE = "RE-xxx table row"
        self.assertIn(
            "birth_sp_provenance=MEASURED",
            skill_point_curve.headless_summary(),
        )


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
