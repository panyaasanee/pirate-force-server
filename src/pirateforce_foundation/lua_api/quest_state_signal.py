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
rounds.  Not a store: :class:`RefusalLedger` remembers only that a row is
currently unreadable, never any quest progress.

ASCII only, no intra-package imports: this is a leaf both halves of the
seam (``lua_api.quest``'s in-memory store and ``lua_api.quest_state_
store``'s durable adapter) import without either importing the other.
"""

from __future__ import annotations

import threading
import weakref
from typing import Any, Dict, Optional, Tuple

#: Console token for a call answered with the third state.  Distinct from
#: ``quest_state_store.REFUSED_TOKEN`` (which reports the STORE refusing a
#: single door call): this one reports a DECISION -- a payout, a charge or
#: a gate -- declining to run on a state it cannot read.
UNREADABLE_TOKEN = "LUA_QUEST_STATE_UNREADABLE"

#: Ceiling on how many quest-state ROWS one ledger remembers as
#: unreadable.
#:
#: A cap is required, not decorative: the ledger is written from the same
#: paths a looping script drives, and an unbounded dict keyed by whatever
#: ids arrive is a memory leak with a script for a throttle.  When the cap
#: is reached the ledger stops ACCEPTING NEW rows and says so through
#: :meth:`RefusalLedger.saturated`; it never evicts an existing row,
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


#: The two shapes of quest-state row this lane can lose a write to.
#: ``FLAG_ROW`` has one row per (character, quest) so its name is always
#: ``""``; ``COUNTER_ROW`` has one row per counter name.
FLAG_ROW = "flag"
COUNTER_ROW = "counter"


class RefusalLedger:
    """Which quest-state ROWS currently have an unrecorded write.

    THE UNIT IS THE ROW, NOT THE (character, quest) PAIR, and that is this
    class's whole correction over its first version.  pf-adversary (round
    ``7cf5ak``, A2) measured what pair-keying costs on a script the game
    ships:

        Quest/q_day_business.lua:59  Quest.ReportDailyQuest()   <- refused
        Quest/q_day_business.lua:63  Quest.SetFlag(Quest.None)  <- succeeds

    Four lines apart, in one script run.  Keyed to the pair, the SetFlag
    that succeeded cleared the poison left by the ReportDailyQuest that
    did not -- so the protection was gone before any gate could read it,
    with the daily stamp still missing from disk.  A write clears the row
    it actually wrote and nothing else.

    THE POINT IS STILL THE STICKINESS.  A refused read is a moment's bad
    luck; a refused WRITE means the server told a script that something
    happened and then failed to remember it, and every later decision that
    reads that row is being made on a state that does not include it.  So
    a refused write poisons that row until a write to THAT row succeeds,
    and the gates that decide "has this already been reported" ask here
    first.

    IT CLEARS, and only that way: not by time, not by a read, not by
    another row's write, not by another character's write.

    Thread-safe: two mobs of the same template dying in one tick reach
    this through two threads.
    """

    def __init__(self, cap: int = LEDGER_CAP) -> None:
        if type(cap) is bool or not isinstance(cap, int) or cap < 1:
            raise ValueError("cap must be a positive int")
        self._cap = cap
        self._lock = threading.RLock()
        self._rows: Dict[Tuple[int, int, str, str], str] = {}
        self._saturated = False

    @staticmethod
    def _key(character_id: int, quest_id: int, kind: str,
             name: str) -> Tuple[int, int, str, str]:
        if kind not in (FLAG_ROW, COUNTER_ROW):
            raise ValueError("kind must be %r or %r" % (FLAG_ROW, COUNTER_ROW))
        if not isinstance(name, str):
            raise TypeError("a row name is a str")
        # A flag row has no name of its own; normalising here means a
        # caller cannot poison `("flag", "")` and clear `("flag", "x")`.
        return (character_id, quest_id, kind,
                "" if kind == FLAG_ROW else name)

    def record(self, character_id: int, quest_id: int, reason: str,
               kind: str = COUNTER_ROW, name: str = "") -> None:
        """Remember that a write to this ROW was refused."""
        key = self._key(character_id, quest_id, kind, name)
        with self._lock:
            if key in self._rows:
                # Keep the FIRST reason: it is the one that names why the
                # progress is missing.  Later calls fail for whatever the
                # store is doing now, which is a symptom of the same gap.
                return
            if len(self._rows) >= self._cap:
                self._saturated = True
                return
            self._rows[key] = reason

    def clear(self, character_id: int, quest_id: int,
              kind: str = COUNTER_ROW, name: str = "") -> None:
        """Forget this ROW -- a write to it has succeeded."""
        key = self._key(character_id, quest_id, kind, name)
        with self._lock:
            self._rows.pop(key, None)

    def unreadable(self, character_id: int, quest_id: int,
                   kind: Optional[str] = None,
                   name: str = "") -> Optional[str]:
        """The reason a row of this quest cannot be trusted, or ``None``.

        With ``kind`` given, the answer is about THAT row and no other --
        which is what a gate reading one row (the daily stamp, one kill
        counter) must ask.  With ``kind`` left out, the answer is "is any
        row of this (character, quest) missing a write", which is what a
        decision about the QUEST as a whole (paying it out, accepting it)
        must ask; the reason returned is then the first in sorted key
        order, so the answer does not depend on dict insertion order.
        """
        with self._lock:
            if kind is not None:
                return self._rows.get(
                    self._key(character_id, quest_id, kind, name))
            for key in sorted(self._rows):
                if key[0] == character_id and key[1] == quest_id:
                    return self._rows[key]
            return None

    def saturated(self) -> bool:
        """True once a row has been dropped for want of room."""
        with self._lock:
            return self._saturated

    def rows(self) -> Tuple[Tuple[Tuple[int, int, str, str], str], ...]:
        """Every remembered row, sorted -- for tests and operators."""
        with self._lock:
            return tuple(sorted(self._rows.items()))

    def pairs(self) -> Tuple[Tuple[Tuple[int, int], str], ...]:
        """The distinct (character, quest) pairs that have a poisoned row.

        Kept because operators and the console think in quests, not rows;
        the reason shown for a pair is the first of its rows in sorted key
        order.  Not the ledger's unit -- see :meth:`rows`.
        """
        seen: Dict[Tuple[int, int], str] = {}
        with self._lock:
            for key in sorted(self._rows):
                seen.setdefault((key[0], key[1]), self._rows[key])
        return tuple(sorted(seen.items()))


#: One ledger per BACKING STORE OBJECT, found by identity.
#:
#: WHY THIS IS NOT AN ATTRIBUTE ON THE STORE.  The backing store is
#: LANE-DB's object (``store.SQLiteStore``); ``store.py`` is not this
#: lane's to write, and a lane that reaches over and sets a field on
#: another lane's instance is one rename away from a silent collision.  A
#: weak-keyed side table owned by this leaf module keeps the association
#: entirely inside LANE-Q's zone and lets the ledger die with the store it
#: describes.
_LEDGERS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
_LEDGERS_LOCK = threading.RLock()


def ledger_for(backing: Any) -> RefusalLedger:
    """The one ledger for ``backing``, created on first ask.

    THIS IS THE ANSWER TO "WHERE IS A LOST FACT REMEMBERED".
    pf-adversary (round ``7cf5ak``, A1) measured that
    ``dispatch.load_quest_script()`` builds a NEW adapter per dispatch, so
    a ledger owned by the adapter was forgotten between the click that
    charged the player and the click that would charge them again -- a
    memory shorter than the fact it stands for is not a gate.  Keyed to
    the backing store, every adapter built over one store shares one
    ledger, and the memory lasts as long as the store does.

    IT DOES NOT OUTLIVE THE PROCESS, and this lane does not pretend
    otherwise: the only place durable enough for that is the row itself,
    which is precisely the thing that could not be written.  After a
    restart the gates re-derive from what the store can be read to say.

    An object that cannot be weak-referenced (a store with ``__slots__``
    and no ``__weakref__``) gets a fresh ledger each time, which is the
    old per-dispatch behaviour rather than a crash; callers that care can
    detect it with :func:`ledger_is_shared`.
    """
    try:
        with _LEDGERS_LOCK:
            ledger = _LEDGERS.get(backing)
            if ledger is None:
                ledger = RefusalLedger()
                _LEDGERS[backing] = ledger
            return ledger
    except TypeError:
        return RefusalLedger()


def ledger_is_shared(backing: Any) -> bool:
    """True iff ``backing`` can carry a ledger that outlives a dispatch."""
    try:
        with _LEDGERS_LOCK:
            return backing in _LEDGERS
    except TypeError:
        return False


def ledger_of(store: Any) -> Optional[RefusalLedger]:
    """The ledger ``store`` keeps, if it keeps one.

    ``getattr``, not an added protocol method: LANE-A's NPC filter, the
    tests' own fakes and any store another lane wires in must keep working
    unchanged, and a store with no ledger simply has no pair to report --
    which is the same answer it gives today.
    """
    ledger = getattr(store, "refusals", None)
    return ledger if isinstance(ledger, RefusalLedger) else None


def unreadable_reason(store: Any, character_id: int, quest_id: int,
                      kind: Optional[str] = None,
                      name: str = "") -> Optional[str]:
    """Why this quest's state cannot be read, or ``None``.

    The one function the decision sites call.  ``None`` means "go ahead":
    either the store keeps no ledger, or it keeps one and the row asked
    about is clean.  Pass ``kind``/``name`` when the decision reads ONE
    row and leave them out when it is about the quest as a whole -- see
    :meth:`RefusalLedger.unreadable`.
    """
    ledger = ledger_of(store)
    if ledger is None:
        return None
    return ledger.unreadable(character_id, quest_id, kind, name)
