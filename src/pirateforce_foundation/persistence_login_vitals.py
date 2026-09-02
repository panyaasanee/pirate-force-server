"""The level and HP a login sends come from the character's row.

CORE-REQUEST from LANE-DB, `pf_bridge/notes_to_chief/20260902_1310_LANE-DB-
CORE-REQUEST-login-carries-hp-and-level-from-the-row.md`, approved by
`pf_bridge/notes_to_chief/20260902_1143_COO-DECISION-login-reads-vitals-from-
row-approved-none-falls-to-literal-and-logs-gap.md` points 1/2/4.  EVERY
CITATION IN THIS FILE THAT BEGINS `pf_bridge/` IS IN THE OTHER REPOSITORY AND
A REVIEWER OF THIS ONE CANNOT OPEN IT -- named that way because
`persistence_vitals.py` already took this defect once ("a `pf-adversary` pass
searched for it here, found nothing, and was right to call the citation
unopenable").  Today every login composes two
hardcoded `100`s and `player_wire.PLAYER_LOGIN_LEVEL`, so a player who is
beaten down to HP 37, logs out and logs back in arrives at FULL HEALTH -- the
M4 hole this lane exists to close.

!! WHICH TWO `100`s, BECAUSE THE REQUEST LETTER NAMED THE WRONG PAIR.  There
are FOUR `legacy.u32tag(0x14, 100)` in `player_wire.py` today, in two
different functions, and THE ONES THAT MATTER ARE NAMED BY SYMBOL HERE RATHER
THAN BY LINE -- `persistence_vitals.py` records why: "named by symbol rather
than by line, because a `pf-adversary` pass moved those lines with an
unrelated edit and every test in this lane stayed green".

* `player_wire._make_actor_attr_with_name_and_class` -- the composer the REAL
  login path reaches (`legacy_bridge.start_game` ->
  `make_actor_attr_with_name_and_class`).  It is the one that already takes
  the walk-speed keyword `login_speed.py` feeds, and its `level` goes out
  through `u16tag(0x12, ...)`
  while the two HP numbers go out through `u32tag(0x14, ...)`.  THIS is the
  pair a seam must parameterise.
* `player_wire._make_actor_attr_with_name` -- what that file's own docstring
  calls "the frozen reference the other lanes compare against".  The login
  seam no longer calls it, and it carries no level field at all.

CORE-REQUEST `20260902_1310` cited the frozen one, so a seam that followed the
citation literally would have parameterised a baseline other lanes pin
byte-for-byte AND left the login unchanged.  Measured on `30e150a1`; a
correction letter went to chief the same round
(`pf_bridge/notes_to_chief/20260903_0116_...`).

WHAT THIS MODULE IS AND IS NOT
------------------------------
It is the LANE-DB half of that request, and it is a resolver: it is handed
what `store.read_character_vitals()` already produced and it answers ONE
question -- do the row's three numbers go on the wire, or do the caller's
literals?  It reads nothing by itself except through the store door it is
given, it writes nothing, and it does not import `player_wire`: the fallbacks
are PASSED IN so this module never becomes a second place `1` and `100` are
written down.  The seam that calls it is chief's (`legacy_bridge.start_game`
/ `session.py`), and it is deliberately still unwritten here.

This is the same shape `login_speed.py` has for `speed_walk`, on purpose: a
reader who has read that module has read this one.  What is NOT the same is
the door -- `login_speed` reads `store.read_typed_attributes` (raw columns),
this one reads `store.read_character_vitals` (the GAP-CARRYING door).  The
request's point 2 required exactly that and said why: `_or_none` throws the
gap list away by design, so a row that is BROKEN (`level 0`, `hp_current >
hp_max`, `hp_max 0`) would be indistinguishable from a row that is merely
UNSEEDED, and an operator reading the console could not tell which server they
were looking at.

ALL THREE OR NONE.  THIS IS THE RULE, NOT AN IMPLEMENTATION DETAIL
------------------------------------------------------------------
There is no path here that sends the row's `hp_current` next to the literal
`level`.  A mixed block is the shape `pf_bridge`'s `PANYA-DECISION 20260901_1059` bans --
"never send a block whose unknown fields were guessed" -- arriving one field
at a time instead of all at once: the client cannot tell which of the three it
is being told the truth about.  So a single gap on any one of the three sends
all three literals and the console line names the gap.

WHAT THIS DOES NOT CLAIM
------------------------
* !! IT DOES NOT CLAIM ANY BYTE ON A FRESH DATABASE CHANGES, AND ON ONE NONE
  DOES.  `persistence_vitals` seeds a newborn at `level 1, hp 100/100`
  (through the one birth-value function `COO-DECISION 20260902_0443` point 1
  names -- NOT NAMED HERE, because that lane's own guard scans this tree for
  a second caller and a mention is indistinguishable from a call to it),
  which is EXACTLY the three literals the login sends
  today, so "read the row" and "send the constant" produce identical bytes on
  every character of a fresh install.  This is the same trap `COO-DECISION
  20260903_0054` -- in `pf_bridge`, unopenable from here -- caught the speed
  seam in (009's `DEFAULT 400.0` equals the
  hardcoded 400.0), and it is written here so that no round reports this
  module as a win on screen.  The bytes differ only for a row something has
  MOVED -- `store.apply_hp_damage` is the mover that exists -- and that
  difference is the whole point: HP survives a logout.
* It does not claim to be plugged in.  Nothing calls this module at the commit
  that adds it; `grep -rn "persistence_login_vitals" src/` finds the file and
  nothing else.  Until chief lands the two seams the request asks for, every
  login behaves exactly as `main` does.
* It does not claim anything client-observable.  This layer is wire-only.
* It does not decide what a server SHOULD do about a character whose row says
  it is dead, AND THE OPEN EDGE IS NAMED RATHER THAN LEFT TO BE FOUND: with
  the seam landed, this is the one login in the server where the wire and the
  database are knowingly made to disagree, and "beaten to 0, logged out, back
  at full health" -- the case M4 is actually named for -- stays exactly as it
  is until COO rules.  See `ROW_HP_NOT_POSITIVE` below: this module takes the one
  option that cannot regress anything, and the decision is asked for by letter
  rather than taken here.
"""

