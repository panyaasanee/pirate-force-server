"""LANE-B round f4oh9y: the removal a 120 s EXPIRY owes, and who pays it.

WHAT THIS FILE IS ABOUT, measured before it was designed.  KA1A R307
(2026-09-03, the owner at her own client, letter
``20260903_1901_KA1A-R307-RESULTS-...``): two drops sat past their
``DROP_LIFETIME_SECONDS`` deadline, she clicked them SEVEN times, and every
click came back ``MOB_PICKUP_REQUEST_REFUSED reason=drop_already_taken`` --
7 of 7.  The rows were gone on the server (expiry is lazy: a sweep happens
inside whichever read gets there first) and still drawn on her screen,
because this server publishes a ground generation on a kill, on a successful
pickup and on a scene crossing, and an expiry is none of those.  COO-DECISION
2026-09-03T19:42+07:00 item 3 made that this lane's debt: "on expiry publish
the pool WITHOUT the row, same shape, no new mask".

THE THREE THINGS PINNED HERE

1. The cell now REMEMBERS what its sweep retired (``rows_owed_a_removal``)
   and can publish it (``frames_after_rows_expired``) -- the scene's
   remaining rows, the boundary publisher's own bytes, with the expired keys
   absent.  Read back OUT OF THE BYTES, never from the composer's opinion.
2. It is NOT a cadence.  A second call with nothing newly expired composes
   nothing.  That is the 2026-08-26 refusal of ``DROP_REFRESH_MS`` kept, and
   it is the difference between an event and a heartbeat.
3. The debt is paid by the PUBLICATION, never by the sweep -- so a kill, an
   arrival and a pickup all clear it, and the last-row case (nothing nonempty
   left to compose, and RE-130 read ``count = 0`` as a consumer no-op) HOLDS
   the debt instead of dropping it on the floor.

WHAT IS NOT CLAIMED.  No client has been watched losing a ghost label.  The
frames composed on a refused click do not leave this server yet either:
``runtime.py`` returns ``[]`` for a pickup whose ``delta`` is None, which
every refusal is, and moving that early return is a one-line CORE-REQUEST to
the chief.  ``TheConstantAndTheRuntimeAgree`` reads that out of runtime.py's
AST every run, so the day the line lands the console word changes with it and
the day somebody deletes it this file goes red rather than lying.
"""

from contextlib import redirect_stdout
from pathlib import Path
import ast
import io
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import (  # noqa: E402
    field_mobs,
    mob_drop_presence,
    mob_loot,
    mob_pickup,
    mob_pickup_request,
)
from pirateforce_foundation.mob_death import DeathRecord  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.mob_loot import (  # noqa: E402
    DropLedger,
    DropLedgerCell,
    GroundDrop,
    MobLootContractError,
    REFUSE_NOTHING_WAS_PUBLISHED,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

V141 = ROOT / "current/pf_login_game_server_v141.py"
RUNTIME_SOURCE = (
    ROOT / "src/pirateforce_foundation/runtime.py").read_text(encoding="utf-8")

ITEM = 2400046
MOB = 0x2068
KILLER = 0x750059
#: The scene every fixture here stands in.  Bg0002 rather than the default
#: bg0001 because the LATE row in half these tests comes out of a real kill,
#: and ``loot_a_kill`` refuses ``kill_in_another_scene`` when the mob and the
#: cell disagree -- so the scene is taken from the roster the kill uses.
SCENE = field_mobs.BG0002_SCENE
ELSEWHERE = field_mobs.BG0015_SCENE
DROP_AT = (1000.0, 20.0, 3000.0)


class _Clock:
    """A clock that only moves when a test says so."""

    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


def a_drop(key_offset=0, scene=SCENE):
    return GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, 1,
        mob_loot.as_wire_float(DROP_AT[0]),
        mob_loot.as_wire_float(DROP_AT[1]),
        mob_loot.as_wire_float(DROP_AT[2]),
        MOB, KILLER, scene,
    )


def a_cell(*drops, scene=SCENE, clock=None):
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(
        DropLedger(tuple(sorted(drops, key=lambda d: d.drop_key)), 1, issued,
                   ()),
        scene=scene, clock=clock)


