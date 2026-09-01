"""LANE-B round m0vp7m: MOB-DROP-PRESENCE-001, the ground that stays.

PANYA-ORDER 2026-08-29 ("make the thing stay for a long time FIRST, before you
hand a tester something that appears for a tenth of a second") reached this
lane as chief's letter 20260829_2105.  This file is the wire/headless half of
the answer, and the first thing it pins is the SPLIT that answer needed:

  * the SERVER's row already lives 120 s and is nevertheless gone in
    microseconds today, because the dispatch takes every key of the kill it
    just announced.  That is testable here and it is what these tests measure.
  * the CLIENT's label lives 0.2-0.4 s and no server-side lifetime value can
    change that number.  NOTHING in this file measures a client, and every
    test that mentions the label pins a constant, not an observation.

The clock is a list of numbers (same shape as tests/test_mob_loot_expiry.py's,
and for the same reason the COO's lazy-expiry ruling gives): nothing here
sleeps, races, or depends on timing.
"""

from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import field_mobs, mob_drop_presence, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_drop_presence import (
    CONSOLE_TOKEN,
    LABEL_LIFE_SECONDS_MAX,
    LABEL_LIFE_SECONDS_MIN,
    PresenceStep,
    REFUSE_CELL_RAISED,
    REFUSE_NOT_A_CELL,
    STATE_NOTHING_ON_THE_GROUND,
    STATE_SNAPSHOT,
    STATE_SUSTAINED,
    STATE_TRIMMED_TO_FIT,
    describe_presence,
    presence_snapshot,
    sustain_a_kill,
)

KILLER = 0x750059
SRC = ROOT / "src/pirateforce_foundation"


def _call_names(module_name):
    """Every name a Python file in src/ actually CALLS, by function/method.

    Same helper, same AST-walk shape, as ``tests/test_mob_pickup.py``'s
    ``_call_names`` (added round hpronz to re-derive that GT-124's call site
    was really absent from ``runtime.py``, instead of trusting a hand-typed
    string that names it).  It lives in both files rather than being shared
    for the same reason that file's docstring gives: a test that imports its
    own oracle from the file it is cross-checking would fail together with
    it.  This copy is used the other way around from that one -- to confirm
    a described call site IS reached, not that it is absent -- because
    ``mob_drop_presence.DROP_PRESENCE_WIRING`` describes an ask that chief
    has since fulfilled (round t7t5yd, commit 432381a2), and only an AST walk
    over ``runtime.py`` itself, not the prose that says so, can keep proving
    that.
    """
    import ast

    source = (
        ROOT / "src" / "pirateforce_foundation" / f"{module_name}.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name:
            names.add(name)
    return names


class _Clock:
    """A clock that only moves when a test says so."""

    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class PresenceTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster(scene=field_mobs.BG0002_SCENE)
        # One dropping seed per mob, found once: a roll that drops nothing is
        # not a bug and is roughly one kill in three, so a test that hard-codes
        # a seed is a test that goes red when a drop table is edited.
        cls.dropping = []
        for mob in cls.roster:
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                if roll.placeable_count:
                    cls.dropping.append((mob, seed))
                    break
        if len(cls.dropping) < 3:
            raise unittest.SkipTest("this scene's tables drop almost nothing")

    def setUp(self):
        self.clock = _Clock()
        self.cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.token = 0

    def kill(self, index=0, cell=None):
        """One kill that dropped something, through the cell, like dispatch."""
        cell = self.cell if cell is None else cell
        mob, seed = self.dropping[index % len(self.dropping)]
        self.token += 1
        drops = cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)),
            kill_token=self.token)
        self.assertTrue(drops, "this test needs a kill with rows")
        return drops


