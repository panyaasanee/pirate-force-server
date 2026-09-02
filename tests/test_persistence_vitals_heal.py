"""LANE-DB: the HEALING half of M4, the mirror `apply_damage` named and this
repository did not have.

WHY THIS FILE EXISTS.  Before this round the server could take a character's
STORED HP down (`persistence_vitals.apply_damage`, and the store's damage
door over it -- named here without spelling the method, because
`tests/test_persistence_vitals.py` scans the whole repository for that
spelling to prove nothing has wired it, and a mention in prose is
indistinguishable from a call to a regex) and had no way to put it back ON
DISK.

THAT SCOPE IS NARROW ON PURPOSE.  A `pf-adversary` pass refuted the wider
sentence this file first carried: at the WIRE layer the server has already
put HP back and a human watched it happen --
`docs/FUNCTIONAL_COVERAGE.json`'s `hp_death_and_respawn` row
(`runtime_pass`) records that the dying state "ended when our own
HP_RESTORED frame arrived", and `scenarios/hp_death_hypothesis_death_
sweep.json:21` ships that step with `{"hp_current": 100}`.  That path
writes no row, so it does not survive a logout; the disk is this lane's
half and the only half this file is about.  That is not a missing convenience: the first call
site that had to raise HP -- a potion, a rest, a respawn -- would have written
its own `UPDATE characters SET hp_current = ...` at the call site, past the
consistency rules, past the u32 validation, past `BEGIN IMMEDIATE`, and past
the fail-closed refusal that keeps an unseeded row from being healed from a
guessed zero.  `apply_damage`'s own docstring already pointed at this door
("healing is not damage with a minus sign and does not go through this
function") and the door did not exist.

WHAT THIS FILE PROVES (wire/DB layer only):

1. **Healing arithmetic has no way to produce a wrong number.**  Overheal is
   clamped at `hp_max` and REPORTED (`requested` vs `applied`), a negative
   amount is refused rather than becoming damage that could land below zero,
   `True` is not one point of healing, an amount wider than the u32 the
   column holds is refused, and an inconsistent input pair cannot be
   laundered through it.
2. **The store doors write what the pure function decided, or nothing.**
   Against a real migrated database with a real character row.
3. **They are fail-closed on an unseeded character.**  A row holding no
   `hp_current` is refused, not resurrected at full.
4. **The write is not lossy under concurrency.**  `BEGIN IMMEDIATE` is the
   property, and the test dies without it.
5. **Nothing calls them** from outside the two modules that define them.
   Asserted by a scan, not promised -- and the scan's OWN blind spot is
   named in `NothingIsWiredTests` rather than left for a reader to find: a
   wiring added INSIDE `src/pirateforce_foundation/store.py` itself is
   invisible to it, because that file has to be excused for defining the
   doors.  A `pf-adversary` pass added a public `SQLiteStore.
   login_and_revive` calling `restore_hp_to_full` and the scan stayed green.
   That is the shape the round file's "wired to nothing" cannot be checked
   against by this file; it is checked by reading the diff.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no frame
is composed, nothing is sent, no player can be healed in the game because of
it.  It has never run against the owner's canonical database -- every
database here is built in a `TemporaryDirectory`.  It does not claim that
respawn is a full heal, or that a character at zero HP may be healed at all:
those are LANE-B's rules and the owner's, and this lane's doors report
`revived` instead of deciding them.
"""
import ast
import contextlib
import re
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed_attrs  # noqa: E402,E501
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.store import Position, SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402

MIGRATIONS = ROOT / "migrations"
U32_MAX = typed_attrs.KIND_STORAGE["u32"][2]


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


@contextlib.contextmanager
def raw(path):
    """A raw sqlite connection that is COMMITTED **and CLOSED**.

    Same wart, same reason as `tests/test_persistence_vitals.py`: a bare
    `with sqlite3.connect(...) as db:` commits and does not close, which is
    free on Linux and takes the Windows gate red at `TemporaryDirectory`
    cleanup.  Every raw connection in this file goes through here.
    """
    db = sqlite3.connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


class ApplyHealTests(unittest.TestCase):
    """Pure arithmetic, at the edges, with no database in sight."""

    def test_a_plain_heal_adds_exactly_what_was_asked(self):
        outcome = vitals.apply_heal(50, 100, 30)
        self.assertEqual(
            (outcome.hp_before, outcome.hp_after, outcome.hp_max), (50, 80, 100))
        self.assertEqual((outcome.requested, outcome.applied), (30, 30))
        self.assertFalse(outcome.revived)
        self.assertFalse(outcome.was_already_full)

    def test_an_overheal_is_clamped_at_the_maximum_and_reported(self):
        outcome = vitals.apply_heal(90, 100, 999)
        self.assertEqual(outcome.hp_after, 100)
        self.assertEqual((outcome.requested, outcome.applied), (999, 10))
        self.assertNotEqual(
            outcome.requested, outcome.applied,
            "an overheal that reports requested == applied is how it becomes "
            "an ordinary heal in a log",
        )

    def test_healing_a_character_who_is_already_full_applies_nothing(self):
        outcome = vitals.apply_heal(100, 100, 25)
        self.assertEqual(outcome.hp_after, 100)
        self.assertEqual(outcome.applied, 0)
        self.assertTrue(outcome.was_already_full)
        self.assertFalse(outcome.revived)

    def test_a_zero_amount_is_an_event_not_an_error(self):
        outcome = vitals.apply_heal(40, 100, 0)
        self.assertEqual(outcome.hp_after, 40)
        self.assertEqual((outcome.requested, outcome.applied), (0, 0))

    def test_healing_from_zero_is_allowed_and_reported_as_a_revival(self):
        """LANE-B decides whether a corpse may be healed; this file refuses to
        decide it by accident in either direction."""
        outcome = vitals.apply_heal(0, 100, 1)
        self.assertEqual(outcome.hp_after, 1)
        self.assertTrue(outcome.revived)

    def test_a_heal_that_lands_on_a_still_zero_bar_is_not_a_revival(self):
        outcome = vitals.apply_heal(0, 100, 0)
        self.assertEqual(outcome.hp_after, 0)
        self.assertFalse(
            outcome.revived,
            "a zero-point heal on a dead character reported as a revival "
            "would tell a caller to stand a corpse back up",
        )

    def test_a_negative_amount_is_refused_rather_than_becoming_damage(self):
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.apply_heal(50, 100, -10)
        self.assertIn("negative", str(caught.exception))

    def test_true_is_not_one_point_of_healing(self):
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.apply_heal(50, 100, True)
        self.assertIn("bool", str(caught.exception))

    def test_a_float_amount_is_refused(self):
        with self.assertRaises(vitals.VitalsError):
            vitals.apply_heal(50, 100, 1.5)

    def test_an_amount_wider_than_the_column_is_refused(self):
        vitals.apply_heal(50, 100, U32_MAX)
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.apply_heal(50, 100, U32_MAX + 1)
        self.assertIn("wider", str(caught.exception))

    def test_an_inconsistent_pair_cannot_be_laundered_through_healing(self):
        for current, maximum in ((120, 100), (5, 0)):
            with self.subTest(current=current, maximum=maximum):
                with self.assertRaises(vitals.VitalsError):
                    vitals.apply_heal(current, maximum, 1)

    def test_the_outcome_is_frozen(self):
        outcome = vitals.apply_heal(50, 100, 10)
        with self.assertRaises(Exception):
            outcome.hp_after = 999

    def test_a_heal_outcome_is_not_a_damage_outcome(self):
        """Two structs on purpose.  One struct whose sign carries the meaning
        is how a heal ends up counted as a hit."""
        self.assertIsNot(vitals.HealOutcome, vitals.DamageOutcome)
        self.assertNotIsInstance(
            vitals.apply_heal(50, 100, 10), vitals.DamageOutcome)


