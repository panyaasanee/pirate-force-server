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

MEASURED, NOT ASSUMED -- AND THE ANSWER CHANGED ON 2026-09-08.  For every
round until now those five doors were absent from ``origin/main`` and this
paragraph said so.  Re-measured at the merge this module's round `7cf5ak`
took (``origin/main`` at ``2e4e3f6``), they are THERE:

    grep -n "def set_quest_flag" src/pirateforce_foundation/store.py -> 3399
    src/pirateforce_foundation/persistence_quest_state.py            -> present
    migrations/019_character_quest_state.sql                         -> present

All five, under LANE-DB's own names and argument order.  What that does
NOT mean: nothing in this codebase yet HANDS one of those stores to
``load_quest_script(persistence=...)``, so quest progress still does not
survive a relog in a running server -- see ``lua_api.dispatch.resolve_
quest_state_store``, which is the one switch that would make it, and the
round file for what is still missing at the call site.  ``store.py``
stays outside LANE-Q's write zone (``prompts/LANE-Q.md``) either way:
this module is written against the CONTRACT and refuses -- loudly, by
name -- when a door is absent, instead of guessing a schema or silently
persisting nothing.

WHAT "REAL" MEANS HERE, and what it does not.  This adapter is real code
on a real seam: hand it any object carrying :data:`REQUIRED_DOORS` and
quest flags/counters live wherever that object puts them (the fifth door
is optional -- :data:`OPTIONAL_DOORS` says why).  It does NOT by itself
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

from . import quest_state_signal

#: The four doors this adapter cannot work without, exactly as LANE-DB's
#: letter spells them.
REQUIRED_DOORS: Tuple[str, ...] = (
    "get_quest_flag",
    "set_quest_flag",
    "get_quest_counter",
    "set_quest_counter",
)

#: Doors LANE-DB's letter offers that this lane names on the seam but does
#: not yet CALL from any production path.
#:
#: PROMOTED TO REQUIRED AND PUT BACK, IN ONE ROUND (`7qw2tr`), because the
#: adversary priced the promotion and it was a bad trade.  The reasoning
#: for promoting was "the seam publishes ``increment_quest_counter`` now,
#: so a store without it cannot back the seam".  The cost: if LANE-DB
#: lands the four flag/counter doors and names the atomic one differently,
#: or ships it a round later, ``missing_doors`` comes back non-empty and
#: :func:`quest_state_store_for` throws away a WORKING durable store --
#: every quest in the game drops back to process memory over a door that
#: nothing calls.  Trading durable flags for volatile ones to protect a
#: path with no callers is worse than the thing it protects against.
#:
#: So the refusal moved to where it can be exact: a store missing this
#: door still backs flags and counters durably, and the ONE method that
#: needs it refuses BY NAME when it is called (see
#: :meth:`StoreBackedQuestStateStore.increment_quest_counter`).  It gets
#: promoted the round it gets a caller, not before.
OPTIONAL_DOORS: Tuple[str, ...] = ("increment_quest_counter",)

#: Attribute carrying the number on the row each door returns (LANE-DB's
#: ``QuestFlagRow`` / ``QuestCounterRow``).
#:
#: BOTH [MEASURED] AS OF ROUND `7cf5ak`, and one of them stopped being a
#: guess in this round rather than by being argued about.  pf-adversary F10
#: (round `7qw2tr`) was right that ``counter_value`` was only ever a
#: PARAMETER name in LANE-DB's letter, never a field of ``QuestCounterRow``,
#: so it carried a ``[PROPOSED]`` label and the lane's own fake pinned the
#: same guess against itself.  LANE-DB's real code landed on ``origin/main``
#: the same day and settles it by reading, not by reply:
#:
#:     src/pirateforce_foundation/persistence_quest_state.py:37
#:         QuestFlagRow(character_id, quest_id, flag_value, updated_at)
#:     src/pirateforce_foundation/persistence_quest_state.py:55
#:         QuestCounterRow(character_id, quest_id, counter_name,
#:                         counter_value, updated_at)
#:
#: The label is lifted because the field EXISTS on the shipped dataclass,
#: not because anyone agreed it would.  What is still not claimed: that
#: this adapter has ever run against that real store -- it has not; the
#: fake in ``tests/test_script_lua_quest_state_store.py`` is still a fake,
#: and it now matches a row shape that can be checked instead of one that
#: could only be believed.
_FLAG_FIELD = "flag_value"
_COUNTER_FIELD = "counter_value"

