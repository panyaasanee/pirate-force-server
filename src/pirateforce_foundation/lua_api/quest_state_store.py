"""LANE-Q's DURABLE half of the quest-state seam.

``lua_api.quest`` already publishes the seam (``QuestStateStore``) and an
INERT default (``InMemoryQuestStateStore``, process memory, gone on relog).
This module is the other half PANYA's order of 2026-09-08 ~15:20
(``pf_bridge/notes_to_chief/20260908_1520_KA1A-PANYA-ORDER-COO-unblock-
gt186-gt308-and-quest-flag-store-first.md`` section 3) named as LANE-Q's
first job: the adapter that puts quest progress on a durable row, so a
charge that already works (``Player.AddCash(Var2 * -1)``, ``Player.Remove
Item``, ...) cannot be collected twice and an NPC stops looping step 1
forever.

WHOSE CONTRACT.  Not designed here.  LANE-DB wrote it in
``pf_bridge/notes_to_chief/20260905_2212_LANE-DB-TO-LANE-Q-quest-state-
doors-declared-and-opened-this-round.md`` and the same order says "use the
existing contract, do not redesign".  The five names below are copied from
that letter verbatim:

    store.get_quest_flag(character_id, quest_id)            -> row | None
    store.set_quest_flag(character_id, quest_id, value)     -> row
    store.get_quest_counter(character_id, quest_id, name)   -> row | None
    store.set_quest_counter(character_id, quest_id, name, v)-> row
    store.increment_quest_counter(character_id, quest_id, name, delta) -> row

MEASURED, NOT ASSUMED: those five doors are NOT on ``origin/main`` today.

    grep -n "def set_quest_flag" src/pirateforce_foundation/store.py   -> 0 hits
    ls src/pirateforce_foundation/persistence_quest_state.py           -> missing
    ls migrations/ | grep -i quest                                     -> 0 hits

and the migration number that letter reserved (``014_character_quest_
state.sql``) is occupied on main by ``014_character_skills_learned_
source.sql``, i.e. LANE-DB's own round-``qul9wo`` pull request never
landed.  That is a fact about the DB lane's tree, not a licence for this
lane to grow its own table: ``store.py`` is explicitly outside LANE-Q's
write zone (``prompts/LANE-Q.md``).  So this module is written against the
CONTRACT and refuses -- loudly, by name -- when the doors are absent,
instead of guessing a schema or silently persisting nothing.

WHAT "REAL" MEANS HERE, and what it does not.  This adapter is real code
on a real seam: hand it any object carrying those five doors and quest
flags/counters live wherever that object puts them.  It does NOT by itself
make anything survive a relog -- that needs LANE-DB's rows to exist.  The
one thing it makes impossible today is the SILENT version of the failure:
a host that keeps quest state in process memory now has a way to say so
(:func:`quest_state_store_for` returns ``None`` and logs
``LUA_QUEST_STATE_VOLATILE`` naming every missing door) rather than
looking identical to a host that persists.
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Any, Callable, Optional, Tuple

#: The four doors this adapter cannot work without, exactly as LANE-DB's
#: letter spells them.
REQUIRED_DOORS: Tuple[str, ...] = (
    "get_quest_flag",
    "set_quest_flag",
    "get_quest_counter",
    "set_quest_counter",
)

#: Named but not required: the ``QuestStateStore`` protocol in
#: ``lua_api.quest`` has no increment method, so nothing in this lane can
#: call it yet.  Listed so a reader of the log token below can tell "the
#: store is missing a door I need" from "the store is missing a door
#: LANE-DB offered and I have not earned a caller for".
OPTIONAL_DOORS: Tuple[str, ...] = ("increment_quest_counter",)

#: Attribute carrying the number on the row each door returns (LANE-DB's
#: ``QuestFlagRow`` / ``QuestCounterRow``).
_FLAG_FIELD = "flag_value"
_COUNTER_FIELD = "counter_value"

#: Console tokens.  ASCII only (the bridge console is cp874).
#: Emitted once per host when a store cannot back quest state durably.
VOLATILE_TOKEN = "LUA_QUEST_STATE_VOLATILE"
#: Emitted when a single read/write is refused rather than performed.
REFUSED_TOKEN = "LUA_QUEST_STATE_REFUSED"

#: The answer a refused read/write hands back.  Deliberately the same 0
#: ``lua_api.quest.STUB_DEFAULT`` already hands back (not imported: that
#: module is this one's future CALLER, and a leaf with no intra-package
#: import is the shape ``lua_api.vendored`` was extracted into for the same
#: reason).  Read downstream as "this quest has not advanced", which is the
#: fail-closed answer: a quest that cannot record progress must not appear
#: finished.
REFUSED_VALUE = 0

#: Ceiling on distinct refusal keys this adapter will log before it goes
#: quiet.  ``Quest.SetFlag``/``GetQuestFlag`` are the two highest-count
#: names in the whole 160-function API map (416 + 489 call sites); a
#: corpus sweep against a store with no rows would otherwise write one log
#: line per call site per script.
REFUSAL_LOG_CAP = 256


class QuestStateDoorsMissing(RuntimeError):
    """Raised by :class:`StoreBackedQuestStateStore` when the object handed
    in does not carry LANE-DB's contract.

    A CONSTRUCTION-TIME error on purpose: a caller that asks for durable
    quest state and cannot have it must find out before a script runs, not
    on the first ``SetFlag`` halfway through a quest.  Callers that would
    rather degrade than raise use :func:`quest_state_store_for`.
    """


def missing_doors(store: Any) -> Tuple[str, ...]:
    """Which of :data:`REQUIRED_DOORS` ``store`` does not offer.

    Callable check, not ``hasattr``: a store carrying ``get_quest_flag =
    None`` (a half-finished wiring) is missing the door as surely as one
    that never named it.
    """
    return tuple(name for name in REQUIRED_DOORS
                 if not callable(getattr(store, name, None)))


class StoreBackedQuestStateStore:
    """A :class:`lua_api.quest.QuestStateStore` backed by LANE-DB's doors.

    Every method takes already-coerced plain ints/strs -- same contract
    the protocol in ``lua_api.quest`` states, unchanged here.

    FAIL-CLOSED, NOT FAIL-LOUD-INTO-LUA.  A store refusal (unknown or
    soft-deleted character -> ``KeyError``; out-of-range id -> ``Value
    Error``; write-lock contention -> ``store.WriteLockTimeout``, which
    subclasses ``sqlite3.OperationalError``) is OURS, not the script's: it
    is logged with :data:`REFUSED_TOKEN` and answered with "no progress
    recorded", never re-raised into the Lua call stack where the host's own
    sweep would write ``LUA_SCRIPT <file> ERR`` and blame the script for a
    server-side fact (the exact shape pf-adversary named D11 in round
    ``7kxfe9`` and again as D9 in round ``0ldyk7``).  Anything OUTSIDE
    those three families propagates: a ``TypeError`` from a mis-wired
    adapter is a bug in this file and must not be swallowed.
    """

    #: Told apart from :class:`lua_api.quest.InMemoryQuestStateStore` by a
    #: caller that wants to know whether progress survives a relog, without
    #: isinstance-ing across module boundaries.
    durable = True

    def __init__(self, store: Any,
                 log: Optional[Callable[[str], None]] = None) -> None:
        absent = missing_doors(store)
        if absent:
            raise QuestStateDoorsMissing(
                "store is missing quest-state doors: %s" % ", ".join(absent))
        self._store = store
        self._log = log
        self._lock = threading.RLock()
        self._logged: set = set()

    # -- refusal bookkeeping ------------------------------------------

    def _refuse(self, method: str, reason: str, character_id: int,
                quest_id: int) -> None:
        if self._log is None:
            return
        key = (method, reason, character_id, quest_id)
        with self._lock:
            if key in self._logged or len(self._logged) >= REFUSAL_LOG_CAP:
                return
            self._logged.add(key)
        self._log("%s method=%s reason=%s character=%d quest=%d"
                  % (REFUSED_TOKEN, method, reason, character_id, quest_id))

    def _live_character(self, method: str, character_id: int,
                        quest_id: int) -> bool:
        """False for the ids no live character can have.

        ``lua_api.quest.DEFAULT_CONTEXT`` is ``character_id=0`` and every
        real character id in this codebase starts at 1 (``store.py``'s own
        autoincrement primary key).  Sending 0 down to a real store would
        earn a ``KeyError`` per call; refusing it here keeps the default
        context inert, which is what it is for.
        """
        if character_id < 1:
            self._refuse(method, "no-character", character_id, quest_id)
            return False
        return True

    @staticmethod
    def _value_of(row: Any, field: str) -> Optional[int]:
        """The number on a row LANE-DB's door returned, or ``None``.

        ``None`` in (never set) stays ``None`` out.  Anything that is not a
        row carrying ``field`` as an ``int`` is NOT guessed at -- an
        unrecognized shape means the contract this module was written
        against changed, and "do not know = refuse" (NOW ``0845``) applies
        to a store's answer exactly as it applies to a table cell.
        """
        if row is None:
            return None
        value = getattr(row, field, None)
        if type(value) is bool or not isinstance(value, int):
            raise _UnreadableRow(field)
        return value

    # -- QuestStateStore ----------------------------------------------

    def get_quest_flag(self, character_id: int, quest_id: int) -> Optional[int]:
        if not self._live_character("get_quest_flag", character_id, quest_id):
            return None
        try:
            return self._value_of(
                self._store.get_quest_flag(character_id, quest_id), _FLAG_FIELD)
        except _REFUSALS as exc:
            self._refuse("get_quest_flag", _reason_of(exc), character_id, quest_id)
            return None

    def set_quest_flag(self, character_id: int, quest_id: int,
                       flag_value: int) -> int:
        if not self._live_character("set_quest_flag", character_id, quest_id):
            return REFUSED_VALUE
        try:
            written = self._value_of(
                self._store.set_quest_flag(character_id, quest_id, flag_value),
                _FLAG_FIELD)
        except _REFUSALS as exc:
            self._refuse("set_quest_flag", _reason_of(exc), character_id, quest_id)
            return REFUSED_VALUE
        # LANE-DB's contract is "read back after the write, never a bare
        # echo of the argument".  A door that answers None to a WRITE has
        # not honoured it, so this returns the refusal answer rather than
        # pretending the argument landed.
        if written is None:
            self._refuse("set_quest_flag", "no-row-after-write",
                         character_id, quest_id)
            return REFUSED_VALUE
        return written

    def get_quest_counter(self, character_id: int, quest_id: int,
                          counter_name: str) -> Optional[int]:
        if not self._live_character("get_quest_counter", character_id, quest_id):
            return None
        try:
            return self._value_of(
                self._store.get_quest_counter(character_id, quest_id, counter_name),
                _COUNTER_FIELD)
        except _REFUSALS as exc:
            self._refuse("get_quest_counter", _reason_of(exc), character_id, quest_id)
            return None

    def set_quest_counter(self, character_id: int, quest_id: int,
                          counter_name: str, counter_value: int) -> int:
        if not self._live_character("set_quest_counter", character_id, quest_id):
            return REFUSED_VALUE
        try:
            written = self._value_of(
                self._store.set_quest_counter(
                    character_id, quest_id, counter_name, counter_value),
                _COUNTER_FIELD)
        except _REFUSALS as exc:
            self._refuse("set_quest_counter", _reason_of(exc), character_id, quest_id)
            return REFUSED_VALUE
        if written is None:
            self._refuse("set_quest_counter", "no-row-after-write",
                         character_id, quest_id)
            return REFUSED_VALUE
        return written


class _UnreadableRow(TypeError):
    """A door answered with something that is not a row this lane can read.

    A ``TypeError`` subclass so that a reader who catches the family sees
    it, and so that it is never mistaken for one of the store's own
    documented refusals; it is caught explicitly alongside them because a
    contract drift on LANE-DB's side must degrade this lane, not crash a
    script.
    """


#: The three refusal families LANE-DB's letter documents, plus the shape
#: drift above.  ``sqlite3.Error`` rather than ``store.WriteLockTimeout``
#: on purpose: importing ``store`` from inside ``lua_api`` would drag the
#: whole persistence module into every Lua host, and ``WriteLockTimeout``
#: is a subclass of ``sqlite3.OperationalError`` by that module's own
#: definition, so the family catches it by construction.
_REFUSALS = (KeyError, ValueError, sqlite3.Error, _UnreadableRow)


def _reason_of(exc: BaseException) -> str:
    """One ASCII word for the log, never the exception's own text.

    A store message can carry a character name or a path; log fields in
    this codebase are grep targets, so the token stays a closed set.
    """
    if isinstance(exc, _UnreadableRow):
        return "unreadable-row"
    if isinstance(exc, KeyError):
        return "no-such-character"
    if isinstance(exc, ValueError):
        return "out-of-range"
    if isinstance(exc, sqlite3.OperationalError):
        return "write-locked"
    return "store-error"


def quest_state_store_for(
        store: Any,
        log: Optional[Callable[[str], None]] = None,
) -> Optional[StoreBackedQuestStateStore]:
    """A durable quest-state store for ``store``, or ``None`` -- loudly.

    THE POINT OF THIS FUNCTION IS THE LOG LINE.  A caller that gets
    ``None`` back is free to fall back to
    ``lua_api.quest.InMemoryQuestStateStore``; what it may not do is make
    that choice invisibly, because a host holding quest progress in process
    memory and a host writing rows look identical from the outside until a
    player relogs and finds an NPC back at step 1.  Every ``None`` here is
    accompanied by ``LUA_QUEST_STATE_VOLATILE`` naming the doors that were
    absent, so the reason is in the console rather than in a lane's head.

    ``store`` of ``None`` (no persistence wired at all) is reported the
    same way, with ``store=none``: it is the same player-visible outcome.
    """
    if store is None:
        if log is not None:
            log("%s store=none missing=%s"
                % (VOLATILE_TOKEN, ",".join(REQUIRED_DOORS)))
        return None
    absent = missing_doors(store)
    if absent:
        if log is not None:
            log("%s store=%s missing=%s"
                % (VOLATILE_TOKEN, type(store).__name__, ",".join(absent)))
        return None
    return StoreBackedQuestStateStore(store, log)