def keys_on_the_wire(frames):
    """Every drop key in the composed bytes, found without asking the composer.

    The same second derivation ``tests/test_mob_loot_removal_publisher.py``
    uses: scan the pc for the element key record rather than trusting the
    module to report its own contents.  A publisher that composed the wrong
    rows cannot answer this with its own opinion.
    """
    seen = []
    for pc, _frame in frames:
        cursor = 0
        while True:
            index = pc.find(bytes([mob_loot.ELEMENT_KEY_TAG]), cursor)
            if index < 0 or index + 5 > len(pc):
                break
            key = int.from_bytes(pc[index + 1:index + 5], "little")
            if mob_loot.DROP_KEY_BASE <= key < mob_loot.DROP_KEY_LIMIT:
                seen.append(key)
            cursor = index + 1
    return seen


class LegacyCase(unittest.TestCase):
    """The frozen serializer, plus the one real kill these tests place with.

    The LATE row -- the one that survives the sweep so there is something
    nonempty to publish -- comes out of ``loot_a_kill`` and ``roll_drops``,
    the module's own placement path, rather than being hand-built into the
    ledger.  A fixture that built it by hand would be pinning this file's
    idea of a ground row instead of the server's.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)
        cls.roster = field_mobs.load_roster(scene=SCENE)
        cls.mob = cls.roster[0]
        cls.record = DeathRecord(
            cls.mob.actor_identity, KILLER, cls.mob.max_hp)

    def a_late_kill(self, cell, token=1, seed=3):
        """One kill that dropped something, or the test is not testing this."""
        drops = cell.loot_a_kill(
            self.mob, self.record,
            mob_loot.roll_drops(self.mob, random.Random(seed)),
            kill_token=token)
        self.assertTrue(
            drops, "this test needs a kill with rows; seed %r dropped none"
            % (seed,))
        return drops


class TheGhostR307Measured(LegacyCase):
    """The headline, driven end to end at the cell: expire, then publish."""

    def test_a_row_swept_inside_somebody_else_s_read_is_still_owed(self):
        """Where a row really dies in production: not in a call that asks.

        Nothing in this test asks for an expiry.  A liveness read performs
        one, silently, and the debt has to survive that -- it is the whole
        reason the bookkeeping lives in ``_sweep_locked`` and not in the
        publisher.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.ledger                                    # noqa: B018 - sweeps
        self.assertEqual(
            sorted(row.drop_key for row in cell.rows_owed_a_removal()),
            [mob_loot.DROP_KEY_BASE, mob_loot.DROP_KEY_BASE + 1])

    def test_the_generation_carries_the_survivors_and_not_the_expired(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        # One row expires while the other is still young: place the second
        # late enough that the first deadline passes alone.
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        late = self.a_late_kill(cell)
        clock.advance(2.0)
        expired, rows_left, frames = cell.frames_after_rows_expired(
            self.legacy, True)
        self.assertEqual(
            sorted(row.drop_key for row in expired),
            [mob_loot.DROP_KEY_BASE, mob_loot.DROP_KEY_BASE + 1])
        self.assertEqual(rows_left, len(late))
        self.assertTrue(frames, "rows remained and nothing was published")
        keys = keys_on_the_wire(frames)
        for row in expired:
            self.assertNotIn(
                row.drop_key, keys,
                "the generation carries a key the sweep already retired")
        self.assertEqual(
            sorted(keys), sorted(row.drop_key for row in late))

    def test_a_second_call_composes_nothing_it_is_not_a_cadence(self):
        """The 2026-08-26 refusal of DROP_REFRESH_MS, kept.

        One event, one publication.  A publisher that answered every call
        with the ground would be a heartbeat wearing an event's name -- and
        a caller putting it on a dispatch (which is exactly what this round
        wires) would have built the timer the COO refused.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        self.a_late_kill(cell)
        clock.advance(2.0)
        first = cell.frames_after_rows_expired(self.legacy, True)
        self.assertTrue(first[2])
        second = cell.frames_after_rows_expired(self.legacy, True)
        self.assertEqual(second, ((), first[1], ()))

    def test_nothing_expired_composes_nothing(self):
        cell = a_cell(a_drop(0), a_drop(1), clock=_Clock())
        self.assertEqual(
            cell.frames_after_rows_expired(self.legacy, True), ((), 2, ()))

    def test_a_cell_with_no_scene_refuses_by_returning_nothing(self):
        """FAIL-CLOSED, like every other publisher on this cell.

        Publishing "every row the ledger holds" for a cell that does not know
        its scene is the cross-scene leak way 1 exists to close.
        """
        cell = DropLedgerCell()
        self.assertEqual(
            cell.frames_after_rows_expired(self.legacy, True), ((), -1, ()))
        self.assertEqual(cell.rows_owed_a_removal(), ())


class TheDebtIsBounded(LegacyCase):
    """The memory that explains a removal must not become the leak.

    ``_expired`` next to it is a bounded deque for the same reason.  What the
    cap costs is the ROW RECORD, never the removal: the generation that pays
    the debt removes by omission, so it takes the forgotten rows with it.
    """

    def test_more_rows_than_the_cap_expire_and_the_memory_stays_bounded(self):
        clock = _Clock()
        many = [a_drop(offset) for offset in range(mob_loot.EXPIRED_KEY_MEMORY
                                                   + 10)]
        cell = a_cell(*many, clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.ledger                                    # noqa: B018 - sweeps
        owed = cell.rows_owed_a_removal()
        self.assertEqual(len(owed), mob_loot.EXPIRED_KEY_MEMORY)
        self.assertEqual(
            [row.drop_key for row in owed],
            [row.drop_key for row in many[-mob_loot.EXPIRED_KEY_MEMORY:]],
            "the deque should keep the NEWEST rows, as a maxlen deque does")

    def test_a_publication_still_clears_the_whole_scene_s_debt(self):
        clock = _Clock()
        many = [a_drop(offset) for offset in range(mob_loot.EXPIRED_KEY_MEMORY
                                                   + 10)]
        cell = a_cell(*many, clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        self.a_late_kill(cell)
        clock.advance(2.0)
        expired, _rows_left, frames = cell.frames_after_rows_expired(
            self.legacy, True)
        self.assertEqual(len(expired), mob_loot.EXPIRED_KEY_MEMORY)
        self.assertTrue(frames)
        self.assertEqual(cell.rows_owed_a_removal(), ())


class TheLastRowKeepsTheDebt(LegacyCase):
    """The hole RE-208 is open on, and the half COO 1942 item 3 offered.

    "or the NULL/empty pool when nothing is left" is REFUSED here, and not on
    taste: RE-130 read ``count = 0`` as a branch that goes straight to the
    consumer's epilogue, so an empty generation removes nothing on the screen.
    Spending this lane's one unmeasured shape to say nothing would also DROP
    the debt -- and then no publisher would owe the ghost anything ever again.
    Holding it is what lets the next kill in that scene pay it.
    """

    def test_the_scene_going_empty_publishes_nothing_and_keeps_the_debt(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        expired, rows_left, frames = cell.frames_after_rows_expired(
            self.legacy, True)
        self.assertEqual([row.drop_key for row in expired],
                         [mob_loot.DROP_KEY_BASE])
        self.assertEqual(rows_left, 0)
        self.assertEqual(frames, ())
        self.assertEqual(
            [row.drop_key for row in cell.rows_owed_a_removal()],
            [mob_loot.DROP_KEY_BASE],
            "the debt was dropped by a call that published nothing")

    def test_the_next_kill_in_that_scene_pays_the_held_debt(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.frames_after_rows_expired(self.legacy, True)
        step = mob_drop_presence.sustain_a_kill(
            cell, self.legacy,
            self.a_late_kill(cell))
        self.assertTrue(step.frames, "the kill published nothing")
        self.assertEqual(
            cell.rows_owed_a_removal(), (),
            "the kill's generation erases the ghost by omission (RE-130) and "
            "the debt should have gone with it")

    def test_an_empty_generation_cannot_clear_a_debt(self):
        cell = a_cell(a_drop(0), clock=_Clock())
        with self.assertRaises(MobLootContractError) as caught:
            cell.note_scene_published(SCENE, ())
        self.assertEqual(caught.exception.args[0], REFUSE_NOTHING_WAS_PUBLISHED)


class TheDebtIsPerScene(LegacyCase):
    """A row that expired in the town is not removed by the field's ground.

    Publishing scene B's generation erases the keys B omits.  It says nothing
    at all about a label drawn for scene A, so clearing A's debt with it would
    record a removal that never travelled.
    """

    def test_publishing_one_scene_leaves_the_other_scene_s_debt_standing(self):
        """The ``scene`` argument is READ, and this is what proves it.

        The cell stands in SCENE and the publication named here is
        ELSEWHERE's, so a method that used ``self._scene`` instead of its
        argument would clear the wrong debt.  A first draft of this test had
        the two the same and a mutant that ignored the argument entirely
        survived the whole suite.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1, scene=ELSEWHERE), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.ledger                                    # noqa: B018 - sweeps
        self.assertEqual(
            [row.drop_key for row in cell.rows_owed_a_removal(SCENE)],
            [mob_loot.DROP_KEY_BASE])
        cleared = cell.note_scene_published(ELSEWHERE, (a_drop(9),))
        self.assertEqual(
            cleared, 1,
            "the reported count is the rows this call really cleared")
        self.assertEqual(cell.rows_owed_a_removal(ELSEWHERE), ())
        self.assertEqual(
            [row.drop_key for row in cell.rows_owed_a_removal(SCENE)],
            [mob_loot.DROP_KEY_BASE],
            "publishing %s cleared a row that expired in %s"
            % (ELSEWHERE, SCENE))

    def test_a_generation_that_still_carries_a_row_keeps_that_row_s_debt(self):
        """The compose window, and the permanent ghost it used to make.

        Bytes are composed outside the lock, so a sweep can retire a row the
        composed generation is about to announce as STANDING.  The first
        draft popped the scene wholesale and marked that row paid -- a key
        left on the client's floor that the server had retired and that no
        publisher owed anything ever again.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.ledger                                    # noqa: B018 - sweeps
        # The generation still carries the row with offset 1: it was composed
        # before that row's deadline passed.
        cleared = cell.note_scene_published(SCENE, (a_drop(1),))
        self.assertEqual(cleared, 1)
        self.assertEqual(
            [row.drop_key for row in cell.rows_owed_a_removal(SCENE)],
            [mob_loot.DROP_KEY_BASE + 1],
            "a row the generation announces as standing was marked removed")

    def test_a_caller_that_cannot_name_the_keys_cannot_clear_anything(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        cell.ledger                                    # noqa: B018 - sweeps
        with self.assertRaises(MobLootContractError) as caught:
            cell.note_scene_published(SCENE, ("this is not a ground row",))
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD)
        self.assertEqual(len(cell.rows_owed_a_removal(SCENE)), 1)


class OnlyAPublisherThatReallySendsPaysTheDebt(LegacyCase):
    """Composing is not publishing, and the debt knows the difference.

    The kill and the pickup hand their frames straight back into the reply
    ``runtime.py`` sends with no gate in front of it.  The BOUNDARY does not:
    what ``enter_scene_frames`` returns is stashed and then held behind the
    arrival census, behind any scenario ground lane in the same dispatch, and
    behind the session still standing in the scene it was composed for -- one
    of which drops the frames by name.  A debt cleared there is cleared by
    bytes a later gate can throw away.
    """

    def test_a_scene_arrival_composes_but_does_not_pay(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        self.a_late_kill(cell)
        clock.advance(2.0)
        cell.enter_scene(ELSEWHERE)
        _p, _n, _e, _x, frames = cell.enter_scene_frames(self.legacy, SCENE)
        self.assertTrue(frames, "the arrival composed nothing")
        self.assertTrue(
            cell.rows_owed_a_removal(SCENE),
            "the boundary paid a debt with frames runtime.py may still drop")

    def test_a_successful_pickup_pays_it(self):
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        # TWO late kills, so one row can be taken and another is still
        # standing to be published.  Asserted rather than assumed: a fixture
        # that quietly rolled one row would make this test pass by skipping
        # the case it exists for.
        late = self.a_late_kill(cell) + self.a_late_kill(cell, token=2)
        clock.advance(2.0)
        self.assertGreaterEqual(
            len(late), 2, "this test needs two late rows, got %d" % len(late))
        taken = cell.take(late[0].drop_key).drop_key
        rows_left, frames = cell.frames_after_a_row_left(self.legacy, taken)
        self.assertTrue(frames, "rows remained and the pickup published none")
        self.assertEqual(cell.rows_owed_a_removal(SCENE), ())
        self.assertGreater(rows_left, 0)


class TheRefusedClickCarriesIt(LegacyCase):
    """The wiring half: the click that found the row gone answers for it.

    A real store, a real bag cell, a real ground cell and the frozen v141
    serializer -- the same transaction the production branch runs, refused the
    same way R307 measured it.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("pickup-expiry-f4oh9y")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "PickupExpiryOne", "pickupexpiryone",
            "fingerprint-pickup-expiry-f4oh9y",
            lambda selector: (b"wire", b"avatar", 0x10000001 + selector, 0),
            home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.registry = mob_pickup.BagCellRegistry()
        # ONE claim for the whole test: the registry refuses a second live
        # cell for the same character by name, which is its job -- and a
        # test that claims per click would be measuring that guard instead
        # of the publication.
        self.bag = self.registry.claim(
            self.character.id,
            self.store.get_backpack(self.sid, self.character.id),
            self.store.backpack_issued_through(self.sid, self.character.id),
        )
        self.addCleanup(self.registry.release, self.character.id)

    def _body(self, object_ref, opaque=0):
        return (
            bytes([mob_pickup_request.PICKUP_REQUEST_OBJECT_REF_TAG])
            + int(object_ref).to_bytes(4, "little")
            + bytes([mob_pickup_request.PICKUP_REQUEST_OPAQUE_U8_TAG, opaque])
        )

    def _parsed(self, object_ref):
        legacy = self.legacy
        pc = bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, mob_pickup_request.PICKUP_REQUEST_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
            + self._body(object_ref)
        )
        return legacy.parse_outer(pc)

    def _click(self, cell, object_ref):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            outcome = mob_pickup_request.dispatch_inbound_pickup_request(
                self.legacy, self._parsed(object_ref), self.store, self.sid,
                self.character.id, self.bag, cell, KILLER,
                DROP_AT[0], DROP_AT[1], DROP_AT[2])
        return outcome, buffer.getvalue()

    def _expiry_token(self):
        """The word the console is ALLOWED to use on this tree.

        Read from the module's own constant rather than hardcoded, exactly as
        the sibling removal publisher's tests do: until runtime.py sends the
        frames of a REFUSED click, a compose may not print PUBLISHED.
        """
        if mob_pickup_request.EXPIRY_PUBLICATION_CALL_SITE_STATUS == "sent":
            return mob_pickup_request.MOB_PICKUP_GROUND_EXPIRY_PUBLISHED_TOKEN
        return mob_pickup_request.MOB_PICKUP_GROUND_EXPIRY_COMPOSED_TOKEN

    def test_the_ghost_click_is_still_refused_and_now_carries_the_floor(self):
        """R307's click, replayed: refused as before, answered for at last."""
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        late = self.a_late_kill(cell)
        self.assertTrue(late)
        clock.advance(2.0)
        outcome, console = self._click(cell, mob_loot.DROP_KEY_BASE)
        self.assertFalse(
            outcome.handled, "an expired row must not become an item")
        self.assertIn("drop_already_taken", outcome.reason)
        self.assertTrue(
            outcome.ground_after,
            "the refusal composed no removal for the row the sweep retired")
        keys = keys_on_the_wire(outcome.ground_after)
        self.assertNotIn(mob_loot.DROP_KEY_BASE, keys)
        self.assertEqual(sorted(keys), sorted(row.drop_key for row in late))
        self.assertEqual(outcome.ground_rows_left, len(late))
        self.assertIn(self._expiry_token(), console)
        self.assertIn("MOB_PICKUP_REQUEST_REFUSED", console)

    def test_a_click_that_sends_nothing_does_not_spend_the_debt(self):
        """The bookkeeping waits for the wire, not for the composer.

        ``EXPIRY_PUBLICATION_CALL_SITE_STATUS`` says the composed frames are
        dropped by ``runtime.py`` today, so the debt must still be owed after
        a click -- otherwise the day the chief's line lands, the first click
        would find nothing left to publish.  This test INVERTS the day that
        line lands: with the constant at "sent" the same click pays.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        self.a_late_kill(cell)
        clock.advance(2.0)
        outcome, _console = self._click(cell, mob_loot.DROP_KEY_BASE)
        self.assertTrue(outcome.ground_after, "nothing was composed at all")
        sends = (mob_pickup_request.EXPIRY_PUBLICATION_CALL_SITE_STATUS
                 == "sent")
        owed = cell.rows_owed_a_removal(SCENE)
        if sends:
            self.assertEqual(
                owed, (), "the frames go out on this tree and the debt "
                "should have been paid")
        else:
            self.assertTrue(
                owed, "the debt was spent by a click that sent nothing")

    def test_the_held_line_is_printed_once_per_debt_not_once_per_click(self):
        """R307 clicked seven times.  A held debt lasts for ever by design.

        An unconditional line here is one console line per click for the rest
        of the session, on a path a stranger's frames drive.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        held = 0
        for _click in range(7):
            _outcome, console = self._click(cell, mob_loot.DROP_KEY_BASE)
            held += console.count(
                mob_pickup_request.MOB_PICKUP_GROUND_EXPIRY_HELD_TOKEN)
        self.assertEqual(held, 1, "seven clicks printed %d HELD lines" % held)

    def test_r307_s_own_shape_still_sends_nothing_and_this_pins_it(self):
        """!! THE CASE THAT WAS MEASURED, and the change does NOT fix it.

        R307's two drops were that scene's WHOLE ground, so the sweep left it
        empty and there is no nonempty generation to compose.  Seven clicks,
        seven refusals, zero frames -- byte for byte the outcome the letter
        records.  This test exists so nobody reads this round's PR, its
        docstrings or its console tokens as "the ghost is fixed": it is the
        branch the first draft of this file never executed, and the mutant
        that deleted the HELD branch entirely survived because of that.

        What the round DOES buy in this shape is one console line naming the
        debt, and the debt itself, which the next kill in that scene pays.
        """
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        frames_out = 0
        for _click in range(7):
            outcome, _console = self._click(cell, mob_loot.DROP_KEY_BASE)
            self.assertFalse(outcome.handled)
            self.assertIn("drop_already_taken", outcome.reason)
            frames_out += len(outcome.ground_after)
        self.assertEqual(
            frames_out, 0,
            "this shape has no nonempty generation to send; if that changed, "
            "NONCLAIM 25 and the PR body have to change with it")
        self.assertEqual(
            len(cell.rows_owed_a_removal(SCENE)), 2,
            "both rows are still owed a removal nobody has composed")

    def test_a_refusal_that_means_you_are_elsewhere_publishes_nothing(self):
        """A ground generation is about ONE scene, and it is the cell's.

        The cell's scene advances on a kill or a GM warp, never on a walked
        crossing, so a refusal that says "that row is in another scene" is
        the one refusal where answering with the cell's ground could send
        scene A's floor to a client standing in scene B.
        """
        self.assertNotIn(
            "drop_is_in_another_scene",
            mob_pickup_request.EXPIRY_PUBLICATION_REASONS)
        clock = _Clock()
        cell = a_cell(a_drop(0), a_drop(1), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS - 1.0)
        self.a_late_kill(cell)
        clock.advance(2.0)
        rows_left, frames = mob_pickup_request._expiry_publication(
            self.legacy, cell, "drop_is_in_another_scene", False)
        self.assertEqual((rows_left, frames), (-1, ()))
        self.assertTrue(
            cell.rows_owed_a_removal(SCENE),
            "the debt must survive a refusal this lane may not answer")

    def test_a_refusal_with_nothing_expired_is_exactly_what_it_was(self):
        """No new line, no frames, on the ordinary "never issued" refusal."""
        cell = a_cell(a_drop(0), clock=_Clock())
        outcome, console = self._click(cell, mob_loot.DROP_KEY_BASE + 40)
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.ground_after, ())
        self.assertEqual(outcome.ground_rows_left, -1)
        self.assertNotIn("MOB_PICKUP_GROUND_EXPIRY", console)

    def test_a_publisher_that_raises_costs_the_frames_not_the_session(self):
        """The never-raises promise, under a stranger's frame.

        The method is replaced ON THE CLASS because the transaction lane
        checks ``type(cell) is DropLedgerCell`` exactly, so a wrapper would
        be refused before the publication is reached.
        """
        original = mob_loot.DropLedgerCell.frames_after_rows_expired

        def boom(*_args, **_kwargs):
            raise ValueError("the composer moved")

        mob_loot.DropLedgerCell.frames_after_rows_expired = boom
        self.addCleanup(
            setattr, mob_loot.DropLedgerCell, "frames_after_rows_expired",
            original)
        clock = _Clock()
        cell = a_cell(a_drop(0), clock=clock)
        clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        outcome, console = self._click(cell, mob_loot.DROP_KEY_BASE)
        self.assertFalse(outcome.handled)
        self.assertIn("drop_already_taken", outcome.reason)
        self.assertEqual(outcome.ground_after, ())
        self.assertIn(
            mob_pickup_request.MOB_PICKUP_GROUND_EXPIRY_REFUSED_TOKEN, console)