_CONSOLE_PREFIX = "LOGIN_VITALS"

#: The row held all three numbers, every rule passed, and they are what the
#: login sends.
FROM_ROW = "from_row"
#: Not one of the three columns has a value.  The literals go out.
ROW_HAS_NO_VALUE = "row_has_no_value"
#: The vitals gate returned at least one gap -- a column with no value, or a
#: cross-column rule that failed.  The literals go out and the detail names
#: every gap, so a broken row and an unseeded row read differently.
ROW_REFUSED_BY_VITALS_GATE = "row_refused_by_vitals_gate"
#: A number that survived the vitals gate would not survive the column's own
#: storage validator (so the encoder would refuse it too).  Literals go out.
#:
#: MEASURED, so nobody reads this as the front door: `persistence_vitals.
#: resolve` RAISES `VitalsError` for a stored number outside a column's range
#: rather than reporting it as a gap, so a row like that reaches
#: `resolve_for_character` as an exception and comes back as
#: `ROW_COULD_NOT_BE_READ` instead.  This reason therefore guards a
#: resolution built by HAND, and a future gate that reports instead of
#: raising.  It stays because what it stops is `struct.error` raised by
#: `legacy.u32tag` INSIDE a login.
ROW_REFUSED_BY_VALIDATOR = "row_refused_by_validator"
#: The read itself could not happen (no store, unknown or soft-deleted
#: character, a database error).  A login is never failed for this.
ROW_COULD_NOT_BE_READ = "row_could_not_be_read"
#: The row's numbers are internally consistent and say the character is DEAD
#: (`hp_current` is not positive).  See the constant below for why that sends
#: the literals rather than a zero.
ROW_HP_NOT_POSITIVE = "row_hp_current_not_positive"