#: The range every WRITE this lane performs coerces a flag value into
#: (``lua_api.quest._coerce_int(..., _MAX_FLAG_VALUE)``, ``0..0xFFFF``,
#: mirrored here rather than imported -- this module is the future
#: import target for ``lua_api.quest``, see the module docstring on
#: :data:`REFUSED_VALUE` for why the dependency runs one way).
#: ``store.py`` deliberately does NOT enforce this range: ``flag_value``
#: is opaque to it by COO decision (``20260901_1059``/``20260908_1642``,
#: "this database stores the integer and never interprets it"), and its
#: own test proves it (``tests/test_persistence_quest_state.py``'s
#: ``test_negative_flag_values_are_stored_as_given``).  So a row written
#: by anything OTHER than this lane's two coerced closures -- an admin
#: tool, a migration, a future lane reaching ``store.py`` directly -- can
#: durably hold a value outside it, INCLUDING ``lua_api.quest.
#: QUEST_FLAG_UNREADABLE`` (``-1``) itself: the exact collision D6 closed
#: for "refused" vs. "never set", reopened one layer down for "refused"
#: vs. "some other writer's out-of-range value" (pf-adversary, re-review
#: of merged PR #1184, F1: "the sentinel's soundness assumes an
#: unenforced convention across a boundary between two lanes" -- not
#: exploitable through the current corpus, since only the two coerced
#: closures write flags today, but enforced at zero layers, not one).
#: Refusing here, not clamping or reinterpreting: a value outside the
#: range this lane ever legitimately writes is a row this lane cannot
#: trust, not a number to narrow.  Counters are deliberately NOT bounded
#: this way -- no artifact in this codebase claims a ceiling on a kill
#: count or any other counter, only on flags.
_MIN_FLAG_VALUE = 0
_MAX_FLAG_VALUE = 0xFFFF


def _flag_in_range(value: Optional[int]) -> bool:
    """``True`` unless ``value`` is a flag number this lane never writes.

    ``None`` (never set) is in range: it is not a stored number at all,
    just the absence of one, and the caller that asked for a flag reads
    that as "never set" downstream of this function, same as before.
    """
    return value is None or _MIN_FLAG_VALUE <= value <= _MAX_FLAG_VALUE

#: Console tokens.  ASCII only (the bridge console is cp874).
#: Emitted once per host when a store cannot back quest state durably.
VOLATILE_TOKEN = "LUA_QUEST_STATE_VOLATILE"
#: Emitted when a single read/write is refused rather than performed.
REFUSED_TOKEN = "LUA_QUEST_STATE_REFUSED"
#: Emitted ONCE per ledger (pf-adversary round `z113cx` addendum, D2) the
#: first time a poisoned-row write is dropped because the process-wide
#: ledger (:data:`quest_state_signal.LEDGER_CAP` rows) is full.  Before
#: this token existed, :meth:`quest_state_signal.RefusalLedger.saturated`
#: had no production reader anywhere in ``src/``: a drop here means a row
#: this server SHOULD have refused instead reads clean, silently, for as
#: long as the process runs.
LEDGER_SATURATED_TOKEN = "LUA_QUEST_LEDGER_SATURATED"

#: The answer a refused read/write hands back.  Deliberately the same 0
#: ``lua_api.quest.STUB_DEFAULT`` already hands back (not imported: that
#: module is this one's future CALLER, and a leaf with no intra-package
#: import is the shape ``lua_api.vendored`` was extracted into for the same
#: reason).  Read downstream as "this quest has not advanced", which is the
#: fail-closed answer: a quest that cannot record progress must not appear
#: finished.
#:
#: STILL 0, AND NOW ALSO SAYS SO.  Every refusal below hands back
#: ``quest_state_signal.refused(<reason>)``, which IS this 0 numerically
#: (an ``int`` subclass) -- so a caller that has never heard of the third
#: state keeps exactly the number and the behaviour it has today -- while
#: a caller that asks ``quest_state_signal.is_refused()`` can tell "the
#: server could not record this" apart from "this quest has not advanced".
#: The two were the same value until round `7cf5ak`, which is how a
#: refused write to ``q_day_business.lua``'s daily stamp came back out of
#: ``Quest.CanReportDailyQuest()`` as "you may report again" and charged
#: the player four times (pf-adversary F1/F4/F6, round `7qw2tr`).
REFUSED_VALUE = 0

