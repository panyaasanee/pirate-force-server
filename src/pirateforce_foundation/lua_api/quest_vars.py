"""``Quest.Var1``..``Quest.Var20``: the quest row's own parameters.

LANE-Q.  This is the layer COO-DECISION ``20260908_0042`` (item 5, option
"kho") named as this lane's own: the one that joins ``Quest.VarN`` to
``QUESTDATA_TH__QUEST.tsv``.  Until this module existed every ``VarN`` read
fell through ``RealQuestNamespace.__getitem__``'s last line and came back
:data:`lua_api.quest.STUB_DEFAULT` (0), which is why every corpus call site
that spends a ``VarN`` -- ``Player.AddCash(Quest.Var4)``,
``Quest.MobKillCount(Quest.Var2, Quest.Var3)`` -- was dead code no matter
how real the API around it got.  MEASURED, because the first draft of this
sentence quoted the wrong number (pf-adversary D10, round `joa0u6`): the
corpus takes a ``Quest.VarN`` as an argument at **5,623** call sites.
(12,653 is the whole corpus's api-call count from
``pf_bridge/gamedata/_LUA_meta.json`` -- a different quantity entirely.)

TWO FILES, TWO DIFFERENT KINDS OF FACT, DELIBERATELY NOT MERGED
---------------------------------------------------------------
``quest_var_rows.tsv``       the 20 cells of each of the 1544 quest rows,
                             copied VERBATIM as the unsigned 32-bit
                             integers the shipped table stores.  Data.
``quest_var_signedness.tsv`` which (script, column) pairs hold a SIGNED
                             quantity, with the call site that proves it.
                             A reading of that data, and the only place
                             this repository is allowed to say so.

COO's words: "song mop = fai taarang nai tree + test thi aan taarang nan ...
haam son nai fangkchan plaeng" -- the rule may not be buried inside a
conversion function.  So :func:`quest_var` reads the table and does what it
says; it holds no list of its own.  Deleting ``quest_var_signedness.tsv``
does not change what this module believes, it makes every wrapped cell a
refusal -- the pure option "ko" the same decision keeps as the rollback.

WHY A CELL IS EVER "WRAPPED" (the bug that produced this file)
-------------------------------------------------------------
``QUESTDATA_TH__QUEST.tsv`` stores every ``n_VARI_k`` as an unsigned 32-bit
decimal, so a designer's ``-15000`` is on disk as ``4294952296``.  Round
``2euu94`` nearly paid that out as a 4.29-billion credit; the i32 ceiling in
``lua_api.player._coerce_signed_int`` stopped it, at the price of refusing
the five real charges too.  This module is what makes those five work.

HOW THE SIGNEDNESS TABLE WAS DERIVED (not guessed -- re-derivable)
-----------------------------------------------------------------
``tools/pf_regen_lua_quest_vars.py`` scans all 1544 x 20 = 30,880 cells for
values at or above ``2**31``, groups the hits by (``s_LUASCRIPT``, column),
and prints the ``.lua`` line that reads that ``VarN``.  Five pairs, and the
corpus answers each one in a single line of source:

    Q_CLASS       n_VARI_4   q_class.lua:60        Player.AddCash(Quest.Var4)
    Q_GUILD_BOSS2 n_VARI_8   q_guild_boss2.lua:59  Player.AddCash(Quest.Var8)
    Q_KILL_SKXYZ  n_VARI_10  q_kill_skxyz.lua:85   Player.CastSkillXYZ(...,Var10,..)
    Q_KILL_SKXYZ  n_VARI_11  q_kill_skxyz.lua:85   (Y)
    Q_KILL_SKXYZ  n_VARI_12  q_kill_skxyz.lua:85   (Z)

Two money columns and three coordinates -- exactly the two kinds COO's
decision predicted, and no id column among them, which is the negative
result that matters: ids never wrap because ids are never negative.

THE GAP IS THE EVIDENCE, AND A TEST PINS IT.  The largest ordinary value in
all 30,880 cells is 2,608,007 (``0x27CB87``); the smallest wrapped one is
``0xFFFF3CB0``.  Nothing at all lies between them.  So "at or above
``2**31`` means a negative was stored here" is not a threshold this lane
picked out of the air -- there is no cell anywhere near it to misclassify,
and :mod:`tests.test_script_lua_quest_vars` fails the day one appears.

WHAT A SIGNED COLUMN AND AN UNSIGNED ONE EACH DO WITH A WRAPPED CELL
--------------------------------------------------------------------
Signed:    two's complement, ``raw - 2**32``, so ``4294952296 -> -15000``.
           Plain i32 decoding, NOT the ``2**31`` scan threshold above; the
           scan is how candidates were FOUND, the decode is what a column
           declared signed MEANS.  They are separate constants on purpose.
Unsigned:  REFUSED, out loud (``LUA_QUEST_VAR_BAD_VALUE`` ... ``reason=
           unsigned_column_holds_wrapped_value``), value 0 to the script.
           A column nobody has read a call site for is a column this lane
           has no opinion about, and inventing one silently is how the
           4.29-billion credit happened in the first place.

WHY THE KEY IS (SCRIPT, COLUMN) AND NOT (QUEST ID, COLUMN)
----------------------------------------------------------
The column's MEANING belongs to the code that reads it, and that is the
script: ``quest_criteria``'s own docstring already records that 1544 rows
name 209 distinct scripts and ``Q_CON1`` alone is named by 160 of them.
Keying by quest id would restate one fact 160 times and let 159 copies
drift.  The quest id -> script direction is the one that is a function, and
it is read from :func:`lua_api.quest_criteria.script_for_quest` rather than
mirrored a second time here -- one mirror, one answer, no third artifact to
disagree with the other two (the ``api_spec.tsv`` lesson, pf-adversary F2 of
round ``5qtaqy``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from . import quest_criteria, vendored
from .quest_criteria import QuestCriteriaError

#: How many ``VarN`` names a quest row has.  Fixed by the shipped table's
#: own column list (``n_VARI_1`` .. ``n_VARI_20``), not by this lane.
VAR_COUNT = 20

#: Column headers of the verbatim row mirror, in order.
ROW_COLUMNS: Tuple[str, ...] = ("quest_id",) + tuple(
    "var%d" % index for index in range(1, VAR_COUNT + 1))

#: Column headers of the signedness table, in order.  ``call_site`` and
#: ``evidence_*`` are provenance, required by COO's decision ("thuk thaeo mee
#: provenance"): every row must say which line of which script proves it and
#: which table rows exhibit the wrapped value.
SIGNEDNESS_COLUMNS: Tuple[str, ...] = (
    "script", "var_index", "kind", "api_name", "call_site",
    "evidence_quest_ids", "evidence_raw",
)

#: The two kinds of signed quantity the corpus actually exhibits.  A closed
#: set: a row with any other kind is a corrupt mirror, not a new feature,
#: because adding a kind means adding a call site that reads it.
KIND_MONEY = "signed_money"
KIND_COORDINATE = "signed_coordinate"
KNOWN_KINDS = frozenset({KIND_MONEY, KIND_COORDINATE})

#: Two's complement decoding of a 32-bit cell.  ``_WRAP`` is the modulus,
#: ``_NEGATIVE_AT`` the first value whose i32 reading is negative.
_WRAP = 1 << 32
_NEGATIVE_AT = 1 << 31

#: The scan threshold ``tools/pf_regen_lua_quest_vars.py`` uses to FIND
#: candidate signed columns.  Equal to :data:`_NEGATIVE_AT` today and kept
#: as its own name anyway: one is a decode rule that follows from the width
#: of the field, the other is a heuristic over one shipped table, and the
#: day they need to differ nobody should have to work out which uses of the
#: constant meant which.
WRAPPED_SCAN_THRESHOLD = _NEGATIVE_AT

#: The largest ordinary (non-wrapped) cell in the shipped table, and the
#: smallest wrapped one.  Pinned here, asserted in the tests: the distance
#: between them is the whole argument that the scan cannot misclassify.
LARGEST_ORDINARY_CELL = 2608007
SMALLEST_WRAPPED_CELL = 4294917296

_HERE = Path(__file__).resolve().parent
_ROWS_PATH = _HERE / "quest_var_rows.tsv"
_SIGNEDNESS_PATH = _HERE / "quest_var_signedness.tsv"

_ROWS_CACHE: Optional[Dict[int, Tuple[int, ...]]] = None
_SIGNEDNESS_CACHE: Optional[Dict[Tuple[str, int], "SignedColumn"]] = None


class SignedColumn:
    """One row of ``quest_var_signedness.tsv``.

    Deliberately carries its provenance into memory instead of dropping it
    at parse time: the refusal and success log lines below quote
    ``call_site``, so a reader who sees ``Quest.Var4`` resolve to -15000 in
    a console log can open the exact line that says it should.
    """

    __slots__ = ("script", "var_index", "kind", "api_name", "call_site",
                 "evidence_quest_ids", "evidence_raw")

    def __init__(self, script: str, var_index: int, kind: str, api_name: str,
                 call_site: str, evidence_quest_ids: Tuple[int, ...],
                 evidence_raw: Tuple[int, ...]):
        self.script = script
        self.var_index = var_index
        self.kind = kind
        self.api_name = api_name
        self.call_site = call_site
        self.evidence_quest_ids = evidence_quest_ids
        self.evidence_raw = evidence_raw

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return ("SignedColumn(%s, var%d, %s, %s)"
                % (self.script, self.var_index, self.kind, self.call_site))


def _read_mirror(path: Path, columns: Tuple[str, ...]) -> list:
    """Parse one vendored mirror into a list of field tuples.

    THE SAME PARSER ``quest_criteria`` USES, called rather than copied.
    Both files are the same format, written by the same kind of tool, with
    the same ``# body_sha256:`` contract; a second implementation here is a
    second thing to get wrong, and this lane has already paid for one
    (pf-adversary D6, round ``5qtaqy``: a duplicated log line whose two
    copies disagreed).  Importing a private name across modules of the SAME
    package is the smaller cost.
    """
    return quest_criteria._read_mirror(path, columns)  # noqa: SLF001


def _parse_int(path: Path, name: str, raw: str) -> int:
    return quest_criteria._parse_int(path, name, raw)  # noqa: SLF001


def _parse_id_list(path: Path, name: str, raw: str) -> Tuple[int, ...]:
    """A comma-separated provenance list, refused rather than defaulted.

    Empty is a corrupt row, not "no evidence": a signedness row with no
    evidence is exactly the guess this table exists to make impossible.
    """
    text = raw.strip()
    if not text:
        raise QuestCriteriaError(
            "%s: %s is empty; a signedness row with no evidence is a guess"
            % (path, name))
    return tuple(_parse_int(path, name, part) for part in text.split(","))


def load_rows() -> Dict[int, Tuple[int, ...]]:
    """``{quest_id: (var1, ..., var20)}`` of RAW cells, parsed once.

    Raw means raw: no unwrapping happens here, so a reader of this mapping
    sees exactly what the shipped table holds.  The read goes through
    ``vendored.read_mirror`` for the same reason every other mirror in this
    package does -- a broken copy is COUNTED under its own key at call time,
    where a construction-time guard is blind (pf-adversary D3/D6, ``95aw54``).
    """
    global _ROWS_CACHE
    if _ROWS_CACHE is None:
        _ROWS_CACHE = vendored.read_mirror(
            vendored.MIRROR_QUEST_VAR_ROWS, _parse_rows)
    return _ROWS_CACHE


def _parse_rows() -> Dict[int, Tuple[int, ...]]:
    table: Dict[int, Tuple[int, ...]] = {}
    for fields in _read_mirror(_ROWS_PATH, ROW_COLUMNS):
        quest_id = _parse_int(_ROWS_PATH, "quest_id", fields[0])
        if quest_id in table:
            raise QuestCriteriaError("%s: duplicate quest_id %d"
                                     % (_ROWS_PATH, quest_id))
        cells = []
        for index in range(1, VAR_COUNT + 1):
            value = _parse_int(_ROWS_PATH, "var%d" % index, fields[index])
            if value < 0 or value >= _WRAP:
                raise QuestCriteriaError(
                    "%s: quest %d var%d is %d, outside the unsigned 32-bit "
                    "range the source stores" % (_ROWS_PATH, quest_id, index,
                                                 value))
            cells.append(value)
        table[quest_id] = tuple(cells)
    return table


def load_signedness() -> Dict[Tuple[str, int], SignedColumn]:
    """``{(script_lowercased, var_index): SignedColumn}``, parsed once.

    Script names are folded to lower case on the way in, the same fold
    :func:`lua_api.quest_criteria.quests_for_script` already uses, so a
    mirror written ``Q_CLASS`` and a caller holding ``q_class`` cannot
    silently miss each other.
    """
    global _SIGNEDNESS_CACHE
    if _SIGNEDNESS_CACHE is None:
        _SIGNEDNESS_CACHE = vendored.read_mirror(
            vendored.MIRROR_QUEST_VAR_SIGNEDNESS, _parse_signedness)
    return _SIGNEDNESS_CACHE


def _parse_signedness() -> Dict[Tuple[str, int], SignedColumn]:
    table: Dict[Tuple[str, int], SignedColumn] = {}
    for fields in _read_mirror(_SIGNEDNESS_PATH, SIGNEDNESS_COLUMNS):
        script = fields[0].strip()
        if not script:
            raise QuestCriteriaError(
                "%s: a signedness row has an empty script name"
                % _SIGNEDNESS_PATH)
        var_index = _parse_int(_SIGNEDNESS_PATH, "var_index", fields[1])
        if not 1 <= var_index <= VAR_COUNT:
            raise QuestCriteriaError(
                "%s: var_index %d is outside 1..%d"
                % (_SIGNEDNESS_PATH, var_index, VAR_COUNT))
        kind = fields[2].strip()
        if kind not in KNOWN_KINDS:
            raise QuestCriteriaError(
                "%s: unknown kind %r (known: %s)"
                % (_SIGNEDNESS_PATH, kind, ", ".join(sorted(KNOWN_KINDS))))
        call_site = fields[4].strip()
        if ":" not in call_site:
            raise QuestCriteriaError(
                "%s: call_site %r is not a file:line" % (_SIGNEDNESS_PATH,
                                                         call_site))
        key = (script.lower(), var_index)
        if key in table:
            raise QuestCriteriaError(
                "%s: duplicate row for %s var%d"
                % (_SIGNEDNESS_PATH, script, var_index))
        table[key] = SignedColumn(
            script=script,
            var_index=var_index,
            kind=kind,
            api_name=fields[3].strip(),
            call_site=call_site,
            evidence_quest_ids=_parse_id_list(
                _SIGNEDNESS_PATH, "evidence_quest_ids", fields[5]),
            evidence_raw=_parse_id_list(
                _SIGNEDNESS_PATH, "evidence_raw", fields[6]),
        )
    return table


def reset_caches() -> None:
    """Drop both parsed mirrors.  For tests that point the module at a
    temporary file; production never calls it."""
    global _ROWS_CACHE, _SIGNEDNESS_CACHE
    _ROWS_CACHE = None
    _SIGNEDNESS_CACHE = None


def signed_column(script: Optional[str], var_index: int) -> Optional[SignedColumn]:
    """The signedness row for this (script, column), or ``None``.

    ``None`` for an unknown script is deliberate and is NOT an error: 204 of
    the 209 scripts have no signed column, and asking about one is the
    ordinary case.
    """
    if script is None:
        return None
    return load_signedness().get((script.strip().lower(), var_index))


def is_wrapped(raw: int) -> bool:
    """Does this raw cell hold a value whose i32 reading is negative."""
    return raw >= _NEGATIVE_AT


def unwrap(raw: int) -> int:
    """Two's complement i32 reading of a raw unsigned cell."""
    return raw - _WRAP if raw >= _NEGATIVE_AT else raw


