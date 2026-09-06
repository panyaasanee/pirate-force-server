"""LANE-Q's ``Quest`` namespace: the one name that needs no other lane.

WHY THIS FILE, WHY THIS ONE NAME.  ``docs/SCRIPT_LANE.md`` (round 4jsydv)
found the charter's own queue for ``Quest.*`` (25 names) fully blocked: every
name that reads or writes per-character quest progress (``GetQuestFlag``,
``SetFlag``, ``MobKillCount``, ``CountDownTime``, ...) needs the LANE-DB
column asked for in ``COO-DECISION 20260905_2058`` -- not landed yet on
``main`` at this round's own start, re-confirmed fresh (``grep -rln
"persistence_quest_state\\|character_quest_state" src/`` -- zero hits;
``migrations/`` still ends at ``014_character_skills_learned_source.sql``,
no ``015``). Grepping the corpus (``gamedata/lua/Quest/*.lua``) for a name
that needs NEITHER that column NOR a wire frame NOR another lane's registry
turned up exactly one: ``CheckOpenTime(start, end)`` -- a pure question
about the SERVER CLOCK, called at 9 sites across 3 files
(``Quest/q_con5.lua``, ``Quest/q_sea_join.lua``, ``Quest/q_arena2.lua``),
with no per-character state and no outbound frame anywhere in its call
shape.

WHAT THE 9 CALL SITES ESTABLISH, GREPPED NOT GUESSED.  ``q_sea_join.lua``'s
``Accept_Run`` chains seven literal windows with ``or``: ``(1930,1955)``,
``(2030,2055)``, ``(2130,2155)``, ``(2230,2255)``, ``(2330,2355)``,
``(0030,0055)``, ``(0130,0155)`` -- seven consecutive hourly 25-minute
windows that cross midnight partway through the list.  Lua has no octal
literal (unlike C), so ``0030``/``0130`` are the plain decimal integers 30
and 130 at runtime -- which is EXACTLY what an ``hour*100+minute`` reading
of them means for hour 0 and hour 1 (``0*100+30=30``, ``1*100+30=130``):
the encoding survives the leading-zero truncation by construction, not by
coincidence a reader has to squint at.  ``q_con5.lua``/``q_arena2.lua``
call it as ``CheckOpenTime(Quest.Var3, Quest.Var4) == false`` / ``== true``
against per-quest table values (``QUESTDATA_TH__QUEST.tsv``'s own
``n_VARI_3``/``n_VARI_4`` columns) -- these read STUB_DEFAULT (0) until
Quest.Var* per-instance data is wired (a different, still-blocked gap; see
``script_host.py``'s own ``CorpusEntryPointReport`` docstring), but the
FUNCTION itself needs no such data to be real: it only ever compares two
caller-supplied literals against the clock.

NONCLAIM, MEASURED: only 2 of these 9 call sites actually execute against
today's corpus under :func:`script_host.run_corpus_entry_points`
(``Quest/q_con5.lua`` and ``Quest/q_arena2.lua``'s own ``Accept_Check``).
``Quest/q_sea_join.lua``'s own ``Accept_Run`` gates its 7-window chain
behind ``if Player.CheckBuff(9903) then ... else <the chain> end``, and
``Player.CheckBuff`` is still a stub returning ``STUB_DEFAULT`` (0) --
TRUTHY in Lua, where only ``nil``/``false`` are falsy -- so that stubbed
condition always takes the ``then`` branch and the chain never runs today.
This is a property of running a real script against today's OTHER stub
coverage, not a defect in this file; a future round making
``Player.CheckBuff`` real can change it in either direction (see
``tests/test_script_lua_corpus.py``'s own ``BASELINE_TOTAL_STUB_CALLS``
comment for the measured count this produces).

WHAT IS DELIBERATELY NOT MADE REAL HERE, AND WHY.  ``GetWeekDay()`` (call
count 48, the next-highest count in this namespace that also touches no
other lane) is NOT implemented this round despite looking similar. Grepped
across every ``Quest.GetWeekDay()`` call site
(``QUESTDATA_TH__QUEST.tsv``'s ``n_VARI_9``/``n_VARI_10``/``n_VARI_11`` for
``Q_WEEK3_KILL3`` read 1/4/6, constant across every level row of that
quest) -- the table proves SOME small-int weekday enum exists, but nothing
in the committed artifacts (no table, no ``external/`` doc, no
``notes_to_chief/consumed/`` letter) says whether day 1 is Sunday or
Monday, or which direction the count runs.  Guessing that mapping would
silently gate weekly quest availability on the wrong day of the week --
exactly the kind of guess ``prompts/LANE-Q.md`` forbids ("the original
script is the spec; do not re-derive quest logic by guessing") and the
same posture ``lua_api/trigger.py`` already took on ``GetContactMode``
(one call site, enum meaning unclear, needs an RE ticket). ``GetWeekDay``
stays a logged stub for the same reason, named in ``STILL_STUBBED`` below
rather than silently skipped.

WHAT "REAL" MEANS HERE, PRECISELY.  No process-memory registry at all --
unlike ``lua_api.trigger.TriggerStatusRegistry``, this function is a pure
read of the SERVER'S OWN wall clock, nothing to remember between calls and
nothing shared or scoped per scene/character.  The clock itself IS the one
injectable seam (a ``Callable[[], datetime]``, mirroring how
``lua_api.trigger.build_namespace`` takes an injectable ``context``/
``registry``): the default reads the real wall clock in the
``Asia/Bangkok`` timezone, an explicit, stated assumption -- this project's
own house convention timestamps every round/letter in that zone
(``prompts/COMMON_LANE_ROUND.md``), and the game's committed artifacts
carry no server-timezone declaration of their own to confirm or refute it
against. Tagged ``[assumption of LANE-Q - pending COO confirmation]``
per ``prompts/COMMON_LANE_ROUND.md``'s own "decide, tag, keep moving"
rule, not silently asserted as fact.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - stdlib since Python 3.9, this project's floor
    ZoneInfo = None  # type: ignore[assignment]

#: Mirrors ``script_host.STUB_DEFAULT`` without importing that module (which
#: imports THIS package, via ``lua_api/__init__.py`` -> would be circular).
#: Kept equal to it by a cross-module test (``tests/test_script_lua_api_quest.py``,
#: same posture ``lua_api/trigger.py`` already takes), not by trust.
STUB_DEFAULT = 0

#: [assumption of LANE-Q - pending COO confirmation]: the server's own
#: quest-clock timezone.  No table or doc in the committed artifacts states
#: one; this matches the project's own house convention for every other
#: timestamp (prompts/COMMON_LANE_ROUND.md).
SERVER_TIMEZONE_NAME = "Asia/Bangkok"

#: A clock is anything callable with no arguments that returns a datetime;
#: only its .hour/.minute are ever read (see _minutes_of_day), so a naive
#: datetime works exactly as well as a tz-aware one for a caller (a test)
#: that already means "this is the wall-clock reading", tz-aware or not.
Clock = Callable[[], datetime]


def _server_clock() -> datetime:
    if ZoneInfo is None:  # pragma: no cover - exercised only on a stdlib without zoneinfo
        raise RuntimeError(
            "zoneinfo is not available on this interpreter - cannot read the "
            "real server clock")
    return datetime.now(ZoneInfo(SERVER_TIMEZONE_NAME))


def _minutes_of_day(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def _decode_hhmm(value: Any) -> Optional[int]:
    """One CheckOpenTime literal (``1930``, or Lua's truncated ``0030``==30)
    decoded to minutes-of-day, or ``None`` for anything not a clean
    ``HH*100+MM`` encoding with a valid hour and minute.

    Refuses rather than guesses, the same posture as
    ``lua_api.trigger._coerce_int``: booleans are rejected explicitly (a
    Lua ``true`` is Python's ``True`` is an ``int`` in this interpreter and
    would otherwise silently decode as hour 0 minute 1), NaN/infinite/
    fractional floats are rejected rather than truncated (lupa hands every
    Lua number back as a float; a WHOLE-number float, e.g. ``1930.0``, is
    what a real call site actually receives and is accepted), and a
    decoded hour outside 0-23 or minute outside 0-59 is refused rather than
    silently wrapped -- the corpus's own literals (grepped, see module
    docstring) never need a value outside that box.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        as_int = int(value)
        if float(as_int) != value:
            return None
        value = as_int
    if not isinstance(value, int):
        return None
    if value < 0 or value > 2359:
        return None
    hour, minute = divmod(value, 100)
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _in_window(now_minutes: int, start_minutes: int, end_minutes: int) -> bool:
    """Inclusive membership, wrapping past midnight when ``end < start``.

    NO CALL SITE IN TODAY'S CORPUS ACTUALLY EXERCISES THE WRAP, SAID
    PLAINLY.  ``q_sea_join.lua``'s own seven literal windows (module
    docstring) each already have ``start < end`` on their own -- ``0030``/
    ``0055`` decode to plain minutes 30/55, i.e. the SAME-day window
    00:30-00:55, not a wrap, because every individual window in that chain
    is 25 minutes long.  The CHAIN as a whole crosses midnight (window 5
    ends 23:55, window 6 begins 00:30), but that is seven separate,
    same-day ``CheckOpenTime`` calls -- never one call whose own two
    arguments span midnight.  The wrap branch below is a structural
    completeness choice, not a guess about a value this round measured:
    ``q_con5.lua``/``q_arena2.lua`` call this with table-driven
    ``Quest.Var3``/``Var4`` (a per-quest-instance start/end this harness
    cannot see yet, per the module docstring), and a night-shift-style
    window spanning midnight is an ordinary pattern for that shape of data
    even though nothing in the committed artifacts proves one exists today.
    A window where ``start == end`` is a single-minute window, not treated
    specially -- no call site in the corpus has one, but nothing about the
    arithmetic below requires excluding it either.
    """
    if start_minutes <= end_minutes:
        return start_minutes <= now_minutes <= end_minutes
    return now_minutes >= start_minutes or now_minutes <= end_minutes