#: Ceiling on distinct refusal keys this adapter will log before it goes
#: quiet.
#:
#: THE NUMBERS HERE WERE WRONG UNTIL ROUND `7qw2tr` and are re-derived
#: rather than repeated.  This comment used to call ``Quest.SetFlag``/
#: ``GetQuestFlag`` "the two highest-count names in the whole 160-function
#: API map (416 + 489 call sites)".  Counted at HEAD from
#: ``pf_bridge/gamedata/PF_GAMEDATA_LUA_API.tsv``:
#:
#:     3532  Player.MobAppear
#:     1430  Player.AddItem
#:     1335  Quest.RewardItemSelect
#:      716  Mob.ShowAnimation
#:      508  Quest.GetQuestFlag     <- rank 5
#:      417  Quest.SetFlag          <- rank 6
#:
#: Both figures were off and the superlative was false.  The cap still
#: earns its place on the true numbers -- 925 call sites across the two,
#: and a corpus sweep against a store with no rows would otherwise write
#: one log line per refused key per script -- but it earns it on measured
#: ones.
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
        #: Public on purpose: ``quest_state_signal.ledger_of`` finds it by
        #: name on whatever store a namespace was handed, so the decision
        #: sites in ``lua_api.quest`` need no isinstance and no import of
        #: this module.
        #: ONE LEDGER PER BACKING STORE, NOT PER ADAPTER.
        #: ``dispatch.load_quest_script()`` builds a fresh adapter for
        #: every script run, so an adapter-owned ledger forgot a refused
        #: write between the click that charged the player and the click
        #: that charged them again (pf-adversary, round ``7cf5ak``, A1).
        #: ``ledger_for`` keys it to the store object instead, and it is
        #: public under this name so ``quest_state_signal.ledger_of``
        #: finds it on whatever store a namespace was handed.
        self.refusals = quest_state_signal.ledger_for(store)

    # -- refusal bookkeeping ------------------------------------------

    def _refuse(self, method: str, reason: str, character_id: int,
                quest_id: int,
                wrote: bool = False,
                kind: str = quest_state_signal.COUNTER_ROW,
                name: str = "") -> quest_state_signal.Refused:
        """Log the refusal once, remember it if it lost a WRITE, answer 0.

        ``wrote`` is the whole difference between the two halves of the
        third state.  A refused READ is a moment's bad luck and the next
        call may well succeed, so it is reported and nothing is
        remembered.  A refused WRITE means a script was told something
        happened and this server failed to record it: every later decision
        about that ROW is now being made on a state that is missing a
        fact, so ``(character, quest, kind, name)`` is poisoned in
        :attr:`refusals` until a write to THAT row succeeds, and the gates
        that read it refuse to decide on it
        (``quest_state_signal.unreadable_reason``).  Keying the poison to
        the row rather than the pair is what stops an unrelated successful
        write four lines later from clearing it (pf-adversary, round
        ``7cf5ak``, A2).

        The log is capped and de-duplicated; the LEDGER is neither, and
        must not be -- a cap on remembering a row is a cap on refusing to
        overcharge it.  (:data:`quest_state_signal.LEDGER_CAP` bounds the
        memory instead, by refusing NEW rows rather than forgetting old
        ones.)
        """
        if wrote:
            dropped = self.refusals.record(
                character_id, quest_id, reason, kind, name)
            if dropped and self._log is not None:
                # D2's simplest fix, not the fuller per-character admission
                # control the addendum also offered -- this makes the drop
                # OBSERVABLE, it does not make it fair between characters
                # (still open; see the round file's letter to COO).
                if self.refusals.mark_saturation_announced():
                    self._log(
                        "%s cap=%d character=%d quest=%d row=%s:%s"
                        % (LEDGER_SATURATED_TOKEN, quest_state_signal.LEDGER_CAP,
                           character_id, quest_id, kind, name))
        answer = quest_state_signal.refused(reason)
        if self._log is None:
            return answer
        key = (method, reason, character_id, quest_id, kind, name)
        with self._lock:
            if key in self._logged or len(self._logged) >= REFUSAL_LOG_CAP:
                return answer
            self._logged.add(key)
        self._log("%s method=%s reason=%s character=%d quest=%d row=%s:%s"
                  % (REFUSED_TOKEN, method, reason, character_id, quest_id,
                     kind, name))
        return answer

    def _live_character(self, method: str, character_id: int,
                        quest_id: int,
                        wrote: bool = False
                        ) -> Optional[quest_state_signal.Refused]:
        """The refusal for ids no live character can have, else ``None``.

        ``lua_api.quest.DEFAULT_CONTEXT`` is ``character_id=0`` and every
        real character id in this codebase starts at 1 (``store.py``'s own
        autoincrement primary key).  Sending 0 down to a real store would
        earn a ``KeyError`` per call; refusing it here keeps the default
        context inert, which is what it is for.
        """
        # NEVER POISONED, whatever ``wrote`` says (pf-adversary, round
        # ``7cf5ak``, A6).  ``character_id < 1`` is not a character whose
        # progress went missing; it is the default context, which no write
        # can ever clear because no write for character 0 will ever be
        # made.  Recording it left a healthy store permanently poisoned and
        # made ``LUA_QUEST_STATE_UNREADABLE`` on the console mean nothing.
        # ``wrote`` is still taken and still ignored here on purpose: the
        # callers are honest about which calls were writes, and this method
        # is the one place that knows the id is not a character.
        if character_id < 1:
            return self._refuse(method, "no-character", character_id,
                                quest_id, wrote=False)
        return None

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
        denied = self._live_character("get_quest_flag", character_id, quest_id)
        if denied is not None:
            return denied
        try:
            value = self._value_of(
                self._store.get_quest_flag(character_id, quest_id), _FLAG_FIELD)
            if not _flag_in_range(value):
                # F1: a row some OTHER writer put outside 0..0xFFFF (store.py
                # enforces no range of its own) -- refuse it exactly like an
                # unreadable shape, rather than handing back a number this
                # lane never wrote and that may equal QUEST_FLAG_UNREADABLE.
                raise _UnreadableRow(_FLAG_FIELD)
            return value
        except _REFUSALS as exc:
            return self._refuse("get_quest_flag", _reason_of(exc),
                                character_id, quest_id)

    def set_quest_flag(self, character_id: int, quest_id: int,
                       flag_value: int) -> int:
        denied = self._live_character("set_quest_flag", character_id,
                                      quest_id, wrote=True)
        if denied is not None:
            return denied
        try:
            written = self._value_of(
                self._store.set_quest_flag(character_id, quest_id, flag_value),
                _FLAG_FIELD)
            if not _flag_in_range(written):
                # F1: the read-back disagrees with the range this lane's own
                # writer just coerced its argument into -- a concurrent
                # writer this lane does not control landed a row in between.
                # Trusting it would let `written` equal QUEST_FLAG_UNREADABLE.
                raise _UnreadableRow(_FLAG_FIELD)
        except _REFUSALS as exc:
            return self._refuse("set_quest_flag", _reason_of(exc),
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.FLAG_ROW)
        # LANE-DB's contract is "read back after the write, never a bare
        # echo of the argument".  A door that answers None to a WRITE has
        # not honoured it, so this returns the refusal answer rather than
        # pretending the argument landed.
        if written is None:
            return self._refuse("set_quest_flag", "no-row-after-write",
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.FLAG_ROW)
        self.refusals.clear(character_id, quest_id,
                            quest_state_signal.FLAG_ROW)
        return written

    def get_quest_counter(self, character_id: int, quest_id: int,
                          counter_name: str) -> Optional[int]:
        denied = self._live_character("get_quest_counter", character_id, quest_id)
        if denied is not None:
            return denied
        try:
            return self._value_of(
                self._store.get_quest_counter(character_id, quest_id, counter_name),
                _COUNTER_FIELD)
        except _REFUSALS as exc:
            return self._refuse("get_quest_counter", _reason_of(exc),
                                character_id, quest_id)

    def set_quest_counter(self, character_id: int, quest_id: int,
                          counter_name: str, counter_value: int) -> int:
        denied = self._live_character("set_quest_counter", character_id,
                                      quest_id, wrote=True)
        if denied is not None:
            return denied
        try:
            written = self._value_of(
                self._store.set_quest_counter(
                    character_id, quest_id, counter_name, counter_value),
                _COUNTER_FIELD)
        except _REFUSALS as exc:
            return self._refuse("set_quest_counter", _reason_of(exc),
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.COUNTER_ROW,
                                name=counter_name)
        if written is None:
            return self._refuse("set_quest_counter", "no-row-after-write",
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.COUNTER_ROW,
                                name=counter_name)
        self.refusals.clear(character_id, quest_id,
                            quest_state_signal.COUNTER_ROW, counter_name)
        return written

    def increment_quest_counter(self, character_id: int, quest_id: int,
                                counter_name: str, delta: int = 1) -> int:
        """LANE-DB's atomic door, handed straight through.

        THE WHOLE POINT IS THAT THIS METHOD DOES NOT READ FIRST.  There is
        no ``get_quest_counter`` call here and there must never be one: the
        contract says the door does read-modify-write-back inside ONE
        transaction, and any read this adapter added around it would put
        the lost-update window back on the outside of the transaction that
        exists to close it.  Two mob deaths in the same tick each add one.

        The refusal posture is ``set_quest_counter``'s, unchanged -- a
        store refusal is logged and answered "no progress recorded", and a
        write that answers with no row is a contract breach rather than a
        reason to report the delta as if it landed.  Reporting an
        unwritten increment is worse here than in any other method on this
        seam: a caller that believes a kill was credited will not credit
        it again.
        """
        denied = self._live_character("increment_quest_counter", character_id,
                                      quest_id, wrote=True)
        if denied is not None:
            return denied
        door = getattr(self._store, "increment_quest_counter", None)
        if not callable(door):
            # NOT a fallback to get-then-set.  A caller reaching this
            # method wants an addition no concurrent addition can lose;
            # answering it with the racy shape would be the lost update
            # wearing the atomic method's name.  Refuse, by the door's
            # own name, and let the caller see it in the console.
            return self._refuse("increment_quest_counter", "no-atomic-door",
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.COUNTER_ROW,
                                name=counter_name)
        try:
            written = self._value_of(
                door(character_id, quest_id, counter_name, delta),
                _COUNTER_FIELD)
        except _REFUSALS as exc:
            return self._refuse("increment_quest_counter", _reason_of(exc),
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.COUNTER_ROW,
                                name=counter_name)
        if written is None:
            return self._refuse("increment_quest_counter", "no-row-after-write",
                                character_id, quest_id, wrote=True,
                                kind=quest_state_signal.COUNTER_ROW,
                                name=counter_name)
        self.refusals.clear(character_id, quest_id,
                            quest_state_signal.COUNTER_ROW, counter_name)
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
#: drift above.  ``sqlite3.Error`` rather than ``store.WriteLockTimeout``,
#: and the reason given here used to be false: "importing ``store`` from
#: inside ``lua_api`` would drag the whole persistence module into every
#: Lua host".  Measured (pf-adversary, round `7qw2tr`): ``lua_api/
#: reward.py:65`` already does ``from ..store import ...`` and
#: ``lua_api/quest.py`` imports ``reward``, so importing ``script_host``
#: already puts ``pirateforce_foundation.store`` in ``sys.modules``.  The
#: drag happened two imports away, before this file existed.
#:
#: The TRUE reason to keep the family here: ``WriteLockTimeout`` is a
#: subclass of ``sqlite3.OperationalError`` by ``store.py``'s own
#: definition, so the family catches it by construction AND catches the
#: same class of failure from any other DB-API store LANE-DB might put
#: behind these doors, which a named import of one class would not.
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