#: The refusal reasons :func:`quest_var` can return, a CLOSED set so a
#: caller (and a test) can tell them apart by name instead of by log text.
#: Every one of them is an ORDINARY outcome of running the corpus, not an
#: error: a script asking for a var of a quest this server has no row for is
#: what happens the moment anything dispatches an unknown quest id.
REFUSE_NO_QUEST_BOUND = "no_quest_bound_to_this_script"
REFUSE_NO_QUEST_ROW = "no_row_for_quest_id"
REFUSE_NO_SCRIPT = "quest_row_names_no_script"
REFUSE_WRAPPED_UNSIGNED = "unsigned_column_holds_wrapped_value"
REFUSAL_REASONS = frozenset({
    REFUSE_NO_QUEST_BOUND, REFUSE_NO_QUEST_ROW, REFUSE_NO_SCRIPT,
    REFUSE_WRAPPED_UNSIGNED,
})

#: The quest id :data:`lua_api.quest.DEFAULT_CONTEXT` carries, and the one
#: id no shipped row can ever have (the table's lowest is 12).  A script
#: running under it is not bound to a quest at all -- the corpus sweep, a
#: spike, a test that did not care -- so its ``VarN`` reads are not a data
#: fault and must not be reported as one.
UNBOUND_QUEST_ID = 0