def _the_pickup_branch(tree):
    """The function ``runtime.py`` dispatches an inbound pickup in.

    ANCHORED, and pf-adversary of this round is why: the first draft walked
    the WHOLE of runtime.py for any ``<x>.delta is None`` guarded ``return
    []``.  Measured -- the chief's line landed in a copy AND one unrelated
    decoy function was added elsewhere in the file, and the guard still
    reported "dropped" while the frames really went out.  That is exactly the
    false negative against the client this file exists to prevent, and it was
    green.  So the search is now scoped to the function that CONTAINS the
    dispatch call, and a decoy outside it cannot answer for it.
    """
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "dispatch_inbound_pickup_request"):
                return node
    return None


def _the_runtime_drops_a_refused_click_s_frames(source):
    """Does ``runtime.py`` still return early for a refused pickup?

    AN AST, NOT A SUBSTRING, for the reason the sibling guard in
    ``tests/test_mob_pickup_request.py`` learned the hard way: the branch
    explains itself in prose that uses every word this could search for.

    True while the pickup branch contains ``if outcome.delta is None:`` whose
    body is a bare ``return`` of an empty list -- the statement that throws
    away everything a refusal composed.  Measured on this tree: exactly ONE
    statement in the whole of runtime.py matches, and it is that one.

    WHAT IT CANNOT SEE, said here rather than left for somebody to trust it
    too far: it keys on the ``.delta`` attribute and the bare ``return []``,
    so a chief who drops the frames through some OTHER shape -- ``if not
    outcome.handled: return []``, say -- would leave this reading "sent"
    while a refusal still sends nothing.  Renaming ``outcome`` is safe (the
    attribute is what is matched); restructuring the condition is not.  It is
    the same class of limit ``_the_runtime_sends_the_ground_generation``
    carries and is why both are checks, not proofs.
    """
    branch = _the_pickup_branch(ast.parse(source))
    if branch is None:
        raise AssertionError(
            "no function in runtime.py calls dispatch_inbound_pickup_request; "
            "the call site this lane's constants describe is gone")
    for node in ast.walk(branch):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Is)
                and isinstance(test.left, ast.Attribute)
                and test.left.attr == "delta"
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None):
            continue
        for statement in node.body:
            if (isinstance(statement, ast.Return)
                    and isinstance(statement.value, ast.List)
                    and not statement.value.elts):
                return True
    return False