class HealToFullTests(unittest.TestCase):
    def test_it_fills_the_whole_missing_bar(self):
        outcome = vitals.heal_to_full(30, 100)
        self.assertEqual(outcome.hp_after, 100)
        self.assertEqual((outcome.requested, outcome.applied), (70, 70))

    def test_from_zero_it_is_a_revival(self):
        outcome = vitals.heal_to_full(0, 250)
        self.assertEqual(outcome.hp_after, 250)
        self.assertTrue(outcome.revived)

    def test_on_a_full_bar_it_asks_for_nothing(self):
        outcome = vitals.heal_to_full(100, 100)
        self.assertEqual((outcome.requested, outcome.applied), (0, 0))
        self.assertTrue(outcome.was_already_full)

    def test_it_refuses_an_inconsistent_pair_naming_THAT_pair(self):
        """Asserting the exception CLASS alone was not a test.

        Measured by `pf-adversary`: delete this function's own validation and
        `heal_to_full(120, 100)` still raises `VitalsError` -- but for the
        wrong reason, complaining about "heal amount -20 is negative", an
        amount no caller passed in.  The class was identical, so the class
        was not the evidence.  These assert the REASON.
        """
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.heal_to_full(120, 100)
        message = str(caught.exception)
        self.assertIn("hp_current_above_hp_max", message)
        self.assertNotIn(
            "negative", message,
            "a negative amount reported here means the subtraction ran "
            "before the check, which is the whole defect",
        )

    def test_a_zero_maximum_is_named_as_a_zero_maximum(self):
        with self.assertRaises(vitals.VitalsError) as caught:
            vitals.heal_to_full(5, 0)
        self.assertIn("hp_max", str(caught.exception))
        self.assertNotIn("negative", str(caught.exception))

    def test_a_non_integer_pair_raises_VitalsError_and_never_TypeError(self):
        """The contract escape the same pass found: without this function's
        own coercion the subtraction runs first and raises `TypeError`, an
        exception class nothing in this module's contract mentions and no
        caller of it is written to catch."""
        for current, maximum in (("50", 100), (50, "100"), (None, 100)):
            with self.subTest(current=current, maximum=maximum):
                with self.assertRaises(vitals.VitalsError):
                    vitals.heal_to_full(current, maximum)

    def test_at_the_u32_ceiling_a_full_heal_is_not_refused_as_too_wide(self):
        """`apply_heal` refuses an amount WIDER than the column; the derived
        amount can reach the ceiling exactly.  A strict `>` is what keeps the
        biggest legitimate full heal from raising, and `>=` would break it."""
        ceiling = U32_MAX
        outcome = vitals.heal_to_full(0, ceiling)
        self.assertEqual(outcome.requested, ceiling)
        self.assertEqual(outcome.hp_after, ceiling)

    def test_it_never_hands_apply_heal_a_negative_amount(self):
        for current in range(0, 101, 10):
            with self.subTest(current=current):
                self.assertGreaterEqual(
                    vitals.heal_to_full(current, 100).requested, 0)


