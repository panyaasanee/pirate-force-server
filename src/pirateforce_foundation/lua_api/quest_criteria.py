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

  * ``f_EXP`` holds 11 distinct values across all 1544 quest rows and
    every one of them is a small ratio -- 0.0, 0.1, 0.25, 0.3, 0.5, 1.0,
    1.4, 1.5, 2.0, 3.0, 5.0 (stored float32-widened, e.g. literally
    ``0.10000000149011612`` on disk).  Those are MULTIPLIERS, not exp
    amounts; no quest in this game awards 1.5 experience points.
    (The 12 this file claimed until round ``na0ftg`` is the count over
    all THREE multiplier columns, 4632 cells: ``f_CASH`` adds 0.85 and
    holds 3 values in total, ``f_SP`` holds 6.  Round ``xlk7hl`` said 11,
    round ``wn088m`` "corrected" it to 12 by counting the other set, and
    pf-adversary D7 of round ``na0ftg`` counted each column on its own.)
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

Both measurements turned out to be right, and RE-295 (2026-09-07T14:25)
is why this paragraph no longer ends in an assumption.  Reading the
client, ``AddLvCriteriaSkillPoint`` (``0x006092B0``) takes its level from
the local player object -- ``global 0x01032EC4`` -> ``+0x348`` -> u16 at
``+0x5E`` -- where the plain ``AddCriteriaSkillPoint`` (``0x00608E60``)
takes a u16 off the QUEST ROW at ``+0x1A``.  ``AddLvCriteriaCash`` and
``AddLvCriteriaExp`` read the same three words.  So ``Lv`` IS the player's
level, measured, and :data:`LEVEL_SOURCE` is a record rather than a bet.
The refusal survives the proof for the same reason: the client at
``0x00609308`` jumps straight OUT when there is no player object -- it
pays nothing rather than falling back to the row's level -- which is
exactly what ``REFUSE_NO_PLAYER_LEVEL`` does here.

WHAT THIS DOES NOT YET REACH, stated before anything else it claims.
A criteria call resolves only when the CALLER says which quest is running.
Round ``wn088m`` mirrored ``s_LUASCRIPT`` and added
``script_host.load_quest_script``, which supplies that: measured, 1213 of
the 1544 quest rows dispatch a script calling at least one criteria name
and 1039 of those now resolve a real amount.  ``quest.DEFAULT_CONTEXT``
still carries ``quest_id=0`` and still refuses, correctly -- and NOTHING
IN THE SERVER CALLS THE DISPATCHER YET (pf-adversary D10, round
``wn088m``: ``load_quest_script`` has two call sites and both are tests).
So the read half is complete and tested and still reaches no player: what
is missing is no longer the argument, it is a quest system to pass it and
a grant to spend the answer on.  The relation stays one-to-many in the
OTHER direction (``Q_CON1`` is the script of 160 quest rows), which is why
a running script can never be asked which quest it is, and why nothing
here infers a quest from a file.

ONE MORE THING, AND THE BRIDGE'S OWN INDEX IS WRONG ABOUT IT:
``gamedata/PF_GAMEDATA_LUA_API.tsv`` records ``AddLvCriteriaExp`` as
``UNRESOLVED``, the one of the six with no binding found.  RE-295 found
it: registration at ``0x00609990``, delegate ``0x00609140``, reading the
same player level as its two siblings.  The index generator missed it
because it expects ``mov [esp+0x34], <delegate>`` AFTER the pushes and
this call site emits ``mov [esp+0x18], ...`` BEFORE them -- same slot,
different instruction order.  So the 59 daily-quest call sites behind
that name are LIVE and this module implements them.  (The mirror is the
bridge's file, not this lane's, so the correction went out as a letter;
until it lands, the ``UNRESOLVED`` in that TSV is the stale value, not
this docstring.)  The one name that really is absent from this build is
``GiveLvCriteriaPercentageEXP``: 0 occurrences in ``.rdata`` in either
encoding, so nothing here chases it.

