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

from . import mob_ground_persistence
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
# ROUND 4e9r7g, COO-DECISION 2026-09-02T02:52+07:00 way 1: the cell does not
# know which scene it is publishing, so this module refuses instead of
# composing a generation out of every scene's rows.  Sending nothing is the
# conservative half of a wrong answer; sending scene A's drops to a player
# standing in scene B is the loud one, and it is the one way 1 closed.
REFUSE_NO_SCENE = REFUSED_PREFIX + "cell_has_no_scene_to_publish"


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
    # ROUND 4e9r7g.  The scene this step published for, and how many rows are
    # standing in OTHER scenes and were deliberately not published.  Both have
    # defaults so every existing construction site keeps working, and both are
    # printed by ``describe_presence`` so "where did my other drops go" has an
    # answer on the console instead of only in this docstring.  ``elsewhere``
    # is a count of rows STILL ON THE GROUND -- nothing was deleted to reach
    # it (COO-DECISION 2026-09-02T02:53+07:00).
    scene: str | None = None
    elsewhere: int = 0

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


def _console_ascii(line: str) -> str:
    """Make one line safe for the cp874 console this project actually runs on.

    ROUND hlwgri, pf-adversary D7, MEASURED: :func:`_say_world_line` keeps a
    dead console from costing a FRAME, but it also swallows the line -- so a
    refusal whose ``%r`` detail carried a character cp874 has no mapping for
    printed NOTHING, and a token whose stated invariant is "silence means
    this build has no call site" then lies.  ``describe_presence`` already
    defends itself this way (``encode("ascii", "backslashreplace")``); every
    line this module composes by hand now does too, so the escape hatch in
    :func:`_say_world_line` is left for what it was written for rather than
    used as the encoding strategy.
    """
    return line.encode("ascii", "backslashreplace").decode("ascii")


def _say_world_line(line: str) -> bool:
    """Print one world line, and LOSE THE LINE rather than the kill.

    ROUND 59iqwi, pf-adversary D7, MEASURED: a bare ``print`` here raised
    ``UnicodeEncodeError`` straight out of :func:`sustain_a_kill` on the
    cp874 console this project actually runs on -- a function every other
    failure of which is caught and returned as a named refusal.  The sibling
    lane already carries the scar and the rule
    (``mob_pickup_request._say``): a console that cannot be written to costs
    a LINE, never a FRAME.  Returns whether the line was printed, so a test
    can prove the loss is the line rather than assume it.
    """
    try:
        print(line)
    except Exception:                            # noqa: BLE001 - see docstring
        return False
    return True


