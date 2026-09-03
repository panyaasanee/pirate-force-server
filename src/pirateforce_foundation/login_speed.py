"""The movement speed a login sends comes from the character's row.

CORE-REQUEST from LANE-DB, `pf_bridge/notes_to_chief/20260902_2010_LANE-DB-
CORE-REQUEST-chief-login-speed-comes-from-the-row-not-a-constant.md`, ordered
by `COO-DECISION 20260902_1846` point 3.  Before this module, every login
composed `player_wire.PLAYER_LOGIN_MOVEMENT_SPEED` (400.0), so a character
whose row held `speed_walk = 300.0` still arrived on screen walking at 400.0.

WHAT THIS MODULE IS AND IS NOT
------------------------------
It is a resolver, not a reader and not a writer.  It is handed the value that
`store.read_typed_attributes()` already produced (or nothing at all) and it
answers ONE question: does that value go on the wire, or does the constant?
The database read stays at the call site that owns a character id; the wire
constant stays in `player_wire` where it is cited.  This module introduces no
second source for either.

THE THREE RULES THE REQUEST BOUND TO THIS SEAM, MEASURED HERE
-------------------------------------------------------------
1. `speed_walk` ONLY.  Nothing else is resolved here (`level`/`hp` are the
   separate, still-open request `20260902_1310`).
2. A row with no value falls back to the constant, never to `0`.  A zero on
   this wire is a value rather than an absence -- the owner's "never guess
   zero" rule, `COO-DECISION 20260901_1059`.
3. Read-only.  Writing a speed belongs to `/speed` (LANE-GM); nothing here
   writes.

FAIL-CLOSED, AND NOT BY A SECOND OPINION
----------------------------------------
Any value that would not survive the wire encoder falls back to the constant
rather than reaching the client.  The predicate that decides that is
`persistence_typed_attrs.validate("speed_walk", ...)` -- the validator the
write path already uses, not a range re-typed here.  A range typed twice is a
range that drifts, and this is the exact shape `COO-DECISION 20260902_0443`
point 1 forbids.

A login must never fail because the database holds something odd, so every
refusal here returns the constant and names itself.  `GT-193` is the standing
evidence for why a bad speed reaching a real client is expensive: `/speed 300`
took a character to HP 0 and then the client locked itself for 426 frames.

WHAT THIS DOES NOT CLAIM
------------------------
* It does not claim `400.0` is wrong.  `400.0` is the client's own
  construction value (`player_wire`'s citation of the BasicAttr ctor
  disassembly).  What was wrong was sending the constant even when the row
  held something else.
* !! IT DOES NOT CLAIM THAT ANY ROW HOLDS ANYTHING ELSE TODAY -- AND THE
  REASON WHY CHANGED UNDER THIS PARAGRAPH, WHICH IS WORSE THAN IT SOUNDS.
  This text used to say: `migrations/006` adds the column NULLable with no
  DEFAULT and `008` is a one-shot seed of the existing cohort, so every later
  character has `speed_walk` NULL forever and every login takes
  `ROW_HAS_NO_VALUE`.  It ended by naming its own expiry condition -- "a
  migration giving the column a DEFAULT was approved in `COO-DECISION
  20260902_1607` and is NOT on `main` at the time this file was written ...
  when it lands, this paragraph is the thing to re-check".
  IT LANDED (`migrations/009_character_birth_defaults.sql`, `speed_walk REAL
  DEFAULT 400.0`), so a newborn's row DOES hold a value and a fresh-database
  login now takes `FROM_ROW`, not `ROW_HAS_NO_VALUE`.
  Nothing reaching the client changed, and that is the trap rather than the
  reassurance: `400.0` IS `player_wire.PLAYER_LOGIN_MOVEMENT_SPEED`, so on a
  fresh database "read the row" and "sent the constant" are BYTE-IDENTICAL on
  the wire.  Only the value attached to the character separates them (the
  call site attaches on `FROM_ROW` alone), so any test that grades this seam
  by the NUMBER is unfalsifiable, and one was written and measured green on
  the exact bug before being removed [pf-adversary, round `eww6tv`; see
  `tests/test_gm_login_scene_override_position_resync.py` and
  `tests/test_login_speed.py::TheRealLoginPathTests`].
  This module is still the seam that makes the row reach the wire; it is
  still not evidence that anything on screen changes today, and a round that
  reports it as a visible feature is reporting something nobody measured.
* It does not claim this makes `GT-193`'s symptom go away.  `COO-DECISION
  20260902_1846` wrote that nonclaim itself and this module stands on it: all
  this does is make the value that reaches the screen the value in the row.
* It does not claim anything client-observable.  This layer is wire-only;
  the eyes-on-screen half is an attended ticket.

ONE LOCK, TWO DOORS: THE `/speed` DEFERRAL HOLDS THE LOGIN FRAME TOO
-------------------------------------------------------------------
`COO-DECISION 20260903_0645`.  `/speed` sends zero bytes today -- LANE-GM's
`gm/speed_wire.send_deferred()` holds every frame that door composes -- but
`/speed` STILL COMMITS THE ROW, and since `#605` a login READS that row.  So
the door this project closed is closed and the window beside it was open:
`/speed 300` leaves `300.0` in the database, the next login encodes it as
`00 00 96 43`, and that is the byte-for-byte value `GT-193` was sending when
a real client locked itself for 426 frames -- with "log in again" being the
RECOVERY STEP written in `GT-193` and `GT-218` themselves.

So while `send_deferred()` is true this resolver returns the constant no
matter what the row holds, and says `wire_deferred` rather than `from_row`.

FOUR THINGS THAT ARE DELIBERATE ABOUT THAT GATE:

1. It is asked LIVE, through the function, every login.  Copying the boolean
   into a module constant here would mean the round that flips LANE-GM's
   `SPEED_LOGIN_READ_LANDED` (one line, in their file) opens one door and not
   the other -- which is the exact class of half-open state this gate exists
   to prevent.
2. It FAILS CLOSED.  An import error, a renamed function, an exception inside
   it -- anything that stops this module from ASKING -- returns the constant
   under `deferral_unreadable`.  A gate that cannot be read is a gate that is
   shut.  (Not literally EVERY failure: an exception whose own `__str__`
   raises escapes while this module is composing the detail.  That shape
   predates this gate and lives on the store read as well.)
3. A PER-SESSION TRIAL DOES NOT OPEN THIS DOOR -- `wire_trial_only`, and this
   is the half a first draft got wrong (pf-adversary, round `4lf2hl`, D1).
   `COO-DECISION 20260903_0646` opens `/speed` for an attended round through a
   RUNTIME gate that sanctions ONE value: `PF_SPEED_TRIAL=<value>` lets
   `/speed <that value>` out and holds every other value.  If that gate is
   implemented by making `send_deferred()` answer False for the session, then
   a login gated on `send_deferred()` alone would send WHATEVER the row holds
   -- and `/speed` writes its row even when the frame is withheld, so the row
   can hold a value the trial never sanctioned.  Concretely: trial opens for
   `400`, tester types `/speed 300` (frame withheld, ROW WRITTEN), the ticket's
   own recovery step re-logs in, and `00 00 96 43` goes out: the GT-193 bytes,
   in the round written to prevent them.  So the row is allowed out only when
   the wire is open for EVERY value, which is what LANE-GM's durable
   `SPEED_LOGIN_READ_LANDED` means; a trial leaves this door shut.  Asking for
   that flag is asking THEIR module live, exactly like the function -- it is
   not a second copy of the truth, and there is an AST pin in the tests that
   fails if this module ever grows one.
4. It sits in `resolve_for_character` ONLY, never in `resolve`.  `resolve` is
   a pure predicate, and LANE-GM's `/speed` console line calls it to print
   `next_login=<reason>`: what THAT line answers is "what would the row do at
   a login if it went out", and gating it would make the console announce the
   deferral it is already announcing on the same line.  The wire path -- the
   one that composes bytes for a client -- goes through
   `resolve_for_character`, and that is where the frame is held.
   !! THE COST OF THAT CHOICE, NAMED RATHER THAN HIDDEN: that console line's
   `next_login_sends=<number>` now over-promises on the deferred route -- it
   says what the row WOULD send, and this gate means no row goes out at all
   while the wire is held.  That field is `gm/chat_command_action.py`'s, which
   this round may not touch; LANE-GM was told in writing
   (`pf_bridge/notes_to_chief/20260903_0725_CHIEF-TO-LANE-GM-*`).

WHAT THIS COSTS TODAY, STATED WITHOUT THE COMFORTABLE HALF: after
`migrations/009` the column's DEFAULT is `400.0`, which IS
`player_wire.PLAYER_LOGIN_MOVEMENT_SPEED` -- so on a database whose rows still
hold that default, the bytes are identical with the gate and without it, and
nothing a player sees changes.  It is NOT true that this is free on every
live database, the owner's included: hers may carry a `300.0` row from
`GT-193` today, and on that database the gate changes the bytes -- which is
the entire reason it exists.  `COO-DECISION 20260903_0645` states both halves
and the first draft of this paragraph quoted only the reassuring one.
"""