#: ``REFUSE_NO_QUEST_BOUND`` is a property of the whole RUN rather than of
#: the column asked for, so it is said once per namespace under ANY column
#: name; every other outcome is said once per column.  Both are the same
#: rule underneath: within one namespace the quest binding never changes,
#: so ``VarN`` has ONE answer for the whole run and repeating it carries no
#: information at all.
#:
#: WHY THIS IS NOT A "never silent" DODGE, measured (pf-adversary D9, round
#: `joa0u6`): dispatching all 1544 quests logged **35,078** lines / 1.5 MiB
#: of ``LUA_QUEST_VAR`` -- a median of 20 per quest, 96 at the worst -- and
#: every line after the first per column was a verbatim duplicate of one
#: above it.  Saying each distinct fact once caps a script at 20 lines and
#: loses nothing a reader could have used.  This module's own docstring made
#: that argument for the refusal case and then did not apply it to the
#: success case; it does now.
REPORT_ONCE_REASONS = frozenset({REFUSE_NO_QUEST_BOUND})


def quest_var(quest_id: int, var_index: int) -> Tuple[Optional[int], Optional[str]]:
    """``(value, None)`` or ``(None, reason)`` -- never raises for game data.

    The whole join, in one function that holds no policy of its own:

      1. the quest row (verbatim mirror),
      2. the script that row dispatches (``quest_criteria``, one mirror),
      3. whether THAT script reads THIS column as signed (the table),
      4. two's complement, or a refusal by name.

    A missing/corrupt mirror still raises :class:`quest_criteria.
    QuestCriteriaError` -- that is a fault of THIS repository, and
    ``script_host`` must report it as ``LUA_HOST`` against us rather than as
    ``LUA_SCRIPT`` against whichever quest file happened to be running
    (pf-adversary D11, same posture as :func:`lua_api.quest._log_criteria`).
    """
    if not 1 <= var_index <= VAR_COUNT:
        raise ValueError("var_index %r is outside 1..%d"
                         % (var_index, VAR_COUNT))
    if quest_id == UNBOUND_QUEST_ID:
        return None, REFUSE_NO_QUEST_BOUND
    cells = load_rows().get(quest_id)
    if cells is None:
        return None, REFUSE_NO_QUEST_ROW
    raw = cells[var_index - 1]
    script = quest_criteria.script_for_quest(quest_id)
    if script is None:
        # A row in one mirror and not the other.  Both are generated from
        # the same source table by the same tool, so this cannot happen
        # without a hand-edit -- and a hand-edit is exactly when a silent
        # 0 would be worst.
        return None, REFUSE_NO_SCRIPT
    if not is_wrapped(raw):
        return raw, None
    column = signed_column(script, var_index)
    if column is None:
        return None, REFUSE_WRAPPED_UNSIGNED
    return unwrap(raw), None