#: Every reason this module can return.  A console reader (and the tests) may
#: treat a token outside this set as a bug rather than as news.
REASONS = frozenset({
    FROM_ROW,
    ROW_HAS_NO_VALUE,
    ROW_REFUSED_BY_VITALS_GATE,
    ROW_REFUSED_BY_VALIDATOR,
    ROW_COULD_NOT_BE_READ,
    ROW_HP_NOT_POSITIVE,
})

#: WHY A DEAD ROW SENDS THE LITERALS, AND WHY THAT IS A QUESTION AND NOT AN
#: ANSWER.
#:
#: `hp_current = 0` is not a guessed zero -- it is a value, and it means the
#: character died.  So this module may not treat it as "no value" and it does
#: not: it gives it its own reason token and its own console line.
#:
#: What to DO about it is a game decision this lane does not own (revive at a
#: spawn point?  send the corpse and let the client show a death screen?), and
#: `GT-193` is standing evidence that a wrong number on a login block is
#: expensive: HP 0 arrived, the character died, and the client then ignored
#: 426 frames of clicks.  Of the two options available to a resolver, sending
#: the literals is the one that cannot regress anything -- it is byte-for-byte
#: what every login sends today -- while sending a zero would put a new number
#: on the wire on the strength of a decision nobody made.  So the safe half is
#: taken here and the decision is asked for in a letter to COO
#: (`pf_bridge/notes_to_chief/20260903_0115_...`), which is what this lane's
#: charter says to do with a choice that is hard to walk back.
_A_LOGIN_A_PLAYER_CAN_PLAY = "hp_current greater than zero"


class ResolvedLoginVitals:
    """The three numbers a login will send, and why those and not others."""

    __slots__ = ("level", "hp_current", "hp_max", "reason", "detail")

    def __init__(
        self, level: int, hp_current: int, hp_max: int,
        reason: str, detail: str = "",
    ):
        if reason not in REASONS:
            raise ValueError(
                f"{reason!r} is not a registered login-vitals reason "
                f"(registered: {sorted(REASONS)})"
            )
        for name, value in (
            ("level", level), ("hp_current", hp_current), ("hp_max", hp_max),
        ):
            # `bool` first: `True` is an `int` in python and would sail
            # through `isinstance(value, int)` and then encode as `1`.
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"a resolved login {name} is an int; got "
                    f"{type(value).__name__}"
                )
        self.level = level
        self.hp_current = hp_current
        self.hp_max = hp_max
        self.reason = reason
        self.detail = detail

    @property
    def came_from_the_row(self) -> bool:
        return self.reason == FROM_ROW

    def wire_kwargs(self) -> dict:
        """The keyword arguments a login seam should splat, or `{}`.

        `{}` for every reason except `FROM_ROW`, which is what makes the
        request's `**extra` shape fail-closed at the CALL SITE as well as
        here: a seam that splats this dict sends its own literals whenever
        this module refused, without the seam having to know the reason
        codes.  The names are the ones the request asked chief for.
        """
        if not self.came_from_the_row:
            return {}
        return {
            "level": self.level,
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
        }

    def console_line(self) -> str:
        """One ASCII line naming the numbers and the reason.

        ASCII only, and no exception path: the bridge console is cp874 and a
        character outside that page kills the tool mid-report (the round-86
        and round-142 lesson, `AGENTS.md`).  The detail carries a gap list
        built from this repository's own ASCII reason strings, but it is
        filtered anyway rather than trusted.
        """
        line = (
            f"{_CONSOLE_PREFIX} {self.reason} level={self.level!r} "
            f"hp={self.hp_current!r}/{self.hp_max!r}"
        )
        if self.detail:
            line = f"{line} detail={self.detail}"
        return "".join(c if 32 <= ord(c) < 127 else "?" for c in line)

    def __repr__(self) -> str:
        return (
            f"ResolvedLoginVitals(level={self.level!r}, "
            f"hp_current={self.hp_current!r}, hp_max={self.hp_max!r}, "
            f"reason={self.reason!r}, detail={self.detail!r})"
        )


def _gap_detail(gaps) -> str:
    """Every gap, not the first one, in one line.

    An operator who fixes only the column the console named comes straight
    back to another line saying the same thing about the next one -- and a
    `pf-adversary` pass measured that a first draft's claim to list them all
    was ungraded, so it is now one function with one test on it.
    """
    return "; ".join(f"{gap.column}[{gap.reason}]" for gap in gaps)


