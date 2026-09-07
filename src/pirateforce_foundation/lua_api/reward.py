"""LANE-Q: the WRITE half of the quest reward seam -- and why it refuses.

WHAT THE READ HALF ALREADY DOES.  ``lua_api.quest_criteria`` resolves what
one of the six ``Quest.Add*Criteria*`` names would pay, out of the game's
own shipped tables, exactly (round ``wn088m``: the multiplier is recovered
through float32 so the product stops coming out one unit short).  Round
``xlk7hl`` gave the number a level, round ``wn088m`` gave it a quest id.
The number has been correct and STRANDED ever since: nothing pays it.

WHAT THIS MODULE IS.  The one seam between that number and a character
row -- and, today, an HONEST REFUSAL rather than a payment, for a reason
that is measured rather than asserted: ``store.py`` has no atomic
``add_typed_attribute``.  See :func:`pay`.

THE SHAPE THIS LANE IS NOT ALLOWED TO TAKE (pf-adversary D14, round
``wn088m``).  The obvious implementation is read the balance, add, write it
back.  That is wrong here in two separate ways, either one of which is
enough:

  1. READ-MODIFY-WRITE ACROSS TWO CONNECTIONS SILENTLY EATS THE OTHER
     WRITER.  Two sessions in one scene share this process (``NOW.md``
     "shared world"), and combat, trade and quest payouts all move the same
     columns.  A read at T0 and an ``UPDATE`` at T2 discards anything
     written at T1 with no error anywhere.  ``store.spend_skill_points``
     is the shape this project already settled on for exactly this: one
     ``BEGIN IMMEDIATE``, the read and the write inside it.
  2. THERE IS NO BALANCE TO READ.  ``store.read_typed_attributes`` DROPS
     columns holding NULL, so ``.get("experience", 0)`` on a character
     nobody has ever granted experience to is a GUESS OF ZERO, which
     ``COO-DECISION 20260901_1059`` forbids by name -- the same refusal
     ``spend_skill_points`` raises ``UnmeasuredSkillPointsError`` for.

So this module never reads a balance at all.  It asks its store for a
DELTA and takes the store's word for what the balance became.  A store
that cannot do that atomically does not get asked to do it slowly: it gets
refused, and the refusal is logged with the number that was not paid, so
the round after this one can measure what is waiting rather than guess.

WHAT MAKES THE COLUMN NAME SAFE.  :data:`KIND_COLUMN` is a frozen
three-entry map from this lane's own reward-kind constants to column
names, and a test pins every value in it against
``persistence_typed_attrs.TYPED_COLUMNS``.  No cell of any shipped game
table, and no string a Lua script can produce, is ever concatenated into
a column name -- the same posture ``lua_api.dispatch`` takes with the
corpus root, and for the same reason: the 616 scripts are untrusted input
(``COO-DECISION 20260905_2248``).

WHAT THIS IS NOT.  Not a quest system: nothing here decides which quest a
player is on, nothing decides whether a quest is complete, and NO FRAME
GOES OUT -- a client that is looking at its EXP bar will not see it move
because of anything in this file.  Paying a reward the player can SEE
needs, on top of this seam: LANE-DB's atomic add, a caller that dispatches
a real quest script at a real NPC interaction, and whatever ``Player.*``
frame tells the client its stats changed.  This is one of those four.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, Tuple

from . import quest_criteria
from .quest_criteria import CriteriaAmount

#: Reward kind (this lane's own constants, never a table cell) -> the
#: ``characters`` column that kind is paid into.  FROZEN AND CLOSED: three
#: entries, one per kind in ``quest_criteria.KINDS``.  Two tests hold it
#: shut -- one that every value is a real
#: ``persistence_typed_attrs.TYPED_COLUMNS`` name, one that every kind in
#: ``KINDS`` appears here, so adding a fourth reward kind upstream cannot
#: quietly leave it unpayable.
KIND_COLUMN: dict[str, str] = {
    quest_criteria.KIND_EXP: "experience",
    quest_criteria.KIND_CASH: "cash",
    quest_criteria.KIND_SKILL_POINT: "skill_points",
}

#: The closed set of reasons :func:`pay` declines, same discipline
#: ``quest_criteria.REFUSE_*`` uses: a caller counting refusals by reason
#: cannot grow one key per input.  ``quest_criteria``'s own reasons pass
#: through unchanged when the number does not even resolve.
REFUSE_NO_STORE = "no_reward_store"
REFUSE_STORE_NOT_ATOMIC = "store_has_no_atomic_add"
REFUSE_NO_CHARACTER = "no_character"
REFUSE_NOTHING_TO_PAY = "amount_is_zero"
REFUSE_NEGATIVE = "amount_is_negative"
REFUSE_STORE_ERROR = "store_error"

#: Every reason this module itself can produce.  A test asserts
#: :func:`pay` never returns a reason outside this set union
#: ``quest_criteria``'s.
REFUSALS: frozenset = frozenset({
    REFUSE_NO_STORE, REFUSE_STORE_NOT_ATOMIC, REFUSE_NO_CHARACTER,
    REFUSE_NOTHING_TO_PAY, REFUSE_NEGATIVE, REFUSE_STORE_ERROR,
})


class QuestRewardStore(Protocol):
    """The ONE method this lane needs from a character store, and its
    contract.  Asked of LANE-DB as a ``CORE-REQUEST`` on 2026-09-07;
    ``store.py`` does not implement it yet, which is why :func:`pay`
    refuses on a real store today rather than paying badly.

    ``add_typed_attribute(character_id, column, delta) -> int``

    * ONE transaction.  The read and the write happen inside a single
      ``BEGIN IMMEDIATE``, so a concurrent writer cannot be lost -- the
      discipline ``store.spend_skill_points`` already uses.
    * NEVER GUESSES ZERO.  A NULL column means nobody has ever measured
      that balance; the method refuses (an exception naming the column)
      instead of treating NULL as ``0`` and inventing a starting point.
    * Returns the balance AFTER the delta, like ``spend_skill_points``
      returns the balance after the deduction, so the caller never has to
      read back and never has to assume the write landed.
    * ``column`` is a ``persistence_typed_attrs.TYPED_COLUMNS`` name; this
      caller only ever passes a value out of :data:`KIND_COLUMN`.
    """

    def add_typed_attribute(self, character_id: int, column: str,
                            delta: int) -> int:
        ...  # pragma: no cover - protocol declaration


@dataclass(frozen=True)
class Payout:
    """One reward that actually reached a row, with the number's provenance.

    ``amount`` is the full :class:`quest_criteria.CriteriaAmount`, not just
    the integer, so a reader of a payout can still see the base, the level,
    the recovered multiplier and the unrounded ``exact`` -- the evidence
    that the integer was resolved rather than chosen.
    """

    api_name: str
    quest_id: int
    character_id: int
    column: str
    amount: CriteriaAmount
    balance_after: int

    def log_fields(self) -> str:
        return ("character=%d column=%s paid=%d balance_after=%d %s"
                % (self.character_id, self.column, self.amount.amount,
                   self.balance_after, self.amount.log_fields()))


def _has_atomic_add(store: Any) -> bool:
    """Whether ``store`` offers the atomic delta :class:`QuestRewardStore`
    describes.

    A capability check, not an ``isinstance``: ``Protocol`` classes are
    structural, and a ``runtime_checkable`` ``isinstance`` would only look
    at the same attribute anyway while ALSO accepting a non-callable
    attribute of that name.  ``callable()`` is the part that matters.
    """
    return callable(getattr(store, "add_typed_attribute", None))


def pay(api_name: str, character_id: int, quest_id: int, *,
        store: Optional[Any] = None,
        player_level: Optional[int] = None,
        log: Optional[Callable[[str], None]] = None,
        ) -> Tuple[Optional[Payout], Optional[str]]:
    """Resolve one criteria reward and pay it, or say exactly why not.

    Returns ``(Payout, None)`` when a row actually moved, and
    ``(None, reason)`` otherwise, where ``reason`` is a member of
    :data:`REFUSALS` or of ``quest_criteria``'s own closed refusal set.

    RESOLVE FIRST, PAY SECOND, AND LOG EITHER WAY.  The number is worked
    out before the store is consulted, so a refusal on the payment side
    still reports what WOULD have been paid: that is the measurement the
    next round needs to size this seam, and it is free.  A resolution
    refusal (no quest row, no player level) short-circuits before the
    store is touched at all -- nothing is written when anything is
    refused, the same all-or-nothing shape ``spend_skill_points`` has.

    NEVER RAISES FOR A REFUSAL.  A missing store, a store that cannot add
    atomically, a character id of 0, or a store that throws are all
    REFUSALS: the Lua script that called ``Quest.AddCriteriaExp()`` keeps
    running, because a host that dies on a payout turns one unpaid reward
    into a whole quest script logged as broken (the ``LUA_SCRIPT <file>
    ERR`` mis-attribution pf-adversary D11 of round ``7kxfe9`` was raised
    for).  ``quest_criteria.QuestCriteriaError`` is the deliberate
    exception: a corrupt mirror in THIS repository propagates, so
    ``script_host`` reports it as ``LUA_HOST`` against this checkout
    rather than against whichever quest file was running.

    ``character_id`` 0 is refused rather than paid.  It is
    ``lua_api.quest.DEFAULT_CONTEXT``'s value -- the well-defined inert
    bucket a caller gets when it supplied no context -- and character ids
    in this codebase start at 1, so a payout addressed to 0 is a caller
    that forgot to say who, not a player.
    """
    log = log or (lambda _line: None)
    amount, reason = quest_criteria.resolve_for_api(
        api_name, quest_id, player_level=player_level)
    if amount is None:
        log("LUA_QUEST_PAYOUT %s quest=%d character=%d refused=%s"
            % (api_name, quest_id, character_id, reason))
        return None, reason

    def _refuse(why: str, extra: str = "") -> Tuple[None, str]:
        log("LUA_QUEST_PAYOUT %s quest=%d character=%d refused=%s "
            "unpaid=%d %s%s"
            % (api_name, quest_id, character_id, why, amount.amount,
               amount.log_fields(), extra))
        return None, why

    if isinstance(character_id, bool) or not isinstance(character_id, int) \
            or character_id <= 0:
        return _refuse(REFUSE_NO_CHARACTER)
    if amount.amount < 0:
        return _refuse(REFUSE_NEGATIVE)
    if amount.amount == 0:
        return _refuse(REFUSE_NOTHING_TO_PAY)
    if store is None:
        return _refuse(REFUSE_NO_STORE)
    if not _has_atomic_add(store):
        return _refuse(REFUSE_STORE_NOT_ATOMIC)

    column = KIND_COLUMN[amount.kind]
    try:
        balance_after = store.add_typed_attribute(
            character_id, column, amount.amount)
    except Exception as exc:  # noqa: BLE001 - deliberate, see docstring
        return _refuse(REFUSE_STORE_ERROR,
                       " err=%s: %s" % (type(exc).__name__, exc))
    if isinstance(balance_after, bool) or not isinstance(balance_after, int):
        # A store that answers with something other than an integer balance
        # has not honoured the contract above; believing it would put a
        # non-number into a log line that reads like a measurement.
        return _refuse(REFUSE_STORE_ERROR,
                       " err=balance_after=%r" % (balance_after,))
    payout = Payout(api_name=api_name, quest_id=quest_id,
                    character_id=character_id, column=column,
                    amount=amount, balance_after=balance_after)
    log("LUA_QUEST_PAYOUT %s quest=%d %s"
        % (api_name, quest_id, payout.log_fields()))
    return payout, None