def log_var(log: Callable[[str], None], quest_id: int, var_index: int,
            value: Optional[int], reason: Optional[str],
            raw: Optional[int] = None, once: bool = False) -> None:
    """One line per resolved or refused ``VarN``.

    Two distinct tokens, because they are read by different people: a
    resolved var is ``LUA_QUEST_VAR``, a refused one is
    ``LUA_QUEST_VAR_BAD_VALUE``, matching the ``LUA_QUEST_REAL`` /
    ``LUA_QUEST_BAD_VALUE`` pair :mod:`lua_api.quest` already established.
    Both name the quest and the column, so a grep can count how often a
    given quest row is being read without parsing prose.
    """
    if reason is not None:
        log("LUA_QUEST_VAR_BAD_VALUE Quest.Var%d quest=%d raw=%s refused=%s%s"
            % (var_index, quest_id, "?" if raw is None else raw, reason,
               " (said once per script run)" if once else ""))
        return
    log("LUA_QUEST_VAR Quest.Var%d quest=%d value=%d" % (var_index, quest_id, value))


def resolve_for_namespace(log: Callable[[str], None], quest_id: int,
                          var_index: int, stub_default: Any,
                          said: Optional[set] = None) -> Any:
    """What ``Quest.VarN`` hands the script: the value, or ``stub_default``.

    ``stub_default`` is passed in rather than imported so this module does
    not import :mod:`lua_api.quest` back (that module imports this one).

    ``said`` is the caller's own mutable set of what has already been
    logged for this namespace.  Pass one and each distinct fact is stated
    once (see :data:`REPORT_ONCE_REASONS`); omit it and every read logs,
    which is what a caller resolving a single var wants.
    """
    if quest_id == UNBOUND_QUEST_ID:
        cells = None
    else:
        cells = load_rows().get(quest_id)
    raw = None if cells is None else cells[var_index - 1]
    value, reason = quest_var(quest_id, var_index)
    if said is None:
        log_var(log, quest_id, var_index, value, reason, raw)
        return value if reason is None else stub_default
    key = reason if reason in REPORT_ONCE_REASONS else (reason, var_index)
    if key not in said:
        said.add(key)
        log_var(log, quest_id, var_index, value, reason, raw, once=True)
    return value if reason is None else stub_default