_CONSOLE_PREFIX = "LOGIN_SPEED"

#: The row had a usable value and it is what the login sends.
FROM_ROW = "from_row"
#: The row has no value for this column, so the wire constant goes out.
ROW_HAS_NO_VALUE = "row_has_no_value"
#: The row held something the wire encoder would refuse, so the constant goes
#: out and the reason names the validator's own complaint.
ROW_REFUSED_BY_VALIDATOR = "row_refused_by_validator"
#: The read itself could not happen (no store, unknown character, a database
#: error).  A login is not failed for this.
ROW_COULD_NOT_BE_READ = "row_could_not_be_read"
#: The row held a number the ENCODER would carry and a PLAYER could not use:
#: zero or negative.  See `_A_SPEED_A_PLAYER_CAN_USE` for why this floor lives
#: here rather than in the write path's validator.
ROW_SPEED_NOT_POSITIVE = "row_speed_not_positive"
#: The `/speed` wire is deferred (`gm.speed_wire.send_deferred()`), so the row
#: does not reach this login either and the constant goes out.  The row is not
#: read at all under this reason: nothing about it can change the answer.
#: `COO-DECISION 20260903_0645`.
WIRE_DEFERRED = "wire_deferred"
#: The deferral itself could not be asked (import error, renamed function, an
#: exception inside it).  Fail-closed: the constant goes out exactly as if the
#: wire were deferred, and the detail names what stopped the question.
DEFERRAL_UNREADABLE = "deferral_unreadable"
#: The `/speed` wire is open for ONE SANCTIONED VALUE only -- an attended
#: trial (`PF_SPEED_TRIAL`, `COO-DECISION 20260903_0646`) rather than the
#: durable landing.  This seam is handed no value to check against, so the row
#: stays off the login frame: see point 3 of the module docstring for the
#: concrete GT-218 sequence that makes this the safe answer.
WIRE_TRIAL_ONLY = "wire_trial_only"

