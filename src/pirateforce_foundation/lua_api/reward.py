"""LANE-Q: the WRITE half of the quest reward seam -- and why it refuses.

WHAT THE READ HALF ALREADY DOES.  ``lua_api.quest_criteria`` resolves what
one of the six ``Quest.Add*Criteria*`` names would pay, out of the game's
own shipped tables, exactly (round ``wn088m``: the multiplier is recovered
through float32 so the product stops coming out one unit short).  Round
``xlk7hl`` gave the number a level, round ``wn088m`` gave it a quest id.
The number has been correct and STRANDED ever since: nothing pays it.

WHAT THIS MODULE IS.  The one seam between a reward number and a
character row, in three doors: :func:`pay` (the amount comes out of the
game's own criteria tables), :func:`grant` (the amount is an argument the
script wrote) and, from round ``2euu94``, :func:`charge` (the amount goes
the OTHER WAY -- two shipped quests take the player's money).  All three
share one closed refusal set and one rule: nothing is written when
anything is refused, and no refusal ever raises into a running script.

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
from ..store import (
    InsufficientSkillPointsError,
    InsufficientTypedAttributeError,
    UnmeasuredSkillPointsError,
    UnmeasuredTypedAttributeError,
)

#: The four store exception types :func:`charge` must tell apart, grouped
#: by WHAT THEY MEAN TO A PLAYER rather than by which door raised them.
#:
#: WHY THIS MODULE IMPORTS ``store`` AT ALL, when every other seam here is
#: a structural :class:`Protocol` and nothing else in ``lua_api`` imports
#: it.  The adding door could stay ignorant: ``add_typed_attribute``
#: either wrote or raised, and every raise means the same thing to a
#: caller ("nothing happened"), so :func:`_store_delta` folds them all
#: into one ``store_error``.  The SUBTRACTING door cannot: "the player
#: cannot afford the ship" is a NORMAL OUTCOME of ``q_ship.lua`` that the
#: quest should keep running past, and "the store is broken" is not, and
#: the ONLY thing that separates them on the wire is the exception's
#: TYPE.  LANE-DB built two distinct types for exactly this reason and
#: warned by letter (``pf_bridge/notes_to_chief/20260907_2226_LANE-DB-TO-
#: Q-the-spend-door-exists-and-what-it-refuses.md``) that catching the
#: wrong one is how an UNPAID charge gets read as PAID.  Matching on
#: class names instead of the classes would be the same bug wearing a
#: disguise, so the types are imported and the coupling is stated here.
#: Measured, not assumed: ``store`` imports nothing from ``lua_api``, so
#: this direction has no cycle.
_INSUFFICIENT_ERRORS = (
    InsufficientTypedAttributeError, InsufficientSkillPointsError)
_UNMEASURED_ERRORS = (
    UnmeasuredTypedAttributeError, UnmeasuredSkillPointsError)

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

#: Reward kind -> the name of the store method that SUBTRACTS from that
#: kind's column.  Not derivable from :data:`KIND_COLUMN`: two of the
#: three columns are served by the generic door and the third has a door
#: of its own, and that split is LANE-DB's, not this lane's.
#:
#: ``skill_points`` IS THE WHOLE REASON THIS MAP EXISTS.  ``store.
#: COLUMNS_WITH_THEIR_OWN_SPEND_DOOR`` makes
#: ``spend_typed_attribute(cid, "skill_points", n)`` raise ``ValueError``
#: BEFORE it reads the row -- deliberately, because a column with two
#: subtracting doors has two refusal shapes and a caller that catches the
#: wrong one reads "not paid" as "paid".  So this lane routes that kind to
#: ``spend_skill_points`` instead of discovering the refusal at runtime.
#: A test pins this map against ``store.COLUMNS_WITH_THEIR_OWN_SPEND_DOOR``
#: in BOTH directions, so the day LANE-DB gives another column its own
#: door, this map fails loudly rather than sending a charge into a
#: ``ValueError`` that :func:`charge` would report as ``store_error``.
SPEND_DOOR: dict[str, str] = {
    quest_criteria.KIND_EXP: "spend_typed_attribute",
    quest_criteria.KIND_CASH: "spend_typed_attribute",
    quest_criteria.KIND_SKILL_POINT: "spend_skill_points",
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
#: :func:`charge` only.  The store has no subtracting door of the shape
#: :data:`SPEND_DOOR` names for this kind -- the mirror of
#: :data:`REFUSE_STORE_NOT_ATOMIC` on the adding side, and a SEPARATE
#: token because a store can perfectly well have one and not the other
#: (every store in this repository did, between round ``yfeauz`` and
#: LANE-DB's round ``dcz2sv``), and a census that could not tell those two
#: apart would have read "the spend door is missing" as "the store is
#: missing".
REFUSE_STORE_CANNOT_SPEND = "store_has_no_atomic_spend"
#: :func:`charge` only.  The row exists, the balance is measured, and it
#: does not cover the charge -- the player cannot afford it.  A NORMAL
#: GAME OUTCOME, not an error: ``q_ship.lua`` charges for a ship the
#: player may not be able to buy, and the quest script keeps running.
#: Nothing was written: the store raises inside the same transaction it
#: read in, before any ``UPDATE`` (``store.spend_typed_attribute``
#: contract 3).
REFUSE_INSUFFICIENT = "balance_does_not_cover_it"
#: :func:`charge` only.  The column is NULL: nobody has ever measured this
#: player's balance, so there is nothing to subtract FROM.  Distinct from
#: :data:`REFUSE_INSUFFICIENT` on purpose and for the reason
#: ``COO-DECISION 20260901_1059`` gives -- reporting an unmeasured balance
#: as "cannot afford it" would be this lane guessing the zero the store
#: refuses to guess, and the two need different fixes (grant the player a
#: starting balance vs. tell them they are short).
REFUSE_UNMEASURED = "balance_was_never_measured"

#: :func:`balance` only.  The store has no ``read_typed_attributes``, the
#: read counterpart of :data:`REFUSE_STORE_NOT_ATOMIC` /
#: :data:`REFUSE_STORE_CANNOT_SPEND`.  Its own token rather than
#: ``store_error`` because "this store cannot answer the question at all"
#: is a WIRING fault of ours, while ``store_error`` is a database that
#: tried and failed -- a census that folds them together cannot tell a
#: half-built process from a sick one.
REFUSE_STORE_CANNOT_READ = "store_has_no_typed_attribute_read"

#: Every reason this module itself can produce.  A test asserts
#: :func:`pay` never returns a reason outside this set union
#: ``quest_criteria``'s.
REFUSALS: frozenset = frozenset({
    REFUSE_NO_STORE, REFUSE_STORE_NOT_ATOMIC, REFUSE_NO_CHARACTER,
    REFUSE_NOTHING_TO_PAY, REFUSE_NEGATIVE, REFUSE_STORE_ERROR,
    REFUSE_UNKNOWN_KIND, REFUSE_BAD_AMOUNT,
    REFUSE_STORE_CANNOT_SPEND, REFUSE_INSUFFICIENT, REFUSE_UNMEASURED,
    REFUSE_STORE_CANNOT_READ,
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

    NEGATIVE AMOUNTS ARE REFUSED, AND THE GAP THAT USED TO BE IS CLOSED.
    ``Player.AddCash(-Quest.Var3)`` exists in the corpus
    (``gamedata/lua/Quest/q_ship.lua:50``, ``q_boat_health.lua:21``): a
    quest that CHARGES the player. ``store.add_typed_attribute`` takes
    ``delta >= 0`` only, deliberately (its own docstring: a subtracting door
    has to answer "what happens at the floor", and this repository already
    has that answer in ``spend_skill_points``). So the spend half was a
    letter to LANE-DB rather than a sign flip here -- and LANE-DB answered
    it: ``store.spend_typed_attribute`` is on ``origin/main``, :func:`charge`
    is the door onto it, and ``Player.AddCash`` opened this round.

    THIS FUNCTION STILL REFUSES NEGATIVES, and that is not left over: the
    sign is resolved by the CALLER now (``lua_api.player``'s signed
    coercion picks :func:`grant` or :func:`charge`), so a negative reaching
    HERE is a caller that did not, and turning it into a charge would make
    one door with two directions -- exactly the shape LANE-DB refused to
    build on their side, for the same reason.
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


class QuestChargeStore(Protocol):
    """The two methods this lane needs to SUBTRACT, and why they are two.

    Asked of LANE-DB as a letter on 2026-09-07
    (``pf_bridge/notes_to_chief/20260907_1942_LANE-Q-TO-DB-add-typed-
    attribute-needs-a-spend-door.md``) and ANSWERED the same day
    (``20260907_2226_LANE-DB-TO-Q-the-spend-door-exists-and-what-it-
    refuses.md``): ``store.SQLiteStore.spend_typed_attribute`` is on
    ``origin/main``.  So the reason ``Player.AddCash`` was stubbed --
    written out at length in ``lua_api.player.STILL_STUBBED``'s
    ``_STAT_SPEND`` text and in :func:`grant`'s docstring -- is gone, and
    this round is where the name opens.

    ``spend_typed_attribute(character_id, column, amount) -> int``
    ``spend_skill_points(character_id, cost) -> int``

    * BOTH take a MAGNITUDE, never a sign.  A negative ``amount`` is a
      ``ValueError``, not a silent addition.  The corpus's minus sign
      (``Player.AddCash(-Quest.Var3)``) is therefore resolved on THIS side
      of the seam, where the script that wrote it can be cited, which is
      the split LANE-DB asked for by name.
    * ONE ``BEGIN IMMEDIATE`` each, the read and the ``UPDATE`` inside it.
    * NEVER GUESS ZERO: a NULL column raises rather than being treated as
      an empty purse.
    * A balance that does not cover the amount raises, and the row keeps
      the value it had -- not clamped to the floor, never negative.
    * Both return the balance AFTER the subtraction, read back inside the
      same transaction.

    WHY TWO METHODS AND NOT ONE.  ``skill_points`` already had a
    subtracting door before the generic one existed, and
    ``store.COLUMNS_WITH_THEIR_OWN_SPEND_DOOR`` makes the generic door
    REFUSE that column rather than become a second door onto it.  That is
    a deliberate guard, not an omission: two doors on one column raise two
    different "insufficient" types, and ``skill_grant_wiring.py`` /
    ``skill_learn_wiring.py`` already document
    ``InsufficientSkillPointsError`` as THE refusal of the skill-point
    spend path, so a charge arriving through the generic door would raise
    a type their ``except`` clauses do not catch -- an unpaid charge read
    as paid.  :data:`SPEND_DOOR` is this lane's half of that agreement.

    WHAT THIS SIDE STILL CANNOT CHECK, said as plainly as the adding door
    says it: atomicity is not observable from a caller, and neither is
    "the row really moved".  See :func:`_store_spend` for the ONE
    post-condition this door can check and why it is weaker than the
    adding door's.
    """

    def spend_typed_attribute(self, character_id: int, column: str,
                              amount: int) -> int:
        ...  # pragma: no cover - protocol declaration

    def spend_skill_points(self, character_id: int, cost: int) -> int:
        ...  # pragma: no cover - protocol declaration


@dataclass(frozen=True)
class Charge:
    """One amount actually taken OFF a row, and what the row became.

    The mirror of :class:`Grant`.  ``amount`` is the MAGNITUDE that was
    subtracted (always positive), never the negative number the script
    wrote: the sign is a fact about the call site, and the log line says
    ``charged=`` rather than ``paid=`` so a reader of the log never has to
    work out which direction a bare number went.
    """

    api_name: str
    character_id: int
    column: str
    amount: int
    balance_after: int

    def log_fields(self) -> str:
        return ("character=%d column=%s charged=%d balance_after=%d"
                % (self.character_id, self.column, self.amount,
                   self.balance_after))


def _spend_door(store: Any, kind: str) -> Optional[Callable[..., Any]]:
    """The bound subtracting method for ``kind``, or ``None``.

    A capability check of the same shape :func:`_has_atomic_add` uses, for
    the same reason: ``Protocol`` is structural, and what matters is that
    the attribute is CALLABLE, not that some class claims a base.

    THE ``try`` IS NOT DEFENSIVE PADDING; it was measured.  ``getattr(x,
    n, default)`` only swallows ``AttributeError``, so an object whose
    ``__getattr__`` raises anything else takes the exception straight out
    through :func:`charge`, which promises never to raise.  That object is
    not hypothetical -- ``tests/test_script_lua_api_reward.py``'s
    ``RmwTripwireStore`` raises ``AssertionError`` from ``__getattr__`` on
    purpose, and it is the store a caller hands over between the day the
    adding door landed and the day the spend door did.  ``_has_atomic_add``
    has the same hole on the adding side and is left alone this round:
    fixing it is a one-line change in code round ``yfeauz`` shipped and
    tested, and doing it here would put an untested edit in a diff whose
    subject is the other door.
    """
    try:
        door = getattr(store, SPEND_DOOR[kind], None)
    except Exception:                                    # noqa: BLE001
        return None
    return door if callable(door) else None


def can_charge(store: Any, kind: str) -> bool:
    """Whether ``store`` can SUBTRACT for ``kind`` -- the public half.

    Exists for one caller and one rule (pf-adversary `D5`, round
    ``2euu94``): a namespace name that can charge must not PAY through a
    store that cannot charge.  ``lua_api.player``'s signed closure asks
    this before it grants, because an add-only store would otherwise pay
    that name's rewards and refuse its charges -- the free ship, reached
    through the store's shape instead of through the sign.
    """
    return kind in SPEND_DOOR and _spend_door(store, kind) is not None


def _store_spend(store: Any, kind: str, character_id: int, column: str,
                 amount: int) -> Tuple[Optional[int], Optional[str],
                                       Optional[str]]:
    """Hand one POSITIVE magnitude to the right subtracting door.

    Returns ``(balance_after, None, None)`` when the store honoured the
    :class:`QuestChargeStore` contract, and ``(None, reason, extra)``
    otherwise, where ``reason`` is one of :data:`REFUSE_INSUFFICIENT`,
    :data:`REFUSE_UNMEASURED` or :data:`REFUSE_STORE_ERROR`.

    THE CLASSIFICATION IS THE POINT, and it is why this is not just
    :func:`_store_delta` with a different method name.  On the adding side
    every raise means one thing and one token is enough.  Here three
    outcomes that are indistinguishable as "an exception happened" have to
    stay apart, because only one of them is a bug:

    * ``Insufficient*`` -- the player cannot afford it.  Expected.  The
      row is untouched (the store raises inside the read transaction,
      before any ``UPDATE``), and the quest script keeps running.
    * ``Unmeasured*`` -- the column is NULL, so there is no balance to
      subtract from.  Also not a bug, and NOT the same as being short:
      ``COO-DECISION 20260901_1059`` forbids collapsing the two.
    * anything else -- schema drift, a write-lock timeout, a missing
      character, a ``ValueError`` from a door that refuses this column.
      Those are ``store_error``.

    ``KeyError`` (character does not exist / soft-deleted) is deliberately
    left in the last bucket rather than given a token of its own: this
    lane already refuses ``character_id <= 0`` before the store is
    reached, so a ``KeyError`` from here means the caller passed an id it
    believed in and the store disagreed, which is exactly the "something
    is wrong" the generic token is for.

    THE POST-CONDITION HERE IS WEAKER THAN THE ADDING DOOR'S, AND THAT IS
    NOT HIDDEN.  :func:`_store_delta` can assert ``balance_after >=
    delta``, which kills a ``return 0`` store outright.  Subtracting has
    no such lever: this lane never reads a balance (by design -- see the
    module docstring), so every non-negative answer is arithmetically
    possible for SOME starting balance, and ``return 0`` is in fact the
    correct answer whenever a player spends their last coin.  What is
    checked is what can be: the answer is an ``int``, not a ``bool``, and
    not negative -- the last one because every column in
    :data:`KIND_COLUMN` carries ``CHECK(... BETWEEN 0 AND ...)`` in
    migration 006, so a negative answer is a store reporting a row state
    its own schema forbids.  A store that answers ``0`` to everything
    would be believed here.  Naming that is better than a check that
    looks stronger than it is.
    """
    door = _spend_door(store, kind)
    if door is None:            # pragma: no cover - caller checks first
        return None, REFUSE_STORE_CANNOT_SPEND, None
    try:
        if SPEND_DOOR[kind] == "spend_skill_points":
            balance_after = door(character_id, amount)
        else:
            balance_after = door(character_id, column, amount)
    except _INSUFFICIENT_ERRORS as exc:
        return None, REFUSE_INSUFFICIENT, " err=%s: %s" % (
            type(exc).__name__, exc)
    except _UNMEASURED_ERRORS as exc:
        return None, REFUSE_UNMEASURED, " err=%s: %s" % (
            type(exc).__name__, exc)
    except Exception as exc:  # noqa: BLE001 - deliberate, see charge()
        return None, REFUSE_STORE_ERROR, " err=%s: %s" % (
            type(exc).__name__, exc)
    if isinstance(balance_after, bool) or not isinstance(balance_after, int):
        return None, REFUSE_STORE_ERROR, " err=balance_after=%r" % (
            balance_after,)
    if balance_after < 0:
        return None, REFUSE_STORE_ERROR, (
            " err=balance_after=%d is negative: the store reported a row "
            "state its own CHECK constraint forbids" % (balance_after,))
    return balance_after, None, None


def charge(api_name: str, kind: str, character_id: int, amount: int, *,
           store: Optional[Any] = None,
           log: Optional[Callable[[str], None]] = None,
           ) -> Tuple[Optional[Charge], Optional[str]]:
    """Take an amount OFF a row, or say exactly why not.

    The third door onto this seam, and the one the corpus has been waiting
    for: ``gamedata/lua/Quest/q_ship.lua:50`` calls
    ``Player.AddCash(-Quest.Var3)`` and ``q_boat_health.lua:21`` calls
    ``Player.AddCash(Quest.Var2 * -1)`` -- the "buy the ship" and "repair
    the ship" quests, which take the player's money.  Until this existed,
    opening ``Player.AddCash`` would have paid the four positive call
    sites and silently dropped the two negative ones, which is a free
    ship; so the name stayed stubbed and the missing half was a letter to
    LANE-DB rather than a sign flip on the adding door.

    ``amount`` IS A MAGNITUDE AND MUST BE POSITIVE.  The minus sign in the
    script is resolved by the CALLER (``lua_api.player``'s signed
    coercion), on the side of the seam where the call site can be cited.
    A negative reaching here is a caller that has not done that, and it is
    refused rather than turned into a payment by a double negative --
    which would be this door quietly becoming :func:`grant`.

    ``kind`` comes from the CALLING CLOSURE, never from a script, and
    selects both the column (:data:`KIND_COLUMN`) and the store door
    (:data:`SPEND_DOOR`).  No Lua value and no shipped table cell is ever
    concatenated into a column name -- the discipline the module docstring
    describes, unchanged.

    NEVER RAISES FOR A REFUSAL, including the one that is a normal game
    outcome.  A player who cannot afford the ship gets
    ``refused=balance_does_not_cover_it`` and the script keeps running to
    its next line, because a host that dies on an unaffordable purchase
    turns one declined transaction into a whole quest file logged as
    broken.

    ALL-OR-NOTHING, AND WITH ONE FEWER HOLE THAN THE ADDING DOOR.  Every
    refusal :func:`grant` can produce after a COMMIT (a non-int answer, an
    impossible balance) exists here too, so a caller that retries on
    ``store_error`` can still charge twice and no idempotency key has been
    written -- this door does not retry either.  What is NOT ambiguous
    here is the affordability refusal: ``InsufficientTypedAttributeError``
    and ``InsufficientSkillPointsError`` are raised BEFORE any ``UPDATE``,
    inside the transaction the read ran in, so
    ``refused=balance_does_not_cover_it`` means the row is untouched and a
    retry is safe.  That distinction is the entire value of LANE-DB's
    separate exception types, and it only survives because this module
    matches on the TYPES rather than on a message or a class name.
    """
    log = log or (lambda _line: None)

    def _refuse(why: str, extra: str = "") -> Tuple[None, str]:
        log("LUA_PLAYER_CHARGE %s character=%s kind=%s refused=%s "
            "uncharged=%r%s"
            % (api_name, character_id, kind, why, amount, extra))
        return None, why

    if kind not in KIND_COLUMN or kind not in SPEND_DOOR:
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
    if _spend_door(store, kind) is None:
        return _refuse(REFUSE_STORE_CANNOT_SPEND)

    column = KIND_COLUMN[kind]
    balance_after, reason, extra = _store_spend(
        store, kind, character_id, column, amount)
    if reason is not None:
        return _refuse(reason, extra or "")
    charged = Charge(api_name=api_name, character_id=character_id,
                     column=column, amount=amount,
                     balance_after=balance_after)
    log("LUA_PLAYER_CHARGE %s %s" % (api_name, charged.log_fields()))
    return charged, None


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


class QuestBalanceStore(Protocol):
    """The one method this lane needs to READ a balance back.

    ``read_typed_attributes(character_id) -> dict[str, int | float]``

    * Returns ONLY the columns that HAVE a value.  A NULL column is
      OMITTED, never rendered as ``0`` -- LANE-DB's own docstring calls
      that omission load-bearing, and it is what lets :func:`balance`
      answer "nobody has ever measured this purse" instead of guessing an
      empty one (``COO-DECISION 20260901_1059``).
    * Raises ``KeyError`` for a character that does not exist or has been
      soft-deleted.
    * Raises ``WriteLockTimeout`` (a ``sqlite3.OperationalError``) under
      contention rather than a bare operational error.
    """

    def read_typed_attributes(self, character_id: int) -> dict:
        ...  # pragma: no cover - structural


def _has_typed_read(store: Any) -> bool:
    """True when ``store`` offers the :class:`QuestBalanceStore` method."""
    return callable(getattr(store, "read_typed_attributes", None))


def balance(api_name: str, kind: str, character_id: int, *,
            store: Optional[Any] = None,
            log: Optional[Callable[[str], None]] = None,
            ) -> Tuple[Optional[int], Optional[str]]:
    """The balance of one kind's column, or exactly why there is none.

    The FOURTH door onto this seam, and the first that only reads.  It
    exists because a shipped quest asks the question before it spends:
    ``gamedata/lua/Quest/q_class.lua:47`` is
    ``if (Player.GetCash() >= Quest.Var3)`` over ``n_VARI_3 = 15000``, and
    ``q_boat_health.lua:17`` is the same shape over the repair price.  With
    ``Player.GetCash`` stubbed at ``0`` those guards were DEAD -- the else
    branch ran every time -- and :func:`charge`'s own docstring names the
    consequence in the other direction: ``q_ship.lua`` charges and then
    hands over the ship with no check of its own, so a player who cannot
    afford it gets the ship anyway and only the log knows.

    WHY THIS DOES NOT CONTRADICT THE MODULE DOCSTRING.  That text forbids
    READ-MODIFY-WRITE -- reading a balance in order to compute a new one
    and writing it back across two connections, which eats a concurrent
    writer.  This function never writes, is never called by :func:`pay`,
    :func:`grant` or :func:`charge`, and hands its answer to a Lua
    comparison, not to an ``UPDATE``.  The write doors still take the
    store's word for what a balance BECAME; they do not consult this one.
    The value is therefore a snapshot and is documented as one: a script
    that reads a purse and then spends from it races anything else moving
    that column, and the SPEND is what settles it -- ``spend_typed_
    attribute`` re-reads inside its own ``BEGIN IMMEDIATE`` and raises
    ``Insufficient*`` rather than going negative.  That is the game's own
    behaviour too: the client's purse is a snapshot between frames.

    ``(value, None)`` or ``(None, reason)``, never raising, the same
    contract the other three doors carry.  An ABSENT column is
    :data:`REFUSE_UNMEASURED`, never ``0``: "we have never measured this
    player's cash" and "this player has no cash" are different answers,
    and the caller that turns the refusal into a stub default is the one
    that has to say so in its own log line.
    """
    log = log or (lambda _line: None)

    def _refuse(why: str, extra: str = "") -> Tuple[None, str]:
        log("LUA_PLAYER_READ %s character=%s kind=%s refused=%s%s"
            % (api_name, character_id, kind, why, extra))
        return None, why

    if kind not in KIND_COLUMN:
        return _refuse(REFUSE_UNKNOWN_KIND)
    if isinstance(character_id, bool) or not isinstance(character_id, int) \
            or character_id <= 0:
        return _refuse(REFUSE_NO_CHARACTER)
    if store is None:
        return _refuse(REFUSE_NO_STORE)
    if not _has_typed_read(store):
        return _refuse(REFUSE_STORE_CANNOT_READ)

    column = KIND_COLUMN[kind]
    try:
        values = store.read_typed_attributes(character_id)
    except Exception as exc:  # noqa: BLE001 - deliberate, see charge()
        return _refuse(REFUSE_STORE_ERROR,
                       " err=%s: %s" % (type(exc).__name__, exc))
    try:
        present = column in values
    except Exception as exc:  # noqa: BLE001 - a store that answered garbage
        return _refuse(REFUSE_STORE_ERROR,
                       " err=%s: %s" % (type(exc).__name__, exc))
    if not present:
        return _refuse(REFUSE_UNMEASURED)
    value = values[column]
    if isinstance(value, bool) or not isinstance(value, int):
        # A float is refused rather than truncated: every column in
        # KIND_COLUMN is declared INTEGER in migration 006, so a float
        # here is schema drift, and rounding it would hand a Lua
        # comparison a number no row holds.
        return _refuse(REFUSE_STORE_ERROR, " err=value=%r" % (value,))
    if value < 0:
        return _refuse(REFUSE_STORE_ERROR, (
            " err=value=%d is negative: the store reported a row state its "
            "own CHECK constraint forbids" % (value,)))
    log("LUA_PLAYER_READ %s character=%d kind=%s column=%s balance=%d"
        % (api_name, character_id, kind, column, value))
    return value, None