class TheGroundStaysTests(PresenceTestBase):
    """The behaviour the owner asked for, measured against the one it replaces."""

    def test_the_shipped_path_today_takes_the_row_it_just_announced(self):
        """The control.  Without it, every number below is unanchored.

        This is exactly what runtime.py does today: announce the kill's own
        rows, then take every key.  The row a player is walking toward is gone
        before the frame has finished travelling.
        """
        drops = self.kill()
        mob_loot.drop_frames(self.legacy, drops)
        for drop in drops:
            self.cell.take(drop.drop_key)
        self.assertEqual(self.cell.ledger.drops, ())
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            self.cell.take(drops[0].drop_key)
        # MEASURED NAME, not the one the ni2wh2 letter used: a row that was
        # TAKEN refuses as drop_not_in_ledger; drop_expired is the separate
        # name a row that timed out gets.  Writing the letter's word here
        # would have pinned a refusal this tree does not raise.
        self.assertEqual(caught.exception.args[0],
                         mob_loot.REFUSE_DROP_NOT_IN_LEDGER)

    def test_the_row_survives_its_own_announcement_and_can_still_be_taken(self):
        drops = self.kill()
        step = sustain_a_kill(self.cell, self.legacy, drops)
        self.assertEqual(step.state, STATE_SUSTAINED)
        self.assertEqual(step.live, len(drops))
        self.assertEqual(step.announced, len(drops))
        self.assertEqual(step.carried, 0)
        # The whole point: a click now finds a row, with its whole life ahead.
        self.assertAlmostEqual(
            self.cell.time_left(drops[0].drop_key),
            mob_loot.DROP_LIFETIME_SECONDS, places=6)
        taken = self.cell.take(drops[0].drop_key)
        self.assertEqual(taken.drop_key, drops[0].drop_key)

    def test_a_second_kill_carries_the_first_kills_rows(self):
        """RE-130's erasure, closed.  This is the client-visible difference.

        A nonempty generation erases the keys it omits, so today's per-kill
        generation removes the previous kill's drops from the client's tree at
        the instant the new one appears.
        """
        first = self.kill(0)
        sustain_a_kill(self.cell, self.legacy, first)
        self.clock.advance(10.0)
        second = self.kill(1)
        step = sustain_a_kill(self.cell, self.legacy, second)

        carried = {row.drop_key for row in step.rows if not row.from_this_kill}
        self.assertEqual(carried, {drop.drop_key for drop in first})
        self.assertEqual(step.announced, len(second))
        self.assertEqual(step.carried, len(first))
        # And the older rows are carried with the LIFE THEY HAVE LEFT, not
        # refreshed: re-emission is not a new placement.
        for row in step.rows:
            expected = (
                mob_loot.DROP_LIFETIME_SECONDS if row.from_this_kill
                else mob_loot.DROP_LIFETIME_SECONDS - 10.0)
            self.assertAlmostEqual(row.seconds_left, expected, places=6)

    def test_the_generation_is_the_whole_ledger_and_never_one_kills_rows(self):
        """The bytes, not the record.  A partial generation is the defect."""
        first = self.kill(0)
        sustain_a_kill(self.cell, self.legacy, first)
        second = self.kill(1)
        step = sustain_a_kill(self.cell, self.legacy, second)

        # STRENGTHENED (round qf83nz, S7 debt carried from pf-adversary's
        # m0vp7m pass): ``whole`` used to be built by calling
        # ``mob_loot.refresh_frames(self.legacy, self.cell.ledger)`` a
        # SECOND time with the exact same arguments ``sustain_a_kill``
        # already called internally to produce ``step.frames`` -- comparing
        # a function's output to a second call of itself on identical
        # inputs, which cannot fail no matter what the function computes.
        # A mutant that broke ``refresh_frames`` would have broken both
        # sides of that assertion identically.  What actually needs
        # checking independently of that function is the LEDGER's own
        # contents: does it genuinely hold both kills' drops, or did
        # ``sustain_a_kill`` silently narrow it to one?  That is asked here
        # directly against the ledger, with no call through the frame
        # encoder at all.
        self.assertEqual(
            {drop.drop_key for drop in self.cell.ledger.drops},
            {drop.drop_key for drop in first} | {drop.drop_key for drop in second})
        self.assertEqual(len(self.cell.ledger.drops), len(first) + len(second))

        narrow = mob_loot.drop_frames(self.legacy, second)
        self.assertNotEqual(tuple(step.frames), tuple(narrow))
        # One generation, always -- the count of frames does not grow with the
        # ground, which is what makes this a shape change and not a cadence one.
        self.assertEqual(len(step.frames), 1)
        self.assertGreater(
            sum(len(frame) for _pc, frame in step.frames),
            sum(len(frame) for _pc, frame in narrow))

    def test_a_kill_that_dropped_nothing_still_re_carries_the_ground(self):
        """Why the wiring ask deletes the ``if drops:`` guard as well.

        Roughly one kill in three drops nothing.  Under today's guard such a
        kill sends no generation at all, which is harmless.  Under this shape
        the guard would be the bug: the rows already on the ground would go
        un-recarried for that kill, for no reason a player could understand.
        """
        first = self.kill(0)
        sustain_a_kill(self.cell, self.legacy, first)
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(step.state, STATE_SUSTAINED)
        self.assertEqual(step.announced, 0)
        self.assertEqual(step.carried, len(first))
        self.assertEqual(len(step.frames), 1)

    def test_the_expiry_still_bounds_the_ground(self):
        """The precondition step 4b named, cashed in: keep the rows AND stay bounded."""
        first = self.kill(0)
        sustain_a_kill(self.cell, self.legacy, first)
        self.clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 0.001)
        second = self.kill(1)
        step = sustain_a_kill(self.cell, self.legacy, second)
        self.assertEqual(step.carried, 0)
        self.assertEqual(
            {row.drop_key for row in step.rows},
            {drop.drop_key for drop in second})

    def test_an_empty_ground_sends_nothing_and_says_so_by_name(self):
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(step.state, STATE_NOTHING_ON_THE_GROUND)
        self.assertEqual(step.frames, ())
        self.assertEqual(step.rows, ())
        self.assertIsNone(step.oldest_seconds_left)

    def test_drops_are_only_a_label_never_the_source_of_the_generation(self):
        """Passing the wrong tuple cannot produce a wrong generation.

        The only thing ``drops`` can change is the announced/carried split on
        the console line.  This is the property that makes a partial
        generation unrepresentable rather than merely discouraged.
        """
        first = self.kill(0)
        honest = sustain_a_kill(self.cell, self.legacy, first)
        lying = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(tuple(honest.frames), tuple(lying.frames))
        self.assertEqual(honest.live, lying.live)
        self.assertEqual((honest.announced, lying.announced),
                         (len(first), 0))