#: Every reason this module can return.  A console reader (and the tests) may
#: treat a token outside this set as a bug rather than as news.
REASONS = frozenset({
    FROM_ROW,
    ROW_HAS_NO_VALUE,
    ROW_REFUSED_BY_VALIDATOR,
    ROW_COULD_NOT_BE_READ,
    ROW_SPEED_NOT_POSITIVE,
    WIRE_DEFERRED,
    DEFERRAL_UNREADABLE,
    WIRE_TRIAL_ONLY,
})

#: THE ONE FLOOR THIS MODULE OWNS, AND WHY IT IS NOT THE VALIDATOR'S JOB.
#:
#: pf-adversary measured the hole: `persistence_typed_attrs.validate` bounds
#: an f32 column to the whole f32 range and refuses only a nonzero value that
#: UNDERFLOWS to zero -- it admits `0.0` itself and it admits `-600.0`.  That
#: is correct for what that validator is for (protecting SQLite and the
#: encoder) and wrong for what this module is for.  `/speed 0` commits a row
#: whose frame is currently deferred, so nothing happens in that session --
#: and then the NEXT login paints `0.0` into BasicAttr `+0x54` and the
#: character cannot walk, with no console line saying why.
#:
#: So the encoder range stays where it is (re-typing it here is the drift the
#: module docstring refuses), and this module adds the one thing a validator
#: about storage cannot know: a movement speed a player can actually use is
#: greater than zero.  Anything else falls back to the constant AND SAYS SO.
#: `GT-193` is the standing evidence for what a wrong number on this field
#: costs -- HP 0, the character dead, and the client locked for 426 frames.
_A_SPEED_A_PLAYER_CAN_USE = "greater than zero"

#: The column this module resolves, and the only one it may resolve.
COLUMN = "speed_walk"


class ResolvedLoginSpeed:
    """The value a login will send, and why that value and not another."""

    __slots__ = ("value", "reason", "detail")

    def __init__(self, value: float, reason: str, detail: str = ""):
        if reason not in REASONS:
            raise ValueError(
                f"{reason!r} is not a registered login-speed reason "
                f"(registered: {sorted(REASONS)})"
            )
        if not isinstance(value, float):
            raise TypeError(
                "a resolved login speed is a float; got "
                f"{type(value).__name__}"
            )
        self.value = value
        self.reason = reason
        self.detail = detail

    @property
    def came_from_the_row(self) -> bool:
        return self.reason == FROM_ROW

    def console_line(self) -> str:
        """One ASCII line naming the value and the reason.

        ASCII only, and no exception path: the bridge console is cp874 and a
        character outside that page kills the tool mid-report (the round-86
        and round-142 lesson, `AGENTS.md`).  The detail is the validator's own
        message, which is ASCII by construction, but it is filtered anyway
        rather than trusted.
        """
        line = f"{_CONSOLE_PREFIX} {self.reason} value={self.value!r}"
        if self.detail:
            line = f"{line} detail={self.detail}"
        return "".join(c if 32 <= ord(c) < 127 else "?" for c in line)

    def __repr__(self) -> str:
        return (
            f"ResolvedLoginSpeed(value={self.value!r}, "
            f"reason={self.reason!r}, detail={self.detail!r})"
        )


