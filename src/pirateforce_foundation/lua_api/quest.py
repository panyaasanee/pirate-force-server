"""LANE-Q's ``Quest`` namespace: the clock (round 4jsydv/s2fxf6 lineage) plus
the flag/counter/daily-stamp group COO-DECISION ``20260906_1846`` named
"flag-quest-state" -- 9 more of the 25 names, all bound to the same
per-(character, quest) state door, none of them needing a wire frame or an
RE ticket.

WHY THESE NINE, GREPPED NOT GUESSED.  Reading ``gamedata/lua/Quest/q_kill5.lua``
(the charter's own named "first full quest lifecycle" script) end to end shows
exactly the shape ``LANE-DB``'s letter (``pf_bridge/notes_to_chief/
20260905_2212_LANE-DB-TO-LANE-Q-quest-state-doors-declared-and-opened-this-
round.md``) already worked out from the same script, independently confirmed
here against the corpus itself before writing a line of this file:

  * ``Accept_Check``: ``Quest.GetQuestFlag(Quest.Var1) == Quest.Finish`` --
    read ANOTHER quest's flag by id (``Quest.Var1`` is table data, not the
    running quest).
  * ``Accept_Run``: ``Quest.SetFlag(Quest.Active)`` -- write the CURRENT
    quest's own flag, no id argument (489 + 416 call sites respectively,
    the two highest-count names in the whole 160-function API map).
  * ``Accept_Run``: ``Quest.MobKillCount(Quest.Var2, Quest.Var3)`` -- start
    tracking kills of mob ``Var2``, target ``Var3`` (127 sites).
  * ``Report_Check``: ``Quest.CheckMobKillCount(Quest.Var2, Quest.Var3)`` --
    has the character reached that target yet (132 sites).
  * ``Quest/q_day_kill4.lua``'s ``Count_MobKillCount``:
    ``Quest.GetMobKillCount(Quest.Var5)`` -- the raw progress number, used
    for a percentage display, not a yes/no (16 sites).
  * ``Quest/q_guild_kill1.lua`` and five sibling ``q_day_*``/``q_week*``
    files: ``Quest.CanReportDailyQuest()`` gates ``Quest.ReportDailyQuest()``
    a few lines later -- a once-per-day completion stamp (61 sites each).
  * ``Quest/q_guildstorage.lua`` and 66 siblings: ``Quest.GetFlag() ==
    Quest.Active`` -- read the CURRENT quest's own flag, no id argument.
  * ``t_exch&setq_q1.lua``: ``Quest.SetQuestFlag(Trigger.Var7, Trigger.Var8)``
    -- write an ARBITRARY quest's flag by id, from a *Trigger* script (90
    sites) -- the one name in this group callable from outside ``Quest.*``
    itself, which is exactly why it takes an explicit id where ``SetFlag``
    does not.

WHAT "CURRENT QUEST" MEANS, AND WHERE IT COMES FROM.  Every quest script in
the corpus (``OpenAcceptUI_Run``/``Accept_Check``/``Accept_Run``/
``Report_Check``/``Report_Run``/``Delete_Run``) runs bound to ONE physical
quest instance for ONE character -- the same shape ``lua_api.trigger``'s
``TriggerContext`` already gives ``Trigger.SetStatus``/``NextStatus`` for
"this trigger", except a quest needs both a character id (there is no
concept of "the current trigger" independent of a player) and a quest id.
:class:`QuestContext` is that pair, supplied by the caller (a test today; a
future dispatch module once a script is actually bound to a live NPC
interaction) -- nothing here reads a real inbound frame or session, same
posture as ``TriggerContext``'s own docstring.

WHAT "REAL" MEANS HERE, AND THE ONE THING IT DELIBERATELY DOES NOT DO YET.
Unlike ``CheckOpenTime`` (a pure clock read, nothing to remember), these nine
names need PER-CHARACTER STATE THAT SURVIVES A RELOG (``PANYA-DECISION
20260904_0233``'s own M5 milestone: "เก็บได้+รอด relog") -- which rules out
``lua_api.trigger.TriggerStatusRegistry``'s process-memory design (that one
is *correctly* volatile: world/trigger state is meant to reset on reboot,
quest progress is not). The real, persistent half of that door is a LANE-DB
table this lane does not own and cannot write (``prompts/LANE-Q.md``'s own
words: ``store.py`` is "not yours, seam = one CORE-REQUEST per seam") --
asked for this round in ``pf_bridge/notes_to_chief/<this round>_LANE-Q-
CORE-REQUEST-quest-flag-counter-daily-stamp-columns.md``, still unanswered
as this file is written. :class:`QuestStateStore` is the injectable seam
that decision names, so plugging in the real accessor the day it lands is a
one-line change to ``script_host.ScriptHost.__init__`` and nothing here.
:class:`InMemoryQuestStateStore` -- the default when no store is injected --
is an INERT BUCKET for tests and spikes (same role ``lua_api.trigger``'s
``DEFAULT_CONTEXT``/private registry play for trigger status), explicitly
NOT the production answer: it is process memory, gone on reboot AND on
relog, which is wrong for a real character but correct for "a test that did
not ask for anything special should still get a working, isolated answer".
No test in this round claims otherwise; see the module's own nonclaims in
``rounds/Q_<this round>*.md``.

QUEST.NONE/ACTIVE/FINISH, DERIVED NOT INVENTED.  The corpus never assigns a
literal to these three (grepped: no ``Quest\\.\\(Active\\|None\\|Finish\\)\\s*=``
anywhere in ``gamedata/lua/**``) -- they are constants the ORIGINAL engine
injects into the ``Quest`` table, the same way it injects the 160 functions
this whole ``lua_api`` package re-implements. Two facts nail down enough of
their numeric value to be real rather than guessed:
  1. ``t_opnq_t1.lua``'s ``ScriptStart``: proceeds (calls
     ``Trigger.QuestActiveProgress(Trigger.Var1)``, see ``lua_api.trigger``)
     ONLY when ``Quest.GetQuestFlag(Trigger.Var1) == 0`` -- so the "never
     started" state that ``QuestStateStore.get_quest_flag`` returns
     ``None`` for must read back as ``0``, i.e. ``Quest.None == 0``.
  2. ``t_clsq.lua``'s ``ScriptStart`` -- the PAIRED closing half of the same
     open/close trigger family -- proceeds (calls
     ``Trigger.QuestFinishProgress(Trigger.Var1)``) ONLY when
     ``Quest.GetQuestFlag(Trigger.Var1) ~= 1`` is FALSE, i.e. the flag
     ``QuestActiveProgress`` just wrote in fact 1. cross-script, cross-file
     but same script FAMILY, this is the corpus's own two scripts agreeing
     with each other on what number ``QuestActiveProgress`` writes, not an
     invented number: ``Quest.Active == 1``.
No corpus site literal-compares ``Quest.Finish`` to any specific integer
(every comparison against it uses the symbolic name) -- so its exact value
is free AS LONG AS it stays distinct from 0 and 1, which is all any script
in the corpus ever depends on. ``2`` is chosen as the next value in the
same small ascending enumeration ``Trigger.NextStatus`` already uses
elsewhere in this codebase for an unrelated state machine, not because any
artifact says so. Tagged **[assumption of LANE-Q - pending COO/RE
confirmation]** per ``prompts/COMMON_LANE_ROUND.md``'s "decide, tag, keep
moving" rule.

WHAT IS DELIBERATELY LEFT STUBBED, ONE MORE NAME THAN THE 12 COO NAMED.
``CheckWishQuest`` (1 call site, ``Quest/q_wish.lua``'s own ``Accept_Check``)
was in COO-DECISION ``20260906_1846``'s list of 12. A FIRST grep pass (by
filename and by a column literally named after the quest) found nothing and
this docstring said so -- WRONG, caught by pf-adversary this round: a wider
pass over TABLE CONTENTS, not just filenames, finds real evidence:
``gamedata/tables/CONSTDATA_TH__VARIABLE_INTEGER.tsv`` rows 174/178
(``GUILD_MAKEWISH_GUILDLV`` = 4, ``GUILD_MAKEWISH_CDTIME`` = 1200),
``CONSTDATA_TH__GUILD_MEMBER.tsv``'s own ``f_CharWish_Chance`` column, and
``TEXTDATA_TH__HELP_CONTENT.tsv`` row 2028's in-game help text describing a
GUILD "Wishing Crystal" mechanic, once per day, granted through OTHER guild
members completing a task -- matching ``Accept_Run``'s own
``Player.OpenUI("Guild_MakeWish")`` call by name. So the semantics are NOT
undocumented; what is still missing is which of THREE candidate gates (a
guild level >= 4 floor, a literal 1200-unit cooldown of unknown unit, or a
per-guild-member chance roll) ``CheckWishQuest()`` itself checks before a
CHARACTER can accept the quest -- and the guild-level gate needs a
guild-level accessor this lane has no seam for regardless (``Guild.*``/
``Player.*`` are not real here). This makes the right classification
CROSS-LANE with LANE-GUILD (the same category as ``CheckGuildOfflineQuest``/
``ReportGuildOfflineQuest``/``StartGuildOfflineQuest`` below), not
"undocumented" -- guessing WHICH gate(s) combine, and how, without
LANE-GUILD's own state door is exactly what ``prompts/LANE-Q.md`` forbids,
the same posture already taken for ``GetWeekDay`` here and
``Trigger.GetContactMode`` in ``lua_api/trigger.py``, just for a different
reason than this docstring first claimed. Left in
``STILL_STUBBED`` with a named reason rather than silently made to match
COO's count; the deviation is called out plainly in this round's own round
file, not buried here.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from typing import Protocol
except ImportError:  # pragma: no cover - stdlib since Python 3.8, this project's floor
    Protocol = object  # type: ignore[assignment,misc]

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - stdlib since Python 3.9, this project's floor
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment,misc]

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

#: Fixed-offset fallback for interpreters/platforms whose stdlib ``zoneinfo``
#: has no IANA database to read ``SERVER_TIMEZONE_NAME`` from -- measured on
#: this project's own Windows gate (pirate-force-server#900, run
#: 34003119697): ``ZoneInfo("Asia/Bangkok")`` raises ``ZoneInfoNotFoundError``
#: there (Windows carries no system tz database and this project does not
#: depend on the ``tzdata`` PyPI package), while the same call succeeds on
#: Linux, which does have one. Not an approximation: Bangkok has been a
#: fixed UTC+7 offset with no DST since 1920 (verified against the IANA
#: ``tz`` database's own ``asia`` file: ``Zone Asia/Bangkok ... 7:00 - %z``
#: with no ``RULES`` entry since 1920 Apr), so this is exactly equal to the
#: named zone, not a stand-in for it. Keyed to the exact zone name it is
#: equivalent to (see the guard in ``_server_clock`` below) -- pf-adversary
#: (round ksp5d3) found that catching ``ZoneInfoNotFoundError``
#: unconditionally would silently substitute Bangkok's offset for ANY zone
#: name that later replaced ``SERVER_TIMEZONE_NAME`` and also failed to
#: resolve (e.g. a future move to "Asia/Tokyo", UTC+9, on the same
#: tzdata-less platform) -- 2 hours wrong with no error and no log line.
_KNOWN_FIXED_OFFSETS = {
    "Asia/Bangkok": timezone(timedelta(hours=7), name="ICT"),
}

#: A clock is anything callable with no arguments that returns a datetime;
#: only its .hour/.minute/.date() are ever read, so a naive datetime works
#: exactly as well as a tz-aware one for a caller (a test) that already
#: means "this is the wall-clock reading", tz-aware or not.
Clock = Callable[[], datetime]

#: Quest status constants the corpus reads off ``Quest.None``/``Active``/
#: ``Finish`` as bare attributes (never calls them). See the module
#: docstring for the two-script derivation of 0/1; 2 is the tagged
#: assumption.
QUEST_NONE = 0
QUEST_ACTIVE = 1
QUEST_FINISH = 2

_STATUS_CONSTANTS = {
    "None": QUEST_NONE,
    "Active": QUEST_ACTIVE,
    "Finish": QUEST_FINISH,
}


def _server_clock() -> datetime:
    if ZoneInfo is None:  # pragma: no cover - exercised only on a stdlib without zoneinfo
        raise RuntimeError(
            "zoneinfo is not available on this interpreter - cannot read the "
            "real server clock")
    try:
        return datetime.now(ZoneInfo(SERVER_TIMEZONE_NAME))
    except ZoneInfoNotFoundError:
        fallback = _KNOWN_FIXED_OFFSETS.get(SERVER_TIMEZONE_NAME)
        if fallback is None:
            # No verified fixed-offset equivalent for this zone name -- fail
            # loud rather than silently reusing Bangkok's offset for a zone
            # that may not share it (see _KNOWN_FIXED_OFFSETS above).
            raise
        return datetime.now(fallback)


def _minutes_of_day(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def _epoch_day(moment: datetime) -> int:
    """Days since the Unix epoch, local wall-clock date -- the smallest
    stable integer that changes exactly once per calendar day, which is all
    :func:`can_report_daily_quest`/:func:`report_daily_quest` need (they
    never care what the number IS, only whether it matches "today")."""
    return (moment.date() - date(1970, 1, 1)).days


def _decode_hhmm(value: Any) -> Optional[int]:
    """One CheckOpenTime literal (``1930``, or Lua's truncated ``0030``==30)
    decoded to minutes-of-day, or ``None`` for anything not a clean
    ``HH*100+MM`` encoding with a valid hour and minute.

    Refuses rather than guesses, the same posture as
    ``lua_api.trigger._coerce_int``: booleans are rejected explicitly (a
    Lua ``true`` is Python's ``True`` is an ``int`` in this interpreter and
    would otherwise silently decode as hour 0 minute 1), NaN/infinite/
    fractional floats are rejected rather than truncated (an integer Lua
    literal comes back from lupa==2.8/Lua 5.5 as a Python ``int`` via its
    integer subtype, not a float as an earlier draft of this docstring
    claimed -- pf-adversary round ksp5d3, 2026-09-06; a WHOLE-number
    float, e.g. ``1930.0``, is still accepted below since a real call site
    can produce one via Lua-side arithmetic, and this function must accept
    both shapes), and a decoded hour outside 0-23 or minute outside 0-59
    is refused rather than silently wrapped -- the corpus's own literals
    (grepped, see module docstring) never need a value outside that box.
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


def _coerce_int(value: Any, ceiling: int) -> Optional[int]:
    """Lua hands numbers back as floats or lupa's own int subtype; a door
    that never raises.  Same shape as ``lua_api.trigger._coerce_int`` --
    duplicated rather than imported, the convention every ``lua_api``
    module in this package already follows (each namespace file is
    self-contained; see e.g. ``trigger.py``'s own copy of this exact
    logic, which itself does not import this one). ``None`` means "not a
    usable number", the caller's job is to refuse the whole write/read
    rather than guess. Booleans are rejected explicitly: ``True`` is an
    ``int`` in Python and would otherwise silently become id/value 1.
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
    if value < 0 or value > ceiling:
        return None
    return value


#: ``quest_id`` bounds: u16, per LANE-DB's own measured evidence
#: (``columbus_quest_dispatch.py:330`` sends a quest id on the wire with
#: ``legacy.u16tag(0x12, quest_id)``) -- reused here rather than re-derived,
#: the same number this lane's own CORE-REQUEST asks LANE-DB's future
#: column to accept.
_MAX_QUEST_ID = 0xFFFF

#: ``flag_value``: no enum ceiling is proven (LANE-DB's letter: "DB ไม่รู้
#: และไม่เดาความหมายเลข"), but every literal the corpus actually writes is
#: one of the three tiny constants above -- 0xFFFF is generous headroom
#: (matches ``lua_api.trigger._MAX_STATUS``'s own reasoning: wide enough
#: for anything a real script needs, tight enough to refuse a NaN/huge
#: float arriving from Lua by mistake) without inventing a "the real max
#: is N" claim nothing in the artifacts supports.
_MAX_FLAG_VALUE = 0xFFFF

#: ``mob_id``: no table this round mined caps mob template ids explicitly;
#: kept wide (matches ``lua_api.trigger._MAX_TRIGGER_ID``'s own posture)
#: since this is a sanity door against garbage floats, not a guessed game
#: rule.
_MAX_MOB_ID = 0xFFFFFFFF

#: Kill-count target/progress: same reasoning, wide sanity ceiling only.
_MAX_KILL_COUNT = 0xFFFFFFFF

#: The fixed counter name :func:`can_report_daily_quest`/
#: :func:`report_daily_quest` use under :class:`QuestStateStore`'s counter
#: door -- reusing that one door for a date stamp rather than asking LANE-DB
#: for a THIRD table, since the door's own contract (LANE-DB's letter) is
#: "a string you choose, keyed to (character, quest, name)": exactly what a
#: fixed sentinel name gives here.  Cannot collide with a mob-kill counter
#: name (see ``_mob_kill_counter_name`` below): that one is always a decimal
#: digit string, this one never is.
_DAILY_REPORT_COUNTER_NAME = "daily_report_epoch_day"


def _mob_kill_counter_name(mob_id: int) -> str:
    """The counter-name key one mob's kill progress lives under.

    A PLAIN DECIMAL STRING (``"1234"``, not ``"mobkill:1234"``): keeping it
    free of any fixed prefix is what makes the collision argument above
    correct by construction (a decimal digit string can never equal
    ``_DAILY_REPORT_COUNTER_NAME``, which contains a letter) without this
    function and that sentinel having to agree on a shared prefix scheme.
    """
    return str(mob_id)


class QuestStateStore(Protocol):
    """The seam :class:`QuestStateStore`-shaped code above this line names:
    per-(character, quest) flag and named-counter storage, exact contract
    LANE-DB's own letter (``pf_bridge/notes_to_chief/20260905_2212_LANE-DB-
    TO-LANE-Q-...``) already designed against this same corpus, reused
    here rather than re-derived so the day a real accessor lands, wiring it
    in is a parameter, not a redesign.

    Every method takes already-COERCED plain ints/strs -- the caller (this
    module's own closures) is responsible for validating whatever a script
    handed in before it ever reaches a store; a store implementation never
    sees an unvalidated Lua value.
    """

    def get_quest_flag(self, character_id: int, quest_id: int) -> Optional[int]:
        """The stored flag, or ``None`` if this (character, quest) has
        never had one set."""
        ...

    def set_quest_flag(self, character_id: int, quest_id: int, flag_value: int) -> int:
        """Write the flag; returns the value now on record (read back
        after the write, per LANE-DB's own contract -- never a bare echo
        of the argument)."""
        ...

    def get_quest_counter(self, character_id: int, quest_id: int,
                           counter_name: str) -> Optional[int]:
        """The stored counter value, or ``None`` if never set."""
        ...

    def set_quest_counter(self, character_id: int, quest_id: int,
                           counter_name: str, counter_value: int) -> int:
        """Write an absolute counter value; returns the value now on
        record."""
        ...


@dataclass(frozen=True)
class QuestContext:
    """Which (character, quest instance) is running the script asking
    these questions -- mirrors ``lua_api.trigger.TriggerContext`` for the
    same reason: no script in the corpus passes its own quest id to
    ``SetFlag``/``GetFlag``/``MobKillCount``/etc. (grepped: every one of
    those four call shapes takes exactly the args the module docstring
    lists, never an extra id), because the game's own engine always knows
    which quest instance is running the script it dispatched. This server
    has no such dispatch yet, so the caller (today: a test; later: whatever
    binds a live NPC interaction to a quest script) supplies the answer up
    front instead.
    """

    character_id: int
    quest_id: int


#: The context a :class:`RealQuestNamespace` gets when nothing more specific
#: is supplied -- a well-defined, inert bucket, same role
#: ``lua_api.trigger.DEFAULT_CONTEXT`` plays there. Character id 0 is not a
#: real character (character ids in this codebase start at 1, per
#: ``store.py``'s own autoincrement primary key), so two unrelated tests
#: that both take the default cannot be mistaken for the same live player
#: even though they DO share the default's own bucket with each other (the
#: same tradeoff ``lua_api.trigger.DEFAULT_CONTEXT`` already makes; a caller
#: that cares passes its own context, per :func:`build_namespace` below).
DEFAULT_CONTEXT = QuestContext(character_id=0, quest_id=0)

#: Per-store bounds, same shape/reasoning as
#: ``lua_api.trigger.TRIGGERS_PER_SCENE_CAP``/``SCENES_CAP``: a cap a script
#: cannot grow past by looping, refused by name rather than silently
#: evicted.
CHARACTERS_CAP = 4096
QUESTS_PER_CHARACTER_CAP = 4096
COUNTERS_PER_CHARACTER_CAP = 16384


class InMemoryQuestStateStore:
    """The default :class:`QuestStateStore` when no real one is injected.

    PROCESS MEMORY, GONE ON REBOOT AND ON RELOG -- an INERT BUCKET for
    tests and spikes (see the module docstring's "what real means here"
    section), never the production answer: quest progress that vanishes
    when a character relogs is a regression against
    ``PANYA-DECISION 20260904_0233``'s own M5 milestone, not a feature.
    Kept for the same reason ``lua_api.trigger``'s own private default
    registry exists -- a caller that does not ask for anything special
    (every test today) still gets a working, isolated answer, and two
    unrelated tests never see each other's writes as long as neither
    reuses the OTHER's instance (the same tradeoff, not a new one).

    Never raises on a read/write a script's own arguments could reach
    (every argument arriving here has already been coerced by the
    namespace closures below); a non-positive cap is a caller-programming
    error and does raise ``ValueError``, same distinction
    ``TriggerStatusRegistry.__init__`` already documents for itself.
    """

    def __init__(self, characters: int = CHARACTERS_CAP,
                 quests_per_character: int = QUESTS_PER_CHARACTER_CAP,
                 counters_per_character: int = COUNTERS_PER_CHARACTER_CAP) -> None:
        for name, value in (("characters", characters),
                            ("quests_per_character", quests_per_character),
                            ("counters_per_character", counters_per_character)):
            if type(value) is bool or not isinstance(value, int) or value < 1:
                raise ValueError("%s must be a positive int" % name)
        self._characters_cap = characters
        self._quests_per_character_cap = quests_per_character
        self._counters_per_character_cap = counters_per_character
        self._lock = threading.RLock()
        self._flags: Dict[int, Dict[int, int]] = {}
        self._counters: Dict[int, Dict[Tuple[int, str], int]] = {}

    def get_quest_flag(self, character_id: int, quest_id: int) -> Optional[int]:
        with self._lock:
            return self._flags.get(character_id, {}).get(quest_id)

    def set_quest_flag(self, character_id: int, quest_id: int, flag_value: int) -> int:
        with self._lock:
            rows = self._flags.get(character_id)
            if rows is None:
                if len(self._flags) >= self._characters_cap:
                    return self.get_quest_flag(character_id, quest_id) or STUB_DEFAULT
                rows = self._flags.setdefault(character_id, {})
            if quest_id not in rows and len(rows) >= self._quests_per_character_cap:
                return rows.get(quest_id, STUB_DEFAULT)
            rows[quest_id] = flag_value
            return flag_value

    def get_quest_counter(self, character_id: int, quest_id: int,
                           counter_name: str) -> Optional[int]:
        with self._lock:
            return self._counters.get(character_id, {}).get((quest_id, counter_name))

    def set_quest_counter(self, character_id: int, quest_id: int,
                           counter_name: str, counter_value: int) -> int:
        with self._lock:
            rows = self._counters.get(character_id)
            if rows is None:
                if len(self._counters) >= self._characters_cap:
                    return self.get_quest_counter(
                        character_id, quest_id, counter_name) or STUB_DEFAULT
                rows = self._counters.setdefault(character_id, {})
            key = (quest_id, counter_name)
            if key not in rows and len(rows) >= self._counters_per_character_cap:
                return rows.get(key, STUB_DEFAULT)
            rows[key] = counter_value
            return counter_value


def _log_real(log: Callable[[str], None], start_raw: Any, end_raw: Any,
              now_minutes: int, result: bool) -> None:
    log("LUA_QUEST_REAL Quest.CheckOpenTime start=%r end=%r now_minutes=%d result=%s"
        % (start_raw, end_raw, now_minutes, result))


def _log_bad_arity(log: Callable[[str], None], api_name: str, got: int, want: str) -> None:
    log("LUA_QUEST_BAD_ARITY Quest.%s got=%d want=%s" % (api_name, got, want))


def _log_bad_value(log: Callable[[str], None], api_name: str, **raw_args: Any) -> None:
    """Same-arity call, one or more arguments not a usable number.

    pf-adversary (this round): a same-arity call that fails ``_coerce_int``
    (a bool/NaN/huge float/oversized int, e.g.) degraded to
    :data:`STUB_DEFAULT`/``False`` with NO log line for 9 of this round's
    11 new real closures -- indistinguishable from the ordinary "never set"
    case, unlike :func:`GetQuestFlag`'s own arity-1 path (already logs via
    :func:`_log_flag` even on a bad value, quest_id=-1). This closes that
    gap uniformly: every refused-by-value call now logs, keyword args named
    after the closure's own parameter names so a reader sees exactly which
    argument was bad.
    """
    log("LUA_QUEST_BAD_VALUE Quest.%s %s"
        % (api_name, " ".join("%s=%r" % (k, v) for k, v in raw_args.items())))


def _log_flag(log: Callable[[str], None], api_name: str, context: "QuestContext",
              quest_id: int, value: int) -> None:
    log("LUA_QUEST_REAL Quest.%s character=%d quest=%d flag=%d"
        % (api_name, context.character_id, quest_id, value))


def _log_counter(log: Callable[[str], None], api_name: str, context: "QuestContext",
                  quest_id: int, counter_name: str, value: Any) -> None:
    log("LUA_QUEST_REAL Quest.%s character=%d quest=%d counter=%s value=%r"
        % (api_name, context.character_id, quest_id, counter_name, value))


#: The 10 names real this round: the clock (round 4jsydv/s2fxf6 lineage)
#: plus the 9 flag/counter/daily-stamp names COO-DECISION `20260906_1846`
#: named. See the module docstring for why `CheckWishQuest` -- also in that
#: decision's list of 12 -- is NOT among them.
REAL_METHODS = frozenset({
    "CheckOpenTime", "GetQuestFlag", "SetFlag", "SetQuestFlag", "GetFlag",
    "MobKillCount", "CheckMobKillCount", "GetMobKillCount",
    "CanReportDailyQuest", "ReportDailyQuest",
})

#: The remaining 15, one honest sentence each for why they are NOT real
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
    "CheckWishQuest": (
        "1 call site (Quest/q_wish.lua Accept_Check); CONSTDATA_TH__VARIABLE_INTEGER.tsv "
        "(GUILD_MAKEWISH_GUILDLV=4, GUILD_MAKEWISH_CDTIME=1200) and "
        "CONSTDATA_TH__GUILD_MEMBER.tsv's f_CharWish_Chance prove a real guild-level/"
        "cooldown/chance-gated mechanic exists, but not which of the three (or what "
        "combination) this function checks, and the guild-level gate needs a Guild.*/"
        "Player.* accessor this lane has no seam for -- cross-lane with LANE-GUILD's "
        "namespace (same category as CheckGuildOfflineQuest/ReportGuildOfflineQuest/"
        "StartGuildOfflineQuest below), needs LANE-GUILD's own state door or an RE "
        "ticket, not a guess; COO-DECISION 20260906_1846 listed this among the 12, "
        "this round refuses it anyway rather than guess, see round file"
    ),
    "CountDownTime": "needs a per-character running quest timer; a fourth LANE-DB accessor not asked for this round (only flag/counter/daily-stamp were)",
    "RewardItemSelect": "needs per-character reward-choice state plus a Player.AddItem grant this lane does not own yet",
    "AddCriteriaExp": "needs a per-character EXP grant; Player.* item/exp/money queue item, not built yet",
    "AddCriteriaSkillPoint": "needs a per-character skill-point grant; Player.* queue item, not built yet",
    "AddCriteriaCash": "needs a per-character cash grant; Player.* queue item, not built yet",
    "AddLvCriteriaExp": "needs a per-character EXP grant; Player.* queue item, not built yet",
    "AddLvCriteriaSkillPoint": "needs a per-character skill-point grant; Player.* queue item, not built yet",
    "AddLvCriteriaCash": "needs a per-character cash grant; Player.* queue item, not built yet",
    "PlayNPCMovie": "needs a cutscene wire frame this lane does not own",
    "PlayNPCVoice": "needs a voice-line wire frame this lane does not own (reclassified message-wire, docs/LUA_HOST_API_MAP.md)",
    "CheckGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
    "ReportGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
    "StartGuildOfflineQuest": "needs per-character guild-quest state, cross-lane with LANE-GUILD's namespace",
}


class RealQuestNamespace:
    """Drop-in replacement for ``script_host.ApiNamespaceStub`` on ``Quest``.

    Same three-way ``__getitem__`` contract the stub has (real API name ->
    callable; other API name -> stub callable that logs and returns
    :data:`STUB_DEFAULT`; anything else, e.g. ``Var1``/``Finish`` -> a
    plain value, silently) the exact shape
    ``lua_api.trigger.RealTriggerNamespace`` already established, so
    ``ScriptHost`` can hand a script this object instead of the generic
    stub without the script being able to tell the difference except by
    the answer it gets back.  ``Quest.None``/``Active``/``Finish`` are the
    one addition to that shape: bare attribute reads (never called) that
    must return DISTINCT small ints rather than fall through to the
    generic ``STUB_DEFAULT`` bucket every other bare name uses -- see the
    module docstring for why silently collapsing them to 0 would be a
    real correctness bug, not a cosmetic one.
    """

    __slots__ = ("_clock", "_context", "_store", "_log", "_stub_methods", "namespace", "calls")

    def __init__(self, methods: frozenset, clock: Clock, log: Callable[[str], None],
                 context: "QuestContext", store: "QuestStateStore"):
        self.namespace = "Quest"
        self._clock = clock
        self._context = context
        self._store = store
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

        if name == "GetQuestFlag":
            def get_quest_flag(*args):
                self.calls.append("Quest.GetQuestFlag")
                if len(args) != 1:
                    _log_bad_arity(self._log, "GetQuestFlag", len(args), "1")
                    return STUB_DEFAULT
                quest_id = _coerce_int(args[0], _MAX_QUEST_ID)
                if quest_id is None:
                    _log_flag(self._log, "GetQuestFlag", self._context, -1, QUEST_NONE)
                    return QUEST_NONE
                value = self._store.get_quest_flag(self._context.character_id, quest_id)
                result = QUEST_NONE if value is None else value
                _log_flag(self._log, "GetQuestFlag", self._context, quest_id, result)
                return result

            return get_quest_flag

        if name == "GetFlag":
            def get_flag(*args):
                self.calls.append("Quest.GetFlag")
                if len(args) != 0:
                    _log_bad_arity(self._log, "GetFlag", len(args), "0")
                    return STUB_DEFAULT
                value = self._store.get_quest_flag(
                    self._context.character_id, self._context.quest_id)
                result = QUEST_NONE if value is None else value
                _log_flag(self._log, "GetFlag", self._context, self._context.quest_id, result)
                return result

            return get_flag

        if name == "SetFlag":
            def set_flag(*args):
                self.calls.append("Quest.SetFlag")
                if len(args) != 1:
                    _log_bad_arity(self._log, "SetFlag", len(args), "1")
                    return STUB_DEFAULT
                value = _coerce_int(args[0], _MAX_FLAG_VALUE)
                if value is None:
                    _log_bad_value(self._log, "SetFlag", value=args[0])
                    return STUB_DEFAULT
                after = self._store.set_quest_flag(
                    self._context.character_id, self._context.quest_id, value)
                _log_flag(self._log, "SetFlag", self._context, self._context.quest_id, after)
                return after

            return set_flag

        if name == "SetQuestFlag":
            def set_quest_flag(*args):
                self.calls.append("Quest.SetQuestFlag")
                if len(args) != 2:
                    _log_bad_arity(self._log, "SetQuestFlag", len(args), "2")
                    return STUB_DEFAULT
                quest_id = _coerce_int(args[0], _MAX_QUEST_ID)
                value = _coerce_int(args[1], _MAX_FLAG_VALUE)
                if quest_id is None or value is None:
                    _log_bad_value(self._log, "SetQuestFlag", quest_id=args[0], value=args[1])
                    return STUB_DEFAULT
                after = self._store.set_quest_flag(
                    self._context.character_id, quest_id, value)
                _log_flag(self._log, "SetQuestFlag", self._context, quest_id, after)
                return after

            return set_quest_flag

        if name == "MobKillCount":
            def mob_kill_count(*args):
                self.calls.append("Quest.MobKillCount")
                if len(args) != 2:
                    _log_bad_arity(self._log, "MobKillCount", len(args), "2")
                    return STUB_DEFAULT
                mob_id = _coerce_int(args[0], _MAX_MOB_ID)
                target = _coerce_int(args[1], _MAX_KILL_COUNT)
                if mob_id is None or target is None:
                    _log_bad_value(self._log, "MobKillCount", mob_id=args[0], target=args[1])
                    return STUB_DEFAULT
                # Starts tracking at progress 0 -- every measured call site
                # (module docstring) fires once, from `Accept_Run`, and the
                # `target` argument is not itself persisted: every sibling
                # `CheckMobKillCount`/`GetMobKillCount` call in the same
                # script re-supplies the same table-driven literal directly,
                # so storing a second copy here would be redundant state,
                # not missing functionality. Actual kill-progress increments
                # are a LANE-B mob-death lane_hook, not built this round
                # (this lane's own boundary: "combat state of B = read via
                # lane_hooks after the event") -- see round file nonclaims.
                counter_name = _mob_kill_counter_name(mob_id)
                after = self._store.set_quest_counter(
                    self._context.character_id, self._context.quest_id,
                    counter_name, 0)
                _log_counter(self._log, "MobKillCount", self._context,
                             self._context.quest_id, counter_name, after)
                return after

            return mob_kill_count

        if name == "CheckMobKillCount":
            def check_mob_kill_count(*args):
                self.calls.append("Quest.CheckMobKillCount")
                if len(args) != 2:
                    _log_bad_arity(self._log, "CheckMobKillCount", len(args), "2")
                    return STUB_DEFAULT
                mob_id = _coerce_int(args[0], _MAX_MOB_ID)
                target = _coerce_int(args[1], _MAX_KILL_COUNT)
                if mob_id is None or target is None:
                    _log_bad_value(self._log, "CheckMobKillCount", mob_id=args[0], target=args[1])
                    return False
                progress = self._store.get_quest_counter(
                    self._context.character_id, self._context.quest_id,
                    _mob_kill_counter_name(mob_id))
                result = (progress or 0) >= target
                _log_counter(self._log, "CheckMobKillCount", self._context,
                             self._context.quest_id, _mob_kill_counter_name(mob_id),
                             result)
                return result

            return check_mob_kill_count

        if name == "GetMobKillCount":
            def get_mob_kill_count(*args):
                self.calls.append("Quest.GetMobKillCount")
                if len(args) != 1:
                    _log_bad_arity(self._log, "GetMobKillCount", len(args), "1")
                    return STUB_DEFAULT
                mob_id = _coerce_int(args[0], _MAX_MOB_ID)
                if mob_id is None:
                    _log_bad_value(self._log, "GetMobKillCount", mob_id=args[0])
                    return STUB_DEFAULT
                progress = self._store.get_quest_counter(
                    self._context.character_id, self._context.quest_id,
                    _mob_kill_counter_name(mob_id))
                result = progress if progress is not None else STUB_DEFAULT
                _log_counter(self._log, "GetMobKillCount", self._context,
                             self._context.quest_id, _mob_kill_counter_name(mob_id),
                             result)
                return result

            return get_mob_kill_count

        if name == "CanReportDailyQuest":
            def can_report_daily_quest(*args):
                self.calls.append("Quest.CanReportDailyQuest")
                if len(args) != 0:
                    _log_bad_arity(self._log, "CanReportDailyQuest", len(args), "0")
                    return STUB_DEFAULT
                stamp = self._store.get_quest_counter(
                    self._context.character_id, self._context.quest_id,
                    _DAILY_REPORT_COUNTER_NAME)
                today = _epoch_day(self._clock())
                result = stamp is None or stamp != today
                _log_counter(self._log, "CanReportDailyQuest", self._context,
                             self._context.quest_id, _DAILY_REPORT_COUNTER_NAME,
                             result)
                return result

            return can_report_daily_quest

        if name == "ReportDailyQuest":
            def report_daily_quest(*args):
                self.calls.append("Quest.ReportDailyQuest")
                if len(args) != 0:
                    _log_bad_arity(self._log, "ReportDailyQuest", len(args), "0")
                    return STUB_DEFAULT
                today = _epoch_day(self._clock())
                after = self._store.set_quest_counter(
                    self._context.character_id, self._context.quest_id,
                    _DAILY_REPORT_COUNTER_NAME, today)
                _log_counter(self._log, "ReportDailyQuest", self._context,
                             self._context.quest_id, _DAILY_REPORT_COUNTER_NAME,
                             after)
                return after

            return report_daily_quest

        if name in _STATUS_CONSTANTS:
            return _STATUS_CONSTANTS[name]

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
                     clock: Optional[Clock] = None,
                     context: Optional["QuestContext"] = None,
                     store: Optional["QuestStateStore"] = None) -> RealQuestNamespace:
    """The ``Quest`` global ``ScriptHost`` installs, real half included.

    ``clock`` defaults to the real server wall clock (:func:`_server_clock`)
    -- not fixed, not a private mutable state -- so a caller that does not
    ask for anything special (every test today except the ones that
    specifically probe clock behaviour) gets the actual current time, the
    same posture ``lua_api.trigger.build_namespace`` takes for its default
    context/registry. ``context``/``store`` default to :data:`DEFAULT_CONTEXT`
    and a FRESH PRIVATE :class:`InMemoryQuestStateStore` -- not a process
    singleton, unlike ``lua_api.trigger.trigger_status_registry()`` -- so two
    unrelated tests/spikes that both take the default can never collide
    (see :class:`InMemoryQuestStateStore`'s own docstring for why this
    default is explicitly not the production answer).
    """
    return RealQuestNamespace(
        methods, clock if clock is not None else _server_clock, log,
        context if context is not None else DEFAULT_CONTEXT,
        store if store is not None else InMemoryQuestStateStore(),
    )