class _ScriptedClock:
    """A clock whose every reading is written down in advance.

    ``_Clock`` above cannot express the failure below, because it returns the
    same number until a test moves it: the defect this pins only exists when
    the clock moves BETWEEN two reads inside one call.
    """

    def __init__(self, readings):
        self.readings = list(readings)
        self.last = self.readings[0]

    def __call__(self):
        if self.readings:
            self.last = self.readings.pop(0)
        return self.last


class OneSnapshotTests(unittest.TestCase):
    """The record must never describe rows the frames do not carry.

    FOUND BY THIS ROUND'S OWN MUTATION SWEEP, and it is the one mutant the new
    test file did not kill: composing with ``cell.frames(legacy)`` instead of
    ``mob_loot.refresh_frames(legacy, <the snapshot>)`` reads the cell a SECOND
    time, and the ``ledger`` property sweeps -- so a row that was live when the
    record described it can be gone by the time the bytes are composed.  The
    module already avoided it deliberately (there is a comment saying so), but
    a comment is not a pin: with a frozen clock both spellings are identical
    and every other test in this file stayed green.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster(scene=field_mobs.BG0002_SCENE)

    def test_a_row_that_expires_between_two_reads_cannot_split_the_record(self):
        mob = self.roster[0]
        for seed in range(60):
            roll = mob_loot.roll_drops(mob, random.Random(seed))
            if roll.placeable_count:
                break
        else:                                        # pragma: no cover
            self.skipTest("this mob's tables drop nothing")

        # FOUR readings is the whole correct call, counted rather than
        # guessed: construction, loot_a_kill's sweep, the one ledger snapshot,
        # and one time_left for the one row.  Everything after that is past
        # the deadline, so a fifth reading -- which only a SECOND read of the
        # cell can cause -- sweeps the row away underneath the record.
        clock = _ScriptedClock([1000.0] * 4 + [9999.0] * 8)
        cell = mob_loot.DropLedgerCell(lifetime_seconds=60.0, clock=clock)
        cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)), kill_token=1)

        step = sustain_a_kill(cell, self.legacy, ())
        self.assertTrue(step.rows)
        self.assertTrue(
            step.frames,
            "the record describes %d row(s) and the generation carries none: "
            "the cell was read twice" % step.live)


class TrimTests(PresenceTestBase):
    def test_rows_that_cannot_travel_are_removed_from_the_cell_too(self):
        """A client and a server that disagree is worse than a lost drop.

        A generation that omits a live key erases that key on the client
        (RE-130).  So when the ground will not fit in one frame, the rows that
        do not travel must not stay live in the cell -- otherwise the server
        would hold a row the client has been told to forget, and a click on it
        could never arrive.  Unreachable on today's numbers (16 drops per kill,
        a 2426-element cap); the cap is patched here rather than waited for.
        """
        for index in range(3):
            self.kill(index)
        before = len(self.cell.ledger.drops)
        self.assertGreaterEqual(before, 3)

        original = mob_loot.DROP_MAX_ELEMENTS_PER_FRAME
        mob_loot.DROP_MAX_ELEMENTS_PER_FRAME = 2
        try:
            step = sustain_a_kill(self.cell, self.legacy, ())
        finally:
            mob_loot.DROP_MAX_ELEMENTS_PER_FRAME = original

        self.assertEqual(step.state, STATE_TRIMMED_TO_FIT)
        self.assertEqual(step.live, 2)
        self.assertEqual(step.trimmed, before - 2)
        # The cell agrees with the frame, which is the whole point.
        self.assertEqual(
            {drop.drop_key for drop in self.cell.ledger.drops},
            {row.drop_key for row in step.rows})
        # The rows kept are the NEWEST, because a player is reaching for the
        # thing that just fell, not for the thing that fell two minutes ago.
        self.assertEqual(
            sorted(row.drop_key for row in step.rows),
            sorted(drop.drop_key for drop in self.cell.ledger.drops))


class CostTests(PresenceTestBase):
    """The sum the module docstring states, pinned rather than asserted in prose.

    "Too much to spend on a mechanism nobody has measured" is the sentence the
    COO refused ``DROP_REFRESH_MS`` with, so a shape that widens a generation
    owes the same arithmetic in a form that can go red.
    """

    def test_the_generation_grows_by_about_one_element_per_row(self):
        """ROUND KA1B-DROPMODEL FOLLOW-UP, 2026-09-01: the per-row cost was
        pinned at 26-29 bytes, which was ``DROP_ELEMENT_SIZE`` (27, the
        narrow mask-0x12 element).  ``sustain_a_kill`` now composes through
        ``refresh_frames`` -> ``drop_frames_with_model_type`` (NONCLAIM 23),
        so each row costs ``DROP_ELEMENT_SIZE_WITH_MODEL_TYPE`` (30) instead
        -- a deliberate, understood shape change, not a drift."""
        sizes = []
        for index in range(len(self.dropping)):
            self.kill(index)
            step = sustain_a_kill(self.cell, self.legacy, ())
            sizes.append(
                (step.live, sum(len(f) for _pc, f in step.frames)))
            if len(sizes) >= 4:
                break
        self.assertGreaterEqual(len(sizes), 2, "need two widths to measure")
        (rows_a, bytes_a), (rows_z, bytes_z) = sizes[0], sizes[-1]
        slope = (bytes_z - bytes_a) / (rows_z - rows_a)
        self.assertEqual(mob_loot.DROP_ELEMENT_SIZE_WITH_MODEL_TYPE, 30)
        self.assertGreater(slope, 29.0)
        self.assertLess(slope, 32.0)

    def test_a_one_row_ground_now_costs_the_exact_57_bytes_of_the_wide_shape(self):
        """ROUND KA1B-DROPMODEL FOLLOW-UP, 2026-09-01, RENAMED AND UPDATED.

        ~~test_a_one_row_ground_still_costs_the_exact_54_bytes_of_gt045~~ IS
        STRUCK: it pinned ``sustain_a_kill``'s (i.e. ``refresh_frames``'s)
        own composed output at the narrow 54-byte GT-045 shape.  That is now
        the WRONG pin for this call chain -- ``refresh_frames`` deliberately
        calls ``drop_frames_with_model_type`` as of this round (NONCLAIM
        23), so the real production path's one-row cost is the wide 57-byte
        frame (``DROP_FRAME_SIZE_WITH_MODEL_TYPE``), not GT-045's 54.
        GT-045's own 54-byte shape stays pinned byte-for-byte, forever,
        against ``mob_loot.drop_frames`` directly (untouched by this round)
        in tests/test_mob_loot.py and tests/test_ground_drop_multi_drop_
        emission_shape.py -- this test pins the OTHER function, not that
        one.  Built by taking rows back off the ground rather than by
        hunting a one-drop seed: a test that depends on a drop table's
        contents goes red when somebody edits the table.
        """
        drops = self.kill()
        for drop in drops[1:]:
            self.cell.take(drop.drop_key)
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(step.live, 1)
        self.assertEqual(
            sum(len(f) for _pc, f in step.frames),
            mob_loot.DROP_FRAME_SIZE_WITH_MODEL_TYPE)
        self.assertEqual(mob_loot.DROP_FRAME_SIZE_WITH_MODEL_TYPE, 57)

    def test_one_kill_is_always_one_frame_however_wide_the_ground_is(self):
        for index in range(len(self.dropping)):
            self.kill(index)
            step = sustain_a_kill(self.cell, self.legacy, ())
            self.assertEqual(len(step.frames), 1)
            if step.live >= 3:
                break
        self.assertGreaterEqual(step.live, 2)


class FailClosedTests(PresenceTestBase):
    """The listener thread must survive every one of these."""

    def test_a_value_beside_the_cell_is_refused_by_name(self):
        step = sustain_a_kill(self.cell.ledger, self.legacy, ())
        self.assertEqual(step.state, REFUSE_NOT_A_CELL)
        self.assertTrue(step.refused)
        self.assertEqual(step.frames, ())

    def test_a_legacy_that_cannot_frame_is_refused_not_raised(self):
        self.kill()
        step = sustain_a_kill(self.cell, None, ())
        self.assertTrue(step.refused)
        self.assertEqual(step.frames, ())

    def test_a_cell_whose_clock_raises_is_refused_not_raised(self):
        def broken():
            raise RuntimeError("the clock went away")

        cell = mob_loot.DropLedgerCell(clock=_Clock())
        self.kill(cell=cell)
        cell._clock = broken
        step = sustain_a_kill(cell, self.legacy, ())
        self.assertEqual(step.state, REFUSE_CELL_RAISED)
        self.assertEqual(step.frames, ())
        self.assertEqual(presence_snapshot(cell).state, REFUSE_CELL_RAISED)

    def test_every_refusal_returns_an_iterable_frames_field(self):
        """A call site with no branch must be correct in all four states."""
        self.kill()
        steps = (
            sustain_a_kill(self.cell, self.legacy, ()),
            sustain_a_kill(None, self.legacy, ()),
            sustain_a_kill(self.cell, None, ()),
            presence_snapshot(self.cell),
        )
        for step in steps:
            self.assertEqual(list(step.frames), list(step.frames))
            describe_presence(step)


class SnapshotTests(PresenceTestBase):
    def test_a_snapshot_never_emits(self):
        self.kill()
        step = presence_snapshot(self.cell)
        self.assertEqual(step.state, STATE_SNAPSHOT)
        self.assertEqual(step.frames, ())
        self.assertTrue(step.rows)

    def test_a_snapshot_of_an_empty_ground_says_so(self):
        self.assertEqual(
            presence_snapshot(self.cell).state, STATE_NOTHING_ON_THE_GROUND)

    def test_a_snapshot_of_something_that_is_not_a_cell_is_refused(self):
        self.assertEqual(presence_snapshot(object()).state, REFUSE_NOT_A_CELL)


class ConsoleLineTests(PresenceTestBase):
    def test_the_line_is_ascii_one_line_and_greppable(self):
        self.kill()
        line = describe_presence(sustain_a_kill(self.cell, self.legacy, ()))
        self.assertTrue(line.startswith(CONSOLE_TOKEN))
        self.assertNotIn("\n", line)
        line.encode("ascii")            # the bridge console is cp874

    def test_the_line_declares_the_lifetime_this_cell_actually_uses(self):
        """chief's letter 2105 point 2, and the defect it prevents.

        A line that printed ``DROP_LIFETIME_SECONDS`` would describe a cell
        built with a different lifetime by a number that cell does not use --
        the same class of defect as a lane-asserted length field that can
        disagree with the payload it describes.
        """
        cell = mob_loot.DropLedgerCell(lifetime_seconds=30.0, clock=self.clock)
        self.kill(cell=cell)
        line = describe_presence(sustain_a_kill(cell, self.legacy, ()))
        self.assertIn("declared_lifetime=30.0s", line)
        self.assertNotIn(
            "declared_lifetime=%.1fs" % mob_loot.DROP_LIFETIME_SECONDS, line)

    def test_the_line_reports_the_split_between_announced_and_carried(self):
        first = self.kill(0)
        sustain_a_kill(self.cell, self.legacy, first)
        second = self.kill(1)
        line = describe_presence(
            sustain_a_kill(self.cell, self.legacy, second))
        self.assertIn("announced=%d" % len(second), line)
        self.assertIn("carried=%d" % len(first), line)
        self.assertIn("live=%d" % (len(first) + len(second)), line)

    def test_the_line_cannot_claim_a_redraw_nobody_measured(self):
        self.kill()
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertIsNone(mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL)
        self.assertIn("redraw=unmeasured", describe_presence(step))
        # And the word is READ from the constant, not written into the string:
        # the day an attended round measures a redraw, the line changes with
        # the fact and not with an edit.
        mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL = True
        try:
            self.assertIn("redraw=yes", describe_presence(step))
        finally:
            mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL = None

    def test_the_line_carries_the_measured_label_life_as_a_range(self):
        self.kill()
        line = describe_presence(sustain_a_kill(self.cell, self.legacy, ()))
        self.assertIn("label_life=0.2-0.4s", line)

    def test_something_that_is_not_a_step_gets_a_refusal_not_a_traceback(self):
        self.assertIn("not_a_presence_step", describe_presence({"live": 3}))


class TheTwoNumbersAreDifferentThingsTests(PresenceTestBase):
    """The finding of this round, pinned so it cannot be re-conflated.

    chief's letter handed this lane ``DROP_LIFETIME_SECONDS=120`` as the lever
    for "the element vanishes in under a second".  It is not that lever, and a
    test is where that sentence stops being an opinion.
    """

    def test_the_declared_lifetime_is_already_tens_of_seconds(self):
        # STRENGTHENED (round qf83nz, S7 debt carried from pf-adversary's
        # m0vp7m pass): the old body was ``assertGreaterEqual(..., 30.0)``,
        # which accepts anything from 30.0 to 3600.0 as equally fine -- a
        # mutant that quietly narrowed the interim figure toward a
        # sub-minute value (say 31.0, still "tens of seconds") would have
        # survived unnoticed.  This pins the exact figure COO-DECISION
        # 2026-08-29T14:44+07:00 item 1 accepted (INTERIM, not measured --
        # GT-149 DROP-LIFETIME-MEASURE-001 is the ticket that replaces it;
        # see the constant's own comment in mob_loot.py) AND the tripwire
        # ceiling it must stay under, so the assertion is anchored to two
        # independent module facts instead of one loose literal bound.
        self.assertEqual(mob_loot.DROP_LIFETIME_SECONDS, 120.0)
        self.assertLessEqual(
            mob_loot.DROP_LIFETIME_SECONDS,
            mob_loot.MAX_DROP_LIFETIME_SECONDS)

    def test_the_label_life_is_a_range_and_is_two_orders_smaller(self):
        self.assertLess(
            LABEL_LIFE_SECONDS_MAX * 100, mob_loot.DROP_LIFETIME_SECONDS)
        self.assertLess(LABEL_LIFE_SECONDS_MIN, LABEL_LIFE_SECONDS_MAX)
        # No midpoint constant, ever: GT-045's own evidence letter forbids
        # writing 0.30 or "about a quarter of a second".  Asserted against the
        # module's VALUES rather than against its text -- a first draft of this
        # test grepped the source for "0.3" and went red on the docstring
        # sentence that forbids it, which is a test measuring prose.
        midpoints = {
            name: value
            for name, value in vars(mob_drop_presence).items()
            if isinstance(value, float)
            and LABEL_LIFE_SECONDS_MIN < value < LABEL_LIFE_SECONDS_MAX
        }
        self.assertEqual(midpoints, {})

    def test_the_observation_that_opened_this_work_is_recorded_as_a_bound(self):
        self.assertLessEqual(
            LABEL_LIFE_SECONDS_MAX,
            mob_drop_presence.LABEL_LIFE_OBSERVED_UNDER_SECONDS)


class AdversaryMutantTests(PresenceTestBase):
    """One test per mutant pf-adversary got past the whole suite (round m0vp7m).

    Every one of these was green before it was written, which is the only
    interesting property a regression test has.
    """

    def test_M_A_the_dispatch_action_carries_pc_then_frame_in_that_order(self):
        """The worst one: the ask was prose, so its tuple order was unpinned.

        Swapping the two names inside DROP_PRESENCE_WIRING kept the suite
        green while every ground drop would have gone out with the 44-byte pc
        in the frame slot.  The tuple is code now; this is its pin.
        """
        self.kill()
        step = sustain_a_kill(self.cell, self.legacy, ())
        actions = mob_drop_presence.loot_actions(step)
        self.assertEqual(len(actions), len(step.frames))
        for (label, pc, frame, delay), (want_pc, want_frame) in zip(
                actions, step.frames):
            self.assertEqual(label, mob_drop_presence.ACTION_LABEL)
            self.assertIs(pc, want_pc)
            self.assertIs(frame, want_frame)
            self.assertEqual(delay, 0.0)
            # And the halves are not interchangeable: the frame CONTAINS the
            # pc, so a swap is detectable without knowing either length.
            self.assertIn(bytes(pc), bytes(frame))
            self.assertGreater(len(frame), len(pc))

    def test_M_A_every_refusal_still_yields_an_empty_action_tuple(self):
        for step in (sustain_a_kill(None, self.legacy, ()),
                     sustain_a_kill(self.cell, self.legacy, ()),
                     presence_snapshot(self.cell),
                     "not a step"):
            self.assertEqual(mob_drop_presence.loot_actions(step), ())

    def test_M_B_the_console_byte_count_is_the_frames_not_the_pcs(self):
        self.kill()
        step = sustain_a_kill(self.cell, self.legacy, ())
        line = describe_presence(step)
        frames = sum(len(f) for _pc, f in step.frames)
        pcs = sum(len(pc) for pc, _f in step.frames)
        self.assertNotEqual(frames, pcs)
        self.assertIn("frame_bytes=%d" % frames, line)
        self.assertNotIn("frame_bytes=%d" % pcs, line)

    def test_M_C_oldest_is_the_smallest_remaining_life_not_the_largest(self):
        self.kill(0)
        sustain_a_kill(self.cell, self.legacy, ())
        self.clock.advance(25.0)
        self.kill(1)
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertLess(step.oldest_seconds_left, step.newest_seconds_left)
        self.assertAlmostEqual(
            step.oldest_seconds_left,
            mob_loot.DROP_LIFETIME_SECONDS - 25.0, places=6)
        self.assertAlmostEqual(
            step.newest_seconds_left, mob_loot.DROP_LIFETIME_SECONDS, places=6)

    def test_M_D_the_attended_observation_is_pinned_to_what_gt146_reported(self):
        """It is an OBSERVER_CONFIRMED number; it may not drift silently."""
        self.assertEqual(
            mob_drop_presence.LABEL_LIFE_OBSERVED_UNDER_SECONDS, 1.0)

    def test_M_E_a_measured_no_prints_no_not_yes(self):
        self.kill()
        step = sustain_a_kill(self.cell, self.legacy, ())
        for value, word in ((None, "unmeasured"), (True, "yes"), (False, "no")):
            mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL = value
            try:
                self.assertIn("redraw=%s" % word, describe_presence(step))
            finally:
                mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL = None

    def test_M_F_a_row_carries_the_drops_own_display_name(self):
        drops = self.kill()
        step = sustain_a_kill(self.cell, self.legacy, drops)
        by_key = {row.drop_key: row.name for row in step.rows}
        for drop in drops:
            self.assertEqual(by_key[drop.drop_key], drop.display_name)
            self.assertTrue(by_key[drop.drop_key])

    def test_S3_a_drops_argument_that_is_not_iterable_does_not_raise(self):
        self.kill()
        for bad in (5, object(), 3.5):
            step = sustain_a_kill(self.cell, self.legacy, bad)
            self.assertEqual(step.state, STATE_SUSTAINED)
            self.assertEqual(step.announced, 0)

    def test_S4_a_deadline_that_passes_mid_call_costs_the_number_not_the_loot(
        self,
    ):
        """The severe one.  A cosmetic console number was costing a kill's loot.

        ``_row`` calls ``time_left``, which sweeps.  A row crossing its
        deadline in that window used to raise, and the whole step refused with
        ``frames=()`` -- so a monster that had just died left the ground empty
        forever while the server still held the rows.
        """
        drops = self.kill()
        # Every reading from the first row's time_left onward is past the
        # deadline: construction, loot_a_kill, the ledger snapshot, then jump.
        cell = mob_loot.DropLedgerCell(
            lifetime_seconds=60.0,
            clock=_ScriptedClock([1000.0] * 3 + [9999.0] * 12))
        mob, seed = self.dropping[0]
        cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)), kill_token=1)
        step = sustain_a_kill(cell, self.legacy, drops)
        self.assertFalse(step.refused, step.detail)
        self.assertTrue(step.rows)
        self.assertTrue(step.frames, "the kill's loot was thrown away")
        self.assertEqual(step.stale, step.live)
        self.assertIsNone(step.oldest_seconds_left)
        self.assertIn("stale=%d" % step.stale, describe_presence(step))

    def test_S5_a_kill_wider_than_the_cap_still_sends_what_fits(self):
        """The trim branch used to refuse instead of trimming.

        ``prune_issued_before`` refuses ``prune_would_take_the_newest_kill``
        when the cut lands inside the newest kill's block -- which is exactly
        the shape that crosses a cap: one kill wider than the whole frame.
        """
        # ONE kill wider than the cap is the shape that matters, and it is the
        # shape a cut point cannot express: pruning below the surviving row
        # means pruning INTO the newest kill's own block, which
        # prune_issued_before refuses by name.  A two-kill ground would let
        # the mutant pass, so this test hunts a multi-drop roll rather than
        # accepting whichever ground the default seeds happen to build.
        mob, seed = None, None
        for candidate in self.roster:
            for trial in range(400):
                if mob_loot.roll_drops(
                        candidate, random.Random(trial)).placeable_count >= 2:
                    mob, seed = candidate, trial
                    break
            if mob is not None:
                break
        if mob is None:                              # pragma: no cover
            self.skipTest("no roll in this scene drops two rows")
        drops = self.cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)), kill_token=1)
        live_before = len(self.cell.ledger.drops)
        self.assertGreaterEqual(len(drops), 2, "this test needs one wide kill")
        self.assertEqual(live_before, len(drops))

        original = mob_loot.DROP_MAX_ELEMENTS_PER_FRAME
        mob_loot.DROP_MAX_ELEMENTS_PER_FRAME = 1
        try:
            step = sustain_a_kill(self.cell, self.legacy, drops)
        finally:
            mob_loot.DROP_MAX_ELEMENTS_PER_FRAME = original

        self.assertFalse(step.refused, step.detail)
        self.assertEqual(step.state, STATE_TRIMMED_TO_FIT)
        self.assertEqual(step.live, 1)
        self.assertEqual(step.trimmed, live_before - 1)
        self.assertTrue(step.frames)
        # The cell and the generation name the same set afterwards.
        self.assertEqual(
            {drop.drop_key for drop in self.cell.ledger.drops},
            {row.drop_key for row in step.rows})

    def test_S6_the_call_site_records_one_event_on_every_outcome(self):
        self.kill()
        seen = set()
        for step in (sustain_a_kill(self.cell, self.legacy, ()),
                     sustain_a_kill(None, self.legacy, ()),
                     presence_snapshot(self.cell)):
            event = mob_drop_presence.presence_event(step)
            self.assertTrue(event.startswith("mob_drop_presence_"))
            # The entry has to SAY something: an operator grepping the session
            # record must be able to tell a sustained kill from a refusal, and
            # a one-row ground from a ten-row one.
            self.assertIn(step.state, event)
            self.assertIn("live_%d" % step.live, event)
            event.encode("ascii")
            seen.add(event)
        self.assertEqual(len(seen), 3, "three outcomes, three distinct entries")
        self.assertIn(
            "not_a_presence_step",
            mob_drop_presence.presence_event(object()))


class ModuleShapeTests(unittest.TestCase):
    @staticmethod
    def _imported_names():
        """Every module name this file imports, from its AST.

        The import list is the honest place to assert both properties below:
        a module that imports no clock cannot have a timer, and a module that
        imports no probe lane cannot be gated by one.  Grepping the source
        text asserts the same thing about the DOCSTRINGS as about the code --
        the first draft of these two tests went red on the module docstring
        that names ``DROP_REFRESH_MS`` in order to say it is not used here.
        """
        import ast

        tree = ast.parse(
            (SRC / "mob_drop_presence.py").read_text(encoding="ascii"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module or "")
                names.update(alias.name for alias in node.names)
        return names

    def test_the_module_is_production_and_has_no_flag(self):
        self.assertIs(mob_drop_presence.production_allowed, True)
        for name in self._imported_names():
            for forbidden in ("hypothesis", "scenario", "probe", "diag"):
                self.assertNotIn(forbidden, name.lower())

    def test_the_module_has_no_thread_and_no_timer(self):
        """ON A TIMER is the part the COO refused (2026-08-26 07:45 +07:00).

        The import list alone is NOT enough, and pf-adversary (round m0vp7m)
        showed why by execution: ``mob_loot`` already imports ``threading``
        and ``time``, so ``mob_loot.threading.Timer(0.08, ...)`` written in
        this file adds a timer while every import stays innocent.  The
        attribute names are checked too.
        """
        import ast

        for name in self._imported_names():
            for forbidden in ("threading", "time", "sched", "asyncio"):
                self.assertNotIn(forbidden, name.lower())
        tree = ast.parse(
            (SRC / "mob_drop_presence.py").read_text(encoding="ascii"))
        reached = {
            node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        for forbidden in ("threading", "Timer", "monotonic", "sleep",
                          "perf_counter", "Thread", "DROP_REFRESH_MS",
                          "refresh_frames_on_a_timer"):
            self.assertNotIn(forbidden, reached)

    def test_the_wiring_ask_names_the_two_lines_it_replaces(self):
        wiring = mob_drop_presence.DROP_PRESENCE_WIRING
        self.assertIn("sustain_a_kill", wiring)
        self.assertIn("take(drop.drop_key)", wiring)
        self.assertIn("prune_previous_kills", wiring)
        wiring.encode("ascii")

    def test_the_wiring_ask_is_fulfilled_re_derived_from_runtime_py(self):
        """THE OTHER DIRECTION of round hpronz's GT-124 tripwire.

        That round's finding (repeated in round j0u64p's letter) was that a
        hand-typed OWNER string cannot self-report going stale once a call
        site starts existing.  ``DROP_PRESENCE_WIRING`` is the same shape of
        string, describing an ask instead of a blocker, and it went stale the
        other way: chief wired it (commit 432381a2, round t7t5yd) and no
        round since has re-derived that fact from source, only from a commit
        message and a behavioural dispatcher test
        (``tests/test_mob_drop_presence_wiring.py``).  This test closes that
        gap with the same tool -- an AST walk over ``runtime.py`` -- rather
        than trusting either the commit message or this test's own comment.

        The four symbols are regex-extracted from ``DROP_PRESENCE_WIRING``
        itself (``mob_drop_presence.<name>(``), not hand-copied a second
        time, so a future edit to the ask's own wording keeps this test
        honest about what it is checking.
        """
        import re

        wiring = mob_drop_presence.DROP_PRESENCE_WIRING
        symbols = re.findall(r"mob_drop_presence\.(\w+)\(", wiring)
        self.assertEqual(
            sorted(symbols),
            sorted(
                ["sustain_a_kill", "describe_presence", "loot_actions",
                 "presence_event"]
            ),
            "DROP_PRESENCE_WIRING's four mob_drop_presence.<name>( calls "
            "changed shape -- this test's expectation needs updating "
            "alongside it before its result can be trusted.",
        )
        runtime_calls = _call_names("runtime")
        missing = [name for name in symbols if name not in runtime_calls]
        self.assertEqual(
            missing, [],
            f"runtime.py no longer calls {missing} -- DROP_PRESENCE_WIRING's "
            "ask has regressed (or was never really wired the way this "
            "module's docstring now claims).  mob_drop_presence.py's "
            "'STATUS: WIRED' note needs this round's attention, not a "
            "silent green.",
        )

    def test_the_step_is_a_typed_record_not_a_dict(self):
        self.assertTrue(issubclass(PresenceStep, tuple))


class CellAccessorTests(PresenceTestBase):
    """The two accessors this round added to mob_loot.DropLedgerCell."""

    def test_lifetime_seconds_is_the_constructors_value(self):
        self.assertEqual(
            mob_loot.DropLedgerCell(lifetime_seconds=45.0).lifetime_seconds,
            45.0)
        self.assertEqual(
            mob_loot.DropLedgerCell().lifetime_seconds,
            mob_loot.DROP_LIFETIME_SECONDS)

    def test_time_left_is_one_reading_of_the_clock(self):
        drops = self.kill()
        key = drops[0].drop_key
        self.assertAlmostEqual(
            self.cell.time_left(key), mob_loot.DROP_LIFETIME_SECONDS,
            places=6)
        self.clock.advance(30.0)
        self.assertAlmostEqual(
            self.cell.time_left(key), mob_loot.DROP_LIFETIME_SECONDS - 30.0,
            places=6)

    def test_time_left_refuses_a_key_that_is_not_on_the_ground(self):
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            self.cell.time_left(mob_loot.DROP_KEY_BASE)
        self.assertEqual(caught.exception.args[0],
                         mob_loot.REFUSE_DROP_NOT_IN_LEDGER)

    def test_time_left_never_returns_a_negative_remainder(self):
        """The reason it is not ``expires_at() - clock()``.

        Two lock acquisitions with a clock read in each can straddle the
        deadline, and a caller would then have to decide what a negative
        remainder means.  One locked read cannot: the row is swept first, so
        either it is live and the remainder is positive, or it refuses.
        """
        drops = self.kill()
        key = drops[0].drop_key
        self.clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 5.0)
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            self.cell.time_left(key)
        self.assertEqual(caught.exception.args[0],
                         mob_loot.REFUSE_DROP_NOT_IN_LEDGER)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