def _log_real(log: Callable[[str], None], start_raw: Any, end_raw: Any,
              now_minutes: int, result: bool) -> None:
    log("LUA_QUEST_REAL Quest.CheckOpenTime start=%r end=%r now_minutes=%d result=%s"
        % (start_raw, end_raw, now_minutes, result))


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_QUEST_BAD_ARITY Quest.%s got=%d want=%s" % (api_name, got, want))


#: The one name this round makes real.  See the module docstring for why
#: this one, and why not GetWeekDay despite its higher call count.
REAL_METHODS = frozenset({"CheckOpenTime"})

#: The remaining 24, one honest sentence each for why they are NOT real
#: this round -- no guessing, per charter.  Every reason names the missing
#: seam, not "not done yet".
STILL_STUBBED: dict[str, str] = {
    "GetWeekDay": (
        "the enum a weekday number encodes is unverified: QUESTDATA_TH__QUEST.tsv "
        "proves Q_WEEK3_KILL3's n_VARI_9/10/11 are the constants 1/4/6 across every "
        "level row, but no table or doc in the committed artifacts says which day "
        "of the week 1 is, or which direction the count runs -- needs an RE ticket, "
        "not a guess (same posture as Trigger.GetContactMode)"
    ),
    "GetQuestFlag": "needs per-character Quest flag state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "SetFlag": "needs per-character Quest flag state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "SetQuestFlag": "needs per-character Quest flag state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "GetFlag": "needs per-character Quest flag state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "MobKillCount": "needs per-character quest kill-count state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "CheckMobKillCount": "needs per-character quest kill-count state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "GetMobKillCount": "needs per-character quest kill-count state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "CountDownTime": "needs a per-character running quest timer; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "RewardItemSelect": "needs per-character reward-choice state plus a Player.AddItem grant this lane does not own yet",
    "AddCriteriaExp": "needs a per-character EXP grant; Player.* item/exp/money queue item, not built yet",
    "AddCriteriaSkillPoint": "needs a per-character skill-point grant; Player.* queue item, not built yet",
    "AddCriteriaCash": "needs a per-character cash grant; Player.* queue item, not built yet",
    "AddLvCriteriaExp": "needs a per-character EXP grant; Player.* queue item, not built yet",
    "AddLvCriteriaSkillPoint": "needs a per-character skill-point grant; Player.* queue item, not built yet",
    "AddLvCriteriaCash": "needs a per-character cash grant; Player.* queue item, not built yet",
    "PlayNPCMovie": "needs a cutscene wire frame this lane does not own",
    "PlayNPCVoice": "needs a voice-line wire frame this lane does not own",
    "CanReportDailyQuest": "needs per-character daily-quest completion state (date-stamped); the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "ReportDailyQuest": "needs per-character daily-quest completion state (date-stamped); the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "CheckWishQuest": "needs per-character quest state; the LANE-DB column asked for in COO-DECISION 20260905_2058",
    "CheckGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
    "ReportGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
    "StartGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
}


class RealQuestNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Quest``.

    Same three-way ``__getitem__`` contract the stub has (real API name ->
    callable; other API name -> stub callable that logs and returns
    :data:`STUB_DEFAULT`; anything else, e.g. ``Var1``/``Finish`` -> bare
    :data:`STUB_DEFAULT`, silently), the exact shape
    ``lua_api.trigger.RealTriggerNamespace`` already established, so
    ``ScriptHost`` can hand a script this object instead of the generic
    stub without the script being able to tell the difference except by
    the answer it gets back.
    """

    __slots__ = ("_clock", "_log", "_stub_methods", "namespace", "calls")

    def __init__(self, methods: frozenset, clock: Clock, log: Callable[[str], None]):
        self.namespace = "Quest"
        self._clock = clock
        self._log = log
        self._stub_methods = methods - REAL_METHODS
        self.calls: list = []

    def __getitem__(self, name):
        if name == "CheckOpenTime":
            def check_open_time(*args):
                self.calls.append("Quest.CheckOpenTime")
                if len(args) != 2:
                    _log_bad_arity(self._log, "CheckOpenTime", len(args), "2")
                    return STUB_DEFAULT
                now_minutes = _minutes_of_day(self._clock())
                start = _decode_hhmm(args[0])
                end = _decode_hhmm(args[1])
                if start is None or end is None:
                    result = False
                else:
                    result = _in_window(now_minutes, start, end)
                _log_real(self._log, args[0], args[1], now_minutes, result)
                return result

            return check_open_time

        if name in self._stub_methods:
            qualified = "Quest.%s" % name

            def stub(*_args, _qualified=qualified):
                self.calls.append(_qualified)
                self._log("LUA_API_STUB %s" % _qualified)
                return STUB_DEFAULT

            return stub

        return STUB_DEFAULT

    def __setitem__(self, name, value):
        # Same posture as ApiNamespaceStub/RealTriggerNamespace: no script
        # in the corpus assigns into a namespace table at runtime (verified
        # there, not re-verified here); accept and discard.
        return None


def build_namespace(methods: frozenset, log: Callable[[str], None], *,
                     clock: Optional[Clock] = None) -> RealQuestNamespace:
    """The ``Quest`` global ``ScriptHost`` installs, real half included.

    ``clock`` defaults to the real server wall clock (:func:`_server_clock`)
    -- not fixed, not a private mutable state -- so a caller that does not
    ask for anything special (every test today except the ones that
    specifically probe clock behaviour) gets the actual current time, the
    same posture ``lua_api.trigger.build_namespace`` takes for its default
    context/registry.
    """
    return RealQuestNamespace(
        methods, clock if clock is not None else _server_clock, log)
