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
  every character of a fresh install.  This is the same trap the speed seam
  fell into -- `migrations/009_character_birth_defaults.sql` gives
  `speed_walk` a DEFAULT that is numerically the constant that seam replaced,
  so its two branches are byte-identical on a fresh database too -- and a
  reviewer of THIS repository can read that one without leaving it:
  `login_speed.py` says it in its own words, and
  `tests/test_login_speed.py::TheRealLoginPathTests` had to write a fixture
  that empties the column before either branch could be told apart.
  `COO-DECISION 20260903_0054` in `pf_bridge` -- unopenable from here -- says
  the same thing, and is named anyway: dropping the identifier would cost a
  reader who DOES have that repository the ability to follow the chain, and
  the rule this file states at the top is to NAME an unopenable citation as
  unopenable, not to avoid one.  What this paragraph now does, and what the
  rest of the file should be read as doing, is preferring an in-repo citation
  where one exists and falling back to a named unopenable one where it does
  not.  It is written here so that no round reports this module as a win on
  screen.  The bytes differ only for a row something has
  MOVED -- `store.apply_hp_damage` is the mover that exists -- and that
  difference is the whole point: HP survives a logout.
* It does not claim to be plugged in.  Nothing calls this module at the commit
  that adds it; `grep -rn "persistence_login_vitals" src/` finds the file and
  nothing else.  Until chief lands the two seams the request asks for, every
  login behaves exactly as `main` does.
* It does not claim anything client-observable.  This layer is wire-only.
* WHAT IT DOES ABOUT A DEAD ROW IS NO LONGER AN OPEN EDGE, AND IT WAS NOT
  THIS LANE'S DECISION EITHER: `COO-DECISION 20260903_0250` ruled and the
  ruling is implemented here rather than argued with.  A row whose
  `hp_current` is not positive is healed to its OWN `hp_max`, and the numbers
  that go out are read back from the row afterwards, so wire and database
  agree.  What is still NOT claimed is that any of it is observable: nothing
  calls this module, so no player has been revived by it, and "beaten to 0,
  logged out, back on your feet" reaches a screen only in the round that
  lands the seam.
* It does not decide what happens when a character dies DURING play -- no
  respawn, no death screen, no penalty.  This is a login-time repair of a row
  that would otherwise be unplayable, and that is the whole of what the
  decision authorised.
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
#: (`hp_current` is not positive).  THIS IS WHAT THE PURE RESOLVER REPORTS,
#: AND IT IS NOT THE END OF THE STORY: `resolve()` has no store and cannot
#: write, so it reports the dead row and carries the caller's literals, and
#: `resolve_for_character` -- which does have the store -- turns this reason
#: into the revive below.  A caller that reaches `resolve()` directly is
#: therefore told the truth about the row and sends nothing new on the wire.
ROW_HP_NOT_POSITIVE = "row_hp_current_not_positive"
#: The row said the character was dead, THE LOGIN REVIVED IT, and these three
#: numbers are what the database holds now -- read back after the write, not
#: predicted from it.
#:
#: `COO-DECISION 20260903_0250` (option `khor`, in
#: `pf_bridge/notes_to_chief/20260903_0250_COO-DECISION-lane-db-a-dead-row-
#: logs-in-and-the-server-revives-it.md` -- IN THE OTHER REPOSITORY AND
#: UNOPENABLE FROM HERE, named as this file's header requires) answers the
#: question the paragraph below used to leave open, and answers it against
#: the option this module had taken: sending the literals over a dead row is
#: the ONE login in this server where the wire and the database are knowingly
#: made to disagree, and nobody owns that disagreement.  So the row is healed
#: to its own `hp_max` -- never to a constant -- and the numbers that go out
#: are the ones the row now holds.
#:
#: THE TOKEN IS THE COO'S NAME LOWERCASED, because every value in `REASONS`
#: is lowercase and a single capitalised member would be a second convention;
#: `console_line` shouts the failure token below in the decision's own case.
ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN = "row_hp_not_positive_revived_on_login"
#: The row said the character was dead and THE REVIVE WRITE DID NOT HAPPEN.
#: The literals go out (point 4 of the decision: a login is never failed for
#: this -- `D1` of `20260903_0115` measured that a failed login parks the
#: client on "connecting" forever), and the failure is SHOUTED on the console
#: rather than filed under the reason for a successful revive.
REVIVE_WRITE_FAILED = "revive_write_failed"