HOW MANY, EXACTLY: SIX INSTRUCTIONS, COPIED.  Round ``wn088m`` had to
guess the width of the multiply and said so in capital letters; RE-295
read it out of the binary at ``0x00608D10``, and the answer was neither
of the two the guess offered::

    movss    xmm0, [esi+0x3c]      ; f_EXP loaded as float32
    cvtsi2ss xmm1, [esp+0x14]      ; the curve base, int -> SINGLE
    cvtss2sd xmm1, xmm1            ; base widened to double
    cvtps2pd xmm0, xmm0            ; multiplier widened to double
    mulsd    xmm1, xmm0            ; the multiply happens at DOUBLE
    cvttsd2si esi, xmm1            ; and the cast TRUNCATES

Not single (which round ``wn088m`` implemented, via a decimal recovery
that reproduces it), not x87 extended: SSE2 double, with both operands
arriving through float32.  :func:`client_product` is those five
arithmetic instructions and :func:`round_amount` is the sixth.

WHAT THAT COST, HONESTLY: the 14 resolutions round ``wn088m`` moved UP by
one are moved back DOWN this round, to the number the client actually
pays.  Measured again this round on the same corpus, both ways, and the
sets match to the row: 14 of the 4632 plain-triple resolutions and 3632
of the 1181160 ``(row, level, kind)`` products a player-level triple can
reach, all of them on the 1.4 multiplier and all in quests 2170-2177.
``15800 * float32(1.4)`` is ``22119.999623298645`` at double and the
truncating cast makes it ``22119`` -- so quest 2170 pays 22119 exp, one
short of the 22120 its designer typed, because the client short-changes
its own table.  ``exact`` keeps that 22120 beside the payout (and
``log_fields`` prints it as ``authored=``) so nobody has to rediscover
the gap; nothing pays out of it.

WHAT IS NOT MEASURED HERE, said plainly.  ``cvtsi2ss`` rounds the base to
single first, and every base in the shipped curve is under 2**24 (max
14252800, measured) so on shipped data that step is the identity: it is
in :func:`client_product` because it is what the instruction does, NOT
because any shipped row proves it, and the test that pins it uses a
hand-made base.  ``cvttsd2si`` also has a documented answer for a product
that overflows int32 (the "integer indefinite" ``0x80000000``); this
module does not reproduce that, it returns the true integer, and no
shipped ``(row, level, kind)`` product comes near the boundary
(max 14252800 * 5.0, measured).  Both are nonclaims, not TODOs.

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
import math
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Dict, Optional

from .vendored import VendoredDataError

#: Column headers of the vendored curve mirror, in order.
CURVE_COLUMNS = ("level", "cash", "exp", "skill_point")

#: Column headers of the vendored per-quest mirror, in order.
ROW_COLUMNS = ("quest_id", "criteria_level",
               "cash_multiplier", "exp_multiplier", "sp_multiplier",
               "script")

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
#: MEASURED, not assumed: the RE ticket COO-DECISION ``0845`` named as the
#: thing that would retire the ``[COO-ASSUMPTION 0845]`` label answered on
#: 2026-09-07T14:25 (RE-295, ``notes_to_chief/20260907_1425_RE-295-``
#: ``RESULT-multiply-is-double-truncate-and-Lv-reads-player-level.md``).
#: The three ``AddLvCriteria*`` delegates read the player's level out of
#: the player object; the three plain ones read a u16 off the quest row.
#: The letter's other order stands and is now also the client's behaviour:
#: never fall back to the quest row's level when the player level is
#: unknown (see :data:`REFUSE_NO_PLAYER_LEVEL`).
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
#: What ``cvtsi2ss`` at ``0x00608DC7`` can load: a signed DWORD.  The
#: shipped curve tops out at 14252800 so nothing comes near it, but
#: :func:`client_product` is public and models the instruction, not the
#: corpus (pf-adversary D4, round ``na0ftg``).
INT32_MIN = -2 ** 31
INT32_MAX = 2 ** 31 - 1

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