class StoreHealTests(unittest.TestCase):
    """Against a real migrated database, with a real character row."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 10.0, 20.0, 30.0, heading=0.0)
        self.account_id = self.store.ensure_account("heal")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "HealChar", "healchar",
            "fingerprint-heal", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)
        # Measured, then CLEARED, for the reason `tests/pf_birth_state.py`
        # gives: the fail-closed tests below are about a row that holds no
        # vital, and once birth seeding lands this is the only way to reach
        # that state.  The measurement refuses any birth state this lane does
        # not accept, so clearing cannot hide a wrong insertion point.
        self.birth = birth_state.measure_birth_typed_state(
            self.store, self.character.id)
        birth_state.clear_vitals_to_pre_seed(self.path, [self.character.id])

    def _hp_on_disk(self, character_id=None):
        with raw(self.path) as db:
            return db.execute(
                "SELECT hp_current,hp_max FROM characters WHERE id=?",
                (self.character.id if character_id is None else character_id,),
            ).fetchone()

    def _seed(self, level=5, hp_current=40, hp_max=120, character_id=None):
        self.store.write_typed_attributes(
            self.character.id if character_id is None else character_id,
            {"level": level, "hp_current": hp_current, "hp_max": hp_max},
        )

    # -- the happy paths, on disk -------------------------------------------

    def test_a_heal_reaches_the_row(self):
        self._seed()
        outcome = self.store.apply_hp_heal(self.character.id, 30)
        self.assertEqual(outcome.applied, 30)
        self.assertEqual(self._hp_on_disk(), (70, 120))

    def test_an_overheal_stores_the_maximum_and_not_the_request(self):
        self._seed(hp_current=110, hp_max=120)
        outcome = self.store.apply_hp_heal(self.character.id, 500)
        self.assertEqual((outcome.requested, outcome.applied), (500, 10))
        self.assertEqual(self._hp_on_disk(), (120, 120))

    def test_restore_to_full_uses_this_character_s_own_maximum(self):
        self._seed(hp_current=1, hp_max=333)
        outcome = self.store.restore_hp_to_full(self.character.id)
        self.assertEqual(outcome.applied, 332)
        self.assertEqual(self._hp_on_disk(), (333, 333))

    def test_restore_to_full_from_zero_is_a_revival_on_disk(self):
        self._seed(hp_current=0, hp_max=200)
        outcome = self.store.restore_hp_to_full(self.character.id)
        self.assertTrue(outcome.revived)
        self.assertEqual(self._hp_on_disk(), (200, 200))

    def test_restoring_a_full_character_writes_nothing_at_all(self):
        self._seed(hp_current=120, hp_max=120)
        with raw(self.path) as db:
            before = db.execute(
                "SELECT updated_at FROM characters WHERE id=?",
                (self.character.id,)).fetchone()[0]
        outcome = self.store.restore_hp_to_full(self.character.id)
        self.assertTrue(outcome.was_already_full)
        with raw(self.path) as db:
            after = db.execute(
                "SELECT updated_at FROM characters WHERE id=?",
                (self.character.id,)).fetchone()[0]
        self.assertEqual(
            before, after,
            "a no-op heal that still stamps updated_at makes every idle "
            "character look like it was touched",
        )

    def test_the_heal_survives_a_new_store_over_the_same_file(self):
        """The whole point of the lane: it is on DISK, not in a process."""
        self._seed(hp_current=10, hp_max=100)
        self.store.apply_hp_heal(self.character.id, 25)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_typed_attributes(self.character.id)["hp_current"], 35)

    # -- fail-closed --------------------------------------------------------

    def test_an_unseeded_character_is_refused_rather_than_resurrected(self):
        self.assertEqual(self._hp_on_disk(), (None, None))
        for call in (lambda: self.store.apply_hp_heal(self.character.id, 10),
                     lambda: self.store.restore_hp_to_full(self.character.id)):
            with self.subTest(call=call):
                with self.assertRaises(vitals.VitalsError):
                    call()
        self.assertEqual(
            self._hp_on_disk(), (None, None),
            "a refusal that still wrote is worse than no refusal",
        )

    def test_a_row_holding_only_a_maximum_is_still_refused(self):
        """The shape a guessed zero would rescue: `hp_max` known, current
        absent.  Healing that from a guessed zero is a resurrection built out
        of the number the owner banned."""
        self.store.write_typed_attributes(self.character.id, {"hp_max": 120})
        with self.assertRaises(vitals.VitalsError):
            self.store.restore_hp_to_full(self.character.id)
        self.assertEqual(self._hp_on_disk(), (None, 120))

    def test_a_missing_character_is_a_key_error(self):
        with self.assertRaises(KeyError):
            self.store.apply_hp_heal(999999, 10)

    def test_a_soft_deleted_character_cannot_be_healed(self):
        self._seed(hp_current=10, hp_max=100)
        # The character must be unselected before it can be deleted, and the
        # delete itself needs an OPEN session: close the one holding it and
        # open a second for the same account.
        self.store.close_session(self.sid)
        self.store.soft_delete_character(
            self.store.open_session(self.account_id), self.character.selector)
        with self.assertRaises(KeyError):
            self.store.apply_hp_heal(self.character.id, 10)
        self.assertEqual(
            self._hp_on_disk(), (10, 100),
            "the row is history behind a soft delete; healing it would edit "
            "history",
        )

    def test_a_bad_amount_is_refused_at_the_door_and_writes_nothing(self):
        self._seed(hp_current=10, hp_max=100)
        for amount in (-1, True, 1.5, U32_MAX + 1):
            with self.subTest(amount=amount):
                with self.assertRaises(vitals.VitalsError):
                    self.store.apply_hp_heal(self.character.id, amount)
        self.assertEqual(self._hp_on_disk(), (10, 100))

    def test_a_level_zero_row_refuses_healing_the_same_way_it_refuses_damage(
            self):
        """`COO-DECISION 20260902_0443` point 4 made a stored `level = 0` a
        refusal, and these doors resolve the WHOLE vitals state before they
        add anything -- so this is a deliberate consequence, pinned here so a
        caller can read it."""
        with raw(self.path) as db:
            db.execute(
                "UPDATE characters SET level=0,hp_current=10,hp_max=100 "
                "WHERE id=?", (self.character.id,))
        with self.assertRaises(vitals.VitalsError):
            self.store.apply_hp_heal(self.character.id, 10)
        self.assertEqual(self._hp_on_disk(), (10, 100))

    def test_healing_one_character_leaves_every_other_row_alone(self):
        other = self.store.create_character(
            self.account_id, "HealOther", "healother",
            "fingerprint-heal-2", _build_wire, self.home,
        )
        birth_state.measure_birth_typed_state(self.store, other.id)
        birth_state.clear_vitals_to_pre_seed(self.path, [other.id])
        self._seed(hp_current=10, hp_max=100)
        self._seed(hp_current=7, hp_max=90, character_id=other.id)
        self.store.restore_hp_to_full(self.character.id)
        self.assertEqual(self._hp_on_disk(), (100, 100))
        self.assertEqual(
            self._hp_on_disk(other.id), (7, 90),
            "a heal that reaches a second row is an UPDATE without a WHERE",
        )


class TheGuardedWriteReportsItselfTests(unittest.TestCase):
    """The `hp_current=?` predicate and the branch behind it.

    A `pf-adversary` pass deleted BOTH -- the predicate from the UPDATE and
    the `written != 1` branch that reports the miss -- and every one of this
    lane's tests stayed green, because nothing had ever forced the UPDATE to
    match no row.  A line-level trace confirmed the report branch had never
    executed once in this repository: the message `the healing was NOT
    applied` was a string nobody had ever seen printed.  These two tests are
    that hole closed.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("heal-guard")
        sid = self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "HealGuard", "healguard", "fingerprint-heal-guard",
            _build_wire, Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        self.store.select_character(sid, self.character.selector)
        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 40, "hp_max": 100,
        })

    def _lying_heal(self, real):
        """`real`, with an `hp_before` that can never match the stored row."""
        def lie(*args, **kwargs):
            outcome = real(*args, **kwargs)
            return vitals.HealOutcome(
                hp_before=outcome.hp_before + 5,
                hp_after=outcome.hp_after,
                hp_max=outcome.hp_max,
                requested=outcome.requested,
                applied=outcome.applied,
                revived=outcome.revived,
                was_already_full=outcome.was_already_full,
            )
        return lie

    def test_a_lost_heal_is_reported_as_a_lost_heal(self):
        with mock.patch.object(
                vitals, "apply_heal", self._lying_heal(vitals.apply_heal)):
            with self.assertRaises(vitals.VitalsError) as caught:
                self.store.apply_hp_heal(self.character.id, 10)
        self.assertIn("matched no row", str(caught.exception))
        self.assertIn("NOT applied", str(caught.exception))
        self.assertNotIsInstance(
            caught.exception, KeyError,
            "saying the character is gone when the write merely missed is "
            "the one lie this branch exists to avoid",
        )

    def test_a_lost_heal_writes_nothing_at_all(self):
        with mock.patch.object(
                vitals, "apply_heal", self._lying_heal(vitals.apply_heal)):
            with self.assertRaises(vitals.VitalsError):
                self.store.apply_hp_heal(self.character.id, 10)
        with raw(self.path) as db:
            stored = db.execute(
                "SELECT hp_current FROM characters WHERE id=?",
                (self.character.id,)).fetchone()[0]
        self.assertEqual(
            stored, 40,
            "the guarded predicate is what keeps a heal computed from a "
            "stale read off the row",
        )

    def test_restore_to_full_reports_its_own_lost_write_too(self):
        """Both public doors go through the same body; both are pinned, so a
        later change cannot leave one of them unmeasured."""
        with mock.patch.object(
                vitals, "heal_to_full", self._lying_heal(vitals.heal_to_full)):
            with self.assertRaises(vitals.VitalsError) as caught:
                self.store.restore_hp_to_full(self.character.id)
        self.assertIn("NOT applied", str(caught.exception))