#: Every reason this module can return.  A console reader (and the tests) may
#: treat a token outside this set as a bug rather than as news.
REASONS = frozenset({
    FROM_ROW,
    ROW_HAS_NO_VALUE,
    ROW_REFUSED_BY_VITALS_GATE,
    ROW_REFUSED_BY_VALIDATOR,
    ROW_COULD_NOT_BE_READ,
    ROW_HP_NOT_POSITIVE,
    ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
    REVIVE_WRITE_FAILED,
})

#: The reasons whose three numbers are the ROW's and therefore go out on the
#: wire.  `FROM_ROW` is the row read; the revived one is the row read BACK
#: AFTER a write this module made, which is the same claim with one more step
#: behind it -- wire and database agree in both.
#:
#: Kept separate from `came_from_the_row` on purpose: a reader asking "did
#: this login touch the database" and a reader asking "does the wire carry
#: the row" are asking different questions, and one property answering both
#: is how the revive would end up invisible in a log.
WIRE_TAKES_THE_ROWS_NUMBERS = frozenset({
    FROM_ROW,
    ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
})

#: Reasons whose console line is SHOUTED.  A revive that failed leaves a
#: character whose row still says it is dead while the wire says it is alive
#: -- the exact disagreement `COO-DECISION 20260903_0250` exists to end -- so
#: it may not read like the five ordinary refusals above it.
LOUD_REASONS = frozenset({REVIVE_WRITE_FAILED})