#: How a fractional reward becomes an integer, in ONE place.  MEASURED
#: now, not chosen: RE-295 (``notes_to_chief/20260907_1425_RE-295-RESULT-``
#: ``multiply-is-double-truncate-and-Lv-reads-player-level.md``) read the
#: cast the client actually executes at ``0x00608DDC`` -- ``cvttsd2si``,
#: the TRUNCATING form, which ignores the FPU rounding mode entirely.
#: Truncate-toward-zero, not floor: the two agree on every product any
#: mirror cell can produce (all multipliers and all curve columns are
#: >= 0, measured) and disagree only below zero, which is reachable only
#: through the public :func:`resolve` with a hand-made negative
#: multiplier.  This line names what the client does; the mode used to
#: name what COO chose while nobody knew.
ROUNDING_MODE = ROUND_DOWN

#: Widest float32 significand, i.e. how many decimal digits can ever be
#: needed to name a float32 exactly.  Used as the search ceiling in
#: :func:`multiplier_decimal`, never as a precision claim.
_FLOAT32_MAX_DIGITS = 17


def _plain(value: Decimal) -> str:
    """``Decimal`` without the trailing zeros a product leaves behind and
    without the exponent ``normalize`` would put on a round number:
    ``22120``, not ``22120.0`` and not ``2.212E+4``.  A log line is read by
    a person, and ``E+4`` in a reward is a second thing to decode."""
    if not value.is_finite():
        # No product makes one, and a log formatter is the last place a
        # reward line should learn to raise (pf-adversary D2, na0ftg).
        return str(value)
    value = value.normalize()
    sign, digits, exponent = value.as_tuple()
    if exponent > 0:
        # NOT `quantize`: it raises InvalidOperation the moment the result
        # passes the decimal context's 28 digits, and this string is built
        # AFTER the grant has already been made (pf-adversary D2, na0ftg).
        return ("-" if sign else "") + "".join(map(str, digits)) + "0" * exponent
    return str(value)


def round_amount(exact: Decimal) -> int:
    """The single rounding point of the reward seam (:data:`ROUNDING_MODE`).

    Takes a :class:`~decimal.Decimal`, never a float, so the number being
    rounded is written down exactly at the one place that rounds it.  The
    caller decides WHICH number to hand over; since RE-295 that is the
    client's own double product (:func:`client_product`), whose decimal
    expansion is finite and therefore loses nothing on the way in.
    """
    return int(exact.to_integral_value(rounding=ROUNDING_MODE))


def _float32_bits(value: float, what: str = "multiplier") -> bytes:
    """The 4 bytes ``value`` occupies as a float32, or raise for a float
    that has no float32 (an out-of-range multiplier is corrupt data).

    ``what`` names the thing in the message, because since RE-295 the
    curve BASE goes through this too (``cvtsi2ss``) and a message that
    calls a base a multiplier sends the reader to the wrong column.
    """
    try:
        return struct.pack("<f", value)
    except (OverflowError, ValueError, struct.error) as exc:
        raise QuestCriteriaError(
            "%s %r does not fit a float32" % (what, value)) from exc


def is_exact_float32(value: float) -> bool:
    """True when ``value`` is exactly a widened float32.

    Every one of the 12 distinct multipliers in the shipped mirror answers
    True (measured); a False here means the source column is NOT the
    float32 this module reads it as, and :func:`multiplier_decimal` would
    be inventing precision rather than recovering it.
    """
    return struct.unpack("<f", _float32_bits(value))[0] == value


def widen_float32(value: float, what: str = "multiplier") -> float:
    """``value`` as the client sees it after a float32 load, i.e. the
    double you get by rounding to single and widening back.

    Two of the client's six arithmetic instructions are exactly this
    (RE-295): ``movss``+``cvtps2pd`` for the multiplier column, and
    ``cvtsi2ss``+``cvtss2sd`` for the integer curve base.  Idempotent on a
    value that already came out of a float32 column, which is why calling
    it on the mirror's numbers changes nothing and calling it on a
    caller-supplied multiplier is what keeps the two paths equal.

    Raises :class:`QuestCriteriaError` for a value with no float32 at all
    (``_float32_bits``), the same refusal the mirror cells get.
    """
    return struct.unpack("<f", _float32_bits(value, what))[0]