def _fallback(
    reason: str, detail: str,
    fallback_level: int, fallback_hp_current: int, fallback_hp_max: int,
) -> ResolvedLoginVitals:
    return ResolvedLoginVitals(
        fallback_level, fallback_hp_current, fallback_hp_max, reason, detail,
    )


def resolve(
    resolution, *,
    fallback_level: int, fallback_hp_current: int, fallback_hp_max: int,
) -> ResolvedLoginVitals:
    """Decide between the row's three numbers and the caller's three literals.

    `resolution` is a `persistence_vitals.VitalsResolution` -- what
    `store.read_character_vitals()` returns.  The three fallbacks are the
    caller's own constants (`player_wire.PLAYER_LOGIN_LEVEL` and the two `100`
    literals inside `player_wire._make_actor_attr_with_name_and_class`); they
    are parameters rather than
    imports so that this module cannot drift away from what the wire actually
    sends when one of those numbers changes.
    """
    for name, value in (
        ("level", fallback_level),
        ("hp_current", fallback_hp_current),
        ("hp_max", fallback_hp_max),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"the login-vitals {name} fallback is an int (player_wire's "
                f"own login constant); got {type(value).__name__}"
            )
    from . import persistence_vitals as vitals

    gaps = getattr(resolution, "gaps", None)
    if gaps is None:
        raise TypeError(
            "resolve() takes a persistence_vitals.VitalsResolution (what "
            "store.read_character_vitals returns); got "
            f"{type(resolution).__name__}"
        )
    if gaps:
        detail = _gap_detail(gaps)
        # "nothing is seeded at all" is a different server from "one rule
        # failed", and a reader should not have to count gaps to tell.
        every_column_unseeded = len(gaps) == len(vitals.VITAL_COLUMNS) and all(
            gap.reason == vitals.REASON_NOT_SEEDED for gap in gaps
        )
        reason = ROW_HAS_NO_VALUE if every_column_unseeded else (
            ROW_REFUSED_BY_VITALS_GATE
        )
        return _fallback(
            reason, detail,
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    # THE WHOLE GATE AGAIN, NOT A RANGE CHECK.  A first draft re-validated each
    # column with `persistence_typed_attrs.validate` and a `pf-adversary` pass
    # measured what that misses: a `VitalsResolution` carrying `gaps=()` and
    # `level = 0`, or `hp_max = 0`, or `hp_current > hp_max`, sailed straight
    # through as `FROM_ROW` -- two of those are states `persistence_vitals`
    # REFUSES BY NAME (`REASON_LEVEL_ZERO`, `REASON_HP_MAX_ZERO`).  A guard
    # that re-implements one third of a gate is a guard that only says it
    # covers the gate.  So the numbers go back through
    # `persistence_vitals.resolve` itself -- the same door, no second copy of
    # any rule, nothing to drift -- and a `float` where an `int` belongs is
    # refused there too rather than silently truncated.
    #
    # `resolve` RAISES (rather than gapping) for a number outside a column's
    # storage range, so the call is wrapped: a login is not failed by a row.
    # THE RAW `present`, NOT THE NUMBERS `require()` HANDS BACK.  `require()`
    # builds `Vitals` with `int(...)`, so `hp_current = 1.5` becomes `1`
    # before any check this module could make -- a silent truncation a
    # `pf-adversary` pass measured going out as `FROM_ROW`.  Re-gating the
    # values the resolution actually carries is what refuses it.
    present = getattr(resolution, "present", None)
    if present is None:
        raise TypeError(
            "a persistence_vitals.VitalsResolution carries `present`; got "
            f"{type(resolution).__name__}"
        )
    try:
        rechecked = vitals.resolve(dict(present))
    except Exception as exc:   # noqa: BLE001 -- a login outranks a bad row
        return _fallback(
            ROW_REFUSED_BY_VALIDATOR, f"{type(exc).__name__}: {exc}",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    if rechecked.gaps:
        return _fallback(
            ROW_REFUSED_BY_VITALS_GATE, _gap_detail(rechecked.gaps),
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    usable = rechecked.require()
    if not usable.alive:
        # `Vitals.alive` rather than a comparison written again here, so that
        # this module cannot end up with the `>= 0` version of the rule while
        # `persistence_vitals` has the `> 0` one.
        return _fallback(
            ROW_HP_NOT_POSITIVE,
            f"{vitals.HP_CURRENT_COLUMN}={usable.hp_current!r} is stored and "
            f"encodable, but a login a player can play needs "
            f"{_A_LOGIN_A_PLAYER_CAN_PLAY}",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    return ResolvedLoginVitals(
        usable.level, usable.hp_current, usable.hp_max, FROM_ROW,
    )


def resolve_for_character(
    store, character_id, *,
    fallback_level: int, fallback_hp_current: int, fallback_hp_max: int,
) -> ResolvedLoginVitals:
    """`resolve` fed by the store, with the read itself made non-fatal.

    Reads through `store.read_character_vitals`, the gap-carrying door this
    lane already owns (`store.py:1104`); no new store method is needed and
    none is added.

    A login is never failed by anything the STORE does or returns.  `KeyError`
    (no such character, or soft-deleted), any database-level error, and any
    shape the store hands back that `resolve` cannot read come back as
    `ROW_COULD_NOT_BE_READ` carrying the caller's literals -- the same three
    numbers main sends today -- so the worst case of this whole change is the
    behaviour that preceded it.

    THE ONE EXCEPTION THIS FUNCTION STILL RAISES is `TypeError` for a
    `fallback_*` that is not an `int`, and it is raised BEFORE the read so it
    can never be mistaken for a database problem.  That value is the caller's
    own wire constant, not player data.
    """
    # THE `resolve` CALL IS INSIDE THIS TRY, AND THAT PLACEMENT IS THE POINT.
    # A first draft wrapped only the read, and a `pf-adversary` pass measured
    # five shapes that then escaped as exceptions THROUGH this function: a
    # store returning `None`, a resolution whose `present` holds a string or a
    # `None`, a non-iterable `gaps`, and a gap object whose `.reason` raises.
    # The class that escaped was `TypeError`/`ValueError`, and the sibling
    # seam's own comment (in `session.py`, above its `login_speed` call)
    # records what that costs: `runtime.py`'s START_GAME_REQ handler catches
    # `KeyError`, `PermissionError`, `ValueError` and `RuntimeError`, and
    # `v141` wraps the per-connection loop in `try/finally` with no `except`
    # at all -- so an escaping `TypeError` unwinds the listener thread and
    # parks the client on "connecting".  The module that exists so a login
    # cannot fail was the one failing it.
    #
    # A PROGRAMMING ERROR IN THE SEAM IS STILL RAISED, and the split is
    # deliberate: a `fallback_*` that is not an `int` is the CALLER's own
    # constant, fixed at the call site and wrong on every login including the
    # first, so hiding it would bury a wiring bug behind a console line nobody
    # reads.  Everything that depends on what the STORE returned falls back.
    for name, value in (
        ("level", fallback_level),
        ("hp_current", fallback_hp_current),
        ("hp_max", fallback_hp_max),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"the login-vitals {name} fallback is an int (player_wire's "
                f"own login constant); got {type(value).__name__}"
            )
    try:
        resolution = store.read_character_vitals(character_id)
        return resolve(
            resolution,
            fallback_level=fallback_level,
            fallback_hp_current=fallback_hp_current,
            fallback_hp_max=fallback_hp_max,
        )
    except Exception as exc:   # noqa: BLE001 -- a login outranks a bad read
        # The MESSAGE, not only the class.  A database missing migration 006
        # ("no such column: hp_current") and a WAL lock timeout ("database is
        # locked") are both `OperationalError`, and a console line that says
        # only the class name cannot tell an operator which one is happening.
        # `console_line` ASCII-filters whatever lands here.
        return _fallback(
            ROW_COULD_NOT_BE_READ, f"{type(exc).__name__}: {exc}",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
