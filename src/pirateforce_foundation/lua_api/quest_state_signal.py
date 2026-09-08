"""REFUSED is the third quest-state answer, told apart from "never set".

WHY THIS FILE EXISTS.  Until now this lane answered a refused quest-state
read or write with the same values a healthy store uses for "nothing has
happened yet": ``None`` from a read, ``0`` from a write
(``quest_state_store.REFUSED_VALUE``, ``quest.STUB_DEFAULT``).  One
integer answering two different questions is fail-closed at some call
sites and FAIL-OPEN at others, and pf-adversary measured the fail-open
half on scripts the game actually ships (round ``7qw2tr``, findings
F1/F4/F6):

    Quest/q_day_business.lua -- charges the player, THEN records the
    report.  With a write-locked store the charge lands and the record
    does not; ``Quest.CanReportDailyQuest()`` reads the missing record as
    "not reported today" and says yes again.  Measured: the player is
    charged FOUR times where a healthy store charges once.

    Quest/q_ship.lua -- the same shape over money AND an item.

    Quest/q_set12.lua -- the mirror image: a refused ``Quest.SetFlag``
    leaves the quest permanently unreportable.

PANYA's order of 2026-09-08 (``NOW.md``, LANE-Q line) states the rule this
module implements: "refusal is a THIRD state; never pay a reward on a
state that cannot be read".

THE SHAPE, AND WHY IT IS AN ``int``.  :class:`Refused` is an ``int``
subclass carrying the same number the refusing call already returned (0
for almost all of them).  Every caller that does not know about this file
therefore keeps EXACTLY today's number and today's behaviour --
this module cannot regress a path it has not been wired into, which is
what makes it safe to land before every call site is audited.  Callers
that do know ask :func:`is_refused` and get the third state, with
:func:`reason_of` naming which door refused and why.

WHAT IT IS NOT.  Not an exception: a refusal is the server's own fact
(write-lock contention, a soft-deleted character, a row shape that drifted
from LANE-DB's contract), not the script's, and raising into the Lua call
stack would make the host log ``LUA_SCRIPT <file> ERR`` and blame the
script -- the exact confusion pf-adversary named D11/D9 in two earlier
rounds.  Not a store: :class:`RefusalLedger` remembers only that a pair is
currently unreadable, never any quest progress.

ASCII only, no intra-package imports: this is a leaf both halves of the
seam (``lua_api.quest``'s in-memory store and ``lua_api.quest_state_
store``'s durable adapter) import without either importing the other.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Tuple

#: Console token for a call answered with the third state.  Distinct from
#: ``quest_state_store.REFUSED_TOKEN`` (which reports the STORE refusing a
#: single door call): this one reports a DECISION -- a payout, a charge or
#: a gate -- declining to run on a state it cannot read.
UNREADABLE_TOKEN = "LUA_QUEST_STATE_UNREADABLE"

#: Ceiling on how many (character, quest) pairs one ledger remembers as
#: unreadable.
#:
#: A cap is required, not decorative: the ledger is written from the same
#: paths a looping script drives, and an unbounded dict keyed by whatever
#: ids arrive is a memory leak with a script for a throttle.  When the cap
#: is reached the ledger stops ACCEPTING NEW pairs and says so through
#: :meth:`RefusalLedger.saturated`; it never evicts an existing pair,
#: because evicting one would silently turn "unreadable" back into
#: "not started" -- the exact confusion this module exists to end.
LEDGER_CAP = 4096


class Refused(int):
    """A number, plus the reason it is not a fact.

    ``Refused("write-locked") == 0`` and ``int(...) == 0`` and ``... + 1
    == 1``: arithmetic, comparisons and the conversion lupa performs when
    a value crosses back into Lua all see the same number they see today.
    ``bool(Refused("x"))`` is ``False`` for a 0, which is why code that
    needs the third state must ask :func:`is_refused` rather than testing
    truthiness.

    ``value`` EXISTS SO THAT ADDING THE THIRD STATE CANNOT CHANGE A
    NUMBER.  Two refusal paths in this codebase already hand back the
    value that IS on record rather than 0 (``InMemoryQuestStateStore``'s
    cap refusals answer with the row that was already stored, because the
    WRITE was refused but the earlier value is still true).  Forcing those
    to 0 in order to mark them refused would trade one wrong answer for
    another, so the mark rides along with whatever number the call already
    returned.
    """

    # No ``__slots__``: CPython refuses a non-empty ``__slots__`` on an
    # ``int`` subclass ("nonempty __slots__ not supported for subtype of
    # 'int'"), which is the language telling us the instance needs its own
    # dict to carry the reason.  Measured by running it, not assumed.

    def __new__(cls, reason: str, value: int = 0) -> "Refused":
        if not isinstance(reason, str) or not reason:
            raise ValueError("a refusal must name its reason")
        if type(value) is bool or not isinstance(value, int):
            raise ValueError("a refusal carries an int, or nothing")
        marked = super().__new__(cls, value)
        object.__setattr__(marked, "reason", reason)
        return marked

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Refused(%r, %d)" % (self.reason, int(self))


def refused(reason: str, value: int = 0) -> Refused:
    """A refusal answer naming ``reason``, carrying ``value``.

    ``reason`` is an ASCII token from a closed set the logs are grepped
    for (``write-locked``, ``no-such-character``, ``unreadable-row``,
    ``no-atomic-door``, ``cap-characters``, ...), never a store's own
    message text, which can carry a character name or a path.
    """
    return Refused(reason, value)


def is_refused(value: Any) -> bool:
    """True iff ``value`` is the third state rather than a stored number.

    ``is_refused(0)`` is ``False``: a real stored 0 (a quest flag of
    ``QUEST_NONE``, a kill counter that was just created) is a fact, and
    treating it as a refusal would refuse every quest at step one.
    """
    return isinstance(value, Refused)


def reason_of(value: Any) -> Optional[str]:
    """The reason on a refusal, or ``None`` for anything else."""
    return value.reason if isinstance(value, Refused) else None


class RefusalLedger:
    """Which (character, quest) pairs currently have UNRECORDED progress.

    THE POINT IS THE STICKINESS.  A refused read is a moment's bad luck; a
    refused WRITE means the server told a script that something happened
    and then failed to remember it, and every later decision about that
    pair is being made on a state that does not include it.  So a refused
    write poisons the pair until a write for that pair succeeds, and the
    gates that pay, charge or advance the quest ask this ledger first.

    That converts ``q_day_business.lua``'s measured failure from "the
    player is charged four times" into "the player is charged once, and
    every later attempt is refused out loud" -- which is the fail-closed
    half of the same fact.

    IT CLEARS.  A successful write for the pair clears it (the server can
    record again), so a transient write-lock does not lock a character out
    of a quest forever; that is the difference between this and a
    blacklist.  Nothing else clears it: not time, not a read, not another
    character's write.

    Thread-safe: two mobs of the same template dying in one tick reach
    this through two threads.
    """

    def __init__(self, cap: int = LEDGER_CAP) -> None:
        if type(cap) is bool or not isinstance(cap, int) or cap < 1:
            raise ValueError("cap must be a positive int")
        self._cap = cap
        self._lock = threading.RLock()
        self._pairs: Dict[Tuple[int, int], str] = {}
        self._saturated = False

    def record(self, character_id: int, quest_id: int, reason: str) -> None:
        """Remember that a write for this pair was refused."""
        key = (character_id, quest_id)
        with self._lock:
            if key in self._pairs:
                # Keep the FIRST reason: it is the one that names why the
                # progress is missing.  Later calls fail for whatever the
                # store is doing now, which is a symptom of the same gap.
                return
            if len(self._pairs) >= self._cap:
                self._saturated = True
                return
            self._pairs[key] = reason

    def clear(self, character_id: int, quest_id: int) -> None:
        """Forget this pair -- a write for it has succeeded."""
        with self._lock:
            self._pairs.pop((character_id, quest_id), None)

    def unreadable(self, character_id: int, quest_id: int) -> Optional[str]:
        """The reason this pair's state cannot be trusted, or ``None``."""
        with self._lock:
            return self._pairs.get((character_id, quest_id))

    def saturated(self) -> bool:
        """True once a pair has been dropped for want of room.

        Read by a caller that wants to say so in the console; the ledger
        does not log by itself, because it has no log to write to and
        borrowing one would make a leaf module hold a callback.
        """
        with self._lock:
            return self._saturated

    def pairs(self) -> Tuple[Tuple[Tuple[int, int], str], ...]:
        """Every remembered pair, sorted -- for tests and operators."""
        with self._lock:
            return tuple(sorted(self._pairs.items()))


def ledger_of(store: Any) -> Optional[RefusalLedger]:
    """The ledger ``store`` keeps, if it keeps one.

    ``getattr``, not an added protocol method: LANE-A's NPC filter, the
    tests' own fakes and any store another lane wires in must keep working
    unchanged, and a store with no ledger simply has no pair to report --
    which is the same answer it gives today.
    """
    ledger = getattr(store, "refusals", None)
    return ledger if isinstance(ledger, RefusalLedger) else None


def unreadable_reason(store: Any, character_id: int,
                      quest_id: int) -> Optional[str]:
    """Why this pair's quest state cannot be read, or ``None``.

    The one function the decision sites call.  ``None`` means "go ahead":
    either the store keeps no ledger, or it keeps one and this pair is
    clean.
    """
    ledger = ledger_of(store)
    if ledger is None:
        return None
    return ledger.unreadable(character_id, quest_id)