def client_product(base: int, multiplier: float) -> float:
    """The number the client has in ``xmm1`` at ``0x00608DD4``, before its
    truncating cast -- reproduced instruction for instruction (RE-295).

    ``base`` goes through float32 too.  That is ``cvtsi2ss`` at
    ``0x00608DC7``, and it is the one step the RE letter's suggested
    Python one-liner leaves out; it is invisible on the shipped curve
    (every base is under 2**24, measured, so float32 holds it exactly) and
    it is not invisible to a caller passing a bigger base by hand.  That
    instruction reads a SIGNED DWORD, so its domain is modelled too: a
    base outside int32 is REFUSED, not wrapped, because the wrap is a
    client behaviour nobody has observed paying anything out.

    Both widenings are exact, so the only rounding in the whole expression
    is the ``mulsd``, and Python's float IS that ``mulsd``: both are IEEE
    binary64 with round-to-nearest-even.
    """
    if not isinstance(base, int) or isinstance(base, bool):
        # `cvtsi2ss` reads a DWORD out of memory; there is no client
        # behaviour to reproduce for a base that is not an integer at all.
        # Ours to name: a bare TypeError out of this module reaches
        # `script_host` as an unknown type and gets logged against
        # whichever quest script was running (pf-adversary D11 and D5).
        raise QuestCriteriaError(
            "base must be an int, not %s" % (type(base).__name__,))
    if not INT32_MIN <= base <= INT32_MAX:
        # And it reads a SIGNED DWORD: the client would wrap 2**31 to
        # -2**31 and pay a negative reward. Reproducing that wrap would be
        # inventing a client behaviour nobody has observed, so this
        # refuses instead -- and says WHICH boundary, since "float32"
        # points a reader at one 12 orders of magnitude away
        # (pf-adversary D4/D5, round na0ftg). The value is named by width,
        # not printed: a 401-digit base in a cp874 log line helps nobody.
        raise QuestCriteriaError(
            "base is outside the int32 the client loads (%d bits)"
            % (base.bit_length(),))
    return (widen_float32(float(base), "base")
            * widen_float32(multiplier, "multiplier"))


#: Memo for :func:`multiplier_decimal`.  BOUNDED on purpose: ``resolve``
#: is public and takes an arbitrary float, so a future grant path applying
#: a per-player scale would leak one entry per distinct float forever --
#: the same unbounded-key defect the ``REFUSE_*`` set exists to avoid
#: (pf-adversary D8, round ``wn088m``).  The mirror holds 12 distinct
#: multipliers; the cap is far above that and finite, which is the point.
_MULTIPLIER_CACHE_MAX = 256
_MULTIPLIER_DECIMALS: Dict[float, Decimal] = {}


def multiplier_decimal(value: float) -> Decimal:
    """The shortest decimal that round-trips through float32 to ``value``.

    ``1.399999976158142`` -> ``Decimal("1.4")``: recovering what the table
    author typed, not rounding the number we were given.  A value that is
    not exactly a float32 is returned digit-for-digit instead (``repr``),
    because there is then nothing to recover and quietly shortening it
    would be the invention this function exists to avoid.
    """
    # Keyed by the float32 BITS, not the float: `-0.0 == 0.0` and they
    # hash alike, so one resolution with a negative zero used to poison
    # every later zero-multiplier log line with `mult=-0` (pf-adversary
    # D8, round na0ftg).
    key = _float32_bits(value)
    cached = _MULTIPLIER_DECIMALS.get(key)
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
    if len(_MULTIPLIER_DECIMALS) < _MULTIPLIER_CACHE_MAX:
        _MULTIPLIER_DECIMALS[key] = result
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
    script: str