class SchemaDriftReachesTheHealDoorsTests(unittest.TestCase):
    """`verify_schema` before the read.  Deleted, the suite stayed green: a
    database missing an HP column produced whatever the SELECT happened to do
    instead of the one error that names the drift."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("heal-drift")
        sid = self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "HealDrift", "healdrift", "fingerprint-heal-drift",
            _build_wire, Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        self.store.select_character(sid, self.character.selector)
        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 10, "hp_max": 100,
        })
        with raw(self.path) as db:
            db.execute("ALTER TABLE characters DROP COLUMN hp_max")

    def test_both_doors_name_the_drift_instead_of_guessing_around_it(self):
        for call in (lambda: self.store.apply_hp_heal(self.character.id, 5),
                     lambda: self.store.restore_hp_to_full(self.character.id)):
            with self.subTest(call=call):
                with self.assertRaises(vitals.SchemaDriftError):
                    call()


class BeginImmediateHoldsTheHealLockTests(unittest.TestCase):
    """The lost-write property, measured the way the damage path's was.

    Without `BEGIN IMMEDIATE` the read and the write are two transactions and
    concurrent heals are lost -- and, because of the guarded `hp_current=?`
    predicate, a lost heal surfaces as "the write did not land" rather than as
    a wrong number.  This test fails if the lock is removed.
    """

    THREADS = 8
    HEALS = 60

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("heal-lock")
        sid = self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "HealLock", "heallock", "fingerprint-heal-lock",
            _build_wire, Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        self.store.select_character(sid, self.character.selector)
        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 0, "hp_max": 100000,
        })

    def test_no_heal_is_lost_when_eight_threads_heal_at_once(self):
        errors = []

        def worker():
            for _ in range(self.HEALS):
                try:
                    self.store.apply_hp_heal(self.character.id, 1)
                except Exception as exc:  # noqa: BLE001 - reported, not hidden
                    errors.append(exc)

        threads = [threading.Thread(target=worker)
                   for _ in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([], [repr(e) for e in errors])
        with raw(self.path) as db:
            stored = db.execute(
                "SELECT hp_current FROM characters WHERE id=?",
                (self.character.id,)).fetchone()[0]
        self.assertEqual(stored, self.THREADS * self.HEALS)


class _RefusingConnection:
    """The smallest thing `_begin_immediate_under_contention` can be run on.

    It counts `BEGIN IMMEDIATE` attempts and can refuse a chosen number of
    them with a chosen error -- which is how the retry rule is measured
    without asking a real SQLite connection to produce an error on demand.
    """

    def __init__(self, error, refusals=None, pragma_error=None):
        self.error = error
        self.refusals = refusals
        self.pragma_error = pragma_error
        self.begins = 0
        self.pragmas = []

    def execute(self, sql, *args, **kwargs):
        if sql.startswith("PRAGMA"):
            self.pragmas.append(sql)
            if self.pragma_error is not None:
                raise self.pragma_error
            return self
        if sql.startswith("BEGIN IMMEDIATE"):
            self.begins += 1
            if self.error is not None and (
                    self.refusals is None or self.begins <= self.refusals):
                raise self.error
            return self
        raise AssertionError("unexpected statement: %r" % (sql,))


class _ContendedHealWorkspace(unittest.TestCase):
    """One character on a real file database, plus a way to hold its write
    lock from another connection for a measured length of time."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("heal-contention")
        sid = self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "Contended", "contended", "fingerprint-contended",
            _build_wire, Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        self.store.select_character(sid, self.character.selector)
        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 10, "hp_max": 100,
        })

    def _hp(self):
        with raw(self.path) as db:
            return db.execute(
                "SELECT hp_current FROM characters WHERE id=?",
                (self.character.id,)).fetchone()[0]

    @contextlib.contextmanager
    def _write_lock_held_for(self, seconds):
        """Another connection holds the database's write lock for `seconds`.

        A real `BEGIN IMMEDIATE` on a second connection, exactly what a
        concurrent heal does -- not a mock, because the thing under test is
        SQLite's own busy handler.
        """
        released = threading.Event()
        holding = threading.Event()

        def hold():
            db = sqlite3.connect(str(self.path))
            try:
                db.execute("PRAGMA busy_timeout=5000")
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "UPDATE characters SET updated_at=updated_at WHERE id=?",
                    (self.character.id,))
                holding.set()
                released.wait(seconds)
                db.rollback()
            finally:
                db.close()

        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(holding.wait(10), "the competitor never took the lock")
        try:
            yield
        finally:
            released.set()
            thread.join(20)
            self.assertFalse(thread.is_alive())

    @contextlib.contextmanager
    def _counted_sleeps(self):
        """Count the retries, by counting the waits between them.

        `store.time` is replaced with a shim rather than patching the real
        `time.sleep`, so nothing else running in this process is affected.
        """
        import time as real_time

        class _Clock:
            def __init__(self):
                self.sleeps = 0

            def monotonic(self):
                return real_time.monotonic()

            def sleep(self, seconds):
                self.sleeps += 1
                real_time.sleep(seconds)

        clock = _Clock()
        with mock.patch.object(store_module, "time", clock):
            yield clock


