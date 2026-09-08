"""``Quest.RewardItem1``..``Quest.RewardChooseNum6``, and the rule that a
half transaction is refused whole.

LANE-Q.  Round ``joa0u6`` joined ``Quest.Var1..Var20`` to the shipped quest
row, and the first thing that produced was a real defect rather than a
feature: ``Quest/q_class.lua`` line 60 took **15,000** off the player
(``Player.AddCash(Quest.Var4)``, cell ``4294952296`` = -15000) and then
line 64, ``if (Quest.RewardItem1 > 0) then Player.AddItem(...)``, could
never be true, because every ``Quest.Reward*`` name still fell through to
``lua_api.quest.STUB_DEFAULT`` (0).  Row 3200 of the shipped table names
three items -- 2480010, 2480011, 2480012 -- that the player was charged
for and did not get.

This module is the two halves of the fix, and they are deliberately in one
file because neither is safe without the other:

  1. THE CELLS.  ``quest_reward_rows.tsv`` mirrors the row's 24 reward
     cells verbatim, so ``Quest.RewardItem1`` answers 2480010 instead of 0.
  2. THE GATE.  ``quest_column_groups.tsv`` records which columns of one
     row are the TAKE side and the GIVE side of ONE transaction, and this
     module refuses EVERY column of a group whose give side cannot
     currently be paid.  ``Player.AddItem`` is still a stub
     (``lua_api.player`` ``_ITEM_STATE``), so today that gate CLOSES the
     q_class charge again: the quest goes back to being free, which is
     what COO-DECISION ``20260908_0242`` item 4 chose over charging
     15,000 for nothing.

Landing (1) without (2) would be the worse of the two states, not the
better one: it makes the give branch *look* live while ``Player.AddItem``
logs ``LUA_API_STUB`` and drops the item on the floor.

THE RULE, IN COO'S WORDS (``20260908_0242`` item 4)
---------------------------------------------------
Columns of one row that TAKE from the player and columns that GIVE in the
same transaction are ONE GROUP, opened together only; an incomplete group
refuses every column in it, take side included.  Columns with no
take/give counterpart (a condition, a message id) are unaffected -- they
are not in any group and this module has no opinion about them.

A TRANSACTION IS NOT A SET OF COLUMNS (pf-adversary D1/D2, MEASURED)
--------------------------------------------------------------------
The first draft of this module gated COLUMNS, and both of its findings
were the same mistake seen from two sides:

  D1  ``q_class.lua`` ``Report_Run`` also calls ``Quest.AddCriteriaExp``,
      ``AddCriteriaSkillPoint`` and ``AddCriteriaCash``, which pay out of
      the criteria curve and read no cell at all.  Refusing ``n_VARI_4``
      and leaving those three running moved the player from -14,930 to
      **+70** cash, plus 19,350 exp and 6,450 skill points, every run.
      The gate would have been a bigger defect than the one it closed.
  D2  ``q_guild_boss2.lua`` rows 8061..8065 name no reward item, so the
      draft called their group "not exercised" and let a 10,000 charge
      through -- take with no give, on one of the only two scripts the
      table named AT THE TIME (round `ad7t6n` took the table to 61
      groups; the reasoning is unchanged, the count is not).  Line 55 of that file calls ``AddLvCriteriaExp``
      UNCONDITIONALLY: the give was there, it just had no column.

So a member may carry :data:`NO_COLUMN` and be addressed by its API name,
and a group holding one is exercised on EVERY row, because the script
calls it on every run.

WHETHER A GROUP IS EXERCISED IS STILL A FACT ABOUT THE ROW
-----------------------------------------------------------
For a group whose give side is columns only, it is the row's own cells
that decide -- a row owing nothing must not have its take refused.  No
shipped group is in that shape today (both carry an unconditional
payout) -- all 61 of them, re-derived round `ad7t6n` -- so this half of
the rule is load-bearing for the future rather than for any shipped row;
it is tested directly rather than left as a comment.  The GROUP is a fact about the code (which entry point
performs both sides); EXERCISED is a fact about the row.

WHAT THIS DOES NOT DECIDE
-------------------------
Nothing here gives an item: ``Player.AddItem`` is somebody else's seam
(LANE-DB owns the inventory rows) and this module never calls it.  Nothing
here decides that a quest is complete, and NO FRAME GOES OUT.  What it
does is make the difference between "charged and paid" and "charged and
not paid" impossible to reach silently: the first is not available yet,
so the second is refused out loud instead of being performed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from . import quest_criteria, quest_vars, vendored
from .quest_criteria import QuestCriteriaError
from .quest_vars import (
    REFUSE_NO_QUEST_BOUND, REFUSE_NO_QUEST_ROW, REPORT_ONCE_REASONS,
    UNBOUND_QUEST_ID,
)

#: How many reward slots a quest row has, of each of the four kinds.  Fixed
#: by the shipped table's own column list, not by this lane.
REWARD_SLOTS = 6

#: The two sides of a transaction group.  A closed set: a row of the group
#: table with any other side is a corrupt mirror.
TAKE = "take"
GIVE = "give"
SIDES = frozenset({TAKE, GIVE})

#: What a group member's ``column`` says when the call it names reads no
#: cell at all -- ``Quest.AddCriteriaCash()``, whose amount comes from the
#: criteria curve.  Such a member is UNCONDITIONAL: the script calls it
#: every run, so a group that has one is always exercised, whatever the
#: row's reward cells say.
#:
#: WHY IT EXISTS (pf-adversary D1, round `l0rbyx`, MEASURED).  The first
#: draft of this module gated columns only, and `q_class.lua`'s
#: `Report_Run` has three column-less gives -- `AddCriteriaExp`,
#: `AddCriteriaSkillPoint`, `AddCriteriaCash` -- that pay out of the curve.
#: Refusing the charge and leaving those running took the player from
#: -14,930 to **+70** cash plus 19,350 exp and 6,450 skill points, free,
#: every run: a bigger defect than the one it was closing.  A transaction
#: is not a set of columns.
NO_COLUMN = "-"

#: The shipped table's own 24 reward column names, in mirror order.
#: ``n_REWARD_NUM*`` and not ``n_REWARD_ITEMNUM*`` -- the table's spelling,
#: which is NOT the spelling of the Lua name that reads it
#: (``Quest.RewardItemNum1``).  Keeping the asymmetry visible in one place
#: is why :data:`_LUA_NAME_TO_SOURCE` is a built map rather than a rule.
SOURCE_COLUMNS: Tuple[str, ...] = (
    tuple("n_REWARD_ITEM%d" % slot for slot in range(1, REWARD_SLOTS + 1))
    + tuple("n_REWARD_NUM%d" % slot for slot in range(1, REWARD_SLOTS + 1))
    + tuple("n_REWARD_CHOOSE%d" % slot for slot in range(1, REWARD_SLOTS + 1))
    + tuple("n_REWARD_CHOOSENUM%d" % slot
            for slot in range(1, REWARD_SLOTS + 1)))

#: Column headers of the verbatim reward mirror, in order.
REWARD_COLUMNS: Tuple[str, ...] = ("quest_id",) + tuple(
    name.lower()[2:] for name in SOURCE_COLUMNS)

#: Column headers of the transaction-group table, in order.  ``call_site``
#: is provenance and is required of every row, the same contract
#: ``quest_var_signedness.tsv`` carries: a group membership nobody can open
#: a file and read is a guess.
GROUP_COLUMNS: Tuple[str, ...] = (
    "script", "group", "side", "column", "api_name", "call_site")

#: ``Quest.<name>`` -> the shipped column it reads.  Built, not parsed, so
#: ``RewardItemNum3 -> n_REWARD_NUM3`` and ``RewardChooseNum3 ->
#: n_REWARD_CHOOSENUM3`` are stated once and cannot drift apart.
_LUA_NAME_TO_SOURCE: Dict[str, str] = {}
for _slot in range(1, REWARD_SLOTS + 1):
    _LUA_NAME_TO_SOURCE["RewardItem%d" % _slot] = "n_REWARD_ITEM%d" % _slot
    _LUA_NAME_TO_SOURCE["RewardItemNum%d" % _slot] = "n_REWARD_NUM%d" % _slot
    _LUA_NAME_TO_SOURCE["RewardChoose%d" % _slot] = "n_REWARD_CHOOSE%d" % _slot
    _LUA_NAME_TO_SOURCE["RewardChooseNum%d" % _slot] = (
        "n_REWARD_CHOOSENUM%d" % _slot)
del _slot

#: The give-side columns a script actually TESTS before giving anything:
#: ``if (Quest.RewardItem1 > 0)`` / ``if (Quest.RewardChoose1 > 0)``.  A
#: row whose only non-zero reward cell is a NUM gives nothing, so it does
#: not exercise its group -- the id is what opens the branch.
GIVE_ID_COLUMNS: Tuple[str, ...] = tuple(
    name for name in SOURCE_COLUMNS
    if name.startswith("n_REWARD_ITEM") or (
        name.startswith("n_REWARD_CHOOSE")
        and not name.startswith("n_REWARD_CHOOSENUM")))

#: Largest reward cell in all 1544 x 24 = 37,056 shipped cells, and the
#: count of cells at or above ``2**31``.  Pinned here and asserted in the
#: tests: unlike ``n_VARI_*``, NOTHING in the reward columns is a wrapped
#: negative, so this module has no signedness reading to make and must not
#: grow one.  The day a wrapped reward cell appears the test fails and a
#: person decides, rather than 4.29 billion items being granted.
LARGEST_REWARD_CELL = 3509557
WRAPPED_REWARD_CELLS = 0

_WRAP = 1 << 32

_HERE = Path(__file__).resolve().parent
_REWARDS_PATH = _HERE / "quest_reward_rows.tsv"
_GROUPS_PATH = _HERE / "quest_column_groups.tsv"

_REWARDS_CACHE: Optional[Dict[int, Tuple[int, ...]]] = None
_GROUPS_CACHE: Optional[Dict[str, Tuple["TransactionGroup", ...]]] = None


class GroupMember:
    """One row of ``quest_column_groups.tsv``."""

    __slots__ = ("side", "column", "api_name", "call_site")

    def __init__(self, side: str, column: str, api_name: str, call_site: str):
        self.side = side
        self.column = column
        self.api_name = api_name
        self.call_site = call_site

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "GroupMember(%s, %s, %s)" % (self.side, self.column,
                                            self.api_name)


class TransactionGroup:
    """The take and give members one Lua entry point performs together."""

    __slots__ = ("script", "group", "members")

    def __init__(self, script: str, group: str,
                 members: Tuple[GroupMember, ...]):
        self.script = script
        self.group = group
        self.members = members

    def side(self, side: str) -> Tuple[GroupMember, ...]:
        return tuple(member for member in self.members if member.side == side)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "TransactionGroup(%s.%s, %d members)" % (
            self.script, self.group, len(self.members))


def _read_mirror(path: Path, columns: Tuple[str, ...]) -> list:
    """The same parser the other mirrors use, called rather than copied."""
    return quest_criteria._read_mirror(path, columns)  # noqa: SLF001


def _parse_int(path: Path, name: str, raw: str) -> int:
    return quest_criteria._parse_int(path, name, raw)  # noqa: SLF001


def load_rewards() -> Dict[int, Tuple[int, ...]]:
    """``{quest_id: (24 cells in SOURCE_COLUMNS order)}``, parsed once."""
    global _REWARDS_CACHE
    if _REWARDS_CACHE is None:
        _REWARDS_CACHE = vendored.read_mirror(
            vendored.MIRROR_QUEST_REWARD_ROWS, _parse_rewards)
    return _REWARDS_CACHE


def _parse_rewards() -> Dict[int, Tuple[int, ...]]:
    table: Dict[int, Tuple[int, ...]] = {}
    for fields in _read_mirror(_REWARDS_PATH, REWARD_COLUMNS):
        quest_id = _parse_int(_REWARDS_PATH, "quest_id", fields[0])
        if quest_id in table:
            raise QuestCriteriaError("%s: duplicate quest_id %d"
                                     % (_REWARDS_PATH, quest_id))
        cells = []
        for index, name in enumerate(REWARD_COLUMNS[1:], start=1):
            value = _parse_int(_REWARDS_PATH, name, fields[index])
            if value < 0 or value >= _WRAP:
                raise QuestCriteriaError(
                    "%s: quest %d %s is %d, outside the unsigned 32-bit "
                    "range the source stores"
                    % (_REWARDS_PATH, quest_id, name, value))
            cells.append(value)
        table[quest_id] = tuple(cells)
    return table


def load_groups() -> Dict[str, Tuple[TransactionGroup, ...]]:
    """``{script_lowercased: (TransactionGroup, ...)}``, parsed once.

    Script names are folded to lower case on the way in, the same fold
    :func:`lua_api.quest_criteria.quests_for_script` and
    :func:`lua_api.quest_vars.load_signedness` already use.
    """
    global _GROUPS_CACHE
    if _GROUPS_CACHE is None:
        _GROUPS_CACHE = vendored.read_mirror(
            vendored.MIRROR_QUEST_COLUMN_GROUPS, _parse_groups)
    return _GROUPS_CACHE


def _parse_groups() -> Dict[str, Tuple[TransactionGroup, ...]]:
    collected: Dict[Tuple[str, str], list] = {}
    order: list = []
    scripts: Dict[str, str] = {}
    for fields in _read_mirror(_GROUPS_PATH, GROUP_COLUMNS):
        script = fields[0].strip()
        if not script:
            raise QuestCriteriaError(
                "%s: a group row has an empty script name" % _GROUPS_PATH)
        group = fields[1].strip()
        if not group:
            raise QuestCriteriaError(
                "%s: %s has a group row with no entry point" % (_GROUPS_PATH,
                                                                script))
        side = fields[2].strip()
        if side not in SIDES:
            raise QuestCriteriaError(
                "%s: unknown side %r (known: %s)"
                % (_GROUPS_PATH, side, ", ".join(sorted(SIDES))))
        column = fields[3].strip()
        if not column:
            raise QuestCriteriaError(
                "%s: %s.%s has a member with no column" % (_GROUPS_PATH,
                                                           script, group))
        if (side == GIVE and column != NO_COLUMN
                and column not in SOURCE_COLUMNS):
            raise QuestCriteriaError(
                "%s: give-side column %r is not one of the shipped reward "
                "columns" % (_GROUPS_PATH, column))
        if side == TAKE and column == NO_COLUMN:
            raise QuestCriteriaError(
                "%s: %s.%s has a take side with no column; a take this "
                "lane cannot name a cell for is one it cannot refuse"
                % (_GROUPS_PATH, script, group))
        api_name = fields[4].strip()
        if not api_name:
            raise QuestCriteriaError(
                "%s: %s.%s member %s names no API"
                % (_GROUPS_PATH, script, group, column))
        call_site = fields[5].strip()
        if ":" not in call_site:
            raise QuestCriteriaError(
                "%s: call_site %r is not a file:line" % (_GROUPS_PATH,
                                                         call_site))
        key = (script.lower(), group)
        if key not in collected:
            collected[key] = []
            order.append(key)
        scripts[script.lower()] = script
        collected[key].append(GroupMember(side, column, api_name, call_site))
    table: Dict[str, list] = {}
    for key in order:
        members = tuple(collected[key])
        group = TransactionGroup(scripts[key[0]], key[1], members)
        if not group.side(TAKE) or not group.side(GIVE):
            raise QuestCriteriaError(
                "%s: group %s.%s has only one side; a group with one side "
                "is not a transaction and this table must not carry it"
                % (_GROUPS_PATH, key[0], key[1]))
        table.setdefault(key[0], []).append(group)
    return {script: tuple(groups) for script, groups in table.items()}


def reset_caches() -> None:
    """Drop both parsed mirrors.  For tests that point the module at a
    temporary file; production never calls it."""
    global _REWARDS_CACHE, _GROUPS_CACHE
    _REWARDS_CACHE = None
    _GROUPS_CACHE = None


def _default_api_is_real(api_name: str) -> bool:
    """Is ``Namespace.Name`` implemented for real, or still a stub?

    IMPORTED INSIDE THE FUNCTION ON PURPOSE.  ``lua_api.quest`` imports
    this module (it has to: the namespace reads the cells), so importing
    it back at module scope is a cycle.  The alternative -- copying the
    two ``REAL_METHODS`` sets here -- is the ``api_spec.tsv`` mistake this
    lane has already paid for once (pf-adversary F2, round ``5qtaqy``): a
    third artifact that disagrees with the two it was copied from.  One
    late import, and the sets stay where their owners keep them.
    """
    namespace, _, name = api_name.partition(".")
    if namespace == "Player":
        from . import player
        return name in player.REAL_METHODS
    if namespace == "Quest":
        from . import quest
        return name in quest.REAL_METHODS
    return False


class GroupState:
    """What :func:`group_state` decided about one group for one row."""

    __slots__ = ("group", "exercised", "blocking")

    def __init__(self, group: TransactionGroup, exercised: bool,
                 blocking: Tuple[str, ...]):
        self.group = group
        #: Does THIS row put an id in a give-side cell of this group.
        self.exercised = exercised
        #: The API names of this group -- EITHER SIDE -- that are not
        #: real yet, in order (pf-adversary D2, round `ad7t6n`).
        self.blocking = blocking

    @property
    def payable(self) -> bool:
        """Can every column of this group be honoured for this row."""
        return not self.exercised or not self.blocking

    def columns(self) -> Tuple[str, ...]:
        return tuple(member.column for member in self.group.members)


#: The refusal this module can produce, its own name so a caller (and a
#: test) can tell it from ``quest_vars``' four.  An ORDINARY outcome, not
#: an error: it is what the server is supposed to do while half of a
#: shipped transaction has no implementation.
REFUSE_GROUP_UNPAYABLE = "transaction_group_give_side_not_implemented"

#: What a REFUSED TAKE-SIDE CELL hands the script: ``-1``, and
#: deliberately NOT the ``0`` every other stub answers with.
#:
#: WHY IT CANNOT BE ZERO (pf-adversary D8, round ``5a3x47``, and MEASURED
#: at scale in round ``ad7t6n``).  Refusing a cell is supposed to mean
#: "this lane will not say what is in it".  ``0`` does not mean that to a
#: script: it is an ordinary number, and the REAL implementations happily
#: compare it.  ``q_boat_health.lua`` guards its repair with
#: ``Player.GetCash() >= Quest.Var2``; with the charge cell refused to
#: ``0`` that guard reads ``>= 0``, is true for a player holding nothing,
#: and the script says "repaired" (``Player.ShowMessage(824)``, a REAL
#: method) on screen.  The gate itself was manufacturing a false message.
#:
#: ``Player.RemoveItem`` turns that from one script into fifty-four.
#: MEASURED on the corpus: the take cells of the 56 groups it opens are
#: read by **91 ``Player.CheckItemNum`` call sites inside ``*_Check``
#: entry points, across 54 scripts** (79 sites in 53 ``Report_Check`` +
#: 12 sites in 6 ``Accept_Check``).  This said "57 scripts" for two
#: rounds; 57 is the number of scripts with a ``RemoveItem`` take member,
#: and three of them (``q_day_business``, ``q_gender_equip1``,
#: ``q_gender_equip2``) guard that cell in no ``*_Check`` at all
#: (pf-adversary D6, round ``0ldyk7``).  ``Player.CheckItemNum`` IS REAL
#: (``player.REAL_METHODS``).  ``CheckItemNum(0, 0)`` asks whether the
#: player holds at least zero of template id zero and answers TRUE, so
#: every one of those 54 gather/send quests would have told a player with
#: an empty backpack "you may report this quest" -- and then refused the
#: reward.  The player would lose the quest and receive nothing.
#:
#: WHERE THIS CONSTANT STILL BITES, AFTER ROUND ``0ldyk7``.  Narrower than
#: the paragraphs above imply, and pf-adversary D7 of that round measured
#: exactly how narrow: over all 66,048 (row, entry point, column) triples,
#: there is NOT ONE where this cell gate fires and
#: :func:`unpayable_group_of_entry_point` does not.  Structurally so -- the
#: cell gate refuses a NAMED entry point only when it owns an unpayable
#: group, which is the same condition on which ``ScriptHost.call`` has
#: already refused the whole entry point.  So through ``call`` with a real
#: name, this constant is unreachable; the one live path left is
#: :data:`UNKNOWN_ENTRY_POINT` -- a cell read outside a call -- which is
#: the fail-closed default and is what makes forgetting to name an entry
#: point safe rather than silent.  Kept, and kept fail-closed, for that;
#: not kept because anything reaches it today.
#:
#: WHY A NEGATIVE NUMBER AND NOT ``nil``.  ``nil`` is the tempting
#: answer -- it is Lua's own "there is no value" -- and this round wrote
#: it first.  pf-adversary D3 of round ``ad7t6n`` measured what it costs,
#: and the cost is a REGRESSION, not a refusal:
#:
#: The refusal is DECIDED per ``(script, Lua entry point)`` -- that is
#: what a group is -- but it is DELIVERED through ``Quest.VarN``, which
#: is keyed on ``(quest_id, column)`` and has no idea which entry point
#: is running.  So a decision made about ``Report_Run`` is enforced in
#: ``Accept_Run`` and ``Delete_Run`` too: 87 of the 88 item take-cell
#: members are read in some OTHER top-level function of their own file.
#: With ``nil`` in the cell, 17 of those reads are in an operator
#: context, and at ``q_gender_equip1.lua:25`` (quests 1072 and 1089) the
#: raise lands AFTER ``Quest.SetFlag(Quest.Active)`` -- a REAL write --
#: has already run, and BEFORE four real ``Player.MobAppear`` writes on
#: lines 27-33.  The gate would manufacture a half-executed entry point,
#: which is the exact thing it exists to prevent.
#:
#: ``-1`` refuses without breaking control flow.  Every ``_coerce_int``
#: door in this package refuses a value outside ``[0, ceiling]`` rather
#: than clamping it, so ``-1`` is rejected as data by every real API
#: exactly the way ``nil`` would be -- ``CheckItemNum`` answers False and
#: the requirement REFUSES -- while ``if (Quest.VarN > 0)`` reads FALSE
#: and simply skips its branch, as it did when the cell was ``0``.  So
#: the refusal is a value no real API will accept and no shipped guard
#: will trip over.
#:
#: WHAT ``-1`` DOES NOT FIX, said plainly: a guard of the shape
#: ``Player.GetCash() >= Quest.Var2`` (``q_boat_health.lua:18``) is still
#: true for a player with no money, so pf-adversary D8 of round
#: ``5a3x47`` is NOT paid by this constant -- it is left exactly where it
#: was, no better and no worse than the ``0`` it replaces.  D8 needs the
#: namespace to know which entry point is running so a refusal can be
#: scoped to the group that made it; that is a change to
#: ``QuestContext``/``script_host``, it is written up in
#: ``docs/SCRIPT_LANE.md``, and it is the next round's first job.
#:
#: The GIVE side keeps ``0`` on purpose: a reward cell of ``0`` is what
#: the shipped scripts already test (``if (Quest.RewardItem1 > 0)``), so
#: ``0`` there means "no reward item" and correctly skips the payout.
#: Refusing to give and refusing to say are different refusals.
REFUSED_CELL = -1


def group_state(quest_id: int) -> Tuple[GroupState, ...]:
    """Every transaction group of this row's script, decided for this row.

    Empty for the 148 of 209 scripts that couple nothing -- which is
    still the ordinary case and not an error.  RE-DERIVED round
    `ad7t6n`, when `Player.RemoveItem` took the count from 2 coupled
    scripts to 61; the old "207 of 209" in this line described a table
    with five groups in it.
    """
    script = quest_criteria.script_for_quest(quest_id)
    if script is None:
        return ()
    groups = load_groups().get(script.strip().lower())
    if not groups:
        return ()
    cells = load_rewards().get(quest_id)
    states = []
    for group in groups:
        # A column-less give is called every run, so it is owed every run.
        exercised = any(member.column == NO_COLUMN
                        for member in group.side(GIVE))
        if not exercised and cells is not None:
            for member in group.side(GIVE):
                if member.column not in GIVE_ID_COLUMNS:
                    continue
                if cells[SOURCE_COLUMNS.index(member.column)]:
                    exercised = True
                    break
        # BOTH SIDES, not just the give (pf-adversary D2, round
        # `ad7t6n`, MEASURED).  This read `group.side(GIVE)` alone, so a
        # group was payable the moment its GIVE side went real -- no
        # matter what the TAKE side was.  On the day `Player.AddItem`
        # lands while `Player.RemoveItem` is still a stub, that is 452 of
        # the 1544 shipped rows across 57 scripts in which the player
        # receives the reward AND KEEPS THE TURN-IN ITEMS, repeatably:
        # the module's own rule ("an incomplete group refuses every
        # column in it") broken by the module, in the one direction it
        # never looked.  A transaction is payable when EVERY member of it
        # can be honoured, and a take that no-ops is a member that
        # cannot.
        blocking = tuple(sorted({member.api_name
                                 for member in group.members
                                 if not _default_api_is_real(member.api_name)}))
        states.append(GroupState(group, exercised, blocking))
    return tuple(states)


#: What a caller names as the running Lua entry point when it does not
#: know which one is running.  EMPTY STRING, not ``None``, for both
#: arguments and for :attr:`lua_api.quest.QuestContext.entry_point`, so
#: there is exactly one spelling of "unknown" in the package and a reader
#: cannot invent a second.
#:
#: UNKNOWN IS FAIL-CLOSED, and this is the whole safety of the scoping
#: below.  An unknown entry point refuses EVERY unpayable group the row
#: has -- byte for byte the behaviour this module had before entry points
#: were scoped at all.  The tempting alternative (unknown -> scope to
#: nothing -> refuse nothing) turns every caller that forgets to say which
#: entry point it is running into a caller that silently disarms the
#: half-transaction gate, which is the state ``COO-DECISION 20260908_0242``
#: item 4 forbids outright.  A gate that opens when you forget to address
#: it is not a gate.
UNKNOWN_ENTRY_POINT = ""


def unpayable_group_for(quest_id: int, column: str,
                        entry_point: str = UNKNOWN_ENTRY_POINT
                        ) -> Optional[GroupState]:
    """The group that refuses ``column`` for this row, or ``None``.

    ``column`` is a SHIPPED column name (``n_VARI_4``, ``n_REWARD_ITEM1``),
    because that is the one spelling both sides of a group share -- or, for
    a member that reads no cell at all, the qualified API name
    (``Quest.AddCriteriaCash``).  A column-less member has nothing else to
    be addressed by, and leaving it unaddressable is what pf-adversary D1
    measured as a 15,000-per-run gift.

    ``entry_point`` is the Lua function the host is CURRENTLY RUNNING
    (``Report_Run``, ``Accept_Check``, ...), or :data:`UNKNOWN_ENTRY_POINT`.
    Naming it scopes the refusal to the group that entry point OWNS; not
    naming it refuses conservatively, as before.  This is pf-adversary D8
    of round ``5a3x47``, and the reason it is a defect rather than an
    over-cautious nicety:

    A group is a fact about ONE entry point -- that is its definition and
    its mirror key (``script``, ``group``).  The refusal, however, was
    delivered through ``Quest.VarN``, keyed only on ``(quest_id, column)``,
    so a decision taken about ``Report_Run`` was ALSO enforced in
    ``Accept_Run``, ``Delete_Run`` and every ``*_Check`` of the same file:
    87 of the 88 item take-cell CALL SITES are read in some other
    top-level function of their own script (168 members over those 88
    sites, since a ``RemoveItem`` site carries an id cell and a count cell
    -- pf-adversary D5 of round ``0ldyk7``, correcting three places where
    this repository called the 88 a member count).  Those readers were
    handed :data:`REFUSED_CELL` for a transaction they are not part of.

    WHAT SCOPING DOES NOT REACH, corrected here because an earlier draft of
    this very docstring said the opposite (pf-adversary D4, same round):
    the ``Player.GetCash() >= Quest.Var2`` guard at
    ``q_boat_health.lua:18`` lives INSIDE ``Accept_Run``, which is the
    entry point that OWNS that script's only group, so scoping does not
    free that cell and never will.  What saves that guard is the other
    half -- :func:`unpayable_group_of_entry_point`, which stops
    ``Accept_Run`` before line 15, so the guard is never evaluated at all.
    (Its cell is 100, the shipped repair price; the 15,000 an earlier draft
    named here belongs to ``Q_CLASS``'s ``n_VARI_4``, a different script.)
    """
    for state in group_state(quest_id):
        if state.payable:
            continue
        if entry_point and state.group.group != entry_point:
            # Someone else's transaction.  Its refusal is not this entry
            # point's business, and imposing it is D8.
            continue
        if column in state.columns():
            return state
        for member in state.group.side(GIVE):
            if member.column == NO_COLUMN and member.api_name == column:
                return state
    return None


def unpayable_group_of_entry_point(quest_id: int,
                                   entry_point: str) -> Optional[GroupState]:
    """The unpayable group ``entry_point`` OWNS for this row, or ``None``.

    The companion of :func:`unpayable_group_for`, and the half that makes
    scoping safe rather than a regression.  Scoping alone lets a
    ``Report_Check`` read its real cells and answer "yes, you may report"
    to a player who genuinely holds the items -- and then ``Report_Run``
    refuses every cell of its own group while ``Quest.SetFlag`` (REAL)
    still marks the quest done: the flag moves, nothing is taken, nothing
    is paid, and the quest is burned.  That is worse than today, where the
    quest is merely unreportable.

    So the owning entry point must be refused AS A WHOLE, before its first
    statement runs, rather than cell by cell from inside it -- see
    ``script_host.ScriptHost.call`` and :class:`script_host.EntryPointRefused`.
    Refusing before the entry point starts is the difference between this
    and the ``nil`` cell pf-adversary D3 measured, which raised at
    ``q_gender_equip1.lua:25`` AFTER a real ``Quest.SetFlag(Quest.Active)``
    and BEFORE four real ``Player.MobAppear`` writes: a half-executed entry
    point.  Nothing runs here, so nothing can half-run.

    ``UNKNOWN_ENTRY_POINT`` owns nothing and refuses nothing: an unknown
    entry point is still gated cell by cell by
    :func:`unpayable_group_for`, which is fail-closed for it.  Refusing a
    call whose name we do not know would refuse every call in the corpus.
    """
    if not entry_point:
        return None
    for state in group_state(quest_id):
        if not state.payable and state.group.group == entry_point:
            return state
    return None


def reward_cell(quest_id: int, lua_name: str,
                entry_point: str = UNKNOWN_ENTRY_POINT
                ) -> Tuple[Optional[int], Optional[str]]:
    """``(value, None)`` or ``(None, reason)`` for one ``Quest.Reward*``.

    Never raises for game data.  A missing/corrupt mirror still raises
    :class:`quest_criteria.QuestCriteriaError` -- that is a fault of THIS
    repository, which ``script_host`` reports as ``LUA_HOST`` against us
    rather than as ``LUA_SCRIPT`` against whichever quest happened to run.
    """
    source = _LUA_NAME_TO_SOURCE.get(lua_name)
    if source is None:
        raise ValueError("%r is not a Quest.Reward* name" % (lua_name,))
    if quest_id == UNBOUND_QUEST_ID:
        return None, REFUSE_NO_QUEST_BOUND
    cells = load_rewards().get(quest_id)
    if cells is None:
        return None, REFUSE_NO_QUEST_ROW
    if unpayable_group_for(quest_id, source, entry_point) is not None:
        return None, REFUSE_GROUP_UNPAYABLE
    return cells[SOURCE_COLUMNS.index(source)], None


def lua_name_of(name) -> Optional[str]:
    """``name`` if it is a ``Quest.Reward*`` this module answers, else None.

    Written to survive an unhashable key from Lua for the same reason
    :func:`lua_api.quest._var_index_of` is: an unhashable namespace read
    must not become a ``TypeError`` inside the host.
    """
    try:
        return name if name in _LUA_NAME_TO_SOURCE else None
    except TypeError:  # pragma: no cover - unhashable key from Lua
        return None


def log_reward(log: Callable[[str], None], quest_id: int, lua_name: str,
               value: Optional[int], reason: Optional[str],
               state: Optional[GroupState] = None) -> None:
    """One line per resolved or refused ``Quest.Reward*``.

    The refusal names the group, the entry point and the API that is not
    real, because the reader of that line is the person who has to decide
    whether to go and implement it.
    """
    if reason is None:
        log("LUA_QUEST_REWARD Quest.%s quest=%d value=%d"
            % (lua_name, quest_id, value))
        return
    if state is None:
        log("LUA_QUEST_REWARD_BAD_VALUE Quest.%s quest=%d refused=%s"
            % (lua_name, quest_id, reason))
        return
    log("LUA_QUEST_REWARD_BAD_VALUE Quest.%s quest=%d refused=%s group=%s.%s "
        "blocked_on=%s" % (lua_name, quest_id, reason, state.group.script,
                           state.group.group, ",".join(state.blocking)))


def log_group_refusal(log: Callable[[str], None], quest_id: int, column: str,
                      state: GroupState) -> None:
    """The take side's own line: what was NOT taken, and why.

    A separate token from the reward one because it answers a different
    question -- "why did this quest not charge me" -- and because the
    money side is the half a player notices.
    """
    log("LUA_QUEST_GROUP_REFUSED %s quest=%d group=%s.%s blocked_on=%s "
        "call_site=%s" % (column, quest_id, state.group.script,
                          state.group.group, ",".join(state.blocking),
                          ",".join(member.call_site
                                   for member in state.group.side(GIVE))))


def resolve_for_namespace(log: Callable[[str], None], quest_id: int,
                          lua_name: str, stub_default,
                          said: Optional[set] = None,
                          entry_point: str = UNKNOWN_ENTRY_POINT):
    """What ``Quest.RewardItem1`` hands the script: the value, or the stub.

    ``said`` is the caller's own set of what has already been logged for
    this namespace, the same contract
    :func:`lua_api.quest_vars.resolve_for_namespace` takes: within one
    namespace the quest binding never changes, so each distinct fact is
    stated once instead of once per read.

    ``entry_point`` is NOT part of ``said``'s key on purpose: the entry
    point changes inside one namespace (a dispatcher calls ``Accept_Run``
    and later ``Report_Run`` on the same host), but each distinct
    ``(reason, lua_name)`` is still worth saying once per namespace, and
    keying the set on the entry point would restate the same refusal for
    every entry point the host runs.
    """
    value, reason = reward_cell(quest_id, lua_name, entry_point)
    state = None
    if reason == REFUSE_GROUP_UNPAYABLE:
        state = unpayable_group_for(quest_id, _LUA_NAME_TO_SOURCE[lua_name],
                                    entry_point)
    if said is None:
        log_reward(log, quest_id, lua_name, value, reason, state)
        return value if reason is None else stub_default
    key = reason if reason in REPORT_ONCE_REASONS else (reason, lua_name)
    if key not in said:
        said.add(key)
        log_reward(log, quest_id, lua_name, value, reason, state)
    return value if reason is None else stub_default



def var_column(var_index: int) -> str:
    """The shipped column name a ``Quest.VarN`` reads.

    The one spelling a group table can use for both sides, so the take
    member of a group and the ``VarN`` the namespace is being asked for
    are compared as the same string rather than through a second rule.
    """
    return "n_VARI_%d" % var_index


def resolve_var_for_namespace(log: Callable[[str], None], quest_id: int,
                              var_index: int, stub_default,
                              said: Optional[set] = None,
                              entry_point: str = UNKNOWN_ENTRY_POINT):
    """``Quest.VarN`` WITH the half-transaction gate in front of it.

    THE ONLY PATH THE NAMESPACE TAKES, on purpose.  The gate cannot live
    inside :func:`lua_api.quest_vars.quest_var` -- that module is the one
    this one is built on, and a module may not consult the module built on
    top of it -- and it must not be something a caller can forget, because
    forgetting it is exactly the state COO's decision forbids: the take
    side runs and the give side does not.  So the namespace asks HERE, the
    gate answers first, and the ungated join is still reachable (and still
    tested) as ``quest_vars.quest_var`` for a reader who wants the raw
    table answer.
    """
    state = unpayable_group_for(quest_id, var_column(var_index), entry_point)
    if state is None:
        return quest_vars.resolve_for_namespace(
            log, quest_id, var_index, stub_default, said)
    key = (REFUSE_GROUP_UNPAYABLE, var_index)
    if said is None or key not in said:
        if said is not None:
            said.add(key)
        log_group_refusal(log, quest_id, var_column(var_index), state)
    # NOT ``stub_default``.  See :data:`REFUSED_CELL`: handing a refused
    # charge cell back as ``0`` is what let a REAL ``CheckItemNum`` read
    # it as "holds at least zero of item zero" and answer True.
    return REFUSED_CELL