@dataclass(frozen=True)
class CriteriaAmount:
    """A resolved reward: every input kept, so the number can be argued with.

    Three views of the same product.  Which one the client uses stopped
    being a question on 2026-09-07 (RE-295), so unlike round ``wn088m``
    this class no longer keeps three candidates -- it keeps one answer and
    two things to check it against:

    * ``raw`` -- :func:`client_product`, the double the client itself
      multiplies (``mulsd`` at ``0x00608DD4``).  THE PAYOUT COMES FROM
      THIS ONE.
    * ``exact`` -- ``Decimal(base) * multiplier_decimal(multiplier)``: what
      the designer who typed ``1.4`` into the table meant.  Provenance
      only.  On 14 shipped resolutions it is one MORE than ``amount``, and
      that gap is the client short-changing its own table, not a bug here.
    * ``amount`` -- ``raw`` through :func:`round_amount`, i.e. the
      truncating cast at ``0x00608DDC``.

    WHAT WOULD RETIRE ``exact`` (pf-adversary asked, round ``na0ftg``, and
    the answer is not "nothing"): it goes the day a measurement shows the
    SERVER should pay the designer's number rather than the client's --
    for instance an attended capture where the client displays 22120 for
    quest 2170 while its own arithmetic computes 22119, which would mean
    the payout does not come from this code path at all.  Until such a
    capture exists, ``exact`` is the only artifact in the tree that says
    the two numbers were ever different, and 14 shipped rewards depend on
    somebody being able to see that.  It is one Decimal multiply per
    resolution on a path that already parses two mirrors.
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
        past this arithmetic once already.  ``product`` appears only when
        the truncating cast actually dropped something, and ``authored``
        only when the table's own decimal would have paid a DIFFERENT
        INTEGER -- not merely a different fraction, which is 171 of the
        185 shipped cells where the two Decimals differ at all
        (pf-adversary D3, round na0ftg).  So a reward that quietly differs
        from the designer's intent cannot hide behind a clean number, and
        a reward that does not differ does not shout.
        """
        fields = ("kind=%s level=%d base=%d mult=%s"
                  % (self.kind, self.level, self.base,
                     multiplier_decimal(self.multiplier)))
        if Decimal(self.raw) != self.amount:
            fields += " product=%r" % self.raw
        if round_amount(self.exact) != self.amount:
            # The client pays `amount`; this is the integer the table
            # author's own decimal would have paid. Printing both is the
            # only operator-visible sign that the client's float32 column
            # and its designer disagree (pf-adversary D9, round wn088m,
            # re-aimed by RE-295 and narrowed by D3, round na0ftg).
            fields += " authored=%s" % _plain(self.exact)
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
    """A finite multiplier, or :class:`QuestCriteriaError` naming the cell.

    ``float("inf")`` and ``float("1e400")`` both succeed and
    ``struct.pack("<f", inf)`` does NOT raise, so an infinity would sail
    through the float32 check and die later as a bare ``OverflowError``
    out of ``int(Infinity)`` -- which ``script_host`` would print as
    ``LUA_SCRIPT <file> ERR`` against up to 616 innocent quest scripts,
    the exact D11 shape this module claims to have closed (pf-adversary
    D4, round ``wn088m``).  It is refused HERE, at the cell, instead.
    """
    try:
        value = float(raw)
    except ValueError as exc:
        raise QuestCriteriaError("%s: %s is not a number: %r"
                                 % (path, name, raw)) from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise QuestCriteriaError("%s: %s is not finite: %r"
                                 % (path, name, raw))
    return value


def _parse_script(path: Path, raw: str) -> str:
    """The ``s_LUASCRIPT`` cell, refused rather than defaulted when empty.

    A quest row with no script is a row this server could never dispatch,
    and an empty cell reaching :func:`script_for_quest` would resolve to
    the corpus root itself.  Measured on the shipped table: 0 of 1544 rows
    are empty, so an empty one means the mirror was truncated.
    """
    name = raw.strip()
    if not name:
        raise QuestCriteriaError("%s: a quest row has an empty script name"
                                 % path)
    return name