class ContendedHealsWaitInsteadOfStarvingTests(_ContendedHealWorkspace):
    """`COO-DECISION 20260902_1646`, and the four repairs it forbids.

    THE DEFECT IT REPAIRS IS NOT IN THE LOCK.  `BeginImmediateHoldsTheHealLock
    Tests` above proves the lock is right and still fails if it is removed.
    What was wrong is that the healing path could LOSE ON TIME: LANE-B
    measured (`pf_bridge/notes_to_chief/20260902_1642_LANE-B-TO-LANE-DB-*`) a
    thread waiting 5,054ms against `PRAGMA busy_timeout=5000` at 8 threads x
    60 heals with a ~40ms transaction, and the resulting
    `OperationalError('database is locked')` closed `server#582`, a pull
    request from another lane whose diff touched neither this file nor
    `store.py`.  SQLite's busy handler makes no fairness guarantee, so the
    5-second ceiling is a bet on machine speed, not a property.

    WHAT MAY NOT BE DONE ABOUT IT, from that letter, so a later reader does
    not undo the repair by "simplifying" it: `BEGIN IMMEDIATE` may not be
    weakened or removed, `THREADS`/`HEALS` may not be lowered, the test may
    never be skipped, xfailed or labelled flaky, and no green counts without a
    test proving no heal is lost and none is counted twice.  Those four are
    what these tests exist to keep.
    """

    def test_a_heal_survives_a_competitor_that_outlasts_the_busy_timeout(self):
        """The repair itself, measured on the RETRY rather than on the bigger
        timeout: the per-attempt ceiling is patched down to 20ms, far below
        the 300ms the competitor holds the lock, so the only thing that can
        make this heal land is the bounded retry."""
        before = self._hp()
        with mock.patch.object(store_module, "HEAL_LOCK_BUSY_TIMEOUT_MS", 20):
            with self._counted_sleeps() as clock:
                with self._write_lock_held_for(0.3):
                    outcome = self.store.apply_hp_heal(self.character.id, 5)
        self.assertGreater(clock.sleeps, 0,
                           "the heal never had to retry; this test measured "
                           "nothing about contention")
        self.assertEqual(outcome.hp_before, before)
        self.assertEqual(outcome.hp_after, before + 5)
        # ONCE, not once per attempt.  The retry is on `BEGIN IMMEDIATE`, so
        # a retried call must land exactly one heal.
        self.assertEqual(self._hp(), before + 5)

    def test_many_retries_still_apply_the_heal_exactly_once(self):
        """The write-once property under a LOT of retries, which is the half
        `COO-DECISION 20260902_1646` point 4 will not accept a green without.
        The competitor is held long enough to force many attempts."""
        before = self._hp()
        with mock.patch.object(store_module, "HEAL_LOCK_BUSY_TIMEOUT_MS", 5):
            with mock.patch.object(
                    store_module, "HEAL_LOCK_RETRY_BACKOFF_S", 0.001):
                with self._counted_sleeps() as clock:
                    with self._write_lock_held_for(0.5):
                        self.store.apply_hp_heal(self.character.id, 7)
        self.assertGreater(clock.sleeps, 2, clock.sleeps)
        self.assertEqual(self._hp(), before + 7)

    def test_when_the_budget_is_spent_it_says_so_and_writes_nothing(self):
        """The control that makes the test above mean something, and the
        error LANE-B asked for: how long it waited, instead of a bare
        `database is locked`."""
        before = self._hp()
        with mock.patch.object(store_module, "HEAL_LOCK_BUSY_TIMEOUT_MS", 5):
            with mock.patch.object(store_module, "HEAL_LOCK_TOTAL_WAIT_S", 0.0):
                with self._write_lock_held_for(0.4):
                    with self.assertRaises(
                            store_module.WriteLockTimeout) as caught:
                        self.store.apply_hp_heal(self.character.id, 5)
        message = str(caught.exception)
        self.assertIn("attempt", message)
        self.assertIn("ms", message)
        self.assertIn("busy_timeout", message)
        self.assertEqual(self._hp(), before, "a refused heal wrote anyway")

    def test_the_timeout_is_an_operational_error_so_no_caller_breaks(self):
        """A caller that already handles `sqlite3.OperationalError` keeps
        working: the new type is a subclass, not a replacement."""
        self.assertTrue(issubclass(store_module.WriteLockTimeout,
                                   sqlite3.OperationalError))

    def test_only_a_locked_database_is_retried(self):
        """Every other `OperationalError` propagates on the FIRST attempt.

        Retrying "no such table" would turn a schema defect into a two-minute
        hang, which is a worse failure than the one being repaired.  Measured
        on the helper itself with a stub connection, because
        `sqlite3.Connection.execute` is an immutable type's attribute and
        cannot be patched -- and because a stub is the only way to produce
        this error deterministically at exactly this statement.
        """
        attempts = _RefusingConnection(sqlite3.OperationalError(
            "no such table: characters"))
        with self._counted_sleeps() as clock:
            with self.assertRaises(sqlite3.OperationalError) as caught:
                SQLiteStore._begin_immediate_under_contention(attempts)
        self.assertNotIsInstance(caught.exception, store_module.WriteLockTimeout)
        self.assertEqual(attempts.begins, 1, "a non-contention error was retried")
        self.assertEqual(clock.sleeps, 0)

    def test_a_locked_database_is_retried_until_it_lets_go(self):
        """The other half of the same measurement, on the same stub: a
        `database is locked` really is retried, and the helper stops the
        moment the lock is granted."""
        connection = _RefusingConnection(
            sqlite3.OperationalError("database is locked"), refusals=3)
        with mock.patch.object(store_module, "HEAL_LOCK_RETRY_BACKOFF_S", 0.0):
            with self._counted_sleeps() as clock:
                SQLiteStore._begin_immediate_under_contention(connection)
        self.assertEqual(connection.begins, 4)
        self.assertEqual(clock.sleeps, 3)

    def test_a_table_lock_is_not_the_contention_this_retries(self):
        """The other edge of the classification, which decides whether a red
        gate is fast and named or a two-minute hang.

        `SQLITE_LOCKED` reads "database TABLE is locked" -- a different
        condition, which retrying cannot fix.  A `pf-adversary` pass measured
        the cost of widening the match to `"locked"`: this file went from
        3.97 s to 123.95 s.  One sample of one non-matching message could not
        tell those apart, so the message that is one word away from the one
        that IS retried is pinned here by name.
        """
        # The budget is cut to 50ms for this test alone.  Not to make the
        # assertion easier -- it is unchanged -- but so that a too-wide match
        # fails FAST: with the shipped 120s budget the same mutant is still
        # caught, and the same pass measured it taking 120 seconds per
        # message to say so.  A slow red on a gate that already burns 655s is
        # a worse red.
        with mock.patch.object(store_module, "HEAL_LOCK_TOTAL_WAIT_S", 0.05):
            for message in ("database table is locked",
                            "attempt to write a readonly database",
                            "no such table: characters"):
                with self.subTest(message=message):
                    connection = _RefusingConnection(
                        sqlite3.OperationalError(message))
                    with self._counted_sleeps() as clock:
                        with self.assertRaises(sqlite3.OperationalError) as e:
                            SQLiteStore._begin_immediate_under_contention(
                                connection)
                    self.assertNotIsInstance(
                        e.exception, store_module.WriteLockTimeout,
                        "this message was retried; it is not the contention "
                        "a retry can fix")
                    self.assertEqual(connection.begins, 1)
                    self.assertEqual(clock.sleeps, 0)

    def test_the_ceiling_the_helper_puts_on_the_wire_is_the_shipped_one(self):
        """What the helper actually TELLS SQLite, read off the connection.

        A `pf-adversary` pass hardcoded the pragma to 1 ms and the whole file
        stayed green, because `_RefusingConnection` recorded the statement and
        nothing ever read the recording.  This reads it.
        """
        connection = _RefusingConnection(None)
        SQLiteStore._begin_immediate_under_contention(connection)
        self.assertEqual(
            connection.pragmas,
            ["PRAGMA busy_timeout=%d" % store_module.HEAL_LOCK_BUSY_TIMEOUT_MS])

    def test_the_call_cannot_outlive_the_budget_by_a_whole_ceiling(self):
        """The budget is a bound on the CALL, not on the gaps between tries.

        Measured defect: with the ceiling set once before the loop, the last
        attempt started inside the budget and then blocked for the whole
        ceiling -- 2,006 ms against a 1,000 ms budget, with an error message
        that contradicted itself.  At the shipped numbers that was a 150 s
        bound advertised as 120 s.
        """
        with mock.patch.object(store_module, "HEAL_LOCK_TOTAL_WAIT_S", 0.4):
            with mock.patch.object(
                    store_module, "HEAL_LOCK_BUSY_TIMEOUT_MS", 5000):
                started = time.monotonic()
                with self._write_lock_held_for(3.0):
                    with self.assertRaises(store_module.WriteLockTimeout):
                        self.store.apply_hp_heal(self.character.id, 5)
                elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2.0, "the call outran its budget: %.2fs" % elapsed)

    def test_a_pragma_a_connection_refuses_does_not_stop_the_heal(self):
        """The per-path `busy_timeout` is an improvement, not a requirement.

        A connection that refuses the pragma still gets its attempts -- it
        just makes them at whatever timeout it already has.  Without this the
        helper would turn a harmless refusal into a failed heal.
        """
        connection = _RefusingConnection(None, pragma_error=sqlite3.Error("no"))
        SQLiteStore._begin_immediate_under_contention(connection)
        self.assertEqual(connection.begins, 1)

    #: The wait LANE-B measured a thread suffering before it died, in
    #: `pf_bridge/notes_to_chief/20260902_1642_LANE-B-TO-LANE-DB-*`: 8 threads
    #: x 60 heals at a ~40ms transaction, maximum wait 5,054 ms against a
    #: 5,000 ms ceiling.  Any ceiling this repository ships must be able to
    #: absorb it, so the number is quoted from the measurement rather than
    #: chosen here.
    LANE_B_MEASURED_STARVATION_MS = 5054

    def test_the_shipped_ceilings_can_absorb_the_wait_lane_b_measured(self):
        """The shipped numbers, pinned against the measurement that produced
        them rather than against themselves.

        A `pf-adversary` pass showed why this is needed: every other test in
        this class patches the two constants down to values it picks, so
        `1 ms / 0.5 s` was as green as `30000 ms / 120 s`, and a later round
        "tidying" the budget would be told nothing.  The next test runs the
        real doors at the shipped values; this one says what those values have
        to be big enough for.
        """
        self.assertGreaterEqual(store_module.HEAL_LOCK_BUSY_TIMEOUT_MS,
                                self.LANE_B_MEASURED_STARVATION_MS)
        # and the budget has to hold several such waits, or the retry cannot
        # outlast a competitor that starves this thread more than once
        self.assertGreaterEqual(store_module.HEAL_LOCK_TOTAL_WAIT_S * 1000.0,
                                self.LANE_B_MEASURED_STARVATION_MS * 4)

    def test_eight_threads_lose_no_heal_when_the_transaction_is_slow(self):
        """The original failure, reproduced through the REAL doors at the
        SHIPPED ceilings, and then measured green.

        *** WHAT THIS REPLACED AND WHY, because the replacement is the whole
        point.  The first version of this test patched
        `HEAL_LOCK_BUSY_TIMEOUT_MS` down to 25 ms to manufacture contention.
        A `pf-adversary` pass measured that it was **green with the repair
        removed**, five runs out of five: the patched constant reaches SQLite
        only through the code under test, so deleting the helper call put the
        eight threads back on `connect()`'s own 5,000 ms and nothing noticed.
        The control had deleted itself, and the round file's claim that it
        went red was not re-derivable.  (The mutant that IS red -- keep the
        new pragma, delete only the loop -- is a state this repository has
        never been in.)

        This version changes the one variable LANE-B changed: how long a
        transaction takes.  40 ms of delay is injected INSIDE the transaction,
        through `persistence_vitals.verify_schema`, which the healing path
        calls after `BEGIN IMMEDIATE` -- no production constant is patched and
        no production code knows this test exists.  Measured on this machine,
        three runs each:

            with a plain `BEGIN IMMEDIATE` (what `main` shipped):
                3-4 x OperationalError('database is locked'), 196-197 of 200
                heals landed -- heals LOST, silently
            with the retry (what this branch ships):
                0 errors, 200 of 200

        THREADS is the 8 the forbidden repairs list protects.  HEALS is 25
        rather than 60 only because each heal now costs 40 ms of injected
        delay; the pressure that matters -- eight writers against one file --
        is unchanged, and `BeginImmediateHoldsTheHealLockTests` still runs the
        full 8 x 60 above.
        """
        threads_count, heals, delay = 8, 25, 0.040
        errors = []

        self.store.write_typed_attributes(self.character.id, {
            "level": 1, "hp_current": 0, "hp_max": 100000,
        })
        before = self._hp()

        def worker():
            for _ in range(heals):
                try:
                    self.store.apply_hp_heal(self.character.id, 1)
                except Exception as exc:  # noqa: BLE001 - reported, not hidden
                    errors.append(exc)

        real_verify = vitals.verify_schema

        def slow_verify(db):
            result = real_verify(db)
            time.sleep(delay)
            return result

        with mock.patch.object(vitals, "verify_schema", slow_verify):
            threads = [threading.Thread(target=worker)
                       for _ in range(threads_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual([], [repr(e) for e in errors])
        self.assertEqual(self._hp(), before + threads_count * heals)

    def test_the_retry_helper_still_asks_for_an_immediate_transaction(self):
        """The forbidden repair, pinned at the source.

        `BEGIN` or `BEGIN DEFERRED` would make every test in this class pass
        and `BeginImmediateHoldsTheHealLockTests` fail; this says the same
        thing where a reader of the retry loop can see it, because the retry
        loop is exactly where someone would be tempted to relax the lock to
        reduce contention.
        """
        source = (ROOT / "src" / "pirateforce_foundation" / "store.py"
                  ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_begin_immediate_under_contention")
        # THE DOCSTRING IS STRIPPED, AND THE FIRST DRAFT DID NOT STRIP IT.
        # A `pf-adversary` pass deleted the `BEGIN IMMEDIATE` from the helper
        # BODY entirely -- a helper that opens no transaction at all -- and
        # this test passed, because the phrase still appeared four times in
        # the prose above it.  Prose read as evidence about code, the same
        # shape this lane has been caught by before.  It cut the other way
        # too: a future comment explaining why `BEGIN DEFERRED` is not used
        # would have turned it red on documentation drift.
        body = list(function.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        statements = "\n".join(ast.dump(node) for node in body)
        self.assertIn("BEGIN IMMEDIATE", statements)
        self.assertNotIn("'BEGIN'", statements)
        self.assertNotIn("BEGIN DEFERRED", statements)


class NothingIsWiredTests(unittest.TestCase):
    """The honest half: this round changed nothing anybody can see.

    Same shape, and the same measured reasons, as the scan in
    `tests/test_persistence_vitals.py`: FULL repository-relative paths rather
    than basenames (a `src/pirateforce_foundation/gm/store.py` calling
    `apply_hp_heal` is a real wiring on a live path and a basename allowlist
    is blind to it), and every python tree, not just `src/`.
    """

    #: A file joins this tuple only together with the round file that says why.
    ALLOWED_TO_NAME_THEM = (
        "src/pirateforce_foundation/store.py",
        "src/pirateforce_foundation/persistence_vitals.py",
        "tests/test_persistence_vitals_heal.py",
    )

    NAMES = r"\b(apply_hp_heal|restore_hp_to_full|apply_heal|heal_to_full)\b"

    #: Directories the scan skips outright.  Named, so that a directory
    #: joining this list is a visible decision rather than an omission.
    SKIPPED = (".git", "__pycache__", ".venv", "venv", "node_modules")

    #: Every python-ish suffix, not just `.py`.  A `pf-adversary` pass got a
    #: real wiring past an `rglob("*.py")` scan by naming the file `.pyw`.
    SUFFIXES = (".py", ".pyw", ".pyi")

    def _would_scan(self, relative: str) -> bool:
        """The walk's rule, as a predicate over one repository-relative path.

        Factored out so the rule can be tested against paths that do NOT
        exist -- the four dodges a `pf-adversary` pass measured -- without
        planting files in the repository to do it.
        """
        parts = tuple(relative.split("/"))
        if any(part in self.SKIPPED for part in parts):
            return False
        return Path(relative).suffix in self.SUFFIXES

    def _scanned_files(self):
        """Every python file in the repository, from the ROOT down.

        The first version listed seven directories by name and was blind to
        four measured things: a file at the repository root, one under
        `rounds/` or `capture/`, and any `.pyw`.  Walking from `ROOT` costs a
        second and has no list to fall behind.
        """
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or path.suffix not in self.SUFFIXES:
                continue
            relative = str(path.relative_to(ROOT)).replace("\\", "/")
            if not self._would_scan(relative):
                continue
            yield relative, path

    def test_no_call_site_anywhere_calls_the_new_healing_doors(self):
        self.assertIn(
            str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
            self.ALLOWED_TO_NAME_THEM,
        )
        callers = []
        seen = 0
        for relative, path in self._scanned_files():
            seen += 1
            if relative in self.ALLOWED_TO_NAME_THEM:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(self.NAMES, text):
                callers.append(relative)
        self.assertGreater(
            seen, 100,
            "the walk found almost nothing, so a green result here would "
            "mean the scan is broken rather than that nothing calls them",
        )
        self.assertEqual(
            [], callers,
            "something now calls the healing doors (%r).  That is not "
            "forbidden -- it means this test's claim, and the round file's "
            "'wired to nothing', are out of date and must be rewritten."
            % (callers,),
        )

    def test_every_allowed_file_exists_and_really_names_them(self):
        """The allowlist cannot rot into a licence: an entry that no longer
        matches a file, or one that names none of the methods, is a hole
        somebody can drop a real caller into."""
        for relative in self.ALLOWED_TO_NAME_THEM:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertTrue(
                re.search(self.NAMES,
                          path.read_text(encoding="utf-8", errors="replace")),
                "%s is excused from the scan but names none of the doors; it "
                "is a hole, not an exception" % relative,
            )

    def test_a_planted_wiring_really_is_caught_by_the_matching_rule(self):
        """The scan RUN against decoys, not two string properties of the
        allowlist.

        The inherited shape of this test asserted only that a decoy path
        shares a basename with an allowed entry and is not itself allowed --
        which would pass even if the scan below had been deleted.  Here the
        rule is exercised: each decoy is a path the scan would visit, and the
        assertion is that the allowlist does NOT excuse it and that the
        pattern DOES match the body a real wiring would have.
        """
        bodies = (
            "store.apply_hp_heal(cid, 50)",
            "self.restore_hp_to_full(cid)",
            "from pirateforce_foundation.persistence_vitals import heal_to_full",
        )
        decoys = (
            "src/pirateforce_foundation/gm/store.py",
            "tools/persistence_vitals.py",
            "wire_heal.py",
            "rounds/wire_heal.pyw",
        )
        for decoy in decoys:
            self.assertNotIn(decoy, self.ALLOWED_TO_NAME_THEM, decoy)
            self.assertIn(
                Path(decoy).suffix, self.SUFFIXES,
                "%s would not even be visited by the walk" % decoy)
            for body in bodies:
                with self.subTest(decoy=decoy, body=body):
                    self.assertTrue(
                        re.search(self.NAMES, body),
                        "the pattern does not match %r, so a file holding it "
                        "would pass the scan" % body,
                    )

    def test_the_walk_reaches_the_four_places_the_named_list_missed(self):
        """The measured dodges, as a property of the RULE.

        Each of these got a real wiring past the previous shape of this scan
        (seven directories listed by name, `rglob("*.py")`).  They are
        asserted as paths the rule accepts, so the rule cannot narrow back
        without going red -- no file is planted in the repository to do it.
        """
        for dodge in ("wire_heal.py",
                      "rounds/wire_heal.py",
                      "capture/wire_heal.py",
                      "src/pirateforce_foundation/gm/heal_hook.pyw"):
            with self.subTest(dodge=dodge):
                self.assertTrue(self._would_scan(dodge), dodge)

    def test_the_walk_really_visits_the_repository(self):
        scanned = {relative for relative, _ in self._scanned_files()}
        self.assertIn("tests/test_persistence_vitals_heal.py", scanned)
        self.assertIn("src/pirateforce_foundation/store.py", scanned)
        self.assertFalse(
            [r for r in scanned if "__pycache__" in r],
            "compiled leftovers are not source and would make the scan "
            "report a caller that no source file has",
        )


class NoGuessedZeroInTheHealingSourceTests(unittest.TestCase):
    """The owner's rule, checked against the source rather than promised."""

    MODULE = ROOT / "src" / "pirateforce_foundation" / "persistence_vitals.py"

    def test_the_module_still_has_no_defaulted_dict_get(self):
        tree = ast.parse(self.MODULE.read_text(encoding="utf-8"))
        offenders = [
            node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) == 2
        ]
        self.assertEqual([], offenders)

    def test_this_test_file_never_opens_a_connection_it_does_not_close(self):
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