#: WHY A DEAD ROW SENDS THE LITERALS, AND WHY THAT IS A QUESTION AND NOT AN
#: ANSWER.
#:
#: `hp_current = 0` is not a guessed zero -- it is a value, and it means the
#: character died.  So this module may not treat it as "no value" and it does
#: not: it gives it its own reason token and its own console line.
#:
#: What to DO about it WAS a game decision this lane does not own, and it has
#: now been made: `COO-DECISION 20260903_0250` rules that the server REVIVES
#: the row and then sends what it wrote (`ROW_HP_NOT_POSITIVE_REVIVED_ON_
#: LOGIN` above).  The three options were weighed on the record and the
#: reasons are worth keeping, because each names a real cost:
#:
#: * send a zero -- refused: nothing in this repository respawns a character,
#:   so a zero on a login block is a character stuck dead forever, and
#:   `GT-193` is standing evidence of what a wrong number there costs (HP 0
#:   arrived, the character died, and the client then ignored 426 frames of
#:   clicks).
#: * send the literals over a dead row -- what this module DID, and refused
#:   for one reason: it is the only login in the server where the wire and
#:   the database are deliberately made to disagree with nobody owning the
#:   disagreement.  That is the silent-debt shape this project has lost
#:   rounds to before.
#: * revive and send what was written -- taken.  It is also the only one of
#:   the three under which M4's name (`beaten down AND able to come back`) is
#:   true at both ends, and it needs no migration and touches no row but the
#:   one logging in, so the owner's standing ban on an irreversible mass
#:   write is not in play.
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
        """The row was read and sent AS FOUND -- nothing was written.

        Deliberately still `FROM_ROW` alone after the revive landed: this is
        the property that answers "did this login leave the database as it
        found it", and widening it to cover the revive would have made the
        one login that writes indistinguishable from the ones that do not.
        """
        return self.reason == FROM_ROW

    @property
    def wire_matches_the_row(self) -> bool:
        """The three numbers going out are the ones the database holds.

        True for `FROM_ROW` (read) and for the revive (read BACK after the
        write).  This -- not `came_from_the_row` -- is what decides whether a
        seam sends the row's numbers or its own literals.
        """
        return self.reason in WIRE_TAKES_THE_ROWS_NUMBERS

    def wire_kwargs(self) -> dict:
        """The keyword arguments a login seam should splat, or `{}`.

        `{}` for every reason whose numbers are the CALLER's literals, which
        is what makes the request's `**extra` shape fail-closed at the CALL
        SITE as well as here: a seam that splats this dict sends its own
        literals whenever this module refused, without the seam having to
        know the reason codes.  The names are the ones the request asked
        chief for.

        A REVIVED LOGIN SENDS THE ROW, and that is `COO-DECISION
        20260903_0250` point 2 arriving at the call site: the write happened,
        so the wire may not go on carrying the literals as if it had not.
        `REVIVE_WRITE_FAILED` returns `{}` for the same reason read the other
        way round -- the write did NOT happen, so the wire may not claim it
        did.
        """
        if not self.wire_matches_the_row:
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
        reason = self.reason
        prefix = _CONSOLE_PREFIX
        if reason in LOUD_REASONS:
            # The decision asked for a line "in capitals" for this one, and
            # the capitalised token is also the spelling the decision itself
            # uses, so an operator grepping the letter finds the console.
            reason = reason.upper()
            prefix = f"!! {_CONSOLE_PREFIX}"
        line = (
            f"{prefix} {reason} level={self.level!r} "
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


def _revive_on_login(
    store, character_id, refusal, *,
    fallback_level: int, fallback_hp_current: int, fallback_hp_max: int,
) -> ResolvedLoginVitals:
    """`COO-DECISION 20260903_0250`: heal the dead row, then send what it says.

    Four things the decision asks for, and where each one is:

    1. **The row is healed to ITS OWN `hp_max`, never to a constant.** That
       arithmetic is not written here: `store.restore_hp_to_full` reads
       `hp_max` out of the row INSIDE the same transaction as the `UPDATE`
       and refuses to write anything when the pair is inconsistent
       (`store.py`, `_apply_hp_transition`).  A subtraction written at this
       call site over a state nobody re-validated is how a negative amount is
       born -- `persistence_vitals.heal_to_full` says so in its own words --
       and this module owning a second copy of it would be the same drift the
       re-gate above exists to stop.
    2. **What goes out is READ BACK, not predicted.**  The obvious shape --
       trust the outcome object the write returned -- would put a number on
       the wire that no read ever confirmed, which is the disagreement
       between wire and row this decision exists to end.  So the row is
       resolved again, through the same gap-carrying door and the same gate,
       and only a clean `FROM_ROW` becomes the revived answer.  A row that
       something re-damaged between the two statements therefore reports the
       failure rather than a stale success.
    3. **Its own reason and its own console line**, above.  A revive is never
       reported as `ROW_HAS_NO_VALUE`; a failure is never reported as a
       revive.
    4. **A failed write never fails the login.**  Every exception, from the
       store or from the read-back, becomes `REVIVE_WRITE_FAILED` carrying
       the caller's three literals -- byte-for-byte what `main` sends today
       -- and the message, not only the class, so an operator can tell a
       locked database from a missing migration.
    """
    try:
        store.restore_hp_to_full(character_id)
    except Exception as exc:   # noqa: BLE001 -- a login outranks a bad write
        return _fallback(
            REVIVE_WRITE_FAILED,
            f"the revive write raised {type(exc).__name__}: {exc}; "
            f"the row still says {refusal.detail}",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    try:
        after = resolve(
            store.read_character_vitals(character_id),
            fallback_level=fallback_level,
            fallback_hp_current=fallback_hp_current,
            fallback_hp_max=fallback_hp_max,
        )
    except Exception as exc:   # noqa: BLE001 -- a login outranks a bad read
        return _fallback(
            REVIVE_WRITE_FAILED,
            f"the revive write reported success and the row could not be "
            f"read back ({type(exc).__name__}: {exc})",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    if after.reason != FROM_ROW:
        return _fallback(
            REVIVE_WRITE_FAILED,
            f"the revive write reported success and the row still reads "
            f"{after.reason}: {after.detail}",
            fallback_level, fallback_hp_current, fallback_hp_max,
        )
    from . import persistence_vitals as vitals

    return ResolvedLoginVitals(
        after.level, after.hp_current, after.hp_max,
        ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
        f"the row said {refusal.detail}; the login healed it to its own "
        f"{vitals.HP_MAX_COLUMN} and these three numbers are what the row "
        f"holds now",
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
        resolved = resolve(
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
    if resolved.reason != ROW_HP_NOT_POSITIVE:
        return resolved
    # THE ONLY WRITE THIS MODULE MAKES, AND IT IS OUTSIDE THE READ'S `try` ON
    # PURPOSE: a failure of the revive is a different event from a failure of
    # the read, it carries its own reason and its own shouted line, and
    # folding it into `ROW_COULD_NOT_BE_READ` above would report a database
    # that refused a WRITE as a database that could not be READ.
    return _revive_on_login(
        store, character_id, resolved,
        fallback_level=fallback_level,
        fallback_hp_current=fallback_hp_current,
        fallback_hp_max=fallback_hp_max,
    )