def sustain_a_kill(
    cell: Any, legacy: Any, drops: Any = (), *,
    store: Any = None, world: Any = None,
) -> PresenceStep:
    """The one call a kill's dispatch makes after the death schedule.

    ROUND 59iqwi ADDS ONE THING TO THIS CALL AND CHANGES NOTHING ELSE ABOUT
    IT: the rows this kill put on the ground are also handed to
    :func:`mob_ground_persistence.remember_generation`, so they belong to the
    WORLD's floor for the scene and not only to the cell of the session that
    made them (`COO-DECISION 2026-09-03T10:48+07:00`; KA1A's R309 measured the
    session-only version as a crystal that vanished across a relogin).  It is
    a REPORT, not a gate: this function's frames, refusals, counts and return
    type are untouched by it, and a world that raised could not cost the
    player their drop (``remember_generation`` never raises, and its outcome
    only reaches the console).

    ``store`` is optional and is the durable half (`COO-DECISION
    2026-09-03T18:44+07:00`, the `commit_ground_drop` call site).  Absent, the
    floor is memory only: a relogin sees the drop, a server restart does not.

    Replaces BOTH halves of what the call site does today: the per-kill
    generation (``mob_loot.drop_frames(legacy, drops)``) and the prune loop
    that takes every key it just announced.  It composes the WHOLE LIVE
    LEDGER as one generation and it takes nothing.

    ``drops`` is the tuple ``cell.loot_a_kill`` returned, and it is used for
    ~~ONE thing~~ TWO since round 59iqwi: telling the console which rows are
    this kill's and which were already on the ground, and handing the new rows
    to the world's floor.  Passing ``()`` is legal and costs that distinction
    AND the world entry (pf-adversary D8: ``runtime.py`` has a live path that
    passes ``()`` when the ledger retry gave up, and those rows are not in the
    cell either, so the floor and the cell still agree) -- the generation is composed from the cell either way, which
    is the property that makes a partial generation unrepresentable here.

    ROUND 4e9r7g, COO-DECISION 2026-09-02T02:52+07:00 way 1.  ~~"the WHOLE
    LIVE LEDGER as one generation"~~ IS STRUCK and replaced by: THE WHOLE LIVE
    LEDGER OF THE SCENE BEING PUBLISHED.  The two were the same thing while a
    ledger could only hold one scene's rows; now that a row owns the scene it
    fell in, they are not, and the difference is a drop from the town riding
    into the first publication a player receives in the field.  The property
    that mattered is untouched: within the scene, the generation is still the
    WHOLE of it, so no live key of this scene is ever omitted (RE-130).

    Rows in other scenes are neither published nor removed -- they keep
    standing where they fell, and ``elsewhere`` on the returned step counts
    them.
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

    # THE WORLD LEARNS ABOUT THIS KILL'S ROWS BEFORE ANYTHING IS COMPOSED, and
    # the order is the argument: the rows are on the ground the moment
    # ``loot_a_kill`` returned them, so a publication that refuses below (an
    # unmined item, a serializer handle that moved) must not also lose them
    # for the next session.  One bounded console line, always, because "the
    # floor was told" and "this seam never ran" are the two states an attended
    # round has to be able to tell apart by grep (G-OBS).
    _say_world_line(
        mob_ground_persistence.describe_remembered(
            mob_ground_persistence.remember_generation(
                drops, world=world, store=store)))

    # ONE snapshot, then everything is derived from it.  Reading ``cell.ledger``
    # twice is not the same as reading it once: the property sweeps expired
    # rows, so a second read can legally return fewer rows than the first --
    # which would let this record describe a generation it did not compose.
    # ONE ACQUISITION for the scene, the scene's rows and the count standing
    # elsewhere.  ``cell.ledger`` followed by ``cell.current_scene`` would be
    # two, and a kill landing between them moves the scene while the rows it
    # added are not in the snapshot -- a generation that omits a live key of
    # its own scene, which is the erasure (RE-130) this whole module exists to
    # make unrepresentable.  See DropLedgerCell.publication.
    try:
        scene, ledger, elsewhere = cell.publication()
    except Exception as error:
        return _refusal(REFUSE_CELL_RAISED, repr(error), lifetime)

    if scene is None:
        return _refusal(
            REFUSE_NO_SCENE,
            "the cell does not know which scene it is publishing; "
            "runtime.py must call cell.enter_scene_frames(legacy, <scene folder>) "
            "at the scene boundary (a kill through cell.loot_a_kill sets it "
            "too).  "
            "Nothing was sent and nothing was removed: %d row(s) are still "
            "standing" % elsewhere,
            lifetime)

    live = tuple(ledger.drops)

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
            detail="no live rows in scene %s; a kill that dropped nothing "
                   "sends nothing (%d row(s) standing in other scenes)"
                   % (scene, elsewhere),
            scene=scene, elsewhere=elsewhere)

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

    # THE KILL PAYS THE SCENE'S REMOVAL DEBT (round f4oh9y).  ``frames``
    # carries this scene's surviving ground, so by RE-130's static reading
    # the consumer drops every key it omits -- which is what the rows a sweep
    # retired are owed.  ``live`` is the POST-TRIM tuple the ledger above was
    # rebuilt from, so the rows named here really are the rows in the frames.
    # Telling the cell keeps DropLedgerCell.frames_after_rows_expired from
    # composing a second generation saying the same thing on the next refused
    # click.  This step is the one publisher in this file that may claim a
    # payment: runtime.py sends a kill's generation with no gate in front of
    # it (unlike the boundary stash, which three gates can drop).
    #
    # NOT FATAL, and the asymmetry is the point: a debt that fails to clear
    # costs one redundant generation later, while a kill that fails to
    # publish costs the player their drop.  The narrow catch is deliberate --
    # note_scene_published raises only its two named contract refusals, and
    # neither is reachable here (``live`` is nonempty by the branch above and
    # is made of this module's own rows), so a broad ``except`` would only
    # hide the day that stops being true.
    try:
        cell.note_scene_published(scene, live)
    except mob_loot.MobLootContractError:
        # Swallowed, never widened: the frames below are already composed and
        # a kill must not lose them over bookkeeping.  What survives the
        # swallow is the DEBT, which the next publisher pays.
        pass

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
        scene=scene, elsewhere=elsewhere,
    )


def presence_snapshot(cell: Any) -> PresenceStep:
    """What is on the ground right now.  Composes nothing and sends nothing.

    For a console line at any moment a caller likes -- a boot, a tick, a
    tester asking "is it still there".  ``frames`` is always empty: a
    snapshot that could emit would be a second, quieter emission path, and
    the cadence rule this module keeps has exactly one.

    ROUND 4e9r7g: THIS ONE IS DELIBERATELY NOT SCENE-SCOPED, and the asymmetry
    with :func:`sustain_a_kill` is the point.  A publication is the client's
    business and must carry one scene; a snapshot is the OPERATOR's, and an
    operator asking "what is on the ground" while a player crosses scenes
    wants the true total -- including the rows way 1 keeps standing in the
    scene that was left.  ``scene`` and ``elsewhere`` on the returned step say
    which scene the cell would publish for and how many of these rows are not
    in it, so the console line can never be read as "these all travel".
    """
    if not isinstance(cell, mob_loot.DropLedgerCell):
        return _refusal(
            REFUSE_NOT_A_CELL, "got %s" % type(cell).__name__)
    try:
        lifetime = float(cell.lifetime_seconds)
        live = tuple(cell.ledger.drops)
        scene = cell.current_scene
        rows = tuple(_row(cell, drop, frozenset()) for drop in live)
        if scene is None:
            # Every row is "elsewhere" when there is no scene to be here in.
            elsewhere = len(live)
        else:
            wanted = mob_loot.scene_key(scene)
            elsewhere = sum(
                1 for drop in live if drop.scene_key != wanted)
    except Exception as error:
        return _refusal(REFUSE_CELL_RAISED, repr(error))
    if not rows:
        return PresenceStep(
            state=STATE_NOTHING_ON_THE_GROUND, frames=(), rows=(), announced=0,
            carried=0, trimmed=0, lifetime_seconds=lifetime,
            oldest_seconds_left=None, newest_seconds_left=None, stale=0,
            detail="nothing is on the ground",
            scene=scene, elsewhere=0)
    return PresenceStep(
        state=STATE_SNAPSHOT, frames=(), rows=rows, announced=0,
        carried=len(rows), trimmed=0, lifetime_seconds=lifetime,
        oldest_seconds_left=_oldest(rows),
        newest_seconds_left=_newest(rows),
        stale=sum(1 for row in rows if row.seconds_left is None),
        detail=PRESENCE_SHAPE,
        scene=scene, elsewhere=elsewhere)


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
    # ROUND 4e9r7g: ``scene=`` and ``elsewhere=`` are on the line because the
    # question way 1 creates -- "there were four things on the ground, why did
    # two travel" -- has to be answerable from the console, not from a
    # docstring.  ``elsewhere`` counts rows STILL STANDING in other scenes;
    # it is never a count of anything deleted.
    scene = "none" if step.scene is None else str(step.scene)
    return (
        "%s state=%s shape=%s scene=%s elsewhere=%d live=%d announced=%d "
        "carried=%d trimmed=%d "
        "stale=%d frames=%d frame_bytes=%d declared_lifetime=%.1fs "
        "oldest_left=%ss newest_left=%ss label_life=%.1f-%.1fs redraw=%s "
        "detail=%s"
        % (
            CONSOLE_TOKEN, step.state, PRESENCE_SHAPE,
            scene.encode("ascii", "backslashreplace").decode("ascii"),
            step.elsewhere, step.live,
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
# ROUND 59iqwi/next, `COO-DECISION 20260904_1649` item 2 answering chief's ask
# (`pf_bridge/notes_to_chief/20260904_1708_CHIEF-TO-LANE-B-ground-reannounce-
# function-request-and-two-guard-exemptions.md`, GT-242).
#
# WHAT A PLAYER SEES BECAUSE OF THIS FUNCTION (once chief wires the call
# site).  KA1A finding 1, R309, measured on the real client
# (`pf_bridge/notes_to_chief/20260904_1430`): drop an item, open the
# inventory bag WITHOUT clicking anything, and the crystal disappears from
# the ground.  The item was never taken and never expired -- the console
# kept printing ``MOB_DROP_PRESENCE ... carried=1 oldest_left=65.6s`` right
# after -- the client was simply told the wrong thing by a DIFFERENT reply:
# ``CheckSecondPwdVital 0x4B98``'s own 44-byte OK frame ends
# ``0B 00``, an empty ground-list, and the client reads that as "the floor
# is bare" and clears it.  This function is the correction for that one
# named frame: call it right after that reply goes out and the client is
# told the truth a second time.
#
# NOT THE REFUSED RESEND.  `COO-DECISION 2026-08-30T17:42+07:00` refused a
# STANDING, repeated resend on a movement cadence -- see
# `WITHDRAWN_DROP_PRESENCE_RESEND_ON_MOVEMENT_WIRING` below, which is still
# withdrawn and this function does not revive it.  This is a single call
# tied to one named inbound frame (`0x4B98`), the same shape the scene-
# boundary reannounce already makes on a kill or a scene entry -- it fires
# once per second-password reply, never on a timer and never on every frame
# of anything.
# ---------------------------------------------------------------------------

#: Printed once per call that actually composed a step, empty ground
#: included -- an explicit ``items=0`` line, not silence, is what tells an
#: operator "the floor was checked and it was bare" apart from "this build
#: has no call site yet" (GT-242 RECHECK criterion: zero lines of this name
#: anywhere in a boot means an old build, not a passing negative control).
GROUND_REANNOUNCE_TOKEN = "GROUND_REANNOUNCE_AFTER_SECOND_PWD"
#: Printed instead of the line above when nothing could be composed at all
#: (no scene, not a real cell, an exception) -- a DIFFERENT name on purpose,
#: so ``items=0`` (checked, bare) is never confused with a refusal on the
#: console or in a grep.
GROUND_REANNOUNCE_REFUSED_TOKEN = "GROUND_REANNOUNCE_AFTER_SECOND_PWD_REFUSED"

REFUSE_SCENE_DISAGREES = REFUSED_PREFIX + "scene_disagrees_with_the_cell"


def reannounce_ground(cell: Any, legacy: Any, scene: Any = None) -> tuple:
    """Re-send everything still live on one scene's floor.  NEVER RAISES.

    THE CALL SITE THIS IS FOR: chief's responder for ``CheckSecondPwdVital
    0x4B98``, right after that reply is queued.  Call with the connection's
    own ``self.mob_loot_cell`` and ``legacy`` -- the same two arguments
    ``sustain_a_kill`` already takes at the kill dispatch, because this
    reuses that exact mechanism (``sustain_a_kill(cell, legacy, ())`` -- no
    new kill, the whole live ledger of the cell's own scene) rather than a
    second encoder path.  ``tests/test_mob_drop_presence_sustained_resend_
    hypothesis.py`` already proved this resend is correct, at zero placement
    cost and zero new byte layout, across a real multi-resend window.

    ``scene`` is OPTIONAL and is a cross-check, not a source of truth: the
    cell alone decides what it publishes (``cell.publication()``, exactly as
    ``sustain_a_kill`` uses it).  Pass it when the caller already has the
    scene id in hand (chief's letter: "I can send you both") and a call
    whose scene disagrees with the cell's own is refused BY NAME rather than
    silently resending the cell's scene under a caller's wrong label --
    reannouncing scene 3's floor while chief believes it just answered scene
    5 would be a worse bug than sending nothing.  Omit it and the cell's own
    scene is trusted alone, same as every other caller in this module.

    Returns a TUPLE of ``loot_actions``-shaped entries, ALWAYS -- ``()`` for
    an empty floor, ``()`` for a cell with no scene, ``()`` for anything this
    call cannot compose.  Never ``None``: a caller that only ever sees a
    tuple needs no branch to tell "nothing to send" from "something went
    wrong" apart, and this function's own console line is what carries that
    difference instead (:data:`GROUND_REANNOUNCE_TOKEN` with ``items=0`` for
    the first, :data:`GROUND_REANNOUNCE_REFUSED_TOKEN` for the second).

    FAIL-CLOSED: every exception is caught here, printed as a named refusal,
    and answered with ``()`` -- this sits under an inbound frame from a
    stranger by way of the same listener thread every other entry point in
    this module already promises not to bring down.

    ROUND hlwgri, AND IT WAS NOT TRUE WHEN THIS DOCSTRING FIRST CLAIMED IT:
    every line here went out through a bare ``print``, which is the exact
    call pf-adversary MEASURED raising ``UnicodeEncodeError`` out of
    :func:`sustain_a_kill` on this project's cp874 console (round 59iqwi,
    D7 -- the reason :func:`_say_world_line` exists).  A refusal detail
    carrying a non-ASCII repr would therefore have thrown straight through
    "NEVER RAISES" into chief's call site.  Every line in this function now
    goes through :func:`_say_world_line`: a console that cannot be written
    to costs a LINE, never a FRAME.
    """
    try:
        if scene is not None:
            cell_scene = getattr(cell, "current_scene", None)
            if (cell_scene is None
                    or mob_loot.scene_key(scene) != mob_loot.scene_key(cell_scene)):
                _say_world_line(_console_ascii("%s scene=%r reason=%s" % (
                    GROUND_REANNOUNCE_REFUSED_TOKEN, scene,
                    REFUSE_SCENE_DISAGREES)))
                return ()
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s scene=%r reason=%s:%r" % (
            GROUND_REANNOUNCE_REFUSED_TOKEN, scene, REFUSE_CELL_RAISED, error)))
        return ()
    try:
        step = sustain_a_kill(cell, legacy, ())
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s scene=%r reason=%s:%r" % (
            GROUND_REANNOUNCE_REFUSED_TOKEN, scene, "reannounce_raised", error)))
        return ()
    if step.refused:
        _say_world_line(_console_ascii("%s scene=%r reason=%s" % (
            GROUND_REANNOUNCE_REFUSED_TOKEN,
            step.scene if step.scene is not None else scene, step.state)))
        return ()
    try:
        actions = loot_actions(step)
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s scene=%r reason=%s:%r" % (
            GROUND_REANNOUNCE_REFUSED_TOKEN, step.scene, "actions_raised",
            error)))
        return ()
    _say_world_line(_console_ascii("%s scene=%r items=%d" % (
        GROUND_REANNOUNCE_TOKEN, step.scene, step.live)))
    return actions


# ---------------------------------------------------------------------------
# The wiring ask for reannounce_ground.  runtime.py is chief's file; this is
# the whole change, and it is the pasteable answer to
# `pf_bridge/notes_to_chief/20260904_1708_CHIEF-TO-LANE-B-*`.  GT-242 is the
# ticket that measures it.
# ---------------------------------------------------------------------------
GROUND_REANNOUNCE_WIRING = """runtime.py, right after the reply to CheckSecondPwdVital
0x4B98 is queued (the block that calls legacy.make_check_second_password_success
or second_password_bypass.make_proactive_second_password_ok -- wherever the 44-byte
reply actually gets appended to actions).

ADD, AFTER that reply is queued, not before (the client must see the OK reply
and the ground truth in that order):

  actions.extend(mob_drop_presence.reannounce_ground(self.mob_loot_cell, legacy))

Nothing else changes: no new import beyond what DROP_PRESENCE_WIRING already put
on the import line, no new event (this call prints its own console line and needs
none), no branch (reannounce_ground returns () on every refusal and on a bare
floor, so the extend is always safe).

WHY NO ``scene=`` ARGUMENT AT THIS CALL SITE: the connection's own
``self.mob_loot_cell`` already knows its scene the same way sustain_a_kill reads
it (cell.publication()); passing this call site's own belief about the scene
would only ever confirm what the cell already says, at the cost of one more name
to keep in sync. Pass it only if a future call site has scene information the
cell itself might not (a resync from another source) and wants the disagreement
refused rather than silently resolved by the cell's own answer.
"""

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
# OPTION (b) OF RE-208's "IT COMES BACK" HALF, RATIFIED BY THE COO ON
# 2026-09-03T19:42+07:00 (notes_to_chief/20260903_1942_COO-DECISION-lane-b-
# bg0015-layer-2-3-unlocked-...md, point 4, word for word:
# "``refresh_frames`` after a blow that does NOT kill = the same 47-byte
# shape, no new mask, one action to roll back").  This is the composer for
# that call site.  It did not exist before round hlwgri: MEASURED on
# ``origin/main`` this round, the non-fatal branch of ``mob_combat.strike``
# (mob_combat.py:2849) returns exactly ``(announce_frame, bar_frame)`` and
# runtime.py's hit dispatch reaches ``return actions`` with no ground call
# at all -- every ground re-emit ON THAT DISPATCH sits inside ``if
# step.death_due:``.  (Not "in that file": the scene-boundary flush near
# runtime.py:7133 publishes ground outside the hit path entirely.
# pf-adversary, pass 2, N8.)  So what is on main today re-draws the floor ON THE
# KILL, which is the "it comes back" half; the "it vanished" half, the
# window between one kill and the next, still has nothing.
#
# [LANE-B ASSUMPTION - AWAITING COO CONFIRMATION].  The COO's own
# ratification keeps this label until a human sees the label NOT blink on a
# real screen -- ``GT-223`` pass criterion (8), which is EYES ONLY (its own
# text: "client-observable (human eyes only)", evidence = a short video).  It
# greps no console line and no ticket greps this module's tokens today.
#
# THIS COMPOSER IS BUILT AND DELIBERATELY NOT WIRED.  See
# :data:`GROUND_SURVIVING_BLOW_CALL_SITE_STATUS` and
# :data:`WITHHELD_GROUND_SURVIVING_BLOW_WIRING`: the wiring ask was drafted
# this round and then WITHDRAWN by this lane, in the same round, on its own
# adversarial measurement.  The reason: a call site there fires once per
# BLOW, and a kill is many blows.
#
# THE NUMBER THAT MATTERS IS THE ONE THIS SERVER CAN PRODUCE, and the first
# number this comment carried was not it.  runtime.py builds exactly one
# attacker -- ``mob_combat.pin_attacker()`` (level 7, ability_str 132),
# ``runtime.py:303``, passed at ``runtime.py:5044`` for every attack; no
# other attacker is constructed anywhere in that file.  Driven against
# Bg0002's shipped roster with THAT attacker (``pin_document``, this round):
#
#     mobs at max_hp 3857, damage 964/blow -> 5 blows/kill -> 4 extra
#     mobs at max_hp 3138, damage 966/blow -> 4 blows/kill -> 3 extra
#
# So the amplification on today's production path is 3-4 extra ground
# publications per kill (~180 B per blow over a five-row floor), NOT the
# 7-132 an earlier draft of this comment quoted from attacker levels 1/10/50
# -- none of which this server can build (pf-adversary, pass 2, and it is
# right: a decision input that is 30x off in the direction of the answer the
# lane already preferred is not evidence, whatever the conclusion).
#
# The withholding stands on the smaller number, because the bar it runs into
# is structural rather than a threshold: the COO
# ruling of 2026-08-30T17:42+07:00 barred any REPEATED resend -- capped or
# movement-driven -- until an attended round fires EXACTLY ONE extra resend
# after a drop and measures whether the label comes back.  THREE IS NOT ONE,
# which is why the smaller number changes nothing about the answer.  The
# 2026-09-03 ratification of option (b) names the event ("a blow that does
# not kill") and nowhere names an amplification at all, so this lane will
# not read it as
# permission for one.  The decision is the COO's, not this lane's, and the
# ask is in pf_bridge/notes_to_chief/20260905_0146_LANE-B-ASK-COO-*.
#
# TWO MORE THINGS THAT MUST BE ANSWERED BEFORE A CALL SITE EXISTS, both
# MEASURED this round and neither fixed here:
#   (i)  runtime.py never rehydrates a session's ``mob_loot_cell`` from the
#        world floor (``runtime.py:1524`` builds an empty ``DropLedgerCell``;
#        ``list_ground_drops_for_scene`` has no caller in runtime.py).  Every
#        publication therefore OMITS every row the session's own cell does
#        not hold -- which is the same replace-by-omission this composer was
#        written to undo, and in ``GT-223``'s filmed window (4b -> 5) it
#        would omit the pre-relogin row once per blow instead of once.
#   (ii) ``sustain_a_kill`` pays ``cell.note_scene_published`` before this
#        function knows whether ``loot_actions`` will succeed, so a raising
#        ``loot_actions`` marks a removal debt paid that nothing published --
#        the ghost ``mob_loot.frames_after_rows_expired``'s ``will_send``
#        exists to prevent.  Reproduced by fault injection this round.
# ---------------------------------------------------------------------------

#: Printed once per surviving blow that composed a generation, empty ground
#: included (``items=0`` = the floor was checked and it was bare), for the
#: same reason the sibling token above prints one: silence must mean "this
#: build has no call site", never "the floor was empty".
#: A DIFFERENT NAME from ``GROUND_REANNOUNCE_AFTER_SECOND_PWD`` on purpose --
#: ``GT-242``'s RECHECK greps that exact string as its negative control, and
#: a second call site printing it would make that control lie.
GROUND_SURVIVING_BLOW_TOKEN = "GROUND_REANNOUNCE_AFTER_A_SURVIVING_BLOW"
#: Printed instead of the line above when nothing could be composed at all.
#: NOT a suffix of :data:`GROUND_SURVIVING_BLOW_TOKEN` -- the word REFUSED
#: comes FIRST, so ``grep`` for the success token cannot also count refusals.
#: (The 0x4B98 sibling above does carry that collision; its exact string is
#: what ``GT-242``'s RECHECK greps, so renaming it is a queue edit this lane
#: may not make -- reported to chief in this round's letter instead.)
GROUND_SURVIVING_BLOW_REFUSED_TOKEN = (
    "GROUND_REANNOUNCE_REFUSED_AFTER_A_SURVIVING_BLOW")

#: WHERE THIS COMPOSER STANDS, in the sibling lane's own vocabulary
#: (``mob_pickup_request.GROUND_AFTER_CALL_SITE_STATUS`` = ``"sent"``,
#: ``PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS`` = ``"landed"``).  A reader
#: who greps this module's name on ``main`` and finds a hit must be able to
#: tell "the fix is shipped" from "the fix is composed and nothing sends it",
#: because that confusion has already cost this project a round once.
#: It is a STRING, not a bool, and it is read by a test rather than by the
#: code: nothing here is gated on it, because the honest gate is that no
#: caller exists.  ITS TEST WALKS ``runtime.py``'s AST rather than comparing
#: this literal with itself -- pf-adversary pass 2 MEASURED that a
#: hand-typed status stays green while a real call site is pasted in, and
#: this lane had proposed grepping this very string as an attended round's
#: pre-boot gate.  So the test fails in BOTH directions now: a landed call
#: site with this still saying "composed_not_sent_no_call_site", and a
#: "sent" written here with nothing calling it.
GROUND_SURVIVING_BLOW_CALL_SITE_STATUS = "composed_not_sent_no_call_site"

#: The blow killed: the per-kill call site already re-emits this same
#: generation, and sending it twice for one blow is the one way this call
#: site could make the wire worse than it is today.
REFUSE_THE_BLOW_KILLED = REFUSED_PREFIX + "the_blow_killed_kill_path_owns_it"
#: ``death_due`` was not a bool -- FAIL CLOSED.  A step this call cannot read
#: is a step this call cannot prove was non-fatal.
REFUSE_DEATH_DUE_UNREADABLE = REFUSED_PREFIX + "step_death_due_unreadable"


def reannounce_ground_after_a_surviving_blow(
    cell: Any, legacy: Any, step: Any,
) -> tuple:
    """Re-send the floor after a blow that did NOT kill.  NEVER RAISES.

    THERE IS NO CALL SITE, AND THAT IS THIS ROUND'S ANSWER, NOT AN OVERSIGHT
    -- see :data:`GROUND_SURVIVING_BLOW_CALL_SITE_STATUS` and
    :data:`WITHHELD_GROUND_SURVIVING_BLOW_WIRING`.  The call site this was
    built for is runtime.py's mob-hit dispatch in the branch where the blow
    did not kill; it is withheld pending a COO decision on a measured 7-132x
    amplification and on two unanswered questions named in the module
    comment above.

    [ASSUMPTION OF LANE B - AWAITING COO] WHY A GROUND RE-EMIT THERE WOULD
    HELP AT ALL: the bar frame is a census recompose (runtime.py prints
    ``MOB_COMBAT_BAR_CENSUS_RECOMPOSE`` beside it), and a census that does
    not carry the floor MIGHT be replace-by-omission for the ground list the
    way RE-092 measured it is for the remote-actor registry.  THAT TRANSFER
    IS NOT MEASURED: ``mob_loot.MOB_LOOT_NONCLAIMS`` entry 18 says in its own
    words that what a RuntimeRes carrying a different derived mask does to a
    live ground entry is UNMEASURED, and ``REEMISSION_REDRAWS_THE_LABEL`` is
    still ``None``.  The only ground wipe this project has actually measured
    is GT-242's, on the ``0x4B98`` reply -- a different frame.  So this
    function is a composer for a hypothesis, not the fix for a proven cause.

    ``step`` is the ``mob_combat.CombatStep`` the caller already has in
    hand; this call reads ONE field of it, ``death_due``, and reads it
    STRICTLY: ``True`` refuses by name (the kill path owns that frame),
    ``False`` proceeds, and anything else -- a missing attribute, ``None``,
    a truthy int, a property that raises -- refuses by a DIFFERENT name.
    Fail-closed: a step this call cannot read is not a step it may treat as
    a survivor, because the cost of guessing wrong is the same generation
    on the wire twice for one blow.

    Returns a TUPLE of ``loot_actions``-shaped entries, ALWAYS -- ``()`` for
    an empty floor, ``()`` for a cell with no scene, ``()`` for a blow that
    killed, ``()`` for anything this call cannot compose.  Never ``None``,
    for the same reason as the sibling: the caller needs no branch, and the
    console line carries the difference between "nothing to send" and
    "something refused".

    CADENCE, MEASURED RATHER THAN ASSERTED: TWO console lines per composing
    call, not one -- this function's own, plus the
    ``MOB_GROUND_WORLD_REMEMBERED ... scene='' new=0 ... keys=none`` line
    ``sustain_a_kill`` prints unconditionally.  That second line is the
    discriminator an attended round greps to tell "the floor was told" from
    "this seam never ran", so a wired version of this call would bury it
    once per blow.  Named here because a cadence claim in a docstring is
    worth exactly what it was measured at, and because it is one more thing
    a call site has to answer for.

    NO TICKET GREPS THESE TWO TOKENS.  ``GT-223`` criterion (8) is EYES ONLY
    (a short video, human eyes, its own text forbids inferring it from the
    console).  Other names in THIS MODULE are grepped -- ``GT-242``'s RECHECK
    runs ``findstr`` for ``MOB_DROP_PRESENCE`` and for the 0x4B98 token above
    -- but nothing collects the surviving-blow pair.  This function's console
    lines are for an operator reading a boot, not evidence a ticket gathers.
    """
    try:
        death_due = step.death_due
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s reason=%s:%r" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN,
            REFUSE_DEATH_DUE_UNREADABLE, error)))
        return ()
    if death_due is True:
        _say_world_line(_console_ascii("%s reason=%s" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN, REFUSE_THE_BLOW_KILLED)))
        return ()
    if death_due is not False:
        _say_world_line(_console_ascii("%s reason=%s value=%r" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN,
            REFUSE_DEATH_DUE_UNREADABLE, death_due)))
        return ()
    try:
        presence = sustain_a_kill(cell, legacy, ())
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s reason=%s:%r" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN, "reannounce_raised", error)))
        return ()
    if presence.refused:
        _say_world_line(_console_ascii("%s scene=%r reason=%s" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN, presence.scene,
            presence.state)))
        return ()
    try:
        actions = loot_actions(presence)
    except Exception as error:                          # noqa: BLE001
        _say_world_line(_console_ascii("%s scene=%r reason=%s:%r" % (
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN, presence.scene,
            "actions_raised", error)))
        return ()
    _say_world_line(_console_ascii("%s scene=%r items=%d" % (
        GROUND_SURVIVING_BLOW_TOKEN, presence.scene, presence.live)))
    return actions


# ---------------------------------------------------------------------------
# THE WIRING ASK, DRAFTED AND THEN WITHHELD BY THIS LANE IN THE SAME ROUND.
# It is kept, struck, rather than deleted -- the record of what was asked for
# before the amplification was measured, exactly as
# WITHDRAWN_DROP_PRESENCE_RESEND_ON_MOVEMENT_WIRING below is kept.
# NOBODY SHOULD WIRE FROM THIS TEXT.  It becomes a live ask only if the COO
# rules on the three things named in the module comment above (the 7-132x
# amplification against the 2026-08-30T17:42 bar; the session cell that is
# never rehydrated, so every publication omits the rows it does not hold;
# the removal debt sustain_a_kill pays before this function knows whether
# anything will be sent) -- and, if the ruling is yes, the shape it should
# take is almost certainly NOT this one but a latch: at most one extra
# publication per new ground generation, which is the "exactly ONE extra
# resend" the 17:42 ruling asked to be measured in the first place.
# ---------------------------------------------------------------------------
WITHHELD_GROUND_SURVIVING_BLOW_WIRING = """~~runtime.py, the mob-hit dispatch,
in the branch that runs when the blow did NOT kill -- after the bar frame is
queued and before the death branch:

  actions.extend(mob_drop_presence.reannounce_ground_after_a_surviving_blow(
      self.mob_loot_cell, legacy, step))~~   WITHHELD, round hlwgri.

WHY THE TEXT ABOVE IS NOT SAFE TO PASTE EVEN IF THE CADENCE QUESTION IS
SETTLED: "after the bar append and before ``if step.death_due:``" names two
different indentation levels.  The append sits inside ``if len(step.frames)
> 1:``; ``if step.death_due:`` is two levels out.  ``CombatStep.frames``
returns a 1-tuple on a killing blow, so at the inner reading the fatal-blow
guard in this module can never fire, and at the outer reading a swing at a
mob already on the HP floor (``no_room`` True, therefore ``death_due``
False) publishes the whole floor for a blow that did nothing.  A future
authorised wiring ask has to name ONE line number and answer the no_room
case; this one did neither.
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