def resolve(stored, *, fallback: float) -> ResolvedLoginSpeed:
    """Decide between the row's value and the wire constant.

    `stored` is what the row holds for `speed_walk`, or `None` for a row that
    holds no value there.  `fallback` is the caller's constant -- passed in
    rather than imported so this module never becomes a second place the
    number 400.0 is written down.
    """
    if not isinstance(fallback, float):
        raise TypeError(
            "the login-speed fallback is a float (player_wire."
            "PLAYER_LOGIN_MOVEMENT_SPEED); got "
            f"{type(fallback).__name__}"
        )
    if stored is None:
        return ResolvedLoginSpeed(fallback, ROW_HAS_NO_VALUE)
    from . import persistence_typed_attrs as typed_attrs
    try:
        value = typed_attrs.validate(COLUMN, stored)
    except typed_attrs.TypedAttrError as exc:
        return ResolvedLoginSpeed(
            fallback, ROW_REFUSED_BY_VALIDATOR, detail=str(exc),
        )
    # `validate` returns the f32-rounded number for a REAL column, which is
    # the number the client will be sent; anything else means the column's
    # storage rule changed under this module rather than that this value is
    # unusual, so it is refused rather than coerced.
    if not isinstance(value, float) or isinstance(value, bool):
        return ResolvedLoginSpeed(
            fallback, ROW_REFUSED_BY_VALIDATOR,
            detail=(
                f"{COLUMN} validated to {type(value).__name__}, not a float; "
                "this module resolves an f32 wire field only"
            ),
        )
    if value <= 0.0:
        return ResolvedLoginSpeed(
            fallback, ROW_SPEED_NOT_POSITIVE,
            detail=(
                f"{COLUMN}={value!r} stores and encodes, but a movement "
                f"speed a player can use is {_A_SPEED_A_PLAYER_CAN_USE}"
            ),
        )
    return ResolvedLoginSpeed(value, FROM_ROW)


def held_by_the_speed_deferral(fallback: float):
    """The gate `COO-DECISION 20260903_0645` put across this seam.

    Returns a `ResolvedLoginSpeed` carrying the constant when the `/speed`
    wire is deferred OR when the deferral cannot be asked, and `None` when the
    wire is open and the row may go out.

    THE QUESTION IS ASKED THROUGH LANE-GM'S OWN FUNCTION, imported inside the
    call rather than at module scope.  Two reasons, and neither is style: a
    module-level import would freeze nothing (the function is re-read each
    call) but WOULD make this module fail to import if `gm` ever failed to,
    turning a deferral question into a dead login path; and the local import
    is what makes the fail-closed branch below reachable and testable at all.

    ANYTHING BUT A LITERAL `False` HOLDS THE FRAME.  `send_deferred()` is
    typed `-> bool` today; if a later round returns `None` from an early exit,
    the truthiness test that "reads naturally" would send the row.  The
    deferral is the safe answer, so it is the DEFAULT answer.

    TWO QUESTIONS, NOT ONE, and the second is the one a first draft missed
    (pf-adversary, round `4lf2hl`, D1; module docstring point 3).  An attended
    TRIAL opens `/speed` for a single sanctioned value; this seam is handed no
    value to check, and the row can hold one the trial never sanctioned, so
    the row is released only when LANE-GM's durable
    `SPEED_LOGIN_READ_LANDED` is `True` as well -- read off THEIR module, live,
    for the same reason the function is.
    """
    if not isinstance(fallback, float) or isinstance(fallback, bool):
        # The same message `resolve` raises, because this gate now answers
        # first and a caller with a bad fallback must still be pointed at its
        # own call site rather than at the resolver's constructor.
        raise TypeError(
            "the login-speed fallback is a float (player_wire."
            "PLAYER_LOGIN_MOVEMENT_SPEED); got "
            f"{type(fallback).__name__}"
        )
    try:
        from .gm import speed_wire
        deferred = speed_wire.send_deferred()
        landed = speed_wire.SPEED_LOGIN_READ_LANDED
    except Exception as exc:   # noqa: BLE001 -- an unaskable gate is a shut one
        return ResolvedLoginSpeed(
            fallback, DEFERRAL_UNREADABLE,
            detail=(
                f"gm.speed_wire could not be asked "
                f"({type(exc).__name__}: {exc}); the constant goes out"
            ),
        )
    if deferred is not False:
        return ResolvedLoginSpeed(
            fallback, WIRE_DEFERRED,
            detail=(
                f"gm.speed_wire.send_deferred() returned {deferred!r}, so the "
                f"row does not reach this login either"
            ),
        )
    if landed is not True:
        return ResolvedLoginSpeed(
            fallback, WIRE_TRIAL_ONLY,
            detail=(
                "gm.speed_wire.send_deferred() is open but "
                f"SPEED_LOGIN_READ_LANDED is {landed!r}: the wire is open for "
                "a sanctioned value, not for whatever this row holds"
            ),
        )
    return None


