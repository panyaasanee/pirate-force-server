"""LANE-DB / M4: a character's HP and level are remembered by the database,
an unwritten one is ABSENT rather than dead, and a hit is arithmetic that
cannot invent a number.

WHAT THIS FILE IS THE EVIDENCE FOR.  ``COO-DECISION 20260901_1100`` named this
lane's queue after ``/speed`` -- HP/level -- and named what it unlocks: M4,
``ตีได้ตายได้``.  ``migrations/006_character_typed_attribute_columns.sql`` built
``level``/``hp_current``/``hp_max``; ``persistence_vitals`` is the decision
layer over them and ``SQLiteStore.read_character_vitals`` /
``SQLiteStore.apply_hp_damage`` are the two store methods on top.  This file
proves four things, in the order they matter:

1. **An unseeded HP column is never read as zero.**  On this wire zero HP is
   not "unknown", it is DEAD -- so the owner's banned guessed zero
   (``COO-DECISION 20260901_1059``) would arrive here not as a wrong field in
   a block but as a character killed by the first hit that ever touched it.
   Measured against a real database: a character row whose three columns are
   NULL reports three named gaps out of ``read_character_vitals``, and
   ``apply_hp_damage`` refuses it and writes nothing.

   THIS SENTENCE USED TO SAY "every character in it today has three NULL
   vitals", AND THAT IS NOW FALSE.  A second ``pf-adversary`` pass measured
   it: run ``007`` and every character it seeded resolves COMPLETE, with no
   gaps at all.  The round that fixed the same overclaim in three test names
   and a section comment further down did not open the top of its own file --
   which is the whole shape of the defect, so the correction is recorded here
   rather than quietly applied.  What this file grades is a ROW holding
   nothing, which its fixtures now build explicitly (``_unseed``).
2. **The cross-column rules SQLite cannot express are enforced somewhere.**
   ``006`` writes one CHECK per column, so ``hp_current > hp_max`` and a zero
   maximum pass the database happily.  Proved by storing exactly those states
   through the repository's own writer and watching the read path refuse them.
3. **Damage arithmetic has no way to produce a wrong number.**  Overkill is
   clamped and REPORTED (``requested`` vs ``applied``), a negative amount is
   refused rather than healing, ``True`` is not one point of damage, and the
   floor is zero.
4. **Nothing is WIRED.**  No call site outside this lane calls any of the
   three store methods; asserted rather than promised, by walking every
   ``.py`` under the repository root (``NothingIsWiredTests``), not by
   trusting a comment.

   THE WORD "EVERY" IS NEW AND IS THE POINT.  When this headline was
   rewritten it said "scanning every python tree in the repository" over a
   scan that walked a hardcoded list of seven directories and skipped the
   missing ones in silence -- two of the seven do not exist.  A third
   ``pf-adversary`` pass dropped a real caller in the repository ROOT and
   another under a new top-level directory, and both left the test green.
   The claim was corrected by making it TRUE (the scan walks ``ROOT``) rather
   than by narrowing the sentence, because a directory added next year should
   join the scan by existing.

   It used to read "nothing is seeded and nothing is wired ... by parsing the
   migrations directory".  Both halves had rotted and a ``pf-adversary`` pass
   named them: ``migrations/007_character_vitals_seed.sql`` SEEDS, and no test
   in this file parses the migrations directory any more -- ``census_sql``
   replaced that text parser, for reasons ``SeedingCensusTests`` records at
   length.  A headline that describes a test the file no longer contains is
   worse than no headline.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no frame is
composed, nothing is sent, and no call site in this repository calls either
new store method.  A player cannot be hit in the game because of this file.
It is wire/DB evidence only, and it has never run against the owner's
canonical database.
"""
import ast
import contextlib
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pf_vitals_wire_decode import decode_basic_block  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: What `migrations/007_character_vitals_seed.sql` writes, transcribed here so
#: that a test can compare against it.  `NewCharacterVitalsTests.
#: test_the_values_are_the_ones_007_wrote` re-derives the same three numbers
#: from that file's SQL, so this constant cannot drift from it in silence.
SEEDED_BY_007 = {"level": 1, "hp_current": 100, "hp_max": 100}
MODULE = ROOT / "src" / "pirateforce_foundation" / "persistence_vitals.py"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _unseed(path, character_id):
    """Put a freshly created character back into the UNSEEDED state.

    `COO-DECISION 20260902_0443` route (KHO) has chief's plug write
    `new_character_vitals()` into the row at `create_character` time, from a
    PR that is not this one.  Several fixtures below need a row that holds
    NOTHING -- that is what they are about -- and until that plug lands they
    got it for free, because `create_character`'s INSERT names no vital
    column.  Measured with the plug applied locally: five tests in this file
    went red, none of them about creation.

    So the unseeded state is now BUILT rather than assumed, and these tests
    grade the same thing either side of chief's landing.  It is a raw UPDATE
    on a test database, never on a real one, which is the only place this
    lane's rules allow one.
    """
    with raw(path) as db:
        changed = db.execute(
            "UPDATE characters SET level=NULL, hp_current=NULL, hp_max=NULL "
            "WHERE id=?", (character_id,)).rowcount
    # A `pf-adversary` pass pointed out that an absent or wrong id makes this
    # a silent no-op: the fixture would look built and grade nothing.
    # Invisible today, because the columns are already NULL; the day the plug
    # lands it is the difference between a fixture and a decoration.
    if changed != 1:
        raise AssertionError(
            "_unseed matched %d rows for character %r, not 1: the fixture it "
            "was supposed to build does not exist" % (changed, character_id))


@contextlib.contextmanager
def raw(path):
    """A raw sqlite connection that is COMMITTED **and CLOSED**.

    `with sqlite3.connect(...) as db:` commits on exit and does NOT close --
    a python API wart that costs nothing on Linux, where an open file can
    still be unlinked, and fails the whole suite on Windows.  Measured, not
    guessed: this file's first version used the bare form and the Windows gate
    went red on three tests with

        PermissionError: [WinError 32] The process cannot access the file
        because it is being used by another process: ...\\state.sqlite3

    raised from `TemporaryDirectory` cleanup, while every test passed on the
    machine it was written on.  Every raw connection in this file goes through
    here so that cannot come back.
    """
    db = sqlite3.connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


class BindingTests(unittest.TestCase):
    """The three columns really are the three wire fields this module claims."""

    def test_the_three_columns_are_level_and_the_hp_pair(self):
        self.assertEqual(
            vitals.VITAL_COLUMNS, ("level", "hp_current", "hp_max"))
        self.assertEqual(vitals.VITAL_X, (2, 3, 4))

    def test_every_column_is_a_built_typed_column(self):
        for column in vitals.VITAL_COLUMNS:
            self.assertIn(column, typed.TYPED_COLUMNS, column)

    def test_each_column_serves_the_wire_field_it_is_bound_to(self):
        for x, column in zip(vitals.VITAL_X, vitals.VITAL_COLUMNS):
            self.assertEqual(typed.TYPED_COLUMNS[column].x, x)

    def test_the_binding_check_fires_when_the_wire_table_drifts(self):
        # The rule is only worth having if it can go off.  x=3 renamed under
        # this module's feet is exactly the drift `_verify_binding` exists for.
        drifted = dict(vitals.BY_X)
        row = list(drifted[3])
        row[6] = "something_else"
        drifted[3] = tuple(row)
        with mock.patch.object(vitals, "BY_X", drifted):
            with self.assertRaises(vitals.VitalsError) as caught:
                vitals._verify_binding()
        self.assertIn("binding is stale", str(caught.exception))

    def test_the_binding_check_fires_when_a_field_stops_being_proven(self):
        # This module says out loud that all three names are proven
        # (`known=True`), unlike x=7.  If that stops being true the claim in
        # the docstring is false and this must not import silently.
        drifted = dict(vitals.BY_X)
        row = list(drifted[2])
        row[7] = False
        drifted[2] = tuple(row)
        with mock.patch.object(vitals, "BY_X", drifted):
            with self.assertRaises(vitals.VitalsError) as caught:
                vitals._verify_binding()
        self.assertIn("known=False", str(caught.exception))


