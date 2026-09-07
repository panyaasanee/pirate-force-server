"""LANE-Q: the READ half of the quest reward-criteria seam.

WHAT THIS ANSWERS.  Six of the 25 ``Quest.*`` names in the corpus grant a
reward and take NO ARGUMENTS (``api_spec.tsv``, arity_min == arity_max == 0
for all six): ``AddCriteriaExp`` (166 calls / 166 files),
``AddCriteriaSkillPoint`` (166), ``AddCriteriaCash`` (165),
``AddLvCriteriaExp`` (59), ``AddLvCriteriaSkillPoint`` (59),
``AddLvCriteriaCash`` (58).  Zero arguments means the AMOUNT is not in the
script -- it is in the game's own tables -- so "how much" is a pure read
that needs no other lane and no database column.  That read is this module.
The GRANT (moving the number onto a character) is the write half and is
still stubbed: it needs the per-character exp/level columns LANE-Q asked
LANE-DB for on 2026-09-07T06:06, per COO-DECISION 2026-09-07T05:46 ("Q owns
the read half through a Protocol; the write half waits for real columns --
do not keep a competing in-memory ledger, not even 'temporarily'").

WHERE THE NUMBER ACTUALLY COMES FROM -- measured, and it is NOT what
LANE-Q's own previous round wrote down.  Round ``02mkqc``'s letter named
``QUESTDATA_TH__QUEST.tsv``'s ``n_LEVEL_EXP`` and ``f_EXP`` as the two
candidate columns holding the amount.  Reading the actual values disproves
both readings:

  * ``f_EXP`` holds 12 distinct values across all 1544 quest rows and
    every one of them is a small ratio -- 0.0, 0.1, 0.25, 0.3, 0.5, 0.85,
    1.0, 1.4, 1.5, 2.0, 3.0, 5.0 (stored float32-widened, e.g. literally
    ``0.10000000149011612`` on disk).  Those are MULTIPLIERS, not exp
    amounts; no quest in this game awards 1.5 experience points.
    (Round ``xlk7hl``'s docstring said 11 and omitted 0.85; recounted from
    the mirror this round -- 12 distinct strings over 4632 cells.)
  * ``n_LEVEL_EXP`` runs 1..120 and EVERY ONE of the 1544 rows resolves to
    a row of ``CONSTDATA_TH__STANDARD_QUEST.tsv`` (0 orphans, measured).
    That is a LEVEL INDEX, not an amount.

``CONSTDATA_TH__STANDARD_QUEST.tsv`` is the amount table: 255 rows keyed by
level 1..255, three columns ``n_QUEST_CASH`` / ``n_QUEST_EXP`` /
``n_QUEST_SP``, rising monotonically with level (level 1 -> 90 exp; level
100 -> 100520).  "Criteria" in the API names is this standard-per-level
quest reward curve.  So the amount is::

    curve[level].<kind> * quest_row.<kind>_multiplier

which is why the six functions need no arguments, and why the three
"kinds" come in two triples of three names each: one triple per level
source, three columns per triple.

WHICH LEVEL, THOUGH -- the one thing here that is an ASSUMPTION, and it is
labelled as one.  The 166 files calling the plain ``AddCriteria*`` triple
and the 59 calling the ``AddLvCriteria*`` triple are DISJOINT (measured:
0 overlap), and inside a file the three names of a triple always appear
together, so the discriminator is the prefix ``Lv`` and nothing else.
LANE-Q's reading is ``Lv`` = "the PLAYER's level", plain = "the level
written on the quest row".  Two independent measurements point that way:

  1. ``n_LEVEL_EXP`` differs from ``n_LEVEL_QUEST`` on 647 of the 1039
     rows whose script calls the plain triple (62%: actively tuned data)
     but on only 32 of the 174 rows behind the ``Lv`` triple (18%, and
     only 31 distinct values at all: the column reads as unused there).
  2. 53 of the 59 ``Lv``-triple files also call ``Quest.ReportDailyQuest``,
     against 5 of the 166 plain files.  A daily repeatable has to pay out
     against whoever is repeating it, not against a level frozen in a row.

Neither measurement is a proof, so this module does not pretend one.
:data:`LEVEL_SOURCE` records the mapping, tagged as a lane assumption
pending COO, and the ``Lv`` triple's resolver REFUSES (returns ``None``,
never a number) when the caller cannot supply a player level, rather than
falling back to the quest row's level and quietly paying the wrong amount.

WHAT THIS DOES NOT YET REACH, stated before anything else it claims.
Against the shipped corpus today EVERY one of the 225 criteria call sites
resolves ``refused=no_quest_row``, measured on real files, because nothing
supplies a quest id: these functions take no arguments precisely because
the ENGINE knows which quest instance dispatched the script, and this
server has no such dispatch, so ``quest.DEFAULT_CONTEXT`` is ``quest_id=0``
and the lowest id in the mirror is 12.  The read half is complete, tested
and inert until a dispatcher exists.  Relatedly, ``s_LUASCRIPT`` is
one-to-many (``q_con1`` is the script of 160 quest rows carrying 86
distinct ``(level, multiplier)`` pairs), so the amount can never be
resolved from the ``.lua`` file alone -- another way of saying the same
missing piece.

ONE MORE THING THE ASSUMPTION ABOVE SHOULD BE READ AGAINST:
``gamedata/PF_GAMEDATA_LUA_API.tsv`` records ``AddLvCriteriaExp`` as
``UNRESOLVED`` -- the one of the six names with no binding found in the
client at all -- and it is exactly the name whose level source is being
assumed here.  The other five carry a ``delegate_va``.

ROUNDING IS STILL NOT KNOWN, and it is not hidden.  ``curve * multiplier``
is not an integer for every row; whether the real client floors, rounds or
keeps a fraction is in no committed artifact.  COO-DECISION
``notes_to_chief/20260907_0845_COO-DECISION-q0742-lv-criteria-player-level-LANE-Q.md``
settled what THIS server does in the meantime -- FLOOR -- with two
conditions this module keeps: the un-rounded product stays on the result
(:attr:`CriteriaAmount.exact`, plus :attr:`CriteriaAmount.raw` for
provenance), and floor lives at ONE place (:data:`ROUNDING_MODE` /
:func:`round_amount`) so an RE answer changes a single line.  Nothing here
states floor as a fact about the client.

THE FLOOR HAS TO BE TAKEN OF THE RIGHT NUMBER, which is the part that was
actually wrong.  ``f_EXP`` is a float32 column, so the mirror faithfully
carries e.g. ``1.399999976158142`` -- one ULP BELOW the 1.4 the table
author wrote.  ``int(base * that)`` therefore floors to one LESS than the
intended reward whenever the true product is a whole number: measured on
the shipped mirrors, 14 of the 4632 plain-triple resolutions and 3632 of
the 1181160 ``(row, level)`` products a player-level triple can reach
(eight quests, 2170-2177; 16 cells carry 1.4 and 14 of them had a whole
number for a true product, which is where the lost unit shows).  ``0.1``/``0.3``/``0.85`` widen
UPWARD and so never lost a unit -- only ``1.4`` did, which is why the bug
was small enough to survive a round.  The fix is not to hand-edit the
mirror (a mirror that is not byte-equal to its source is not a mirror):
:func:`multiplier_decimal` recovers, at parse time, the shortest decimal
that round-trips through float32 to the same bits, and the product is
taken in :class:`decimal.Decimal`.  All 12 distinct values in the mirror
are exactly representable as float32 (measured), which is the evidence
this recovery is reading a float32 column and not inventing precision.

THE TWO VENDORED MIRRORS.  ``quest_criteria_curve.tsv`` and
``quest_criteria_rows.tsv`` are complete, ASCII, machine-regenerated copies
of the two source tables' reward-relevant columns, in the shape
``message_catalog.tsv`` already established for this package (COO-DECISION
2026-09-07T04:05): a vendored file with a ``tools/`` regenerator and a
digest of its own body, so the Windows gate -- which has no ``pf_bridge``
checkout at all -- can still check the copy is internally honest.  Corrupt
or missing mirrors raise :class:`QuestCriteriaError`, which
``script_host._host_side_error_types`` treats as OUR defect: it is logged
``LUA_HOST ... discovered_at=<file>``, never as ``LUA_SCRIPT <file> ERR``
blaming whichever quest script happened to be loading (pf-adversary D11).
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Dict, Optional

from .vendored import VendoredDataError

#: Column headers of the vendored curve mirror, in order.
CURVE_COLUMNS = ("level", "cash", "exp", "skill_point")

#: Column headers of the vendored per-quest mirror, in order.
ROW_COLUMNS = ("quest_id", "criteria_level",
               "cash_multiplier", "exp_multiplier", "sp_multiplier")

#: The three reward kinds, spelled the way the API names spell them.
KIND_EXP = "Exp"
KIND_CASH = "Cash"
KIND_SKILL_POINT = "SkillPoint"
KINDS = (KIND_EXP, KIND_CASH, KIND_SKILL_POINT)

#: Which curve column and which row multiplier each kind reads.
_KIND_FIELDS = {
    KIND_EXP: ("exp", "exp_multiplier"),
    KIND_CASH: ("cash", "cash_multiplier"),
    KIND_SKILL_POINT: ("skill_point", "sp_multiplier"),
}

#: Level source per API name.  ``"quest"`` = the level on the quest's own
#: row; ``"player"`` = the level of the character running the script.
#: [COO-ASSUMPTION 0845 - NOT A PROOF]: accepted by COO round ``0845`` in
#: ``notes_to_chief/20260907_0845_COO-DECISION-q0742-lv-criteria-player-``
#: ``level-LANE-Q.md`` on the two measurements in the module docstring,
#: which that letter itself calls weight and not proof.  The letter also
#: forbids ever falling back to the quest row's level when the player
#: level is unknown (see :data:`REFUSE_NO_PLAYER_LEVEL`), and names the RE
#: ticket that would retire this label as the thing that must answer it.
LEVEL_SOURCE_QUEST = "quest"
LEVEL_SOURCE_PLAYER = "player"
LEVEL_SOURCE: Dict[str, str] = {
    "AddCriteriaExp": LEVEL_SOURCE_QUEST,
    "AddCriteriaCash": LEVEL_SOURCE_QUEST,
    "AddCriteriaSkillPoint": LEVEL_SOURCE_QUEST,
    "AddLvCriteriaExp": LEVEL_SOURCE_PLAYER,
    "AddLvCriteriaCash": LEVEL_SOURCE_PLAYER,
    "AddLvCriteriaSkillPoint": LEVEL_SOURCE_PLAYER,
}

#: Which reward kind each API name pays out.
API_KIND: Dict[str, str] = {
    "AddCriteriaExp": KIND_EXP,
    "AddCriteriaCash": KIND_CASH,
    "AddCriteriaSkillPoint": KIND_SKILL_POINT,
    "AddLvCriteriaExp": KIND_EXP,
    "AddLvCriteriaCash": KIND_CASH,
    "AddLvCriteriaSkillPoint": KIND_SKILL_POINT,
}

#: Levels a caller may ask for.  Checked before the lookup for a PLAYER
#: level (a level outside this pair is a caller bug worth naming, not a
#: reward of nothing); the curve mirror is still the authority on which
#: levels actually have a row, and `resolve` returns None for the rest.
MIN_LEVEL = 1
MAX_LEVEL = 255

#: Refusal reasons.  A closed set, for the same reason
#: ``lua_api.message`` keeps one: a reason string built from runtime data
#: is an unbounded key (pf-adversary D7).
REFUSE_NO_QUEST_ROW = "no_quest_row"
REFUSE_NO_PLAYER_LEVEL = "player_level_unknown"
REFUSE_LEVEL_OUT_OF_RANGE = "level_out_of_range"
REFUSE_UNKNOWN_API = "unknown_api"
REFUSE_BAD_PLAYER_LEVEL = "bad_player_level"

BODY_DIGEST_PREFIX = "# body_sha256: "

#: How a fractional reward becomes an integer, in ONE place.  COO-DECISION
#: ``20260907_0845`` chose floor for now and said explicitly that no file
#: may write "the client floors" down as a fact: the RE ticket this lane
#: sends to LANE-K this round is what would turn this constant into a
#: measured one.  When that answer lands, change this line and
#: :func:`round_amount` -- nothing else in the tree decides rounding.
ROUNDING_MODE = ROUND_FLOOR

#: Widest float32 significand, i.e. how many decimal digits can ever be
#: needed to name a float32 exactly.  Used as the search ceiling in
#: :func:`multiplier_decimal`, never as a precision claim.
_FLOAT32_MAX_DIGITS = 17


def round_amount(exact: Decimal) -> int:
    """The single rounding point of the reward seam (:data:`ROUNDING_MODE`).

    Takes a :class:`~decimal.Decimal`, never a float: the whole reason
    this function exists is that flooring a float that is one ULP below
    its intended value silently pays one less (module docstring).
    """
    return int(exact.to_integral_value(rounding=ROUNDING_MODE))


def _float32_bits(value: float) -> bytes:
    """The 4 bytes ``value`` occupies as a float32, or raise for a float
    that has no float32 (an out-of-range multiplier is corrupt data)."""
    try:
        return struct.pack("<f", value)
    except (OverflowError, ValueError) as exc:
        raise QuestCriteriaError(
            "multiplier %r does not fit a float32 column" % (value,)) from exc


def is_exact_float32(value: float) -> bool:
    """True when ``value`` is exactly a widened float32.

    Every one of the 12 distinct multipliers in the shipped mirror answers
    True (measured); a False here means the source column is NOT the
    float32 this module reads it as, and :func:`multiplier_decimal` would
    be inventing precision rather than recovering it.
    """
    return struct.unpack("<f", _float32_bits(value))[0] == value


_MULTIPLIER_DECIMALS: Dict[float, Decimal] = {}


def multiplier_decimal(value: float) -> Decimal:
    """The shortest decimal that round-trips through float32 to ``value``.

    ``1.399999976158142`` -> ``Decimal("1.4")``: recovering what the table
    author typed, not rounding the number we were given.  A value that is
    not exactly a float32 is returned digit-for-digit instead (``repr``),
    because there is then nothing to recover and quietly shortening it
    would be the invention this function exists to avoid.
    """
    cached = _MULTIPLIER_DECIMALS.get(value)
    if cached is not None:
        return cached
    if not is_exact_float32(value):
        result = Decimal(repr(value))
    else:
        target = _float32_bits(value)
        result = Decimal(repr(value))
        for digits in range(1, _FLOAT32_MAX_DIGITS + 1):
            candidate = "%.*g" % (digits, value)
            if _float32_bits(float(candidate)) == target:
                result = Decimal(candidate)
                break
    _MULTIPLIER_DECIMALS[value] = result
    return result


class QuestCriteriaError(VendoredDataError):
    """A vendored mirror in THIS repository is missing or corrupt.

    Deliberately not a subclass of anything a script can trigger: it means
    go fix this checkout, not go read that quest file.  ``script_host``
    reports it as ``LUA_HOST`` for exactly that reason.
    """


def body_digest(text: str) -> str:
    """sha256 over every line of a mirror that is not a ``#`` comment.

    Same helper shape (and same purpose) as ``lua_api.message.body_digest``:
    it is checkable on the gate machine, which has no source table beside
    it.  Kept local rather than imported so a corrupt message catalog and a
    corrupt criteria mirror cannot take each other down.
    """
    body = "".join(line + "\n" for line in text.splitlines()
                   if not line.startswith("#"))
    return hashlib.sha256(body.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class CriteriaCurveRow:
    """One level of ``CONSTDATA_TH__STANDARD_QUEST.tsv``."""

    level: int
    cash: int
    exp: int
    skill_point: int


@dataclass(frozen=True)
class QuestRewardRow:
    """The reward-relevant columns of one ``QUESTDATA_TH__QUEST.tsv`` row."""

    quest_id: int
    criteria_level: int
    cash_multiplier: float
    exp_multiplier: float
    sp_multiplier: float


@dataclass(frozen=True)
class CriteriaAmount:
    """A resolved reward: every input kept, so the number can be argued with.

    Three views of the same product, all kept, because which one the real
    client uses is unverified (module docstring):

    * ``raw`` -- ``base * multiplier`` in binary floats, exactly what the
      mirror's bytes produce.  Provenance only.  It is the number that
      floors one short on the 1.4 rows; nothing grants from it.
    * ``exact`` -- ``Decimal(base) * multiplier_decimal(multiplier)``, the
      product with the float32 column's authored value recovered.  This is
      the one an RE answer will argue with.
    * ``amount`` -- ``exact`` through :func:`round_amount`, i.e. today's
      floor and only today's.
    """

    kind: str
    level: int
    base: int
    multiplier: float
    raw: float
    exact: Decimal
    amount: int

    def log_fields(self) -> str:
        """ASCII, one line, for the console the bridge reads (cp874).

        ``mult`` is the recovered decimal (``1.4``), not the widened float,
        because the widened float in a log line is what made a human read
        past this bug once already.  ``exact`` appears only when it differs
        from ``amount``, so a fractional reward cannot hide behind a clean
        integer.
        """
        fields = ("kind=%s level=%d base=%d mult=%s"
                  % (self.kind, self.level, self.base,
                     multiplier_decimal(self.multiplier)))
        if self.exact != self.amount:
            fields += " exact=%s" % self.exact
        return fields + " amount=%d" % self.amount


_CURVE_PATH = Path(__file__).with_name("quest_criteria_curve.tsv")
_ROWS_PATH = Path(__file__).with_name("quest_criteria_rows.tsv")

_CURVE_CACHE: Optional[Dict[int, CriteriaCurveRow]] = None
_ROWS_CACHE: Optional[Dict[int, QuestRewardRow]] = None


def _read_mirror(path: Path, columns: tuple) -> list:
    """Parse one vendored mirror into a list of field tuples.

    Every failure mode below is a :class:`QuestCriteriaError` naming the
    path: a mirror that is half-read is worse than one that is absent,
    because the second is obvious and the first pays wrong rewards.
    """
    try:
        text = path.read_text(encoding="ascii")
    except FileNotFoundError as exc:
        raise QuestCriteriaError("%s is missing" % path) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise QuestCriteriaError("%s is unreadable: %s" % (path, exc)) from exc

    declared = None
    for line in text.splitlines():
        if line.startswith(BODY_DIGEST_PREFIX):
            declared = line[len(BODY_DIGEST_PREFIX):].strip()
            break
    if declared is None:
        raise QuestCriteriaError("%s has no %s header"
                                 % (path, BODY_DIGEST_PREFIX.strip()))
    actual = body_digest(text)
    if declared != actual:
        raise QuestCriteriaError(
            "%s body digest mismatch (header %s, body %s): the file was "
            "hand-edited or truncated" % (path, declared, actual))

    data = [line for line in text.splitlines() if not line.startswith("#")]
    if not data:
        raise QuestCriteriaError("%s has no rows" % path)
    header = tuple(data[0].split("\t"))
    if header != columns:
        raise QuestCriteriaError("%s header is %r, expected %r"
                                 % (path, header, columns))
    rows = []
    for number, line in enumerate(data[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(columns):
            raise QuestCriteriaError(
                "%s line %d has %d fields, expected %d"
                % (path, number, len(fields), len(columns)))
        rows.append(fields)
    if not rows:
        raise QuestCriteriaError("%s has a header but no rows" % path)
    return rows


def _parse_int(path: Path, name: str, raw: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise QuestCriteriaError("%s: %s is not an integer: %r"
                                 % (path, name, raw)) from exc


def _parse_float(path: Path, name: str, raw: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise QuestCriteriaError("%s: %s is not a number: %r"
                                 % (path, name, raw)) from exc


def load_curve() -> Dict[int, CriteriaCurveRow]:
    """``{level: CriteriaCurveRow}``, parsed once and cached."""
    global _CURVE_CACHE
    if _CURVE_CACHE is None:
        table: Dict[int, CriteriaCurveRow] = {}
        for fields in _read_mirror(_CURVE_PATH, CURVE_COLUMNS):
            level = _parse_int(_CURVE_PATH, "level", fields[0])
            if level in table:
                raise QuestCriteriaError("%s: duplicate level %d"
                                         % (_CURVE_PATH, level))
            table[level] = CriteriaCurveRow(
                level=level,
                cash=_parse_int(_CURVE_PATH, "cash", fields[1]),
                exp=_parse_int(_CURVE_PATH, "exp", fields[2]),
                skill_point=_parse_int(_CURVE_PATH, "skill_point", fields[3]),
            )
        _CURVE_CACHE = table
    return _CURVE_CACHE


def load_reward_rows() -> Dict[int, QuestRewardRow]:
    """``{quest_id: QuestRewardRow}``, parsed once and cached."""
    global _ROWS_CACHE
    if _ROWS_CACHE is None:
        table: Dict[int, QuestRewardRow] = {}
        for fields in _read_mirror(_ROWS_PATH, ROW_COLUMNS):
            quest_id = _parse_int(_ROWS_PATH, "quest_id", fields[0])
            if quest_id in table:
                raise QuestCriteriaError("%s: duplicate quest_id %d"
                                         % (_ROWS_PATH, quest_id))
            table[quest_id] = QuestRewardRow(
                quest_id=quest_id,
                criteria_level=_parse_int(
                    _ROWS_PATH, "criteria_level", fields[1]),
                cash_multiplier=_parse_float(
                    _ROWS_PATH, "cash_multiplier", fields[2]),
                exp_multiplier=_parse_float(
                    _ROWS_PATH, "exp_multiplier", fields[3]),
                sp_multiplier=_parse_float(
                    _ROWS_PATH, "sp_multiplier", fields[4]),
            )
        _ROWS_CACHE = table
    return _ROWS_CACHE


def reset_caches() -> None:
    """Drop both parsed mirrors.  For tests that point the module at a
    temporary file; production never calls it."""
    global _CURVE_CACHE, _ROWS_CACHE
    _CURVE_CACHE = None
    _ROWS_CACHE = None


def _coerce_player_level(value: Any) -> Optional[int]:
    """A player level, or ``None`` for anything that is not one.

    `type(...) is bool` FIRST, the order `lua_api.message` already uses:
    bool IS int in Python, so ``True`` would otherwise index the curve at
    level 1 and pay a level-90 player the newbie reward with nothing
    looking broken (pf-adversary, round xlk7hl).

    A whole-number float IS accepted -- lupa hands every Lua number across
    as a float, and this house already settled that question the same way
    for ``Quest.CheckOpenTime`` (``900.0`` is 900).  ``30.5`` is not a
    level and is refused rather than truncated.
    """
    if type(value) is bool:
        return None
    if isinstance(value, float):
        if value != int(value):
            return None
        value = int(value)
    if not isinstance(value, int):
        return None
    if not MIN_LEVEL <= value <= MAX_LEVEL:
        return None
    return value


def resolve(kind: str, level: int, multiplier: float) -> Optional[CriteriaAmount]:
    """``curve[level].<kind> * multiplier``, or ``None`` if ``level`` has no row.

    ``None`` rather than an exception or a zero: a level outside the curve
    is a caller mistake to report, not a reward of nothing to pay out.

    The product is taken in :class:`~decimal.Decimal` over the recovered
    multiplier, never in binary floats: see the module docstring for the
    14 shipped resolutions that ``int(base * multiplier)`` pays short.
    """
    if kind not in _KIND_FIELDS:
        raise QuestCriteriaError("unknown reward kind %r" % (kind,))
    curve_field, _ = _KIND_FIELDS[kind]
    row = load_curve().get(level)
    if row is None:
        return None
    base = getattr(row, curve_field)
    exact = Decimal(base) * multiplier_decimal(multiplier)
    return CriteriaAmount(kind=kind, level=level, base=base,
                          multiplier=multiplier, raw=base * multiplier,
                          exact=exact, amount=round_amount(exact))


def resolve_for_api(api_name: str, quest_id: int,
                    player_level: Optional[int] = None):
    """Resolve what one of the six API names would pay, or say why not.

    Returns ``(CriteriaAmount, None)`` on success and ``(None, reason)``
    otherwise, where ``reason`` is one of the ``REFUSE_*`` constants -- a
    closed set, so a caller counting refusals cannot grow a key per input.
    Never guesses a level: an ``AddLvCriteria*`` name with no
    ``player_level`` refuses, it does not silently fall back to the quest
    row's level and pay the wrong number.
    """
    if api_name not in LEVEL_SOURCE:
        return None, REFUSE_UNKNOWN_API
    row = load_reward_rows().get(quest_id)
    if row is None:
        return None, REFUSE_NO_QUEST_ROW
    if LEVEL_SOURCE[api_name] == LEVEL_SOURCE_PLAYER:
        if player_level is None:
            return None, REFUSE_NO_PLAYER_LEVEL
        level = _coerce_player_level(player_level)
        if level is None:
            return None, REFUSE_BAD_PLAYER_LEVEL
    else:
        level = row.criteria_level
    kind = API_KIND[api_name]
    _, multiplier_field = _KIND_FIELDS[kind]
    amount = resolve(kind, level, getattr(row, multiplier_field))
    if amount is None:
        return None, REFUSE_LEVEL_OUT_OF_RANGE
    return amount, None
