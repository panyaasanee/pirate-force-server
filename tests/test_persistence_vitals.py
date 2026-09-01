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
   Measured against a real database: every character in it today has three
   NULL vitals, ``read_character_vitals`` reports three named gaps, and
   ``apply_hp_damage`` refuses and writes nothing.
2. **The cross-column rules SQLite cannot express are enforced somewhere.**
   ``006`` writes one CHECK per column, so ``hp_current > hp_max`` and a zero
   maximum pass the database happily.  Proved by storing exactly those states
   through the repository's own writer and watching the read path refuse them.
3. **Damage arithmetic has no way to produce a wrong number.**  Overkill is
   clamped and REPORTED (``requested`` vs ``applied``), a negative amount is
   refused rather than healing, ``True`` is not one point of damage, and the
   floor is zero.
4. **Nothing is seeded and nothing is wired.**  Asserted rather than promised,
   by parsing the migrations directory and the module's own source.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no frame is
composed, nothing is sent, and no call site in this repository calls either
new store method.  A player cannot be hit in the game because of this file.
It is wire/DB evidence only, and it has never run against the owner's
canonical database.
"""
import ast
import contextlib
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MODULE = ROOT / "src" / "pirateforce_foundation" / "persistence_vitals.py"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


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

    def test_the_repository_as_it_stands_has_seeded_nothing(self):
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
        self.store.create_character(
            self.account_id, "FreshChar", "freshchar", "fingerprint-fresh",
            _build_wire, self.home,
        )
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

    # -- the unseeded database this repository actually has today ------------

    def test_a_fresh_character_has_three_gaps_and_no_numbers(self):
        resolution = self.store.read_character_vitals(self.character.id)
        self.assertFalse(resolution.complete)
        self.assertEqual(
            {gap.reason for gap in resolution.gaps},
            {vitals.REASON_NOT_SEEDED},
        )
        self.assertEqual(self._hp_on_disk(), (None, None, None))

    def test_damage_on_an_unseeded_character_refuses_and_writes_nothing(self):
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
        # was right that two method calls cannot carry that claim.  The claim
        # is carried by `git diff --numstat` on this round (91 insertions, 0
        # deletions in store.py); this test only pins the two methods the new
        # ones are built on top of.
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

    def test_no_call_site_outside_this_lane_calls_either_new_method(self):
        # Scans every python tree in the repository, not just `src/`: a
        # `pf-adversary` pass pointed out that the first version looked only
        # at `src/` while `tools/`, `scenarios/`, `current/` and `tests/` can
        # all call a store method too.
        callers = []
        trees = [ROOT / "src", ROOT / "tools", ROOT / "scenarios",
                 ROOT / "current", ROOT / "tests", ROOT / "drafts",
                 ROOT / "reports"]
        for tree in trees:
            if not tree.exists():
                continue
            for path in tree.rglob("*.py"):
                if path.name in ("store.py", "persistence_vitals.py",
                                 Path(__file__).name):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if re.search(
                        r"\b(apply_hp_damage|read_character_vitals|"
                        r"vitals_seeding_census)\b", text):
                    callers.append(str(path.relative_to(ROOT)))
        self.assertEqual(
            [], callers,
            "something now calls the vitals store methods (%r).  That is not "
            "forbidden -- it means this test's claim, and the round file's "
            "'wired to nothing', are out of date and must be rewritten."
            % (callers,),
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