class NoGuessedZeroInTheSourceTests(unittest.TestCase):
    """The rule that matters most, checked against the source rather than
    against a promise -- the same way `persistence_typed_attrs` is checked."""

    def setUp(self):
        self.tree = ast.parse(MODULE.read_text(encoding="utf-8"))

    def test_no_dict_get_with_a_default_anywhere_in_the_module(self):
        offenders = [
            node.lineno for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) == 2
        ]
        self.assertEqual(
            [], offenders,
            "persistence_vitals.py calls .get(key, default) at lines %r: a "
            "default here is the guessed zero the owner banned, and for an HP "
            "column it is a guessed DEATH" % (offenders,),
        )

    def test_this_test_file_never_opens_a_connection_it_does_not_close(self):
        # The Windows gate's own regression, as a rule with teeth.  A bare
        # `with sqlite3.connect(p) as db:` commits and does NOT close, which
        # is invisible on Linux and takes the gate red on Windows when
        # TemporaryDirectory cannot unlink the still-open file.  Parsed, so a
        # mention in a docstring does not trip it.
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                call = item.context_expr
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "connect"
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "sqlite3"):
                    offenders.append(node.lineno)
        self.assertEqual(
            [], offenders,
            "line(s) %r use `with sqlite3.connect(...)`, which commits but "
            "never closes: use the `raw()` helper in this file instead, or "
            "the Windows gate goes red on TemporaryDirectory cleanup"
            % (offenders,),
        )

    def test_the_module_never_returns_a_bare_zero_for_a_missing_column(self):
        # `dict.get(k)` with no default returns None, which is not a zero; the
        # dangerous shape is the two-argument one above.  This asserts the
        # complementary half: no `or 0` fallback either.
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn(" or 0", source)


class ResolveTests(unittest.TestCase):
    """`resolve` over the shape `read_typed_attributes` returns."""

    def test_an_empty_read_gaps_all_three_and_never_returns_a_number(self):
        resolution = vitals.resolve({})
        self.assertFalse(resolution.complete)
        self.assertEqual(resolution.present, {})
        self.assertEqual(
            [gap.column for gap in resolution.gaps],
            ["level", "hp_current", "hp_max"],
        )
        for gap in resolution.gaps:
            self.assertEqual(gap.reason, vitals.REASON_NOT_SEEDED)

    def test_require_raises_and_names_every_missing_column(self):
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.resolve({}).require()
        message = str(caught.exception)
        for column in vitals.VITAL_COLUMNS:
            self.assertIn(column, message)

    def test_a_complete_row_resolves_to_three_numbers(self):
        resolution = vitals.resolve(
            {"level": 7, "hp_current": 40, "hp_max": 120})
        self.assertTrue(resolution.complete)
        state = resolution.require()
        self.assertEqual((state.level, state.hp_current, state.hp_max),
                         (7, 40, 120))
        self.assertTrue(state.alive)

    def test_zero_current_hp_is_a_usable_state_and_reads_as_not_alive(self):
        # Zero is refused as an ABSENCE, never as a stored value: a character
        # really at 0 HP is a corpse the database is allowed to remember.
        state = vitals.resolve(
            {"level": 7, "hp_current": 0, "hp_max": 120}).require()
        self.assertFalse(state.alive)

    def test_other_typed_columns_in_the_read_are_ignored(self):
        resolution = vitals.resolve({
            "level": 1, "hp_current": 100, "hp_max": 100,
            "cash": 5000, "speed_walk": 400.0,
        })
        self.assertTrue(resolution.complete)
        self.assertEqual(sorted(resolution.present), sorted(vitals.VITAL_COLUMNS))

    def test_half_a_pair_is_incomplete_rather_than_half_used(self):
        resolution = vitals.resolve({"level": 1, "hp_current": 50})
        reasons = {gap.reason for gap in resolution.gaps}
        self.assertIn(vitals.REASON_NOT_SEEDED, reasons)
        self.assertIn(vitals.REASON_HP_PAIR_INCOMPLETE, reasons)

    def test_current_above_maximum_is_refused(self):
        resolution = vitals.resolve(
            {"level": 1, "hp_current": 200, "hp_max": 100})
        self.assertEqual(
            [gap.reason for gap in resolution.gaps],
            [vitals.REASON_HP_ABOVE_MAX],
        )

    def test_a_zero_maximum_is_refused(self):
        resolution = vitals.resolve(
            {"level": 1, "hp_current": 0, "hp_max": 0})
        self.assertEqual(
            [gap.reason for gap in resolution.gaps],
            [vitals.REASON_HP_MAX_ZERO],
        )

    def test_a_zero_level_is_refused(self):
        """COO-DECISION 20260902_0443 point 4.

        This is the rule 007 already applied to itself -- it declines to
        complete a `level = 0` row -- moved into the read path so that the
        migration is no longer the only thing in the repository that knows
        the number is not adjudicated.
        """
        resolution = vitals.resolve(
            {"level": 0, "hp_current": 100, "hp_max": 100})
        self.assertEqual(
            [gap.reason for gap in resolution.gaps],
            [vitals.REASON_LEVEL_ZERO],
        )
        with self.assertRaises(vitals.VitalsError) as caught:
            resolution.require()
        self.assertIn("level", str(caught.exception))

    def test_a_zero_level_is_named_even_with_a_half_written_pair(self):
        """The ordering defect the rule was written around.

        `_consistency_gaps` returns EARLY on an incomplete HP pair.  Put the
        level rule after that early return and a row at `level = 0` with one
        HP end missing reports the pair and nothing else -- so the level
        becomes visible only once somebody fixes the HP, which is the exact
        moment it stops being catchable.  Both reasons must be present.
        """
        reasons = {
            gap.reason
            for gap in vitals.resolve({"level": 0, "hp_current": 100}).gaps
        }
        self.assertIn(vitals.REASON_LEVEL_ZERO, reasons)
        self.assertIn(vitals.REASON_HP_PAIR_INCOMPLETE, reasons)

    def test_level_one_is_not_refused(self):
        """The control: the rule refuses zero, not every small level."""
        self.assertEqual(
            vitals.resolve(
                {"level": 1, "hp_current": 100, "hp_max": 100}).gaps, ())

    def test_a_zero_level_does_not_leak_into_damage_arithmetic(self):
        """`apply_damage` takes two HP numbers and no level, so the new rule
        must not start firing there -- a hit on a valid HP pair is not the
        place to discover a level nobody passed in."""
        outcome = vitals.apply_damage(100, 100, 10)
        self.assertEqual(outcome.hp_after, 90)

    def test_a_hand_built_resolution_raises_a_vitals_error_not_a_keyerror(self):
        # `VitalsResolution` is public and can be built with an empty
        # `present` and no gaps.  A `pf-adversary` pass did that and got
        # `KeyError('level')` out of a contract written in `VitalsError` --
        # and a KeyError from a store caller reads as "no such character".
        empty = vitals.VitalsResolution(present={}, gaps=())
        self.assertTrue(empty.complete)
        with self.assertRaises(vitals.VitalsError) as caught:
            empty.require()
        self.assertIn("not built by resolve()", str(caught.exception))

    def test_a_none_in_the_read_raises_rather_than_becoming_a_number(self):
        # `read_typed_attributes` drops NULLs, but nothing forces a future
        # caller through it -- the same hole `typed_values_for_compose` closes
        # one module over.
        with self.assertRaises(vitals.VitalsError):
            vitals.resolve({"level": 1, "hp_current": None, "hp_max": 100})

    def test_a_value_outside_the_wire_range_raises_as_a_vitals_error(self):
        # The refusal comes from `persistence_typed_attrs.validate` one layer
        # down; this module's contract says VitalsError, so it must be one.
        with self.assertRaises(vitals.VitalsError):
            vitals.resolve({"level": 70000, "hp_current": 1, "hp_max": 1})


