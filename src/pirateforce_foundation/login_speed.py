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

#: Every reason this module can return.  A console reader (and the tests) may
#: treat a token outside this set as a bug rather than as news.
REASONS = frozenset({
    FROM_ROW,
    ROW_HAS_NO_VALUE,
    ROW_REFUSED_BY_VALIDATOR,
    ROW_COULD_NOT_BE_READ,
    ROW_SPEED_NOT_POSITIVE,
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
    """
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
