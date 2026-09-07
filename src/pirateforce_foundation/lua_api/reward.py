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
#: :func:`grant` only.  ``pay`` takes its kind from the game's own tables
#: through ``quest_criteria``, so it cannot produce this one; ``grant``
#: takes the kind from ITS CALLER (a namespace closure naming which column
#: that API grants), and a caller naming a kind this module cannot pay is a
#: bug in this package, refused by name rather than KeyError'd into a
#: script's traceback.
REFUSE_UNKNOWN_KIND = "unknown_reward_kind"
#: :func:`grant` only.  Something that is not an ``int`` at all (a string,
#: a table, ``True``) is a DIFFERENT fact from a negative number, so it
#: refuses under its own name rather than being folded into
#: :data:`REFUSE_NEGATIVE`.
#:
#: NEITHER OF THE TWO IS REACHABLE THROUGH A LUA SCRIPT TODAY, said plainly
#: (pf-adversary D5, round yfeauz).  ``lua_api.player``'s grant closure
#: coerces with ``_coerce_int``, whose floor is 0, so a negative and a
#: string come out of it identically -- as ``None`` -- and are logged as
#: ``LUA_PLAYER_BAD_VALUE`` with NO ``refused=`` token before this module
#: is called at all.  So a census counting ``refused=`` lines sees neither
#: case, and the distinction these two constants draw is available only to
#: a caller that hands :func:`grant` an already-typed value (this lane's
#: tests today; a future closure that wants to tell a CHARGE from a
#: GARBAGE ARGUMENT must coerce with a signed door and pass the number
#: through rather than filtering it first).
REFUSE_BAD_AMOUNT = "amount_is_not_an_integer"

#: Every reason this module itself can produce.  A test asserts
#: :func:`pay` never returns a reason outside this set union
#: ``quest_criteria``'s.
REFUSALS: frozenset = frozenset({
    REFUSE_NO_STORE, REFUSE_STORE_NOT_ATOMIC, REFUSE_NO_CHARACTER,
    REFUSE_NOTHING_TO_PAY, REFUSE_NEGATIVE, REFUSE_STORE_ERROR,
    REFUSE_UNKNOWN_KIND, REFUSE_BAD_AMOUNT,
})


