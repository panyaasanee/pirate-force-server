"""LANE-B round uq2lxw: a pickup that goes through the dispatch path reaches
the database, survives a relog, and is still admitted at the next login.

WHAT THIS FILE IS THE EVIDENCE FOR, and how it differs from
``tests/test_store_acquired_item_insert.py``, which chief wrote for
``STORE-INSERT-001``.  That file proves the STORE half: a row minted through
``mob_pickup.place_in_bag`` and handed straight to
``store.commit_acquired_backpack_item`` lands and survives.  It never goes
through the path ``runtime.py`` would actually take -- no ``BagCell``, no
ground ledger, no claim, no delta bytes, and nothing takes the drop off the
ground.  Every test in THIS file runs the real dispatch path
(``mob_pickup_persist.pickup_and_persist``), which is the one line the chief
would add at the inbound pickup opcode, and then reads the database RAW --
not through the store's own accessors -- to see what is there.

THE CONTROL THIS FILE IS BUILT AROUND is ``GT-142``'s own: S0 before the
pickup, S1 straight after it and before any relog, S2 after the relog.  S1 is
what separates "the row was never written" from "the row was written and lost
at relog", and it is the question that had no answer in ``src/`` before this
round: nothing in the shipped tree called the store's INSERT at all.

WHAT IT DOES NOT PROVE, stated here rather than in a footnote.  Nothing in
this file is client-observable evidence.  The relog is a session close and
reopen against the store, not a client logging in; no window is opened and no
label is clicked.  And ``runtime.py`` still has no inbound pickup call site
(``GT-124``), so no player has caused any of this to run.  Attended ``GT-142``
is where the other layer comes from.
"""
import io
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    bag_admission,
    mob_loot,
    mob_pickup,
    mob_pickup_persist,
)
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.mob_loot import DropLedger, DropLedgerCell  # noqa: E402
from pirateforce_foundation.mob_pickup_persist import (  # noqa: E402
    MobPickupPersistError,
    pickup_and_persist,
    precheck_persistable,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

ITEM = 2400046            # the roster's most common drop
MOB = 0x2068
KILLER = 0x750059
# The claimant stands ON the drop, so every pickup here is well inside
# mob_pickup.PICKUP_RADIUS.  The three coordinates are FAR APART on purpose
# (pf-adversary, this round): with (10, 20, 30), permuting x and y anywhere in
# the chain left the distance at ~14 against a radius of 450, so the test that
# exists to catch a swapped argument in the published wiring line could not
# catch one.  The second draft moved only x, which left y<->z granted at 10
# apart; ALL THREE are far apart now, and the swap test drives all three
# permutations rather than the one it happened to write down.
DROP_AT = (1000.0, 20.0, 3000.0)


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


def a_drop(key_offset=0, quantity=1):
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, quantity,
        mob_loot.as_wire_float(DROP_AT[0]),
        mob_loot.as_wire_float(DROP_AT[1]),
        mob_loot.as_wire_float(DROP_AT[2]),
        MOB, KILLER,
    )


def a_ground_cell(*drops):
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(DropLedger(tuple(drops), 1, issued, ()))


class PickupPersistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("pickup-persist-uq2lxw")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "PickupPersistOne", "pickuppersistone",
            "fingerprint-pickup-persist-uq2lxw", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.registry = mob_pickup.BagCellRegistry()

    # ----- harness -------------------------------------------------------

    @contextmanager
    def _raw(self):
        """A connection this helper CLOSES.

        Copied deliberately from ``tests/test_store_acquired_item_insert.py``,
        which records why: ``with sqlite3.connect(...)`` commits and does NOT
        close, and an open handle is a locked file on Windows, where the
        gate then fails TemporaryDirectory cleanup with WinError 32 while the
        cloud stays green.
        """
        db = sqlite3.connect(self.path)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _rows(self):
        """The bag, read RAW -- not through the store that just wrote it."""
        with self._raw() as db:
            return [
                tuple(row) for row in db.execute(
                    "SELECT item_identity,template_id,quantity,slot,"
                    "raw_u8_38,raw_u8_39,detail_present "
                    "FROM character_backpack_items WHERE character_id=? "
                    "ORDER BY item_identity",
                    (self.character.id,),
                )
            ]

    def _column(self):
        with self._raw() as db:
            return int(db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?", (self.character.id,),
            ).fetchone()[0])

    def _claim_cell(self):
        """The cell as ``MOB_PICKUP_WIRING`` step 0 seeds it, verbatim."""
        return self.registry.claim(
            self.character.id,
            self.store.get_backpack(self.sid, self.character.id),
            self.store.backpack_issued_through(self.sid, self.character.id),
        )

    def _relog(self):
        """Close this session and open a new one on the same character.

        Also releases the bag cell, because a logout does: a cell that
        outlived its session is exactly what ``BagCellRegistry`` refuses to
        duplicate.
        """
        self.registry.release(self.character.id)
        self.store.close_session(self.sid)
        self.sid = self.store.open_session(self.account_id)
        self.store.select_character(self.sid, self.character.selector)

    def _pickup(self, cell, ground, key_offset=0, echo=False):
        return pickup_and_persist(
            self.store, self.sid, self.character.id, cell, ground,
            self.legacy, KILLER, DROP_AT[0], DROP_AT[1], DROP_AT[2],
            mob_loot.DROP_KEY_BASE + key_offset, 0, echo=echo,
        )

    # ----- the loop ------------------------------------------------------

    def test_the_row_the_dispatch_promised_is_the_row_the_database_holds(self):
        """S0 -> S1 of GT-142's control, headless.

        The promise is ``outcome.row_write`` -- the value whose
        ``MOB_PICKUP_ROW_WOULD_INSERT`` line the dispatch path prints -- and
        the check is that the raw row equals it field for field.  A test that
        compared the store's own read-back with the store's own write would
        agree with itself.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        s0 = self._rows()
        self.assertEqual(len(s0), len(INITIAL_BACKPACK.items))
        result = self._pickup(cell, ground)
        s1 = self._rows()
        self.assertEqual(len(s1), len(s0) + 1)
        row = result.outcome.row_write
        self.assertIn(
            (row.item_identity, row.template_id, row.quantity, row.slot,
             row.raw_u8_38, row.raw_u8_39, row.detail_present),
            s1,
        )
        self.assertTrue(result.agrees)
        # the counter moved with it, in the same transaction
        self.assertEqual(self._column(), row.item_identity + 1)
        # and the drop really did leave the ground
        self.assertEqual(ground.ledger.drops, ())

    def test_the_item_survives_a_relog_and_gate_2_still_admits_the_bag(self):
        """S1 -> S2, and the question the relog half of M5 actually asks.

        Gate 2 is checked with the HYP-PF-008 opt-in OFF, so admission is
        earned by the acquired row itself and not by the permissive term: a
        row that persisted but locked the character out of the world would
        close no loop.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        result = self._pickup(cell, ground)
        s1 = self._rows()
        self._relog()
        self.assertEqual(self._rows(), s1)
        reloaded = self.store.get_backpack(self.sid, self.character.id)
        self.assertIn(result.outcome.item, reloaded.items)
        admission = bag_admission.classify(reloaded)
        self.assertEqual(
            admission.verdict, bag_admission.VERDICT_GOLDEN_PLUS_ACQUIRED)
        self.assertEqual(admission.acquired, (result.outcome.item,))
        self.assertTrue(bag_admission.may_enter_world(
            reloaded, allow_hypothesized_item_move=False))
        # and the next session's cell seeds from the moved column, so the
        # pickup after the relog does not re-mint the identity that survived
        after = self._claim_cell()
        self.assertEqual(
            mob_pickup.next_item_identity(after.bag, after.issued_through),
            result.outcome.item.identity + 1,
        )

    def test_two_pickups_in_one_session_take_two_slots_and_two_identities(self):
        ground = a_ground_cell(a_drop(0), a_drop(1))
        cell = self._claim_cell()
        first = self._pickup(cell, ground, 0)
        second = self._pickup(cell, ground, 1)
        self.assertNotEqual(
            first.outcome.item.identity, second.outcome.item.identity)
        self.assertNotEqual(first.outcome.item.slot, second.outcome.item.slot)
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items) + 2)
        self.assertEqual(self._column(), second.outcome.item.identity + 1)

    # ----- the order rule this module exists for -------------------------

    def test_a_cell_that_drifted_from_the_database_refuses_before_the_take(self):
        """The load-bearing property: the drop is STILL THERE after refusal.

        A row written behind the session's back (another writer, a stale
        cell) makes the store refuse the write.  Without the precheck that
        refusal arrives after ``commit_pickup`` has already taken the drop
        off the ground: the player's item would be destroyed by a database
        error.  So the ground ledger is inspected after the refusal, and the
        drop has to be on it.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        # somebody else writes to this character's bag
        stranger_cell = mob_pickup.BagCell(
            self.store.get_backpack(self.sid, self.character.id),
            self.character.id,
            self.store.backpack_issued_through(self.sid, self.character.id),
        )
        other_ground = a_ground_cell(a_drop(5))
        pickup_and_persist(
            self.store, self.sid, self.character.id, stranger_cell,
            other_ground, self.legacy, KILLER, DROP_AT[0], DROP_AT[1],
            DROP_AT[2], mob_loot.DROP_KEY_BASE + 5, 0, echo=False,
        )
        before = self._rows()
        with self.assertRaises(MobPickupPersistError) as caught:
            self._pickup(cell, ground)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_CELL_DISAGREES_WITH_THE_DATABASE)
        self.assertEqual(len(ground.ledger.drops), 1, "the drop was eaten")
        self.assertEqual(self._rows(), before)

    def test_without_the_precheck_the_same_drift_destroys_the_drop(self):
        """The counterfactual, executed rather than asserted in prose.

        This is what the dispatch path does on its own -- the recipe
        ``MOB_PICKUP_WIRING`` hands the chief today -- against the same
        drifted cell: the take happens, and the write then fails.  If this
        test ever stops failing at the write, the precheck above is
        protecting against nothing and should be deleted rather than kept as
        decoration.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        stranger_cell = mob_pickup.BagCell(
            self.store.get_backpack(self.sid, self.character.id),
            self.character.id,
            self.store.backpack_issued_through(self.sid, self.character.id),
        )
        pickup_and_persist(
            self.store, self.sid, self.character.id, stranger_cell,
            a_ground_cell(a_drop(5)), self.legacy, KILLER, DROP_AT[0],
            DROP_AT[1], DROP_AT[2], mob_loot.DROP_KEY_BASE + 5, 0, echo=False,
        )
        outcome = mob_pickup.dispatch_pickup_request(
            cell, ground, self.legacy, KILLER, DROP_AT[0], DROP_AT[1],
            DROP_AT[2], mob_loot.DROP_KEY_BASE, 0,
        )
        self.assertEqual(ground.ledger.drops, (), "the take already happened")
        with self.assertRaises(MobPickupPersistError) as caught:
            mob_pickup_persist.persist_pickup(
                self.store, self.sid, self.character.id, outcome, echo=False)
        # Narrowed (pf-adversary, this round): a bare assertRaises(ValueError)
        # would have been satisfied by this module's OWN guards, which refuse
        # before the store is reached and prove nothing about the wall this
        # test is named for.  The refusal has to be the one that means the
        # write itself failed, and the store's own words have to be in it.
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_WRITE_FAILED_AFTER_THE_TAKE)
        self.assertIn("is not this character's next free identity",
                      str(caught.exception.__cause__))

    def test_a_cell_belonging_to_another_character_is_refused(self):
        other = self.store.create_character(
            self.account_id, "PickupPersistTwo", "pickuppersisttwo",
            "fingerprint-pickup-persist-uq2lxw-2", _build_wire, self.home,
        )
        cell = self.registry.claim(
            other.id, self.store.get_backpack(self.sid, self.character.id))
        ground = a_ground_cell(a_drop())
        with self.assertRaises(MobPickupPersistError) as caught:
            pickup_and_persist(
                self.store, self.sid, self.character.id, cell, ground,
                self.legacy, KILLER, DROP_AT[0], DROP_AT[1], DROP_AT[2],
                mob_loot.DROP_KEY_BASE, 0, echo=False,
            )
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_CELL_IS_ANOTHER_CHARACTERS)
        self.assertEqual(len(ground.ledger.drops), 1)

    def test_a_cell_seeded_from_the_column_instead_of_the_mark_is_refused(self):
        """Migration 005's trap, caught before it eats a drop.

        Seeding the cell with ``next_item_identity`` (EXCLUSIVE) instead of
        ``backpack_issued_through`` (INCLUSIVE) mints one identity too high.
        The store refuses such a row -- after the take.  Here it refuses
        before, by name.
        """
        cell = self.registry.claim(
            self.character.id,
            self.store.get_backpack(self.sid, self.character.id),
            self._column(),          # the column itself: one too high
        )
        with self.assertRaises(MobPickupPersistError) as caught:
            precheck_persistable(
                self.store, self.sid, self.character.id, cell)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS)

    def test_a_session_without_this_character_selected_is_refused_by_name(self):
        """And the NAME is its own, not the store's catch-all.

        pf-adversary, this round: the first draft reported an ownership
        violation -- possibly a client asking for somebody else's character --
        under ``store_cannot_be_asked``, the same reason a full disk gets.  An
        operator reading a log could not tell the two apart.
        """
        cell = self._claim_cell()
        other_sid = self.store.open_session(self.account_id)
        with self.assertRaises(MobPickupPersistError) as caught:
            precheck_persistable(
                self.store, other_sid, self.character.id, cell)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_SESSION_DOES_NOT_OWN_THIS_CHARACTER)
        self.assertIsInstance(caught.exception.__cause__, PermissionError)

    def test_a_store_that_cannot_answer_is_reported_as_that_and_stays_ascii(self):
        """The catch-all, and the cp874 exposure in its own detail string.

        The detail interpolates ``%r`` of an exception this lane did not
        compose, and the bridge console is cp874 with errors='strict' -- so a
        sqlite error naming a Windows path with an unmappable character would
        raise inside the report.  Forced with a store whose read raises one.
        """
        cell = self._claim_cell()
        boom = sqlite3.OperationalError(
            "unable to open database file 'C:\\\\Panya\\\\\u0e01\u0e23\u0e38\u0e07\u0e40\u0e17\u0e1e\\\\a.db'")
        with mock.patch.object(
                self.store, "backpack_issued_through", side_effect=boom):
            with self.assertRaises(MobPickupPersistError) as caught:
                precheck_persistable(
                    self.store, self.sid, self.character.id, cell)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_STORE_CANNOT_BE_ASKED)
        caught.exception.detail.encode("cp874")
        self.assertIs(caught.exception.__cause__, boom)

    def test_a_write_that_fails_after_the_take_is_named_and_printed(self):
        """The one path in this lane that costs a player an item.

        pf-adversary, this round, by execution: a second process holding a
        write transaction makes the store raise ``database is locked`` AFTER
        ``dispatch_pickup_request`` has taken the drop off the ground.  The
        first draft let that reach the caller as a raw
        ``sqlite3.OperationalError`` -- a class with no reason name, which in
        a listener thread unwinds the connection.  Now: one named refusal,
        one console line that says which row was lost, and the drop is still
        gone (nothing here pretends otherwise).
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        boom = sqlite3.OperationalError("database is locked")
        buffer = io.StringIO()
        with mock.patch.object(
                self.store, "commit_acquired_backpack_item", side_effect=boom):
            with redirect_stdout(buffer):
                with self.assertRaises(MobPickupPersistError) as caught:
                    self._pickup(cell, ground, echo=True)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_WRITE_FAILED_AFTER_THE_TAKE)
        self.assertIs(caught.exception.__cause__, boom)
        printed = buffer.getvalue()
        self.assertIn("MOB_PICKUP_ROW_LOST", printed)
        self.assertIn("item_identity=5", printed)
        # the loss is real and this test does not pretend it is not
        self.assertEqual(ground.ledger.drops, ())
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))
        # ...and the session does not go on diverging: the next pickup is
        # refused BEFORE its take, because the cell no longer matches the DB
        second = a_ground_cell(a_drop(1))
        with self.assertRaises(MobPickupPersistError) as after:
            self._pickup(cell, second, 1)
        self.assertEqual(
            after.exception.reason,
            mob_pickup_persist.REFUSE_CELL_DISAGREES_WITH_THE_DATABASE)
        self.assertEqual(len(second.ledger.drops), 1)

    def test_a_write_that_committed_then_failed_is_not_reported_as_a_loss(self):
        """The aftermath is READ BACK, not inferred from the exception.

        pf-adversary, second pass: a store that commits and then raises on
        the way out (``db.close()`` in a ``finally`` is enough) made this
        module print ``MOB_PICKUP_ROW_LOST`` for a row that was in the
        database -- and that line invites an operator to put it back by hand,
        i.e. to insert a duplicate.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        real = self.store.commit_acquired_backpack_item

        def commit_then_fail(sid, character_id, item):
            real(sid, character_id, item)
            raise sqlite3.OperationalError("disk I/O error while closing")

        buffer = io.StringIO()
        with mock.patch.object(
                self.store, "commit_acquired_backpack_item", commit_then_fail):
            with redirect_stdout(buffer):
                with self.assertRaises(MobPickupPersistError) as caught:
                    self._pickup(cell, ground)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_WRITE_FAILED_AFTER_THE_TAKE)
        printed = buffer.getvalue()
        self.assertIn(mob_pickup_persist.AFTERMATH_ROW_PRESENT, printed)
        self.assertNotIn(mob_pickup_persist.AFTERMATH_ROW_ABSENT, printed)
        self.assertIn("do NOT insert it by hand", printed)
        # and the row really is there, which is what the line now says
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items) + 1)

    def test_when_the_read_back_also_fails_the_fate_is_named_unknown(self):
        """Three answers, never two: "I do not know" is one of them.

        The database is unreachable for the write AND for the read after it,
        which is what a locked or dying database actually looks like.  The
        precheck's own read still has to succeed -- otherwise the pickup is
        refused before the take and there is nothing to be unsure about -- so
        the store fails from the SECOND read onwards.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        real_get = self.store.get_backpack
        calls = []

        def fails_after_the_precheck(sid, character_id):
            calls.append(1)
            if len(calls) > 1:
                raise sqlite3.OperationalError("still locked")
            return real_get(sid, character_id)

        buffer = io.StringIO()
        with mock.patch.object(
                self.store, "commit_acquired_backpack_item",
                side_effect=sqlite3.OperationalError("database is locked")):
            with mock.patch.object(
                    self.store, "get_backpack", fails_after_the_precheck):
                with redirect_stdout(buffer):
                    with self.assertRaises(MobPickupPersistError):
                        self._pickup(cell, ground)
        self.assertIn(
            mob_pickup_persist.AFTERMATH_UNKNOWN, buffer.getvalue())
        self.assertIn("UNKNOWN - check before changing anything",
                      buffer.getvalue())

    def test_the_loss_report_is_printed_even_with_echo_off(self):
        # echo is a console preference for the ordinary path; a possibly
        # destroyed item is not a preference (pf-adversary, second pass: the
        # first draft's docstring promised this unconditionally and the code
        # had it inside `if echo:`).
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        buffer = io.StringIO()
        with mock.patch.object(
                self.store, "commit_acquired_backpack_item",
                side_effect=sqlite3.OperationalError("database is locked")):
            with redirect_stdout(buffer):
                with self.assertRaises(MobPickupPersistError):
                    self._pickup(cell, ground, echo=False)
        self.assertIn(
            mob_pickup_persist.AFTERMATH_ROW_ABSENT, buffer.getvalue())

    def test_the_loss_line_that_is_really_printed_survives_cp874(self):
        """The cp874 fix, driven through the print that actually happens.

        pf-adversary, second pass: removing ``console_safe`` from the loss
        path left the suite green, because the ASCII test composed a line
        itself instead of driving the path where a foreign string reaches a
        real ``print()``.  A sqlite error naming a Windows path is the
        hazard, so that is what is injected.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        buffer = io.StringIO()
        with mock.patch.object(
                self.store, "commit_acquired_backpack_item",
                side_effect=sqlite3.OperationalError(
                    "unable to open 'C:\\Panya\\\u4e2d\\state.sqlite3'")):
            with redirect_stdout(buffer):
                with self.assertRaises(MobPickupPersistError) as caught:
                    self._pickup(cell, ground)
        buffer.getvalue().encode("cp874")
        caught.exception.detail.encode("cp874")

    def test_the_loss_line_refuses_a_value_that_is_not_the_typed_row(self):
        # Same guard as the sibling composer, and it matters more here: this
        # one runs inside persist_pickup's except block, where an
        # AttributeError would replace the named refusal (pf-adversary).
        with self.assertRaises(MobPickupPersistError) as caught:
            mob_pickup_persist.row_lost_console_line(
                {"item_identity": 5}, ValueError("boom"))
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_persist_pickup_refuses_an_outcome_from_another_characters_cell(self):
        """The guard on the PUBLIC entry point, exercised through it.

        pf-adversary, this round: deleting this guard left the suite green,
        because ``pickup_and_persist`` refuses earlier on the cell and the
        only test that "covered" it was an AST walk proving a ``raise``
        statement exists.  ``persist_pickup`` is public and takes the
        character id separately from the outcome, so the mix is reachable.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        outcome = mob_pickup.dispatch_pickup_request(
            cell, ground, self.legacy, KILLER, DROP_AT[0], DROP_AT[1],
            DROP_AT[2], mob_loot.DROP_KEY_BASE, 0,
        )
        other = self.store.create_character(
            self.account_id, "PickupPersistThree", "pickuppersistthree",
            "fingerprint-pickup-persist-uq2lxw-3", _build_wire, self.home,
        )
        with self.assertRaises(MobPickupPersistError) as caught:
            mob_pickup_persist.persist_pickup(
                self.store, self.sid, other.id, outcome, echo=False)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_CELL_IS_ANOTHER_CHARACTERS)
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))

    def test_the_precheck_returns_the_identity_the_write_will_demand(self):
        # The documented return value, read by a test rather than only
        # promised: returning None left the suite green (pf-adversary).
        cell = self._claim_cell()
        minted = precheck_persistable(
            self.store, self.sid, self.character.id, cell)
        self.assertEqual(minted, self._column())
        ground = a_ground_cell(a_drop())
        result = self._pickup(cell, ground)
        self.assertEqual(result.outcome.item.identity, minted)

    def test_a_cell_whose_mark_lags_its_own_bag_is_refused_at_seeding(self):
        """Where that refusal really lives, pinned so the precheck stays thin.

        ``precheck_persistable`` calls ``next_item_identity`` unguarded, which
        would be wrong if a lagging mark could reach it -- the exception is
        this lane's SIBLING class and would read to a player as "you cannot
        pick that up".  It cannot reach it: ``BagCell`` refuses such a mark at
        CONSTRUCTION, which is what this measures.  If this test ever stops
        being red at ``claim``, the precheck needs the guard the comment there
        currently argues against.
        """
        ground = a_ground_cell(a_drop())
        self._pickup(self._claim_cell(), ground)
        self.registry.release(self.character.id)
        current = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(mob_pickup.MobPickupContractError) as caught:
            self.registry.claim(self.character.id, current, 1)
        self.assertEqual(
            caught.exception.args[0],
            mob_pickup.REFUSE_IDENTITY_HIGH_WATER_BELOW_THE_BAG)

    def test_the_bag_is_read_before_the_mark_and_that_is_the_argument(self):
        """An ordering the code depends on, pinned where a tidy-up would break it.

        ``precheck_persistable`` calls ``next_item_identity`` on a bag and a
        mark read from the cell in SEPARATE lock acquisitions.  The reason a
        lagging mark cannot arrive there is the ORDER: bag first, so a
        concurrent ``commit_pickup`` can only pair an older bag with a newer
        mark.  Swapping the two adjacent lines inverts that argument and left
        the whole suite green (pf-adversary, second pass).  This reads the
        function's own source, because the property is textual.
        """
        import ast

        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_pickup_persist.py")
            .read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "precheck_persistable")
        reads = [
            node.value.attr
            for node in function.body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Attribute)
            and getattr(node.value.value, "id", "") == "bag_cell"
        ]
        self.assertEqual(
            reads[:2], ["bag", "issued_through"],
            "the bag must be read before the mark; see the comment above the "
            "next_item_identity call for what the order buys")

    def test_a_mark_at_the_identity_ceiling_is_a_persistence_refusal(self):
        """The second raise site the first draft's argument did not count.

        ``next_item_identity`` also refuses when the mark is at the column
        ceiling, and that one IS reachable from a validly constructed cell:
        seed at MAX-1, take one pickup, and the next precheck hits it.  It
        needs 2^63 identities to happen for real -- but it must not arrive as
        a ``MobPickupContractError``, which a caller reads as "you cannot
        pick that up" (pf-adversary, second pass, who fired it).
        """
        cell = self._claim_cell()
        ceiling = mob_pickup.MobPickupContractError(
            mob_pickup.REFUSE_IDENTITY_BLOCK_SPENT,
            "item identity %d is at the column ceiling"
            % mob_pickup.MAX_ITEM_IDENTITY)
        # INJECTED, and the reason it has to be injected is itself the point.
        # Reaching this for real needs a cell whose mark is AT the ceiling,
        # and such a cell can only come from a commit_pickup -- which also
        # moves the bag, so the bag-equality check above refuses first.  That
        # is a shield made of two checks' ORDER, and an argument of exactly
        # that shape is what this round already got wrong once (the first
        # draft removed this guard as "a branch that cannot fire" after
        # counting one of next_item_identity's two raise sites).  So the
        # CONVERSION is held by a test even though the path is shielded: what
        # must never happen is this reaching a caller as the sibling class.
        with mock.patch.object(
                mob_pickup, "next_item_identity", side_effect=ceiling):
            with self.assertRaises(MobPickupPersistError) as caught:
                precheck_persistable(
                    self.store, self.sid, self.character.id, cell)
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS)
        self.assertNotIsInstance(
            caught.exception, mob_pickup.MobPickupContractError)
        self.assertIs(caught.exception.__cause__, ceiling)

    def test_a_bag_value_is_not_a_cell_and_says_so(self):
        with self.assertRaises(MobPickupPersistError) as caught:
            precheck_persistable(
                self.store, self.sid, self.character.id,
                self.store.get_backpack(self.sid, self.character.id))
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_TYPE_NOT_TYPED_RECORD)

    # ----- what a reader of the console sees -----------------------------

    def test_the_two_console_lines_describe_the_same_row(self):
        """WOULD and DID, side by side, which is how GT-142 reads them.

        The dispatch path prints ``MOB_PICKUP_ROW_WOULD_INSERT`` and this
        module prints ``MOB_PICKUP_ROW_INSERTED``.  Every field they share
        must carry the same value, or the log claims one row was promised and
        another written.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = self._pickup(cell, ground, echo=True)
        printed = buffer.getvalue().splitlines()
        would = [ln for ln in printed if "MOB_PICKUP_ROW_WOULD_INSERT" in ln]
        did = [ln for ln in printed if "MOB_PICKUP_ROW_INSERTED" in ln]
        self.assertEqual(len(would), 1, printed)
        self.assertEqual(len(did), 1, printed)
        fields = ("character_id", "item_identity", "template_id", "quantity",
                  "slot")
        promised = dict(
            part.split("=", 1) for part in would[0].split() if "=" in part)
        written = dict(
            part.split("=", 1) for part in did[0].split() if "=" in part)
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(promised[field], written[field])
        self.assertEqual(result.lines[0], did[0])

    def test_the_disagreement_line_names_its_fields_and_survives_a_bad_value(self):
        """Its content is pinned, and it cannot raise on the raise-proof path.

        pf-adversary, this round, two findings in one place: scrambling the
        field names left the suite green (only ``.encode("ascii")`` looked at
        this line, which ``return ""`` would also pass), and a store that
        committed and returned ``None`` turned the report into an
        ``AttributeError`` inside the one path documented as never raising.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        result = self._pickup(cell, ground)
        line = mob_pickup_persist.disagreement_console_line(
            result.outcome, result.bag_after_db)
        self.assertTrue(line.startswith("MOB_PICKUP_PERSIST_DISAGREES "))
        fields = dict(
            part.split("=", 1) for part in line.split() if "=" in part)
        self.assertEqual(
            fields["character_id"], str(result.outcome.row_write.character_id))
        self.assertEqual(
            fields["item_identity"],
            str(result.outcome.row_write.item_identity))
        self.assertEqual(
            fields["in_memory_rows"], str(len(result.outcome.bag_after.items)))
        self.assertEqual(
            fields["database_rows"], str(len(result.bag_after_db.items)))
        # the store's read-back is not a bag at all: reported, never raised
        unreadable = mob_pickup_persist.disagreement_console_line(
            result.outcome, None)
        self.assertIn("database_rows=unreadable(NoneType)", unreadable)

    def test_a_console_line_refuses_a_value_that_is_not_the_typed_row(self):
        # Exercised through the public function rather than left to the AST
        # walk, which proves a raise statement exists and never that it runs.
        with self.assertRaises(MobPickupPersistError) as caught:
            mob_pickup_persist.row_inserted_console_line(
                {"character_id": 1, "item_identity": 5})
        self.assertEqual(
            caught.exception.reason,
            mob_pickup_persist.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_every_console_line_is_ascii(self):
        # The bridge console is cp874; a non-ASCII byte there is a crash, not
        # a cosmetic problem.
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        result = self._pickup(cell, ground)
        for line in result.lines:
            line.encode("ascii")
        mob_pickup_persist.disagreement_console_line(
            result.outcome, result.bag_after_db).encode("ascii")
        # ...including the loss line, whose tail is a store exception this
        # lane did not compose, so it goes through console_safe
        lost = mob_pickup_persist.console_safe(
            mob_pickup_persist.row_lost_console_line(
                result.outcome.row_write,
                # a character cp874 cannot map at all, which is the round-142
                # failure this project keeps a whole Windows gate for
                sqlite3.OperationalError("locked \u4e2d")))
        lost.encode("cp874")
        self.assertIn("MOB_PICKUP_ROW_LOST", lost)

    def test_the_wiring_note_the_chief_reads_names_this_module(self):
        """D2 of this round's adversarial pass, held by a test.

        ``mob_pickup.MOB_PICKUP_WIRING`` is the note a chief actually follows
        at the pickup opcode, and until this round it still taught the recipe
        that destroys a drop when the cell has drifted -- with no mention that
        a safer one exists.  Two recipes for one opcode, and the canonical one
        was the old one.  This keeps them from drifting apart again.
        """
        note = mob_pickup.MOB_PICKUP_WIRING
        self.assertIn(mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL, note)
        self.assertIn("test_without_the_precheck", note)
        # NOT JUST "the name appears".  pf-adversary rewrote the paragraph's
        # opening to "CONSIDERED AND REJECTED THE FOLLOWING; DO NOT use
        # mob_pickup_persist.pickup_and_persist(...)" and every assertIn above
        # still held -- a note telling the chief to do the opposite, with CI
        # approving.  The DIRECTION is what has to be pinned, so the
        # instruction is quoted here in full and the negation is excluded.
        self.assertIn(
            "SUPERSEDES THE DISPATCH CALL ABOVE AND STEP 3 BELOW WITH ONE "
            "CALL", note)
        self.assertIn("DO NOT follow those two as written; use ", note)
        self.assertNotIn("DO NOT use mob_pickup_persist", note)
        self.assertNotIn("REJECTED", note)
        # and the instruction and the call are one sentence, not two
        # paragraphs that a later edit could separate
        directive = note[note.index("DO NOT follow those two as written"):]
        self.assertLess(
            directive.index(
                mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL), 200)

    def test_a_disagreement_is_reported_and_not_raised_after_the_write(self):
        """The one thing this module cannot refuse its way out of.

        By the time the two derivations of the bag can be compared, the row
        is committed and the drop is gone.  Raising would tell the caller the
        pickup failed when it did not -- and in a listener thread that reads
        as "the player's click did nothing" while the item sits in their bag.
        So it reports.  Forced with a store whose read-back lies.
        """
        ground = a_ground_cell(a_drop())
        cell = self._claim_cell()
        real = self.store.commit_acquired_backpack_item

        def lying_commit(sid, character_id, item):
            written = real(sid, character_id, item)
            return written.__class__(
                written.base_mask, written.base_identity, written.range_mask,
                written.items[:-1],
            )

        with mock.patch.object(
                self.store, "commit_acquired_backpack_item", lying_commit):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                result = self._pickup(cell, ground, echo=True)
        self.assertFalse(result.agrees)
        self.assertIn("MOB_PICKUP_PERSIST_DISAGREES", buffer.getvalue())
        # ...and the row really is in the database: the report is about the
        # two views disagreeing, not about a failed write.
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items) + 1)

    # ----- the line handed to the chief ----------------------------------

    def test_the_headline_call_this_lane_hands_the_chief_actually_runs(self):
        """The wiring line is EXECUTED here, not grepped for.

        A docstring's own example is exactly where a swapped argument hides;
        the sibling lane proved that concretely by swapping two arguments in
        its headline text and watching a substring test stay green.  So this
        evaluates the published text against real objects.
        """
        ground = a_ground_cell(a_drop())
        scope = {
            "mob_pickup_persist": mob_pickup_persist,
            "store": self.store,
            "sid": self.sid,
            "character_id": self.character.id,
            "bag_cell": self._claim_cell(),
            "drop_ledger_cell": ground,
            "legacy": self.legacy,
            "identity": KILLER,
            "x": DROP_AT[0], "y": DROP_AT[1], "z": DROP_AT[2],
            "object_ref_u32": mob_loot.DROP_KEY_BASE,
            "opaque_u8": 0,
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = eval(  # noqa: S307 - the published line is the subject
                mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL, scope)
        self.assertTrue(result.agrees)
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items) + 1)

    def test_the_headline_call_would_notice_a_swapped_argument(self):
        """The test above is only worth its docstring if THIS one is red-able.

        pf-adversary, this round: swapping ``x, y`` inside the published text
        left the whole suite green, because the fixture's three coordinates
        were 20 apart and the pickup radius is 450 -- so the test that exists
        to catch a transcription slip could not catch the exact slip it names.
        This runs the published line with two of its arguments transposed and
        requires the pickup to be REFUSED; if this ever passes, the test
        above is decoration again.
        """
        transpositions = {
            "x<->y": "identity, y, x, z",
            "x<->z": "identity, z, y, x",
            "y<->z": "identity, x, z, y",
        }
        for label, mutated_args in transpositions.items():
            with self.subTest(swap=label):
                ground = a_ground_cell(a_drop())
                swapped = (
                    mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL
                    .replace("identity, x, y, z", mutated_args))
                self.assertNotEqual(
                    swapped,
                    mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL,
                    "the published line no longer has the argument names "
                    "this test transposes; re-derive the mutation")
                scope = {
                    "mob_pickup_persist": mob_pickup_persist,
                    "store": self.store,
                    "sid": self.sid,
                    "character_id": self.character.id,
                    "bag_cell": self._claim_cell(),
                    "drop_ledger_cell": ground,
                    "legacy": self.legacy,
                    "identity": KILLER,
                    "x": DROP_AT[0], "y": DROP_AT[1], "z": DROP_AT[2],
                    "object_ref_u32": mob_loot.DROP_KEY_BASE,
                    "opaque_u8": 0,
                }
                with self.assertRaises(
                        mob_pickup.MobPickupContractError) as caught:
                    eval(swapped, scope)  # noqa: S307 - the line is the subject
                self.assertEqual(
                    caught.exception.args[0],
                    mob_pickup.REFUSE_CLAIMANT_OUT_OF_RANGE)
                self.assertEqual(len(ground.ledger.drops), 1)
                self.assertEqual(
                    len(self._rows()), len(INITIAL_BACKPACK.items))
                self.registry.release(self.character.id)

    def test_the_module_ships_with_no_flag_and_no_clock(self):
        import ast

        source = (ROOT / "src/pirateforce_foundation/mob_pickup_persist.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for forbidden in ("socket", "sqlite3", "time", "datetime", "random",
                          "os", "subprocess"):
            self.assertNotIn(forbidden, imported)
        self.assertTrue(mob_pickup_persist.production_allowed)
        self.assertNotIn("scenario", imported)
        # No opt-in gate anywhere in the signatures.  Checked on the ARGUMENT
        # NAMES rather than on the file's prose, which was this test's first
        # shape and failed on its own docstring saying "not a scenario".
        # ``echo`` is the one keyword-only argument and it is about the
        # console; a parameter that could switch the WRITE off is what this
        # forbids.
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            names = [
                arg.arg for arg in
                node.args.args + node.args.kwonlyargs + node.args.posonlyargs
            ]
            for name in names:
                with self.subTest(function=node.name, argument=name):
                    for gate in ("scenario", "hypothes", "enable", "opt_in",
                                 "allow", "dry_run"):
                        self.assertNotIn(gate, name.lower())

    def test_every_declared_refusal_is_raised_somewhere_in_the_module(self):
        import ast

        raised = set()
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_pickup_persist.py")
            .read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            call = node.exc
            if (isinstance(call, ast.Call)
                    and getattr(call.func, "id", "") == "MobPickupPersistError"
                    and call.args
                    and isinstance(call.args[0], ast.Name)):
                raised.add(getattr(mob_pickup_persist, call.args[0].id))
        self.assertEqual(
            sorted(raised),
            sorted(mob_pickup_persist.MOB_PICKUP_PERSIST_REFUSAL_REASONS),
            "a refusal is declared and never raised, or raised and never "
            "declared")


if __name__ == "__main__":
    unittest.main()
