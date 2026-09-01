"""LANE-B / MOB-DROP-PRESENCE-001: what a kill leaves on the ground STAYS there.

WHY THIS MODULE EXISTS, IN THE OWNER'S OWN WORDS.  PANYA-ORDER 2026-08-29
(pf_bridge notes_to_chief/20260829_2013_KA3A-GT146-RESULT-*, relayed to this
lane as 20260829_2105_CHIEF-TO-LANE-B-persist-first-element-lifetime-before-
any-capture.md):

    "go make the thing stay for a long time FIRST, before you hand a tester
     something that appears for a tenth of a second"

THE FIRST THING THIS MODULE HAD TO DO WAS SPLIT THAT ORDER IN TWO, because
"it does not stay" is two independent holes with two different owners, and
the lever the order was handed with only touches one of them:

  HOLE 1 -- THE SERVER'S ROW.  ``mob_loot.DropLedgerCell`` keeps a row for
    ``DROP_LIFETIME_SECONDS`` (120.0 s today).  That is already tens of
    seconds, so ``DROP_LIFETIME_SECONDS`` is NOT the lever that fixes what a
    tester sees -- and this lane says so in the module rather than only in a
    letter.  The row is nevertheless gone within microseconds today, and not
    by expiry: the dispatch call site takes every key of the kill it just
    announced (``runtime.py`` "for drop in drops: cell.take(...)"), measured
    by chief in round ni2wh2 as ``drop_already_taken`` on 100% of pickups.
    Fixing that is TWO LINES in a file this lane does not own -- see
    :data:`DROP_PRESENCE_WIRING`.

    **THIS IS NOW WIRED.**  Chief's commit ``432381a2`` (round ``t7t5yd``,
    2026-08-30T01:33+07:00) put the ask into ``runtime.py``'s MOB_LOOT block
    -- the commit message's own words are "is the five DROP_PRESENCE_WIRING
    lines verbatim".  Read that as a fact about ``runtime.py`` re-derived by
    a test, not as this sentence: ``tests/test_mob_drop_presence.py``'s
    ``ModuleShapeTests.test_the_wiring_ask_is_fulfilled_re_derived_from_
    runtime_py`` parses the four ``mob_drop_presence.<name>(`` calls the ask
    below names and confirms ``runtime.py``'s own AST really calls all four
    today; ``tests/test_mob_drop_presence_wiring.py`` separately drives the
    real dispatcher through a kill and pins the resulting behaviour.  The ask
    text right below is kept as it was written -- this lane does not rewrite
    an ask after the fact -- but a reader landing on it from the module
    docstring should not treat it as still open.

  HOLE 2 -- THE CLIENT'S LABEL.  GT-045 measured the floating red name at
    0.2-0.4 s of screen life (frame-extracted, and the recorder duplicates
    frames in threes, so the number may not be written more precisely than
    that).  NO server-side lifetime value can change that number: the label
    is drawn on receipt of a frame and the server sends nothing else.  The
    only lever this lane has on it is RE-EMISSION, and whether re-emission
    redraws the label at all is UNMEASURED -- see
    :data:`REEMISSION_REDRAWS_THE_LABEL`, which is ``None`` and is read by
    the console line rather than assumed by it.

WHAT THIS MODULE SHIPS, AND WHY IT IS NOT A TIMER.  The COO refused
``DROP_REFRESH_MS`` on any production path on 2026-08-26 (07:45 +07:00):
12.5 frames a second per row is too much to spend on a mechanism nobody has
measured.  ON A TIMER is the refused part, and this module does not have one:
no thread, no interval, no clock of its own.  What it implements is the shape
``mob_loot``'s own MOB_LOOT_WIRING step 4b already wrote down and left to the
caller, and which that step says the refusal does not cover:

    keep the rows, and send ``cell.frames(legacy)`` -- the WHOLE LIVE
    LEDGER as one generation -- once per kill.  "That is a shape change,
    not a cadence change ... what it does need is an expiry or a pickup,
    because without one the ledger and the generation both grow without
    bound."

THE EXPIRY IT NEEDED NOW EXISTS (round 0n9inw, COO-DECISION 2026-08-29T12:41
+07:00, per-drop and lazy).  So the precondition step 4b named is satisfied
and this is a shippable behaviour, not a proposal.

~~[ASSUMPTION OF LANE B - AWAITING COO] Step 5 of the same header also says
"ONE ANNOUNCEMENT PER DROP -- each drop announced ONCE and never
re-announced", and this shape re-announces a live row on every later kill.
This lane reads the two together the way step 4b itself does -- step 5 names
itself a CADENCE rule, the COO's refusal names ON A TIMER as the refused
part, and there is no timer here: the number of emissions equals the number
of kills exactly, and one kill is still ONE frame however wide the ground is.
The letter asking the COO to confirm or overturn that reading is
pf_bridge/notes_to_chief/20260829_2248_LANE-B-ASK-COO-whole-live-ledger-per-
kill-vs-announce-once.md.~~  RULED, round qf83nz: COO-DECISION
2026-08-29T23:42+07:00 (pf_bridge/notes_to_chief/20260829_2342_COO-DECISION-
whole-floor-generation-not-covered-by-timer-refusal.md) confirms this
reading -- the 2026-08-26 refusal covers ON A TIMER only, shape (a) has no
timer, and what shipped stands.  The condition COO attached is the one this
module already pins: ``test_one_kill_is_always_one_frame_however_wide_the_
ground_is`` (emissions == kills, never a cadence) and ``test_rows_that_
cannot_travel_are_removed_from_the_cell_too`` (the trim in :func:`sustain_a_
kill`) must not be removed.  IF THIS READING IS LATER OVERTURNED the
rollback is still one line at the call site (``step.frames`` ->
``mob_loot.drop_frames(legacy, drops)``); nothing else in the tree depends
on this shape.

WHAT CHANGES FOR THE PLAYER, STATED SO IT CAN BE FALSIFIED.  RE-130 measured
the consumer erasing every key a nonempty generation OMITS.  Today each kill
announces only its own rows, so the second kill's generation ERASES the first
kill's drops out of the client's keyed tree -- a player who kills two monsters
has one monster's loot on the ground, and the older one vanishes at the exact
moment the newer one appears.  Under this module's shape every generation
carries every live row, so:

  * a drop stays in the client's keyed tree for its whole 120 s, instead of
    being erased by the next kill;
  * a live drop's label is REDRAWN on every later kill (event-driven, no
    timer) -- which is the first thing an attended round can decide, because
    "did the older label come back when the second monster died" is one boot
    and one pair of eyes.  THAT PROOF IS RUNNABLE: pf-adversary (S1b) held
    that it is not, quoting this lane's own letter 20260829_2058 that no
    Bg0002 monster can die -- and that letter is WRONG, measured this round.
    Four Bg0002 mobs (0x2033 Tornado Eagle template 31, 0x203B-0x203D
    Fighting Fish soldier template 34) go 3857/3138 -> 0 in one hit and
    ``mob_death.kill(..., widened=mob_death.ruling_for(mob))`` ACCEPTS every
    one, dying and dead frames 172 bytes each, hold 700 ms.  The permit is
    PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18), templates
    {31, 34, 35, 103} tied to scene "Bg0002", and ``runtime.py`` passes
    ``mob_death.ruling_for(mob)`` -- it derives the right ruling per mob.
    What letter 2058 measured was its own script naming the 916 ruling BY
    HAND for a template-31 mob;
  * the ground ACCUMULATES within the lifetime instead of being replaced.

THE COST, AS ARITHMETIC RATHER THAN ADJECTIVES -- because "too expensive for
a mechanism nobody has measured" is the exact sentence the COO refused
``DROP_REFRESH_MS`` with, and this shape owes the same sum.  MEASURED on the
real composer, not estimated: one live row is 54 bytes framed and each further
row adds 27.3 (54, 82, 109, 136, ... at 1, 2, 3, 4 rows).  Emissions equal
KILLS, not seconds, and one kill is always ONE frame however wide the ground
is.  So a player killing something every three seconds for the whole 120 s
lifetime, with every kill dropping the 16-row maximum, reaches ~640 live rows
= ~17 KB in the last frame, and averages under 6 KB/s.  The refused timer, on
the same ground, would have been 12.5 frames a second PER ROW: ~430 KB/s.
Two orders of magnitude is the difference, and it is a difference in kind --
one is bounded by how fast a player can kill, the other by a clock.

WHAT IT DOES NOT CLAIM.  Nothing here picks anything up, writes a row, or
makes a label live longer than 0.2-0.4 s on its own.  Between kills a live
drop is UNDRAWN, and whether an undrawn key is still clickable is UNMEASURED
-- it is the open half of GT-146 and this module reports it as ``unmeasured``
on its own console line rather than implying either answer.

FAIL-CLOSED, AND WHY IT MATTERS HERE SPECIFICALLY.  Every entry point returns
a typed record; none raises at the caller.  The call site is the dispatch path
inside the listener thread (the same reasoning ``mob_scene_recompose`` and
``mob_ledger_admission`` wrote down): an exception escaping into it does not
cost a drop, it costs the connection.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from . import mob_loot


production_allowed = True


# ---------------------------------------------------------------------------
# The two numbers that are MEASURED -- AND THE EMITTER THEY WERE MEASURED ON,
# which is NOT the emitter this module drives.  READ THIS BEFORE CITING THEM.
#
# pf-adversary (round m0vp7m, S1) refuted the first draft of this section by
# execution and it is the most important correction in the file.  BOTH numbers
# below were measured on ``ground_loot_hypothesis`` (HYP-PF-032): a
# SCENARIO-GATED probe that emits its own two hard-coded elements once per
# session, latched by ``ground_loot_pair_sent``, fired by a TargetPosVital
# W-tap -- not by a kill, and never touching ``DropLedgerCell``,
# ``drop_frames`` or a drop key.  GT-146's own RECV census confirms it: no
# monster was attacked and none died in that boot.
#
# THIS MODULE DRIVES ``mob_loot``'s PER-KILL EMITTER, WHICH NO ATTENDED SESSION
# HAS EVER OBSERVED (docs/FUNCTIONAL_COVERAGE.json says so in its own words).
# The elements are the same 44 bytes by construction -- mob_loot re-derives the
# encoder and pins it against the probe lane's own element for element -- so
# carrying the label's behaviour across is a REASONABLE INFERENCE.  It is an
# inference, it is written here as one, and the round that cites these numbers
# as if they had been measured on a kill is the round that has to be corrected.
# ---------------------------------------------------------------------------
# GT-045 (chief R163, 2026-08-25; evidence letter 20260825_1615): the floating
# red name label was present at t = 249.733 and gone by t = 250.067 at a 30 fps
# capture whose own frames are duplicated in threes -- so the real sampling is
# ~10 fps and the honest reading is a RANGE.  Writing 0.30, or "about a quarter
# of a second", is forbidden by the measurement itself; hence two constants and
# no midpoint.
LABEL_LIFE_SECONDS_MIN = 0.2
LABEL_LIFE_SECONDS_MAX = 0.4
# GT-146 P3 (attended, Panya driving, 2026-08-29, OBSERVER_CONFIRMED): the
# ground element "appears and is gone under 1 second", and every click in two
# full sets produced no frame at all in a 394-frame RECV census.  That is the
# observation this module exists to answer, and it is consistent with the
# range above rather than a second, different measurement of it.
LABEL_LIFE_OBSERVED_UNDER_SECONDS = 1.0

# UNMEASURED, deliberately ``None`` rather than ``False``: nobody has watched a
# re-emitted generation to see whether the label is redrawn, does nothing, or
# only restarts the brown dust.  ``describe_presence`` reads this constant, so
# the day it becomes ``True`` the console line stops saying ``unmeasured``
# without anybody editing a string.
REEMISSION_REDRAWS_THE_LABEL = None

# MOB_LOOT_WIRING step 4b's shape, named so a reviewer can grep for it.
PRESENCE_SHAPE = "whole_live_ledger_per_kill"

CONSOLE_TOKEN = "MOB_DROP_PRESENCE"

STATE_SUSTAINED = "sustained"
STATE_NOTHING_ON_THE_GROUND = "nothing_on_the_ground"
STATE_TRIMMED_TO_FIT = "trimmed_to_fit"
STATE_SNAPSHOT = "snapshot"

REFUSED_PREFIX = "refused_"
REFUSE_NOT_A_CELL = REFUSED_PREFIX + "not_a_drop_ledger_cell"
REFUSE_NO_LEGACY = REFUSED_PREFIX + "legacy_cannot_frame"
REFUSE_CELL_RAISED = REFUSED_PREFIX + "cell_raised"
REFUSE_COMPOSE_RAISED = REFUSED_PREFIX + "compose_raised"
# The defect this module exists to make unrepresentable, kept as a NAME so a
# refusal counter can see it: a generation built from one kill's rows while
# other rows are live erases those other rows from the client (RE-130).
REFUSE_PARTIAL_GENERATION = REFUSED_PREFIX + "partial_generation_would_erase"


class PresenceRow(NamedTuple):
    """One row that is on the ground right now, and for how much longer."""

    drop_key: int
    name: str
    # ``None`` when the row's deadline passed underneath the snapshot -- the
    # row still travels, only its number is unknown.  See ``_row``.
    seconds_left: float | None
    from_this_kill: bool


class PresenceStep(NamedTuple):
    """What the call site should send, and the evidence for why that is right.

    ``frames`` is exactly what ``mob_loot.drop_frames`` returns -- a tuple of
    ``(pc, frame)`` pairs -- so the call site's existing loop keeps working
    unread.  It is EMPTY on every refusal and on an empty ground, and a call
    site that iterates it is correct in all four cases without a branch.

    Deliberately no ``frame_bytes`` field: the call site derives the length
    from the bytes it actually queues, so the greppable evidence cannot
    disagree with the wire (pf-adversary, round 73fhoc).  ``describe_presence``
    does print one, and pf-adversary (round m0vp7m, M-B) put a mutant through
    it -- summing the PCs instead of the frames printed ``frame_bytes=44``
    while 54 bytes went out.  That number is now pinned by a test that
    compares it against the frames the same step carries.
    """

    state: str
    frames: tuple
    rows: tuple
    announced: int
    carried: int
    trimmed: int
    lifetime_seconds: float
    oldest_seconds_left: float | None
    newest_seconds_left: float | None
    # Rows whose deadline passed between the snapshot and the reading.  They
    # still travel in the generation; only their number is unknown.
    stale: int
    detail: str

    @property
    def live(self) -> int:
        return len(self.rows)

    @property
    def refused(self) -> bool:
        return self.state.startswith(REFUSED_PREFIX)


def _refusal(state: str, detail: str, lifetime: float = 0.0) -> PresenceStep:
    return PresenceStep(
        state=state, frames=(), rows=(), announced=0, carried=0, trimmed=0,
        lifetime_seconds=lifetime, oldest_seconds_left=None,
        newest_seconds_left=None, stale=0, detail=detail,
    )


def _oldest(rows: Any) -> float | None:
    """The smallest remaining life among the rows that still have a number."""
    known = [row.seconds_left for row in rows if row.seconds_left is not None]
    return min(known) if known else None


def _newest(rows: Any) -> float | None:
    known = [row.seconds_left for row in rows if row.seconds_left is not None]
    return max(known) if known else None


def _row(cell: Any, drop: Any, mine: frozenset) -> PresenceRow:
    """One reported row.  NEVER raises, and the reason is worth the paragraph.

    pf-adversary (round m0vp7m, S4) measured what the first draft cost: this
    function called ``cell.time_left``, which takes the lock, reads the clock
    and SWEEPS -- so a row that crossed its deadline in the microseconds
    between the ledger snapshot and this call raised ``drop_not_in_ledger``,
    the whole ``sustain_a_kill`` returned a refusal, and EVERY drop of the
    kill that just happened -- brand new, 120 s of life ahead, sitting live in
    the cell -- was never announced to the client at all.  A cosmetic number
    on a console line was being paid for with a player's loot.

    So a deadline that passes underneath us costs the NUMBER, not the row:
    ``seconds_left`` is ``None`` and the console line counts it as ``stale=``.
    """
    try:
        name = str(drop.display_name)
    except Exception as error:                     # pragma: no cover - typed
        name = "<name %r>" % (error,)
    try:
        seconds_left = float(cell.time_left(drop.drop_key))
    except Exception:
        seconds_left = None
    return PresenceRow(
        drop_key=int(drop.drop_key),
        name=name,
        seconds_left=seconds_left,
        from_this_kill=int(drop.drop_key) in mine,
    )


def _keys(drops: Any) -> frozenset:
    """Every drop key in ``drops``.  Takes anything, including a non-iterable.

    pf-adversary (round m0vp7m, S3): the ``for`` statement itself is outside
    the per-item ``try``, so ``sustain_a_kill(cell, legacy, 5)`` raised
    ``TypeError`` straight into the caller -- which for this module's one
    intended call site is the listener thread, and the module header says an
    exception there costs the connection, not a drop.  Latent today (the
    dispatch always passes a tuple) and closed anyway, because a claim that
    nothing here raises is either true or it is not.
    """
    keys = set()
    try:
        iterator = iter(drops or ())
    except TypeError:
        return frozenset()
    for drop in iterator:
        try:
            keys.add(int(drop.drop_key))
        except Exception:
            continue
    return frozenset(keys)


def _current_frame_cap() -> int:
    """The trim ceiling that matches whatever ``refresh_frames`` will do.

    pf-adversary (this round): this module trimmed against
    ``mob_loot.DROP_MAX_ELEMENTS_PER_FRAME`` -- the OLD narrow-shape cap --
    even after ``refresh_frames`` started calling
    ``mob_loot.drop_frames_with_model_type``, whose real ceiling is the
    SMALLER ``DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE`` (each wide
    element costs 3 more bytes).  A ledger in the gap between the two caps
    then passed this guard unchanged, got handed whole to
    ``refresh_frames``, and ``drop_frames_with_model_type`` raised
    ``generation_too_wide_to_frame`` -- turning a graceful trim into a full
    refusal, zero frames, for that kill.

    The fix is not a hardcoded constant swap: it is reading the SAME flag
    ``drop_frames_with_model_type`` reads
    (:data:`mob_loot.DROP_MODEL_TYPE_FIELD_ENABLED`) and picking the cap
    that composer will actually enforce.  This keeps the trim guard correct
    under either state of the flag, including the documented one-line
    rollback -- a rollback that flips the flag but leaves this guard using
    the wide cap would recreate the same bug in the opposite direction
    (over-trimming when the narrow shape has more room).
    """
    if mob_loot.DROP_MODEL_TYPE_FIELD_ENABLED:
        return mob_loot.DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE
    return mob_loot.DROP_MAX_ELEMENTS_PER_FRAME


def sustain_a_kill(cell: Any, legacy: Any, drops: Any = ()) -> PresenceStep:
    """The one call a kill's dispatch makes after the death schedule.

    Replaces BOTH halves of what the call site does today: the per-kill
    generation (``mob_loot.drop_frames(legacy, drops)``) and the prune loop
    that takes every key it just announced.  It composes the WHOLE LIVE
    LEDGER as one generation and it takes nothing.

    ``drops`` is the tuple ``cell.loot_a_kill`` returned, and it is used for
    ONE thing: telling the console which rows are this kill's and which were
    already on the ground.  Passing ``()`` is legal and only costs that
    distinction -- the generation is composed from the cell either way, which
    is the property that makes a partial generation unrepresentable here.
    """
    if not isinstance(cell, mob_loot.DropLedgerCell):
        return _refusal(
            REFUSE_NOT_A_CELL,
            "presence is composed from the cell, not from a value beside it; "
            "got %s" % type(cell).__name__)
    try:
        lifetime = float(cell.lifetime_seconds)
    except Exception as error:                     # pragma: no cover - typed
        return _refusal(REFUSE_CELL_RAISED, repr(error))

    # ONE snapshot, then everything is derived from it.  Reading ``cell.ledger``
    # twice is not the same as reading it once: the property sweeps expired
    # rows, so a second read can legally return fewer rows than the first --
    # which would let this record describe a generation it did not compose.
    try:
        ledger = cell.ledger
        live = tuple(ledger.drops)
    except Exception as error:
        return _refusal(REFUSE_CELL_RAISED, repr(error), lifetime)

    mine = _keys(drops)
    trimmed = 0
    cap = _current_frame_cap()
    if len(live) > cap:
        # A generation that omits a live key erases that key on the client
        # (RE-130).  So when the ground cannot fit in one frame, the rows that
        # will not travel are removed from the CELL as well -- a client and a
        # server that disagree about what is on the ground is a worse failure
        # than a lost drop, and this way the loss has a name and a count.
        # Unreachable on today's numbers (16 drops per kill, 120 s, a cap in
        # the low thousands either way) and kept because "unreachable" is a
        # property of the numbers, not of the code.
        #
        # ROW BY ROW, NOT ``prune_issued_before``, and pf-adversary (round
        # m0vp7m, S5) is why: that method refuses ``prune_would_take_the_
        # newest_kill`` whenever the cut point lands inside the newest kill's
        # block -- which is EXACTLY the case a cap can be crossed in, a kill
        # wider than the cap all by itself.  The branch that exists to give a
        # loss "a name and a count" was instead returning a refusal with
        # ``frames=()``, so the whole kill sent nothing.  An untested defence
        # that does not defend.  ``take`` carries no such guard and removes
        # precisely the rows that will not travel.
        #
        # ``cap`` is :func:`_current_frame_cap`, NOT a hardcoded constant --
        # pf-adversary (this round) is why: this used to read
        # ``mob_loot.DROP_MAX_ELEMENTS_PER_FRAME`` even after
        # ``refresh_frames`` (below) started calling
        # ``drop_frames_with_model_type``, whose real ceiling is the smaller
        # ``DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE``.  A ledger between
        # the two caps passed this guard unchanged and then blew up inside
        # ``refresh_frames`` -- a full refusal where a graceful trim was the
        # whole point of this branch.
        keep = cap
        dropped = live[:-keep] if keep else live
        live = live[-keep:] if keep else ()
        try:
            for row in dropped:
                cell.take(row.drop_key)
            # Composed from the rows that SURVIVED, not from a second read of
            # the cell -- the cell and the generation now name the same set,
            # and the snapshot rule above is not broken to achieve it.
            ledger = mob_loot.DropLedger(
                live, ledger.generation, ledger.issued_through, ledger.looted)
        except Exception as error:
            return _refusal(REFUSE_CELL_RAISED, repr(error), lifetime)
        trimmed = len(dropped)

    if not live:
        return PresenceStep(
            state=STATE_NOTHING_ON_THE_GROUND, frames=(), rows=(),
            announced=0, carried=0, trimmed=trimmed,
            lifetime_seconds=lifetime, oldest_seconds_left=None,
            newest_seconds_left=None, stale=0,
            detail="no live rows; a kill that dropped nothing sends nothing")

    try:
        rows = tuple(_row(cell, drop, mine) for drop in live)
    except Exception as error:
        return _refusal(REFUSE_CELL_RAISED, repr(error), lifetime)

    try:
        frames = mob_loot.refresh_frames(legacy, ledger)
    except mob_loot.MobLootContractError as error:
        return _refusal(
            REFUSE_COMPOSE_RAISED, "%s: %s" % (error.args[0], error), lifetime)
    except Exception as error:
        return _refusal(REFUSE_NO_LEGACY, repr(error), lifetime)

    announced = sum(1 for row in rows if row.from_this_kill)
    return PresenceStep(
        state=STATE_TRIMMED_TO_FIT if trimmed else STATE_SUSTAINED,
        frames=frames, rows=rows,
        announced=announced, carried=len(rows) - announced, trimmed=trimmed,
        lifetime_seconds=lifetime,
        oldest_seconds_left=_oldest(rows),
        newest_seconds_left=_newest(rows),
        stale=sum(1 for row in rows if row.seconds_left is None),
        detail=PRESENCE_SHAPE,
    )


def presence_snapshot(cell: Any) -> PresenceStep:
    """What is on the ground right now.  Composes nothing and sends nothing.

    For a console line at any moment a caller likes -- a boot, a tick, a
    tester asking "is it still there".  ``frames`` is always empty: a
    snapshot that could emit would be a second, quieter emission path, and
    the cadence rule this module keeps has exactly one.
    """
    if not isinstance(cell, mob_loot.DropLedgerCell):
        return _refusal(
            REFUSE_NOT_A_CELL, "got %s" % type(cell).__name__)
    try:
        lifetime = float(cell.lifetime_seconds)
        live = tuple(cell.ledger.drops)
        rows = tuple(_row(cell, drop, frozenset()) for drop in live)
    except Exception as error:
        return _refusal(REFUSE_CELL_RAISED, repr(error))
    if not rows:
        return PresenceStep(
            state=STATE_NOTHING_ON_THE_GROUND, frames=(), rows=(), announced=0,
            carried=0, trimmed=0, lifetime_seconds=lifetime,
            oldest_seconds_left=None, newest_seconds_left=None, stale=0,
            detail="nothing is on the ground")
    return PresenceStep(
        state=STATE_SNAPSHOT, frames=(), rows=rows, announced=0,
        carried=len(rows), trimmed=0, lifetime_seconds=lifetime,
        oldest_seconds_left=_oldest(rows),
        newest_seconds_left=_newest(rows),
        stale=sum(1 for row in rows if row.seconds_left is None),
        detail=PRESENCE_SHAPE)


def _seconds(value: Any) -> str:
    if value is None:
        return "-"
    return "%.1f" % float(value)


def describe_presence(step: Any) -> str:
    """ONE console line, ASCII, greppable by :data:`CONSOLE_TOKEN`.

    It reports the DECLARED lifetime (chief's letter 2105, point 2: "a console
    line that says the element lifetime this build actually declares") next to
    the measured label life, because the whole finding of this round is that
    those two numbers are about different things and only the second one is
    what a tester sees.  ``redraw=`` is read off
    :data:`REEMISSION_REDRAWS_THE_LABEL` rather than written as a word, so the
    line cannot claim more than the project has measured.
    """
    if not isinstance(step, PresenceStep):
        return "%s state=%snot_a_presence_step got=%s" % (
            CONSOLE_TOKEN, REFUSED_PREFIX, type(step).__name__)
    redraw = {None: "unmeasured", True: "yes", False: "no"}.get(
        REEMISSION_REDRAWS_THE_LABEL, "unmeasured")
    frame_bytes = sum(len(frame) for _pc, frame in step.frames)
    return (
        "%s state=%s shape=%s live=%d announced=%d carried=%d trimmed=%d "
        "stale=%d frames=%d frame_bytes=%d declared_lifetime=%.1fs "
        "oldest_left=%ss newest_left=%ss label_life=%.1f-%.1fs redraw=%s "
        "detail=%s"
        % (
            CONSOLE_TOKEN, step.state, PRESENCE_SHAPE, step.live,
            step.announced, step.carried, step.trimmed, step.stale,
            len(step.frames),
            frame_bytes, step.lifetime_seconds,
            _seconds(step.oldest_seconds_left),
            _seconds(step.newest_seconds_left),
            LABEL_LIFE_SECONDS_MIN, LABEL_LIFE_SECONDS_MAX, redraw,
            step.detail.encode("ascii", "backslashreplace").decode("ascii"),
        )
    )


ACTION_LABEL = "MOB_LOOT_DROP"


def loot_actions(step: Any) -> tuple:
    """The dispatch actions for ``step``, composed HERE rather than at the ask.

    pf-adversary (round m0vp7m, M-A) named the hole this closes, and it was the
    worst finding of that review: ``DROP_PRESENCE_WIRING`` is prose, no test
    executes it, and this lane's only player-facing product was four hand-typed
    lines nobody could run.  Swapping ``loot_pc`` and ``loot_frame`` inside that
    string kept the whole suite green while every ground drop would have gone
    out with the 44-byte pc in the frame slot -- no client would ever draw a
    drop again, and the round would have called itself verified.

    So the tuple shape is code now, pinned by a test, and the pasteable line is
    ``actions.extend(mob_drop_presence.loot_actions(step))`` -- which has no
    order to get wrong.  Empty for every refusal and for an empty ground, so
    the call site needs no branch.
    """
    if not isinstance(step, PresenceStep):
        return ()
    return tuple(
        (ACTION_LABEL, pc, frame, 0.0) for pc, frame in step.frames)


def presence_event(step: Any) -> str:
    """The one ``self.events`` entry the call site records for this step.

    pf-adversary (round m0vp7m, S6): the first draft of the ask dropped the
    existing ``mob_loot_drops_sent_..._pruned`` event and put nothing back, so
    every refusal became a ``print()`` and nothing else -- invisible to a
    headless test and to an operator grepping the session record.
    """
    if not isinstance(step, PresenceStep):
        return "mob_drop_presence_refused_not_a_presence_step"
    return "mob_drop_presence_%s_live_%d" % (step.state, step.live)


# ---------------------------------------------------------------------------
# The wiring ask.  runtime.py is chief's file; this is the whole change.
#
# STATUS: WIRED, not open.  Chief's commit 432381a2 (round t7t5yd,
# 2026-08-30T01:33+07:00) put these five lines into runtime.py's MOB_LOOT
# block -- verbatim, per that commit's own message.  This lane found this
# text still framed as an unanswered ask on round jiy6lj (this round) with
# no test re-deriving that fact from source, which is the same failure mode
# GOVERNED_BAG_ALLOWLIST_OWNER had before round hpronz's AST tripwire: a
# hand-typed status that cannot self-report going (or having gone) stale.
# The string body below is left byte-for-byte as it was asked -- this lane
# does not rewrite an ask after the fact -- but tests/test_mob_drop_presence.
# py's ModuleShapeTests.test_the_wiring_ask_is_fulfilled_re_derived_from_
# runtime_py is the thing that would go red if this status note itself ever
# went stale (wiring reverted without this comment being noticed).
# ---------------------------------------------------------------------------
DROP_PRESENCE_WIRING = """runtime.py, the MOB_LOOT block of _dispatch_mob_combat
(today: 'if drops:' ... 'for loot_pc, loot_frame in mob_loot.drop_frames(' ...
'for drop in drops: self.mob_loot_cell.take(drop.drop_key)').

REPLACE THAT WHOLE 'if drops:' BODY WITH FIVE LINES, AND DROP THE 'if drops:'
GUARD ITSELF -- a kill that dropped nothing must still re-carry what is already
on the ground, which is the entire point:

  step = mob_drop_presence.sustain_a_kill(self.mob_loot_cell, legacy, drops)
  print(mob_loot.drops_console_line(mob, drops))
  print(mob_drop_presence.describe_presence(step))
  actions.extend(mob_drop_presence.loot_actions(step))
  self.events.append(mob_drop_presence.presence_event(step))

plus mob_drop_presence on the import line at the top of the file.
drops_console_line(mob, ()) is safe for an empty tuple (tests/test_mob_loot.py
pins it), so no guard is needed around it.

NOTE THAT NO TUPLE IS TYPED BY HAND HERE.  An earlier draft of this ask asked
chief to paste 'actions.append(("MOB_LOOT_DROP", loot_pc, loot_frame, 0.0))',
and pf-adversary showed that swapping those two names passes the entire suite
while breaking every ground drop on the wire.  loot_actions() is that tuple,
with a test on it.

WHAT EACH LINE REPLACES, AND WHY IT IS NOT A CADENCE CHANGE:

1. mob_loot.drop_frames(legacy, drops) -> step.frames.  Same return type, same
   loop, same position (after the whole death schedule including hold_ms --
   this is NOT moved into the dying/dead hold).  The generation is now the
   whole live ledger instead of one kill's rows: MOB_LOOT_WIRING step 4b, the
   shape it says the COO's 2026-08-26 timer refusal does not cover, whose one
   precondition (an expiry) landed in round 0n9inw.

2. 'for drop in drops: cell.take(drop.drop_key)' -> DELETED, replaced by
   nothing.  This is the two-line half of the fix and it is the reason
   chief measured drop_already_taken on 100% of pickups in round ni2wh2: the
   dispatch takes every key of the kill it just announced, so a click can
   never find a row.  Do NOT substitute cell.prune_previous_kills() here
   either -- that was the right call under the per-kill generation and it is
   the wrong one under this shape, because it removes rows that are still
   inside their 120 s lifetime and still in the client's tree.  The bound is
   now the per-drop expiry (COO-DECISION 2026-08-29T12:41+07:00) plus
   sustain_a_kill's own trim, both of which need no call site.

3. mob_loot.drops_console_line(mob, drops) stays if chief wants it -- it says
   what this kill rolled.  describe_presence says what is on the ground, which
   is a different question, and the round's evidence needs the second one.

NOTHING ELSE MOVES.  No timer, no thread, no new dispatch branch, no scenario
flag: production_allowed is True and this behaviour is on for every boot.
"""

# ---------------------------------------------------------------------------
# PANYA-ORDER 2026-08-30T14:50+07:00 step 1-2 (relayed
# notes_to_chief/20260830_1450_PANYA-ORDER-prove-drop-persistence-BEFORE-
# GT146-click-test-plus-nonclaim-routing-error.md): can the ground-loot
# element be made to stay visible/clickable >= 30 s, proven headless first.
#
# tests/test_mob_drop_presence_sustained_resend_hypothesis.py answers the
# mechanism half: ``sustain_a_kill(cell, legacy, ())`` -- the SAME function
# the per-kill path above already calls, called again with no new kill --
# resends the whole live ledger's frames at zero placement cost and zero new
# byte layout, and does so correctly across a proven >= 30 s window (34 s,
# uneven cadence, well inside the 120 s DROP_LIFETIME_SECONDS ceiling). This
# test still stands as a true, adversary-checked fact about the mechanism.
#
# ~~"Send the frame again periodically" is therefore not a mechanism to
# build; it is a call site to add, gated by a scenario flag so it stays
# test-only.."~~ WITHDRAWN, same round (u98etz), after a fetch surfaced work
# this lane did not have when it wrote that sentence: round ``xt0g9c``
# (earlier the same evening) had already re-verified this exact mechanism
# headless (tests/test_mob_drop_presence.py, 48/48) and an ATTENDED round
# that followed it (GT143/GT132/GT149, notes_to_chief/20260830_1554) measured
# the real client label life at 0.2 s regardless of the server-side ledger
# surviving 120 s -- the bottleneck this lane's proof addresses was never the
# one blocking GT-146.  The COO then explicitly RULED, 2026-08-30T17:42+07:00
# (notes_to_chief/20260830_1742_COO-DECISION-label-life-drop-announcement-
# rule-stands.md), NOT to open any repeated-resend path -- capped or
# movement-driven -- until an attended round fires exactly ONE extra resend
# after the first drop and measures whether the label comes back.  The
# call-site proposal below is exactly the kind of standing (repeated, not
# single) resend that ruling refuses, so it is NOT a live ask: nobody should
# wire it from this text.  It is kept, struck, rather than deleted, as the
# record of what this lane asked for before it knew the ruling existed.
# ---------------------------------------------------------------------------
WITHDRAWN_DROP_PRESENCE_RESEND_ON_MOVEMENT_WIRING = """runtime.py, the TargetPosVital
scenario cluster that already gates ground_loot_hypothesis and
ground_loot_nameprop_hypothesis (search 'nested_id == legacy.TARGET_POS_VITAL'
-- three sibling blocks, all reading a scenario kwarg that defaults to None).

ADD A FOURTH SIBLING BLOCK, new scenario kwarg
``mob_drop_presence_resend_scenario`` (None by default, same constructor/
__slots__/repr wiring as the two neighbours it sits beside -- see how
``ground_loot_hypothesis_scenario`` is threaded through __init__ and
docs/GM_LANE.md-style scenario tables for the exact shape chief already
copies twice):

  if (
      mob_drop_presence_resend_scenario is not None
      and self.runtime_ack_sent
      and self.teleport_sent
      and self.foundation.selected is not None
      and nested_id == legacy.TARGET_POS_VITAL
  ):
      step = mob_drop_presence.sustain_a_kill(self.mob_loot_cell, legacy, ())
      print(mob_drop_presence.describe_presence(step))
      actions.extend(mob_drop_presence.loot_actions(step))
      self.events.append(mob_drop_presence.presence_event(step))

NOTE WHAT IS DELIBERATELY ABSENT: no ``_sent`` latch (unlike the two
neighbours, which fire ONCE per session).  This block is meant to fire on
EVERY qualifying TargetPosVital while the flag is set, because the whole
point is CADENCE -- a client-driven event that already arrives every time
the player moves, not a server clock (the COO's 2026-08-26 refusal was of a
TIMER; there is no timer here, only an existing message handled one more
way). ``sustain_a_kill`` costs nothing extra when the ground is empty
(STATE_NOTHING_ON_THE_GROUND, frames=()) and composes no new bytes ever --
it is the identical function object the always-on per-kill call site above
already calls in production.

THE SCENARIO FLAG ITSELF is the part this lane has not built: a permission-
token loader/validator following the ``ground_loot_hypothesis`` pattern
(frozen allowlisted profile, ``production_allowed = False``, refuses any
drifted file by name). Until that token exists this block simply never
fires (``mob_drop_presence_resend_scenario is None`` on every default boot),
so landing the block ahead of the token is safe and unblocks the token being
built in either lane's next round without a second runtime.py edit.

pf-adversary (this round) asked who verifies the token defaults to refused
before this wiring lands: the same guarantee ``ground_loot_hypothesis`` gives
by construction, not by convention -- the CONSTRUCTOR arg defaults to
``None`` (nothing fires with no file passed), the loader accepts only the
one frozen profile by identity (``require_ground_loot_hypothesis_scenario``,
``is`` not ``==``, so no value-equal lookalike opens it), and
``load_ground_loot_hypothesis_scenario`` refuses any file that is not an
exact match to the allowlisted body. Whoever builds the token for this flag
owes the same three properties and a test pinning each one, exactly as
``tests/test_ground_loot_hypothesis.py`` already does for the sibling --
this file does not build that token and must not be read as claiming the
default is safe until that test exists.

WHAT THIS DOES NOT DO: it does not change what LABEL_LIFE_SECONDS_MIN/MAX
mean, it does not set REEMISSION_REDRAWS_THE_LABEL (that stays an attended-
only measurement), and it does not touch the always-on per-kill call site
above in any way.
"""