class QuestRewardStore(Protocol):
    """The ONE method this lane needs from a character store, and its
    contract.  Asked of LANE-DB as a ``CORE-REQUEST`` on 2026-09-07 and
    ANSWERED: ``store.SQLiteStore.add_typed_attribute`` is on ``main``
    (measured this round, ``git grep -c add_typed_attribute origin/main --
    src/pirateforce_foundation/store.py`` = 2), so :func:`pay` no longer
    refuses a real store -- it pays a real row.  What still refuses is a
    store WITHOUT the method, and that refusal is the one the reasons
    below are about.

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

    WHAT THIS SIDE CANNOT CHECK, SAID OUT LOUD (pf-adversary finding 7,
    this round).  :func:`_has_atomic_add` tests for a callable of that
    NAME.  A method named ``add_typed_attribute`` that is internally a
    read-modify-write across two connections -- precisely what D14
    forbids -- would be used here without a murmur.  Atomicity is not a
    property a caller can observe; it is a promise the implementer keeps.
    The tripwire in this lane's tests constrains THIS module, never the
    store it is handed.  That is why the contract above is written down
    here and repeated in the CORE-REQUEST rather than left implied.

    ANSWERED BY LANE-DB, AND CARRIED HERE RATHER THAN CITED (their letter
    ``pf_bridge/notes_to_chief/20260907_1453_LANE-DB-TO-Q-add-typed-
    attribute-is-on-the-branch-your-tripwire-is-turned-round.md``, and the
    method's own docstring says the same in ``store.py``): the read, the
    ``UPDATE`` and the read-back all run inside ONE ``BEGIN IMMEDIATE``,
    and ``store.connect()`` rolls the transaction back on any exception
    before re-raising.  So a RAISE out of ``add_typed_attribute`` means
    NOTHING was committed.

    THAT SENTENCE IS ABOUT ``store.py``, AND THE PARAGRAPH THIS DOCSTRING
    BUILT ON IT WAS TOO WIDE (pf-adversary D6, round ``h20x7g``, correcting
    round ``95aw54``'s wording).  It used to read "a retry pays exactly
    once" and "the half-paid case cannot be produced".  Both are false of
    :func:`pay`, whatever is true of the store: :func:`pay` has TWO refusal
    branches that run AFTER the store has already committed -- a return
    that is not an ``int``, and a ``balance_after`` smaller than the delta
    -- and both report ``refused=store_error``, indistinguishable to a
    caller from the raising case.  A store wrapper that commits and returns
    ``None`` increments the row, logs ``refused=store_error``, and a caller
    who believed the old sentence and retried would pay TWICE.  What the
    letter's guarantee actually buys is narrower and is all that is claimed
    here: a retry after a RAISE pays once.

    ALSO CORRECTED: the letter cited above is titled ``add_typed_attribute``
    **is not on main yet**.  The method IS on ``origin/main`` now, so the
    conclusion stands -- but it stands on the grep, not on that letter, and
    quoting the letter as the authority for the opposite of its own
    headline is the kind of citation this lane has been caught making
    before.

    WHAT IS STILL NOT PROMISED, so this is not read as more than it is: a
    process killed between ``COMMIT`` and return is outside that guarantee
    and needs an idempotency key nobody has written.  :func:`pay` therefore
    still does not retry, and a caller that adds a retry loop owes that key
    first.
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


def _store_delta(store: Any, character_id: int, column: str,
                 delta: int) -> Tuple[Optional[int], Optional[str]]:
    """Hand one POSITIVE delta to the store and check what comes back.

    Returns ``(balance_after, None)`` when the store honoured the
    :class:`QuestRewardStore` contract, and ``(None, extra)`` otherwise,
    where ``extra`` is the ``" err=..."`` tail the caller appends to its own
    ``refused=store_error`` line.  ONE implementation for both doors
    (:func:`pay`, criteria-resolved, and :func:`grant`, caller-supplied), so
    a store that lies cannot be believed by one of them and caught by the
    other.

    THREE THINGS ARE CHECKED, and each one has already been the hole:

    * The call RAISED.  Per LANE-DB's contract (``store.py``'s own
      ``add_typed_attribute`` docstring, and ``store.connect()`` rolling
      back before re-raising) a raise means NOTHING was committed.
    * The answer is not an ``int``.  A store that answers with something
      else has not honoured the contract, and believing it would put a
      non-number into a log line that reads like a measurement.
    * The answer is BELOW the delta.  Until round ``95aw54`` the token was
      compared against nothing, so a store whose ``add_typed_attribute``
      was ``return 0`` -- the ``mov al,1; ret`` of stores, writing nothing
      -- produced a line reading ``paid=1050 balance_after=0`` with no
      refusal.  Why this invariant and not a stronger one: all three
      columns in :data:`KIND_COLUMN` carry ``CHECK(... BETWEEN 0 AND ...)``
      in migration 006 and every ``delta`` reaching here is positive (both
      callers refuse zero and negative first), so ``balance_after >=
      delta`` holds for ANY correct atomic add regardless of what the
      balance was before -- which this lane deliberately never reads.

    WHAT IS STILL NOT CHECKABLE FROM THIS SIDE, unchanged by moving the
    code: the two refusal branches after the store has already COMMITTED (a
    non-int answer, a too-small balance) are indistinguishable to a caller
    from the raising case, so a caller that retries on ``store_error`` can
    pay twice.  Neither door retries, and a caller that adds a retry loop
    owes an idempotency key nobody has written.
    """
    try:
        balance_after = store.add_typed_attribute(character_id, column, delta)
    except Exception as exc:  # noqa: BLE001 - deliberate, see pay()'s docstring
        return None, " err=%s: %s" % (type(exc).__name__, exc)
    if isinstance(balance_after, bool) or not isinstance(balance_after, int):
        return None, " err=balance_after=%r" % (balance_after,)
    if balance_after < delta:
        return None, (" err=balance_after=%d is below the delta it was "
                      "asked to add (%d): the store reported a write that "
                      "cannot have happened" % (balance_after, delta))
    return balance_after, None


@dataclass(frozen=True)
class Grant:
    """One EXPLICIT amount that actually reached a row.

    The sibling of :class:`Payout` for the other door.  No
    :class:`quest_criteria.CriteriaAmount` here on purpose: a
    ``Player.AddExp(n)`` amount does not come out of a shipped table, it
    comes out of the running script (``Player.GetLv()*Trigger.Var5`` in
    ``t_getm_rat_exp&sp.lua``), so there is no base/level/multiplier
    provenance to carry and pretending otherwise would be the invention
    this lane refuses.  What IS carried is which API asked, which column
    moved, and what the store said the balance became.
    """

    api_name: str
    character_id: int
    column: str
    amount: int
    balance_after: int

    def log_fields(self) -> str:
        return ("character=%d column=%s paid=%d balance_after=%d"
                % (self.character_id, self.column, self.amount,
                   self.balance_after))


def grant(api_name: str, kind: str, character_id: int, amount: int, *,
          store: Optional[Any] = None,
          log: Optional[Callable[[str], None]] = None,
          ) -> Tuple[Optional[Grant], Optional[str]]:
    """Pay an amount the SCRIPT named, or say exactly why not.

    The second door onto the same seam :func:`pay` uses, for the API names
    whose amount is an argument rather than a table row --
    ``Player.AddExp``/``Player.AddSkillPoint`` today.  Same store contract,
    same closed refusal set, same all-or-nothing posture, and the same
    never-raise rule: a refusal here leaves the calling Lua script running,
    because a host that dies on an unpaid grant turns one missing reward
    into a whole quest file logged as broken.

    ``kind`` is one of ``quest_criteria.KIND_*`` and comes from the CALLING
    CLOSURE, never from a script: no cell of any shipped table and no Lua
    value is ever concatenated into a column name, the same discipline the
    module docstring describes for :data:`KIND_COLUMN`.

    ``amount`` must already be a coerced non-negative ``int`` -- the
    namespace closure that read it off the Lua stack owns that coercion
    (``lua_api.player._coerce_int``).  A ``bool``, a non-``int`` or a
    negative is REFUSED rather than trusted, because this door is also
    reachable from a future closure whose coercion is not yet written.

    NEGATIVE AMOUNTS ARE REFUSED, AND THAT IS A REAL GAP, NOT AN OVERSIGHT.
    ``Player.AddCash(-Quest.Var3)`` exists in the corpus
    (``gamedata/lua/Quest/q_ship.lua:50``, ``q_boat_health.lua:21``): a
    quest that CHARGES the player. ``store.add_typed_attribute`` takes
    ``delta >= 0`` only, deliberately (its own docstring: a subtracting door
    has to answer "what happens at the floor", and this repository already
    has that answer in ``spend_skill_points``). So the spend half is a
    letter to LANE-DB, not a sign flip here, and ``Player.AddCash`` stays
    stubbed until it exists -- see ``lua_api.player.STILL_STUBBED``.
    """
    log = log or (lambda _line: None)

    def _refuse(why: str, extra: str = "") -> Tuple[None, str]:
        log("LUA_PLAYER_GRANT %s character=%s kind=%s refused=%s unpaid=%r%s"
            % (api_name, character_id, kind, why, amount, extra))
        return None, why

    if kind not in KIND_COLUMN:
        return _refuse(REFUSE_UNKNOWN_KIND)
    if isinstance(character_id, bool) or not isinstance(character_id, int) \
            or character_id <= 0:
        return _refuse(REFUSE_NO_CHARACTER)
    if isinstance(amount, bool) or not isinstance(amount, int):
        return _refuse(REFUSE_BAD_AMOUNT)
    if amount < 0:
        return _refuse(REFUSE_NEGATIVE)
    if amount == 0:
        return _refuse(REFUSE_NOTHING_TO_PAY)
    if store is None:
        return _refuse(REFUSE_NO_STORE)
    if not _has_atomic_add(store):
        return _refuse(REFUSE_STORE_NOT_ATOMIC)

    column = KIND_COLUMN[kind]
    balance_after, err = _store_delta(store, character_id, column, amount)
    if err is not None:
        return _refuse(REFUSE_STORE_ERROR, err)
    granted = Grant(api_name=api_name, character_id=character_id,
                    column=column, amount=amount,
                    balance_after=balance_after)
    log("LUA_PLAYER_GRANT %s %s" % (api_name, granted.log_fields()))
    return granted, None


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
    balance_after, err = _store_delta(store, character_id, column,
                                      amount.amount)
    if err is not None:
        return _refuse(REFUSE_STORE_ERROR, err)
    payout = Payout(api_name=api_name, quest_id=quest_id,
                    character_id=character_id, column=column,
                    amount=amount, balance_after=balance_after)
    log("LUA_QUEST_PAYOUT %s quest=%d %s"
        % (api_name, quest_id, payout.log_fields()))
    return payout, None