class ApplyDamageTests(unittest.TestCase):
    """Pure arithmetic, so every edge is reachable."""

    def test_a_normal_hit(self):
        outcome = vitals.apply_damage(100, 100, 30)
        self.assertEqual((outcome.hp_before, outcome.hp_after), (100, 70))
        self.assertEqual((outcome.requested, outcome.applied), (30, 30))
        self.assertFalse(outcome.died)
        self.assertFalse(outcome.was_already_zero)

    def test_an_exact_kill(self):
        outcome = vitals.apply_damage(30, 100, 30)
        self.assertEqual(outcome.hp_after, 0)
        self.assertTrue(outcome.died)

    def test_an_overkill_is_clamped_and_the_difference_is_reported(self):
        outcome = vitals.apply_damage(10, 100, 999)
        self.assertEqual(outcome.hp_after, 0)
        self.assertEqual((outcome.requested, outcome.applied), (999, 10))
        self.assertTrue(outcome.died)

    def test_hp_never_goes_below_zero(self):
        for amount in (0, 1, 10, 11, 4294967295):
            outcome = vitals.apply_damage(10, 100, amount)
            self.assertGreaterEqual(outcome.hp_after, 0, amount)

    def test_a_zero_damage_hit_is_an_event_not_an_error(self):
        outcome = vitals.apply_damage(100, 100, 0)
        self.assertEqual(outcome.hp_after, 100)
        self.assertEqual(outcome.applied, 0)
        self.assertFalse(outcome.died)

    def test_hitting_a_character_already_at_zero_is_reported_not_refused(self):
        outcome = vitals.apply_damage(0, 100, 50)
        self.assertTrue(outcome.was_already_zero)
        self.assertFalse(outcome.died)
        self.assertEqual(outcome.applied, 0)

    def test_a_negative_amount_is_refused_rather_than_healing(self):
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.apply_damage(50, 100, -10)
        self.assertIn("negative", str(caught.exception))

    def test_a_bool_amount_is_refused(self):
        # `True` is an int in python and would land as a one-point hit.
        with self.assertRaises(vitals.VitalsError):
            vitals.apply_damage(50, 100, True)

    def test_a_float_amount_is_refused(self):
        with self.assertRaises(vitals.VitalsError):
            vitals.apply_damage(50, 100, 1.5)

    def test_an_amount_wider_than_the_hp_field_is_refused(self):
        # `applied` is clamped so nothing wrong could be STORED, but
        # `requested` is handed back to a caller as a damage figure -- and a
        # `pf-adversary` pass got `requested == 2**70` out of this function.
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.apply_damage(10, 100, 2 ** 70)
        self.assertIn("wider than the u32", str(caught.exception))
        # the largest amount the field can describe is still accepted
        self.assertEqual(vitals.apply_damage(10, 100, 4294967295).applied, 10)

    def test_damage_cannot_launder_a_state_the_read_path_would_refuse(self):
        with self.assertRaises(vitals.VitalsError):
            vitals.apply_damage(200, 100, 1)
        with self.assertRaises(vitals.VitalsError):
            vitals.apply_damage(0, 0, 1)