class TheConstantAndTheRuntimeAgree(unittest.TestCase):
    """The console may not say PUBLISHED on a boot that sends nothing.

    Same discipline, same reason, as ``GROUND_AFTER_CALL_SITE_STATUS``: a GT
    round grades on console lines, and PUBLISHED for frames that never left
    would be recorded as "the server published it and the client ignored it"
    -- a false negative against the CLIENT.
    """

    def test_the_status_constant_is_what_runtime_py_actually_does(self):
        dropped = _the_runtime_drops_a_refused_click_s_frames(RUNTIME_SOURCE)
        self.assertEqual(
            mob_pickup_request.EXPIRY_PUBLICATION_CALL_SITE_STATUS,
            "composed_not_sent" if dropped else "sent",
            "runtime.py and EXPIRY_PUBLICATION_CALL_SITE_STATUS disagree "
            "about whether a REFUSED click's ground generation is sent.  "
            "Either the chief's one-line change landed and this constant was "
            "not moved (the console then says COMPOSED_NOT_SENT for frames "
            "that DO go out), or the constant says 'sent' for a boot that "
            "returns [] before it ever reaches outcome.ground_after.")

    def test_the_composed_token_says_so_in_words(self):
        self.assertEqual(
            mob_pickup_request.MOB_PICKUP_GROUND_EXPIRY_COMPOSED_TOKEN,
            "MOB_PICKUP_GROUND_EXPIRY_COMPOSED_NOT_SENT_NO_CALL_SITE")


if __name__ == "__main__":                       # pragma: no cover
    unittest.main()