def script_for_quest(quest_id: int) -> Optional[str]:
    """The one script name a quest dispatches, or ``None`` for no such row.

    The only direction of this relation that is a function: 1544 quest rows
    name 209 distinct scripts, and ``Q_CON1`` alone is named by 160 rows.
    That is why a running script cannot be asked which quest it is, and why
    :func:`resolve_for_api` refuses instead of guessing.
    """
    row = load_reward_rows().get(quest_id)
    return None if row is None else row.script


def quests_for_script(script: str) -> tuple:
    """Every quest id that dispatches ``script``, ascending.  Case-folded.

    Returned so a caller can SEE the ambiguity rather than trip over it:
    a corpus file alone is never enough to resolve a reward.
    """
    key = script.strip().lower()
    return tuple(sorted(qid for qid, row in load_reward_rows().items()
                        if row.script.lower() == key))


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
                script=_parse_script(_ROWS_PATH, fields[5]),
            )
        _ROWS_CACHE = table
    return _ROWS_CACHE


def reset_caches() -> None:
    """Drop both parsed mirrors.  For tests that point the module at a
    temporary file; production never calls it."""
    global _CURVE_CACHE, _ROWS_CACHE
    _CURVE_CACHE = None
    _ROWS_CACHE = None
    _MULTIPLIER_DECIMALS.clear()


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
        # `inf`/`nan` FIRST: `int(inf)` raises OverflowError and `int(nan)`
        # raises ValueError, so the `value != int(value)` test below cannot
        # reach its own `return None` for them -- it raises THROUGH this
        # function and out of `resolve_for_api`, and (since round `8ou0zg`
        # exposed `player_level` as a public keyword) out of
        # `lua_api.reward.pay`, whose docstring promises it never raises for
        # a refusal (pf-adversary finding 5, round `8ou0zg`). This is not a
        # theoretical input: `lupa` hands every Lua number across as a
        # float, and Lua's `1/0` is `inf`.
        #
        # Same defect, same fix, as the multiplier cell three functions
        # away -- which this module already refuses at the cell and says so
        # in its docstring. The claim was true of multipliers and not of
        # levels; it is true of both now.
        if not math.isfinite(value):
            return None
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

    The product is the client's own (:func:`client_product`): both
    operands through float32, the multiply at double, the cast
    truncating.  ``exact`` still carries the authored-decimal product
    beside it, which is what round ``wn088m`` paid out of and what RE-295
    disproved as the payout (module docstring).
    """
    if kind not in _KIND_FIELDS:
        raise QuestCriteriaError("unknown reward kind %r" % (kind,))
    if isinstance(multiplier, (str, bytes, bytearray)):
        # `float("1.4")` succeeds, and a multiplier that arrived as text
        # is a caller bug worth naming rather than a number worth paying.
        raise QuestCriteriaError(
            "multiplier is not a number: %s" % (type(multiplier).__name__,))
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError) as exc:
        # `isinstance(multiplier, float)` was the old guard, and a
        # `Decimal`, a `Fraction` or anything else carrying `__float__`
        # walked straight past it into `Decimal(repr(value))` and died
        # there as `decimal.InvalidOperation` (pf-adversary D6, na0ftg).
        raise QuestCriteriaError(
            "multiplier is not a number: %s" % (type(multiplier).__name__,)
        ) from exc
    if not math.isfinite(multiplier):
        # Public function, so it is reachable with a multiplier no mirror
        # cell can hold. Refused by name (pf-adversary finding 5, round
        # `8ou0zg`) instead of raising an undocumented OverflowError out of
        # `multiplier_decimal` -- and, worse, CACHING the way there.
        raise QuestCriteriaError(
            "multiplier %r is not a finite number" % (multiplier,))
    curve_field, _ = _KIND_FIELDS[kind]
    row = load_curve().get(level)
    if row is None:
        return None
    base = getattr(row, curve_field)
    raw = client_product(base, multiplier)
    return CriteriaAmount(kind=kind, level=level, base=base,
                          multiplier=multiplier, raw=raw,
                          exact=Decimal(base) * multiplier_decimal(multiplier),
                          amount=round_amount(Decimal(raw)))


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