class NewCharacterVitalsTests(unittest.TestCase):
    """`new_character_vitals()` -- COO-DECISION 20260902_0443 route (KHO).

    The decision is about WHERE the three numbers for an unborn character
    live: written into the row at creation (route KHO) rather than as a
    schema `DEFAULT` (route KO, forbidden).  This lane owns the function; the
    plug that calls it in `SQLiteStore.create_character` is chief's, by the
    same decision's point 1.  So what is graded here is the VALUE and its
    provenance, not a database -- there is nothing of this lane's on any live
    path yet, and `SeedsACohortNotADatabaseTests` in the 007 file is where
    that stays honest.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_it_answers_the_three_vital_columns_and_nothing_else(self):
        self.assertEqual(
            sorted(vitals.new_character_vitals()),
            sorted(vitals.VITAL_COLUMNS),
        )

    def test_the_values_are_the_ones_007_wrote(self):
        """Re-derived from 007's SQL, not compared against a constant.

        The point of the decision is that a character created tomorrow is
        indistinguishable from one 007 seeded this morning.  A test that
        asserted `{"level": 1, ...}` would pass on the day somebody changed
        one of them and left 007 alone -- and the drift would show up as two
        cohorts of characters with different birth values, which is the one
        thing this function exists to prevent.
        """
        sql = (MIGRATIONS / "007_character_vitals_seed.sql").read_text(
            encoding="utf-8")
        body = "\n".join(
            line for line in sql.splitlines()
            if not line.lstrip().startswith("--")
        )
        from_migration = {}
        for statement in body.split(";"):
            statement = " ".join(statement.split())
            if " SET " not in statement:
                continue
            assignments = statement.split(" SET ", 1)[1].split(" WHERE ", 1)[0]
            # EVERY assignment is matched and each must be a BARE integer.
            # A `pf-adversary` pass broke the first version with
            # `SET hp_current = 100 + 20`: the loose `(\w+)\s*=\s*(\d+)`
            # search read the token `100`, compared equal, and passed while
            # 007 wrote 120 -- this test re-deriving a TOKEN and calling it a
            # VALUE, in the test whose whole claim is that the two cohorts
            # cannot drift apart.
            for assignment in assignments.split(","):
                match = re.fullmatch(
                    r"\s*(\w+)\s*=\s*(\d+)\s*", assignment)
                self.assertIsNotNone(
                    match,
                    "007 assigns something this test cannot re-derive as a "
                    "plain integer (%r); it must be read by hand before this "
                    "comparison means anything" % (assignment,))
                column, value = match.group(1), match.group(2)
                self.assertIn(column, vitals.VITAL_COLUMNS, statement)
                self.assertNotIn(column, from_migration, statement)
                from_migration[column] = int(value)
        self.assertEqual(len(from_migration), 3, from_migration)
        self.assertEqual(vitals.new_character_vitals(), from_migration)

    def test_the_values_are_still_what_player_wire_sends(self):
        """The provenance the TRANSCRIBED label claims, checked against the
        source rather than against this module's own comment."""
        from pirateforce_foundation import player_wire
        source = Path(player_wire.__file__).read_text(encoding="utf-8")
        start = source.index("def _make_actor_attr_with_name_and_class")
        body = source[start:source.index("\ndef ", start + 1)]
        self.assertIn("legacy.u16tag(0x12, level)", body)
        # THE FRAME IS DECODED, NOT DESCRIBED.
        #
        # Four versions of this assertion read `player_wire.py`'s SOURCE and
        # all four were defeated, each by the mutation the previous fix's own
        # comment invited: `== 2` on a tag count (false red), `>= 2` (false
        # green -- hp_max 150 plus one unrelated tag), "the first two after
        # the level tag" (the extra tag goes ABOVE the pair), and finally a
        # window with a named edge on both sides -- which a fourth
        # `pf-adversary` pass broke by pasting the four anchor lines into the
        # function's DOCSTRING, because `body` includes it and `str.index`
        # takes the first match.  It then broke the byte test too, by keeping
        # the source text and changing the bytes, leaving a decoy
        # `level + 100 + 100` later in the frame for the substring check to
        # find.  Both files green; hp_max 150 on the wire.
        #
        # Every one of those is the same mistake: comparing the frame to a
        # TRANSCRIPTION of the frame.  So this reads the field back out of the
        # bytes at its own wire position, through `pf_vitals_wire_decode`,
        # which walks the mask using `gm/attr_wire.FIELDS` for tags and
        # widths.  A docstring cannot move it, a decoy cannot be mistaken for
        # the pair, and mp_current/mp_max -- which `player_wire`'s docstring
        # pre-announces and whose bits sit between hp_max and movement speed
        # -- join the walk instead of turning an HP assertion red.
        legacy = load_legacy(ROOT / "current" / "pf_login_game_server_v141.py")
        frame = player_wire._make_actor_attr_with_name_and_class(
            legacy, 0x20000001, 0, 3, 0, "WireProbe", 7,
            player_wire.PLAYER_LOGIN_LEVEL, basic_faction=1)
        decoded = decode_basic_block(frame)
        born = vitals.new_character_vitals()
        self.assertEqual(
            decoded[vitals.HP_CURRENT_X], born[vitals.HP_CURRENT_COLUMN],
            "the login frame's hp_current field decodes to %r"
            % (decoded[vitals.HP_CURRENT_X],))
        self.assertEqual(
            decoded[vitals.HP_MAX_X], born[vitals.HP_MAX_COLUMN],
            "the login frame's hp_max field decodes to %r"
            % (decoded[vitals.HP_MAX_X],))
        self.assertEqual(
            decoded[vitals.LEVEL_X], born[vitals.LEVEL_COLUMN],
            "the login frame's level field decodes to %r"
            % (decoded[vitals.LEVEL_X],))
        self.assertEqual(
            born[vitals.LEVEL_COLUMN], player_wire.PLAYER_LOGIN_LEVEL)

    def test_what_it_returns_is_a_state_the_read_path_accepts(self):
        """A birth value the lane's own door refuses would produce characters
        that can never be composed for -- worse than the NULLs it replaces,
        because a NULL is at least reported as a named gap."""
        resolution = vitals.resolve(vitals.new_character_vitals())
        self.assertEqual(resolution.gaps, ())
        born = resolution.require()
        self.assertTrue(born.alive)
        self.assertEqual(born.hp_current, born.hp_max)

    def test_the_answer_comes_from_the_validated_state_not_the_constants(self):
        """The F8 change, graded.  A `pf-adversary` pass reverted
        `return {LEVEL_COLUMN: checked.level, ...}` to `return values` and
        367 tests stayed green: the fix was right and nothing protected it,
        because for every input `require()` accepts the two are equal.

        So the two are forced apart.  `resolve` is replaced with one that
        returns a DIFFERENT complete state; whatever comes back must be that
        state, because the contract is "what the door validated", not "the
        constants that went in".
        """
        other = vitals.Vitals(level=7, hp_current=70, hp_max=80)

        class _Resolution:
            def require(self_inner):
                return other

        with mock.patch.object(vitals, "resolve",
                               lambda values: _Resolution()):
            self.assertEqual(
                vitals.new_character_vitals(),
                {vitals.LEVEL_COLUMN: 7,
                 vitals.HP_CURRENT_COLUMN: 70,
                 vitals.HP_MAX_COLUMN: 80},
            )
        self.assertEqual(vitals.new_character_vitals(), SEEDED_BY_007)

    def test_mutating_the_answer_does_not_change_the_next_one(self):
        """It hands back a fresh dict, not a shared module-level mapping: a
        caller that pops a key out of it must not change what the character
        after that one is born holding."""
        first = vitals.new_character_vitals()
        first[vitals.HP_CURRENT_COLUMN] = 1
        del first[vitals.LEVEL_COLUMN]
        self.assertEqual(vitals.new_character_vitals(),
                         {vitals.LEVEL_COLUMN: 1,
                          vitals.HP_CURRENT_COLUMN: 100,
                          vitals.HP_MAX_COLUMN: 100})

    def test_it_refuses_rather_than_returns_if_a_later_edit_breaks_it(self):
        """The self-check is not decoration.  Route (KHO) means these numbers
        reach a live INSERT; if an edit ever makes them inconsistent, that has
        to fail at creation rather than write a row every later read refuses.

        A `pf-adversary` pass measured the FIRST version of this test, which
        drove only the two zeroes -- the two cases `resolve()` already has
        rules for -- and reported the honest limit: `NEW_CHARACTER_HP` at
        `2**32-1` and `NEW_CHARACTER_LEVEL` at `65535` both came back
        RETURNED, so "not decoration" was proved for zero and nothing else.
        Every drift the door can catch is driven here now, and the two the
        door CANNOT catch are named rather than left to look covered.
        """
        refused = {
            "NEW_CHARACTER_LEVEL": [0, -1, 70000, 1.0, "1", None],
            "NEW_CHARACTER_HP": [0, -1, 2 ** 32, 100.5, "100", None],
        }
        for constant, values in refused.items():
            for value in values:
                with mock.patch.object(vitals, constant, value):
                    with self.assertRaises(vitals.VitalsError, msg=(
                            "%s = %r was RETURNED, not refused"
                            % (constant, value))):
                        vitals.new_character_vitals()
        # In range and therefore NOT refused here.  Named so that nobody reads
        # the loop above as "any wrong number is caught": a level of 65535 and
        # an HP of 2**32-1 are absurd birth values and this door has no
        # opinion about them.  What holds them to 1/100/100 is
        # `test_the_values_are_the_ones_007_wrote` and the wire test, not this.
        for constant, value in (("NEW_CHARACTER_LEVEL", 65535),
                                ("NEW_CHARACTER_HP", 2 ** 32 - 1)):
            with mock.patch.object(vitals, constant, value):
                self.assertIn(value, vitals.new_character_vitals().values())
        self.assertEqual(vitals.new_character_vitals()[vitals.LEVEL_COLUMN], 1)

    def test_a_pre_006_database_is_named_rather_than_raising_raw_sqlite(self):
        """The precondition a `pf-adversary` pass found by simulating chief's
        plug: `create_character` with these three columns in its INSERT dies
        on a 005 database with a raw `sqlite3.OperationalError` out of
        `store.py`.  Passing the connection turns that into this module's own
        named error, which is what `verify_schema` exists for.
        """
        older = Path(self.tmp.name) / "migrations_upto_005"
        older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) < 6:
                shutil.copy2(path, older / path.name)
        path = Path(self.tmp.name) / "pre006.sqlite3"
        SQLiteStore(path, older).migrate()
        with raw(path) as db:
            with self.assertRaises(vitals.SchemaDriftError) as caught:
                vitals.new_character_vitals(db)
        self.assertIn("level", str(caught.exception))

    def test_passing_a_migrated_database_changes_nothing(self):
        path = Path(self.tmp.name) / "migrated.sqlite3"
        SQLiteStore(path, MIGRATIONS).migrate()
        with raw(path) as db:
            self.assertEqual(vitals.new_character_vitals(db),
                             vitals.new_character_vitals())