def _withheld_row_detail(store, character_id) -> str:
    """What the held frame WOULD have carried, for the console line only.

    !! THIS READ EXISTS BECAUSE SKIPPING IT MADE THE GATE UNGRADEABLE, and
    that was measured rather than argued (pf-adversary, round `4lf2hl`, D5).
    Without it every login prints the identical `wire_deferred` line whether
    the row holds the harmless default or the `300.0` that locked a client --
    so an attended round can never show that the gate caught anything, and the
    round that has to prove `COO-DECISION 20260903_0645` is on `main` has no
    console evidence to point at.  It also restores a warning the gate would
    otherwise have silenced (D6): a database missing `migrations/006` used to
    say `no such column: speed_walk` at every login, and would have gone quiet
    until the first trial session.

    IT CANNOT CHANGE THE ANSWER AND IT CANNOT FAIL A LOGIN.  The caller has
    already decided; this only appends text, and every failure -- including a
    store whose exception cannot even be rendered -- comes back as a string.
    """
    try:
        attributes = store.read_typed_attributes(character_id)
        return f" withheld_row={attributes.get(COLUMN)!r}"
    except Exception as exc:   # noqa: BLE001 -- a console detail outranks nothing
        try:
            return f" withheld_row=unreadable({type(exc).__name__})"
        except Exception:   # noqa: BLE001
            return " withheld_row=unreadable"


def resolve_for_character(store, character_id, *, fallback: float) -> ResolvedLoginSpeed:
    """`resolve` fed by the store, with the read itself made non-fatal.

    Reads through `store.read_typed_attributes`, which LANE-DB's charter names
    as the existing door for this (its own CORE-REQUEST letter, point 2: no new
    store method is needed).  That method OMITS a NULL column rather than
    rendering it as `0`, so a missing key here really does mean "the database
    does not know this one".

    A login is never failed by this function.  `KeyError` (no such character,
    or soft-deleted) and any database-level error come back as
    `ROW_COULD_NOT_BE_READ` carrying the constant -- the same value main sends
    today -- so the worst case of this whole change is the behaviour that
    preceded it.

    THE `/speed` DEFERRAL IS ASKED FIRST, BEFORE THE ROW DECIDES ANYTHING
    (`COO-DECISION 20260903_0645`).  While that wire is held, nothing the row
    holds can change the answer -- but the row is still READ, for the console
    line only, and `_withheld_row_detail` explains why a first draft that
    skipped the read was wrong (pf-adversary D5/D6).  The module docstring's
    "one lock, two doors" section carries the evidence for the gate itself.
    """
    held = held_by_the_speed_deferral(fallback)
    if held is not None:
        return ResolvedLoginSpeed(
            held.value, held.reason,
            detail=held.detail + _withheld_row_detail(store, character_id),
        )
    try:
        attributes = store.read_typed_attributes(character_id)
        stored = attributes.get(COLUMN)
    except Exception as exc:   # noqa: BLE001 -- a login outranks a bad read
        # The MESSAGE, not only the class.  A database missing migration 006
        # ("no such column: speed_walk") and a WAL lock timeout ("database is
        # locked") are both `OperationalError`, and a console line that says
        # only the class name cannot tell an operator which one is happening.
        # `console_line` ASCII-filters whatever lands here.
        return ResolvedLoginSpeed(
            fallback, ROW_COULD_NOT_BE_READ,
            detail=f"{type(exc).__name__}: {exc}",
        )
    return resolve(stored, fallback=fallback)