class SeedingCensusTests(unittest.TestCase):
    """"Is anything seeded" is asked of the DATABASE, and could not be asked
    of the migration text.

    The first draft of this module answered it by parsing `migrations/*.sql`.
    A `pf-adversary` pass beat that parser with seven seeding shapes and then
    built a real database, seeded in every row, that the parser still called
    unseeded.  These tests run the shape that broke it hardest -- `ADD COLUMN
    ... DEFAULT 100`, which writes a value into every existing row without any
    UPDATE or INSERT anywhere -- against the replacement.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("census")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)
        self.character = self.store.create_character(
            self.account_id, "CensusChar", "censuschar",
            "fingerprint-census", _build_wire, self.home,
        )
        _unseed(self.path, self.character.id)

    def test_the_census_reads_zero_over_a_row_that_holds_nothing(self):
        """RENAMED, and the old name is the finding.

        It was `test_the_repository_as_it_stands_has_seeded_nothing` -- the
        exact sentence a round file would quote.  Once chief's plug lands
        (COO-DECISION 20260902_0443 route KHO) the repository DOES seed, on
        the very character this fixture creates, and `_unseed` erases it so
        the assertion keeps passing.  A `pf-adversary` pass measured that:
        before `_unseed` runs, all three `*_seeded_any` read 1.  The test is
        still worth having -- the census must read zero over an empty row --
        but it is about a ROW this test built, not about the repository.
        """
        census = self.store.vitals_seeding_census()
        self.assertEqual(census["characters_any"], 1)
        self.assertEqual(census["characters_live"], 1)
        self.assertEqual(census["database"], str(self.path))
        for column in vitals.VITAL_COLUMNS:
            self.assertEqual(census[column + "_seeded_any"], 0, column)
            self.assertEqual(census[column + "_seeded_live"], 0, column)

    def test_a_default_on_add_column_seeds_every_row_and_is_counted(self):
        # The shape 006's own header invites ("a rename is a later, cheap
        # migration") and the shape the text parser could not see at all.
        with raw(self.path) as db:
            db.execute(
                "ALTER TABLE characters RENAME COLUMN hp_current "
                "TO hp_current_old")
            db.execute(
                "ALTER TABLE characters ADD COLUMN hp_current INTEGER "
                "DEFAULT 100")
        census = self.store.vitals_seeding_census()
        self.assertEqual(census["hp_current_seeded_any"], 1)
        self.assertEqual(census["hp_current_seeded_live"], 1)
        self.assertEqual(census["level_seeded_any"], 0)

    def test_a_plain_update_is_counted(self):
        self.store.write_typed_attributes(self.character.id, {"level": 3})
        self.assertEqual(
            self.store.vitals_seeding_census()["level_seeded_any"], 1)

    def test_a_seeded_row_stays_visible_after_it_is_soft_deleted(self):
        # THE DEFECT THIS TEST EXISTS FOR.  The first version of this method
        # carried `WHERE deleted_at IS NULL` and this same setup asserted
        # `level_seeded == 0` -- a test that pinned the blindness as correct.
        # A `pf-adversary` pass read it the right way round: a report whose
        # whole job is to say "nothing has been seeded" must not be able to
        # say that over a row holding a seeded value, and 004 keeps
        # soft-deleted rows forever, so it was a permanent wrong answer.
        self.store.write_typed_attributes(
            self.character.id, {"level": 3, "hp_current": 5, "hp_max": 5})
        sid = self.store.open_session(self.account_id)
        self.store.soft_delete_character(sid, self.character.selector)
        census = self.store.vitals_seeding_census()
        self.assertEqual(census["characters_live"], 0)
        self.assertEqual(census["characters_any"], 1)
        self.assertEqual(census["level_seeded_live"], 0)
        self.assertEqual(census["level_seeded_any"], 1)

    def test_the_two_counts_disagree_exactly_when_a_seeded_row_is_deleted(self):
        # Scenario B of the adversary report: one seeded-then-deleted
        # character and one fresh one.  The live counts alone read as "one
        # character, nothing seeded"; the `_any` counts sit beside them.
        self.store.write_typed_attributes(
            self.character.id, {"level": 9, "hp_current": 50, "hp_max": 50})
        sid = self.store.open_session(self.account_id)
        self.store.soft_delete_character(sid, self.character.selector)
        fresh = self.store.create_character(
            self.account_id, "FreshChar", "freshchar", "fingerprint-fresh",
            _build_wire, self.home,
        )
        _unseed(self.path, fresh.id)
        census = self.store.vitals_seeding_census()
        self.assertEqual(census["characters_live"], 1)
        self.assertEqual(census["characters_any"], 2)
        self.assertEqual(census["level_seeded_live"], 0)
        self.assertEqual(census["level_seeded_any"], 1)

    def test_the_census_names_the_drift_instead_of_raising_a_raw_sqlite_error(self):
        with raw(self.path) as db:
            db.execute(
                "ALTER TABLE characters RENAME COLUMN hp_max TO hp_ceiling")
        with self.assertRaises(vitals.SchemaDriftError) as caught:
            self.store.vitals_seeding_census()
        self.assertIn("hp_max", str(caught.exception))


class SchemaDriftTests(unittest.TestCase):
    """A rename that happens only in SQL is invisible to `_verify_binding`
    (it reads python tables and never opens a database).  `verify_schema` is
    the half that needs a connection, and the store methods call it -- so the
    drift arrives as this module's own named error rather than as a raw
    `sqlite3.OperationalError` out of a method whose contract does not
    mention one.  Measured by a `pf-adversary` pass on the shipped first
    draft, where both methods raised OperationalError."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("drift")
        self.character = self.store.create_character(
            self.account_id, "DriftChar", "driftchar", "fingerprint-drift",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        with raw(self.path) as db:
            db.execute(
                "ALTER TABLE characters RENAME COLUMN hp_current TO hp_cur")

    def test_import_time_binding_cannot_see_a_sql_only_rename(self):
        # Asserted rather than hidden: this is the limit the docstring now
        # states, and if it ever stops being true the docstring is wrong.
        vitals._verify_binding()

    def test_reading_vitals_raises_the_named_error(self):
        with self.assertRaises(vitals.SchemaDriftError) as caught:
            self.store.read_character_vitals(self.character.id)
        self.assertIn("hp_current", str(caught.exception))

    def test_applying_damage_raises_the_named_error(self):
        with self.assertRaises(vitals.SchemaDriftError):
            self.store.apply_hp_damage(self.character.id, 1)

    def test_renaming_any_column_the_methods_read_is_named_too(self):
        # THE DEFECT THIS TEST EXISTS FOR.  The first `verify_schema` checked
        # only the three vital columns, while both store methods SELECT all
        # 21 typed columns and touch id/deleted_at/updated_at.  A
        # `pf-adversary` pass renamed `speed_walk` -- the ONE rename
        # `migrations/006...sql` explicitly pre-announces, because that
        # column's name still encodes an unproven identification -- and got a
        # raw `sqlite3.OperationalError` out of both methods.  `updated_at`
        # was worse: every gate passed and the error came from the UPDATE,
        # inside the open transaction.
        for column in ("speed_walk", "mp_current", "updated_at", "deleted_at"):
            with self.subTest(column=column):
                path = Path(self.tmp.name) / ("drift_%s.sqlite3" % column)
                store = SQLiteStore(path, MIGRATIONS)
                store.migrate()
                account_id = store.ensure_account("drift-" + column)
                character = store.create_character(
                    account_id, "D" + column, "d" + column,
                    "fingerprint-" + column, _build_wire,
                    Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
                )
                with raw(path) as db:
                    db.execute(
                        "ALTER TABLE characters RENAME COLUMN %s TO %s_moved"
                        % (column, column))
                for call in (
                    lambda: store.read_character_vitals(character.id),
                    lambda: store.apply_hp_damage(character.id, 1),
                    lambda: store.vitals_seeding_census(),
                ):
                    with self.assertRaises(vitals.SchemaDriftError) as caught:
                        call()
                    self.assertIn(column, str(caught.exception))

    def test_a_view_wearing_the_table_name_is_refused_before_the_read(self):
        # `PRAGMA table_info` answers identically for a view.  A
        # `pf-adversary` pass renamed the table away, left a view of the same
        # name, and got three plausible numbers out of the read and
        # `cannot modify characters because it is a view` out of the write.
        path = Path(self.tmp.name) / "view.sqlite3"
        store = SQLiteStore(path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("view")
        character = store.create_character(
            account_id, "ViewChar", "viewchar", "fingerprint-view",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        store.write_typed_attributes(
            character.id, {"level": 1, "hp_current": 80, "hp_max": 100})
        with raw(path) as db:
            db.execute("ALTER TABLE characters RENAME TO characters_real")
            db.execute(
                "CREATE VIEW characters AS SELECT * FROM characters_real")
        for call in (
            lambda: store.read_character_vitals(character.id),
            lambda: store.apply_hp_damage(character.id, 1),
            lambda: store.vitals_seeding_census(),
        ):
            with self.assertRaises(vitals.SchemaDriftError) as caught:
                call()
            self.assertIn("view", str(caught.exception))

    def test_a_database_that_is_not_a_pirate_force_database_is_named_as_such(self):
        path = Path(self.tmp.name) / "empty.sqlite3"
        store = SQLiteStore(path, MIGRATIONS)
        with self.assertRaises(vitals.SchemaDriftError) as caught:
            store.vitals_seeding_census()
        self.assertIn("no `characters` object", str(caught.exception))

    def test_the_named_error_is_still_a_vitals_error(self):
        # A caller written to the documented contract catches VitalsError.
        self.assertTrue(issubclass(vitals.SchemaDriftError, vitals.VitalsError))


class StoreVitalsTests(unittest.TestCase):
    """Against a real migrated database, with a real character row."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 10.0, 20.0, 30.0, heading=0.0)
        self.account_id = self.store.ensure_account("vitals")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "VitalsChar", "vitalschar",
            "fingerprint-vitals", _build_wire, self.home,
        )
        _unseed(self.path, self.character.id)
        self.store.select_character(self.sid, self.character.selector)

    def _hp_on_disk(self):
        with raw(self.path) as db:
            return db.execute(
                "SELECT hp_current,hp_max,level FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()

    def _seed(self, level=5, hp_current=80, hp_max=120):
        self.store.write_typed_attributes(self.character.id, {
            "level": level, "hp_current": hp_current, "hp_max": hp_max,
        })

    # -- rows whose vitals columns are NULL ----------------------------------
    # NOT "the unseeded database this repository actually has today", which is
    # what this line said until a `pf-adversary` pass pointed out that
    # `_unseed` in `setUp` manufactures the state, and that chief's plug ends
    # it for created characters.  The tests below are about a row, not a
    # repository.

    def test_a_row_holding_nothing_has_three_gaps_and_no_numbers(self):
        """RENAMED for the same reason: post-plug a freshly CREATED character
        has zero gaps.  What this grades is a row whose columns are NULL,
        which `_unseed` in `setUp` now guarantees explicitly."""
        resolution = self.store.read_character_vitals(self.character.id)
        self.assertFalse(resolution.complete)
        self.assertEqual(
            {gap.reason for gap in resolution.gaps},
            {vitals.REASON_NOT_SEEDED},
        )
        self.assertEqual(self._hp_on_disk(), (None, None, None))

    def test_damage_on_an_unseeded_row_refuses_and_writes_nothing(self):
        before = self._hp_on_disk()
        with self.assertRaises(vitals.VitalsError) as caught:
            self.store.apply_hp_damage(self.character.id, 10)
        self.assertIn("hp_current", str(caught.exception))
        self.assertEqual(self._hp_on_disk(), before)

    # -- seeded, which is what a later migration will make normal ------------

    def test_seeded_vitals_resolve_and_survive_a_reopen(self):
        self._seed()
        reopened = SQLiteStore(self.path, MIGRATIONS)
        state = reopened.read_character_vitals(self.character.id).require()
        self.assertEqual((state.level, state.hp_current, state.hp_max),
                         (5, 80, 120))

    def test_damage_lands_on_disk_and_survives_a_reopen(self):
        self._seed()
        outcome = self.store.apply_hp_damage(self.character.id, 30)
        self.assertEqual((outcome.hp_before, outcome.hp_after), (80, 50))
        self.assertEqual(self._hp_on_disk()[0], 50)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_character_vitals(self.character.id).require().hp_current,
            50,
        )

    def test_a_killing_blow_stops_at_zero_and_says_so(self):
        self._seed(hp_current=20, hp_max=120)
        outcome = self.store.apply_hp_damage(self.character.id, 500)
        self.assertTrue(outcome.died)
        self.assertEqual(self._hp_on_disk()[0], 0)

    def test_hitting_the_corpse_again_changes_nothing_on_disk(self):
        self._seed(hp_current=1, hp_max=120)
        self.store.apply_hp_damage(self.character.id, 1)
        with raw(self.path) as db:
            stamp = db.execute(
                "SELECT updated_at FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()[0]
        outcome = self.store.apply_hp_damage(self.character.id, 99)
        self.assertTrue(outcome.was_already_zero)
        self.assertFalse(outcome.died)
        with raw(self.path) as db:
            after = db.execute(
                "SELECT updated_at FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()[0]
        self.assertEqual(stamp, after)
        self.assertEqual(self._hp_on_disk()[0], 0)

    def test_damage_never_touches_the_other_typed_columns(self):
        self._seed()
        self.store.write_typed_attributes(
            self.character.id, {"cash": 1234, "speed_walk": 400.0})
        self.store.apply_hp_damage(self.character.id, 10)
        state = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(state["cash"], 1234)
        self.assertEqual(state["speed_walk"], 400.0)
        self.assertEqual(state["level"], 5)

    # -- what SQLite itself cannot catch, measured ---------------------------

    def test_the_database_really_does_accept_current_above_maximum(self):
        # This is why `consistency_gaps` exists.  006 writes one CHECK per
        # column and no CHECK can see two columns at once, so the repository's
        # own writer stores this state without complaint -- and the read path
        # is the only thing between it and a caller.
        self.store.write_typed_attributes(
            self.character.id, {"level": 1, "hp_current": 500, "hp_max": 100})
        self.assertEqual(self._hp_on_disk()[:2], (500, 100))
        resolution = self.store.read_character_vitals(self.character.id)
        self.assertEqual(
            [gap.reason for gap in resolution.gaps],
            [vitals.REASON_HP_ABOVE_MAX],
        )
        with self.assertRaises(vitals.VitalsError):
            self.store.apply_hp_damage(self.character.id, 1)

    def test_the_database_really_does_accept_a_zero_maximum(self):
        self.store.write_typed_attributes(
            self.character.id, {"level": 1, "hp_current": 0, "hp_max": 0})
        self.assertEqual(self._hp_on_disk()[:2], (0, 0))
        self.assertEqual(
            [gap.reason
             for gap in self.store.read_character_vitals(self.character.id).gaps],
            [vitals.REASON_HP_MAX_ZERO],
        )

    # -- the guards every store method of this lane carries ------------------

    def test_a_character_that_does_not_exist_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.store.read_character_vitals(999999)
        with self.assertRaises(KeyError):
            self.store.apply_hp_damage(999999, 1)

    def test_a_soft_deleted_character_raises_keyerror(self):
        self._seed()
        self.store.close_session(self.sid)
        deleter = self.store.open_session(self.account_id)
        self.store.soft_delete_character(deleter, self.character.selector)
        with self.assertRaises(KeyError):
            self.store.read_character_vitals(self.character.id)
        with self.assertRaises(KeyError):
            self.store.apply_hp_damage(self.character.id, 1)
        # and the row's HP is untouched by the refusal
        self.assertEqual(self._hp_on_disk()[0], 80)

    def test_the_two_pre_existing_typed_attribute_methods_still_answer(self):
        # NOT a proof that no existing method changed -- a `pf-adversary` pass
        # was right that two method calls cannot carry that claim.  What
        # carries it is the diff of the round, read for `store.py`.
        #
        # The number that used to stand here -- "91 insertions, 0 deletions in
        # store.py" -- was removed because a fourth `pf-adversary` pass could
        # not re-derive it at ANY commit of this lane: the round that
        # introduced it recorded 193/0 in its own message, the next round to
        # touch `store.py` was 17/7, and on THIS round the file is untouched
        # (`git diff --numstat e318b37e..HEAD -- src/pirateforce_foundation/
        # store.py` is empty).  A figure nobody can reproduce is worse than
        # none, because it reads as evidence.  This test only pins the two
        # methods the new ones are built on top of.
        self._seed()
        self.assertEqual(
            self.store.read_typed_attributes(self.character.id),
            {"level": 5, "hp_current": 80, "hp_max": 120},
        )
        self.assertEqual(
            self.store.write_typed_attributes(
                self.character.id, {"level": 6}),
            {"level": 6, "hp_current": 80, "hp_max": 120},
        )


class NothingIsWiredTests(unittest.TestCase):
    """The honest half: this round changed nothing anybody can see."""

    #: The files that MAY name these methods: the two modules that define
    #: them, and this lane's own tests for them.  **FULL REPOSITORY-RELATIVE
    #: PATHS, and the match is on the whole path, not on the basename.**
    #:
    #: A `pf-adversary` pass broke the basename spelling of this list twice in
    #: a row and it is worth writing down what it did, because the hole is not
    #: obvious: with `path.name in ALLOWED`, a new file at
    #: `src/pirateforce_foundation/gm/store.py` whose body is
    #: `store.apply_hp_damage(character_id, amount)` -- a real GM-side wiring,
    #: in `src/`, on a live path -- walks straight past this scan, because its
    #: BASENAME is `store.py`.  Same for `tools/persistence_vitals.py`.  Both
    #: were built and both left this test green.  `src/pirateforce_foundation/
    #: gm/` is a directory another lane writes in every round, so that is not
    #: a hypothetical filename.
    #:
    #: A file joins this tuple only together with the round file that says why.
    ALLOWED_TO_NAME_THEM = (
        "src/pirateforce_foundation/store.py",
        "src/pirateforce_foundation/persistence_vitals.py",
        "tests/test_persistence_vitals.py",
        # LANE-DB round 4m48tf: `migrations/007_character_vitals_seed.sql`
        # is graded through `read_character_vitals` and
        # `vitals_seeding_census` (COO-DECISION 20260902_0250 conditions 1
        # and 2 require exactly that), so this lane's own test file for it
        # names them.  A test exercising the method is not a wiring.
        "tests/test_persistence_vitals_seed_007.py",
    )

    def test_no_call_site_outside_this_lane_calls_either_new_method(self):
        # Scans every python tree in the repository, not just `src/`: a
        # `pf-adversary` pass pointed out that the first version looked only
        # at `src/` while `tools/`, `scenarios/`, `current/` and `tests/` can
        # all call a store method too.
        self.assertIn(
            str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
            self.ALLOWED_TO_NAME_THEM,
        )
        # EVERY `.py` UNDER THE REPOSITORY ROOT, not a list of directories.
        #
        # The list this replaced named seven trees and `continue`d silently
        # over any that did not exist -- and two of the seven do not
        # (`scenarios/` is absent, `drafts/` holds no python), which nothing
        # counted or pinned.  A third `pf-adversary` pass walked through the
        # hole twice: a real caller at `wire_probe_root.py` in the repository
        # ROOT, and another under a new top-level `docs_scripts/`, both left
        # this test green.  A silent skip over a stale pin, in the one test
        # whose whole job is to say nobody calls these methods -- and the
        # headline of this file claimed it scanned the repository.
        #
        # `.git` is excluded because it holds no source this claim is about;
        # everything else is walked, so a directory added next year joins the
        # scan by existing rather than by somebody remembering this list.
        callers = []
        for path in sorted(ROOT.rglob("*.py")):
            relative = str(path.relative_to(ROOT)).replace("\\", "/")
            if relative.startswith(".git/"):
                continue
            if relative in self.ALLOWED_TO_NAME_THEM:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(
                    r"\b(apply_hp_damage|read_character_vitals|"
                    r"vitals_seeding_census)\b", text):
                callers.append(relative)
        self.assertEqual(
            [], callers,
            "something now calls the vitals store methods (%r).  That is not "
            "forbidden -- it means this test's claim, and the round file's "
            "'wired to nothing', are out of date and must be rewritten."
            % (callers,),
        )

    def test_every_allowed_file_exists_and_really_names_them(self):
        """The allowlist cannot rot into a licence.  An entry that no longer
        matches a file, or matches one that does not mention these methods at
        all, is a hole someone can drop a real caller into.

        Every entry is resolved as ONE exact path.  The first version of this
        test used `ROOT.rglob(name)` and `any(...)` over the matches, which
        made it useless against the defect it was written for: the real
        `src/pirateforce_foundation/store.py` satisfied the `any()` for a
        decoy `store.py` anywhere else in the tree.  `any()` over a set that
        the attacker can add to is not a check.
        """
        for relative in self.ALLOWED_TO_NAME_THEM:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertTrue(
                re.search(
                    r"\b(apply_hp_damage|read_character_vitals|"
                    r"vitals_seeding_census)\b",
                    path.read_text(encoding="utf-8", errors="replace")),
                "%s is excused from the scan but names none of the methods; "
                "it is a hole, not an exception" % relative,
            )

    #: Paths that share a BASENAME with an allowlisted file but are not it.
    #: A file named `store.py` under `src/pirateforce_foundation/gm/` -- a
    #: directory another lane writes in every round -- calling
    #: `apply_hp_damage` is a real wiring of this lane's method on a live
    #: path, and under a basename allowlist it was invisible.
    DECOYS = (
        "src/pirateforce_foundation/gm/store.py",
        "tools/persistence_vitals.py",
        "tests/gm/test_persistence_vitals.py",
    )

    def _scan_for_callers(self):
        """The scan above, as data, so a test can drive it over a real tree.

        `test_no_call_site_outside_this_lane_calls_either_new_method` is the
        caller that asserts; this is the same walk with the assertion taken
        off, and both go through it so neither can drift from the other.
        """
        callers = []
        for path in sorted(ROOT.rglob("*.py")):
            relative = str(path.relative_to(ROOT)).replace("\\", "/")
            if relative.startswith(".git/"):
                continue
            if relative in self.ALLOWED_TO_NAME_THEM:
                continue
            if re.search(
                    r"\b(apply_hp_damage|read_character_vitals|"
                    r"vitals_seeding_census)\b",
                    path.read_text(encoding="utf-8", errors="replace")):
                callers.append(relative)
        return callers

    def test_a_real_decoy_dropped_into_the_tree_is_caught_by_the_scan(self):
        """THE SCAN IS RUN, over a decoy that really exists on disk.

        The version this replaces asserted two things about the ALLOWLIST
        TUPLE and never touched the loop, never created a file, never ran the
        scan -- while its docstring said it "asserts the scan's matching rule
        directly, so the hole cannot come back through a later
        'simplification'".  A fourth `pf-adversary` pass reverted the loop to
        the basename rule -- the exact regression of round `4m48tf` -- and
        this test stayed green while a live `gm/store.py` wiring went
        invisible.

        So each decoy is written, scanned for, and removed.  Under the
        basename rule every one of them is missed and this goes red.
        """
        for decoy in self.DECOYS:
            path = ROOT / decoy
            existed = path.exists()
            self.assertFalse(
                existed, "%s exists; this test would overwrite it" % decoy)
            path.parent.mkdir(parents=True, exist_ok=True)
            created = [p for p in path.parents
                       if p != ROOT and not p.exists()]
            path.write_text(
                "store.apply_hp_damage(1, 1)\n", encoding="utf-8")
            try:
                self.assertIn(
                    decoy, self._scan_for_callers(),
                    "a real caller at %s was not seen by the scan; the "
                    "matching rule is not full-path" % decoy)
            finally:
                path.unlink()
                for parent in created:
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()

    def test_the_decoys_still_share_a_basename_with_an_allowed_entry(self):
        """The decoys only test anything while they collide by basename."""
        for decoy in self.DECOYS:
            self.assertNotIn(decoy, self.ALLOWED_TO_NAME_THEM, decoy)
            self.assertTrue(
                any(decoy.endswith("/" + Path(allowed).name)
                    for allowed in self.ALLOWED_TO_NAME_THEM),
                "%s no longer shares a basename with any allowed entry, so it "
                "no longer tests anything" % decoy,
            )


class BeginImmediateHoldsTheWriteLockTests(unittest.TestCase):
    """`apply_hp_damage`'s `BEGIN IMMEDIATE` is a real safety property, and
    this is the test that fails without it.

    A `pf-adversary` pass deleted the line and ran 8 threads x 60 hits of 1
    damage at one character: 232 of the 480 hits vanished (hp 99752 instead of
    99520) and surfaced as `KeyError`, which the method's own contract says
    means "no such character".  That measurement is not a test -- it is
    thread-timing, and a flaky test on the Windows gate costs a whole round.

    So the property is tested DETERMINISTICALLY instead, by asserting the
    thing `BEGIN IMMEDIATE` actually does: it takes the database's write lock
    at the start of the transaction, before the SELECT, so a second
    connection cannot write to `characters` at all while this method is
    between its read and its write.  With the line deleted the transaction is
    deferred, the second connection's write succeeds, and this test fails.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("lock")
        self.character = self.store.create_character(
            self.account_id, "LockChar", "lockchar", "fingerprint-lock",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 100, "hp_max": 100,
        })

    def _outsider(self):
        db = sqlite3.connect(self.path, timeout=0.2)
        self.addCleanup(db.close)
        return db

    def test_an_outside_writer_is_locked_out_during_the_whole_call(self):
        seen = {}
        real_resolve = vitals.resolve

        def resolve_and_probe(stored):
            # Runs INSIDE the method's transaction, after its SELECT and
            # before its UPDATE -- the exact window the lock exists for.
            outsider = self._outsider()
            try:
                outsider.execute(
                    "UPDATE characters SET hp_current=1 WHERE id=?",
                    (self.character.id,),
                )
                outsider.commit()
                seen["outsider_wrote"] = True
            except sqlite3.OperationalError as error:
                seen["outsider_wrote"] = False
                seen["error"] = str(error)
            return real_resolve(stored)

        with mock.patch.object(vitals, "resolve", resolve_and_probe):
            outcome = self.store.apply_hp_damage(self.character.id, 10)

        self.assertFalse(
            seen.get("outsider_wrote"),
            "a second connection wrote to characters while apply_hp_damage "
            "was between its SELECT and its UPDATE: BEGIN IMMEDIATE is not "
            "holding the write lock, and a hit can be lost",
        )
        self.assertIn("locked", seen.get("error", ""))
        self.assertEqual(outcome.hp_after, 90)
        with raw(self.path) as db:
            self.assertEqual(
                db.execute("SELECT hp_current FROM characters WHERE id=?",
                           (self.character.id,)).fetchone()[0],
                90,
            )

    def test_a_lost_write_would_not_be_reported_as_a_missing_character(self):
        # The second half of the same defect: if the guarded UPDATE ever
        # matches nothing while the row is still there, saying `KeyError`
        # tells the caller the character is gone.  Forced here by moving the
        # value the method thinks it read.
        real_apply = vitals.apply_damage

        def apply_and_lie(hp_current, hp_max, amount):
            outcome = real_apply(hp_current, hp_max, amount)
            return vitals.DamageOutcome(
                hp_before=outcome.hp_before + 5,  # never matches the row
                hp_after=outcome.hp_after,
                hp_max=outcome.hp_max,
                requested=outcome.requested,
                applied=outcome.applied,
                died=outcome.died,
                was_already_zero=outcome.was_already_zero,
            )

        with mock.patch.object(vitals, "apply_damage", apply_and_lie):
            with self.assertRaises(vitals.VitalsError) as caught:
                self.store.apply_hp_damage(self.character.id, 10)
        self.assertIn("matched no row", str(caught.exception))
        self.assertIn("NOT applied", str(caught.exception))


class ImportTimeGuardTests(unittest.TestCase):
    """`_verify_binding()` is called at import.  A `pf-adversary` pass deleted
    that call and every test stayed green, because the other tests call the
    function by hand -- so the guard's whole point (a stale binding stops the
    process at import, not at the first hit) had no coverage at all."""

    def test_importing_the_module_with_a_drifted_table_raises(self):
        import importlib
        from pirateforce_foundation.gm import attr_wire

        drifted = dict(attr_wire.BY_X)
        row = list(drifted[4])
        row[6] = "hp_ceiling"
        drifted[4] = tuple(row)
        with mock.patch.object(attr_wire, "BY_X", drifted):
            # `ValueError`, not `vitals.VitalsError`: a reload builds a NEW
            # exception class, and the name captured before the reload is the
            # OLD one, which the new raise is not an instance of.  Measured --
            # the first version of this test failed for exactly that reason.
            # `VitalsError` is a `ValueError`, so this still cannot pass on a
            # different exception, and the message is pinned below.
            with self.assertRaises(ValueError) as caught:
                importlib.reload(vitals)
        self.assertIn("binding is stale", str(caught.exception))
        # and the module is restored for every test that runs after this one
        importlib.reload(vitals)
        self.assertEqual(vitals.VITAL_COLUMNS,
                         ("level", "hp_current", "hp_max"))


if __name__ == "__main__":
    unittest.main()
