"""LANE-B round uq2lxw: the pickup path's write half, joined to the store.

WHAT WAS MISSING, MEASURED RATHER THAN ASSERTED.  Two halves of M5's
kill -> pickup -> relog loop were on ``main`` before this file and had never
been introduced to each other:

  * ``mob_pickup.dispatch_pickup_request`` -- what ``runtime.py`` is meant to
    call on an inbound pickup request.  It takes the drop off the ground,
    composes the client's bag delta, and then only LOGS the row it would have
    written (token ``MOB_PICKUP_ROW_WOULD_INSERT``).  It has no cursor by
    design: THE WALL in that module's docstring is the reason.
  * ``store.commit_acquired_backpack_item`` (chief's ``STORE-INSERT-001``,
    merged as ``pirate-force-server#244``) -- the one method that puts an
    acquired row in the database and advances
    ``character_backpacks.next_item_identity`` in the same transaction.

``grep -rn commit_acquired_backpack_item src/`` at HEAD of round uq2lxw found
callers in ``tests/`` and in PROSE, and none in ``src/``.  So a pickup that
went all the way through the dispatch path still wrote nothing, and
``GT-142``'s S1-vs-S0 control ("did the row reach the database at all, before
relog is even involved") would have answered NO with both halves shipped and
green.  This module is that call, and nothing else.

WHAT IT IS NOT.  It is not a second pickup rule.  Every refusal that decides
whether a claim is granted still lives in ``mob_pickup``; every rule about
what a row must look like to be written still lives in ``store``.  This file
adds exactly one rule of its own, and it is about ORDER rather than about
items: see :func:`precheck_persistable`.

THE ORDER PROBLEM THIS FILE EXISTS TO SOLVE.  ``mob_pickup`` states its own
discipline plainly -- "everything that can refuse, refuses BEFORE the take",
because a refusal after the take destroys the object the player was reaching
for.  Persistence breaks that discipline by construction: the row can only be
written AFTER the drop leaves the ground, and ``store.commit_acquired_
backpack_item`` refuses in ten places of its own plus whatever SQLite raises.
The ones that DEPEND ONLY ON STATE THE CALLER ALREADY HOLDS -- this session
does not have this character selected; the identity is not the column's next
free one; the slot is occupied; the row would be malformed -- are knowable
before the take, and :func:`precheck_persistable` asks them there.

WHAT IS LEFT AFTER THAT, STATED IN THE FIRST PARAGRAPH THAT MENTIONS IT
rather than in a footnote, because an earlier draft of this file said "every
one of them is knowable BEFORE the take" and pf-adversary refuted it by
execution (a second process holding a write transaction: ``database is
locked``, the drop gone, nothing written, and a raw ``sqlite3.OperationalError``
reaching a listener thread).  A write can still fail after the take -- a
locked database, a full disk, a schema the migration did not reach.  This
module cannot prevent that.  What it does instead, since round uq2lxw:

  * the failure is re-raised as :exc:`MobPickupPersistError` with the named
    reason ``write_failed_after_the_take``, never as the store's own
    exception class, so a caller has one vocabulary to catch;
  * the database is READ BACK and the console gets one of FOUR lines --
    ``MOB_PICKUP_ROW_LOST`` (read back, not there),
    ``MOB_PICKUP_ROW_WROTE_THEN_FAILED`` (this exact row IS there),
    ``MOB_PICKUP_ROW_COLLIDED`` (another row wears the identity this pickup
    minted) or ``MOB_PICKUP_ROW_FATE_UNKNOWN`` (the read failed too).
    Printed whatever ``echo`` says, because an item that may have been
    destroyed is not a console preference.  Two earlier drafts got this
    wrong and pf-adversary measured both: one printed "LOST" on the strength
    of an exception having arrived, while the row was in the database; the
    next read the bag back but matched on the identity alone, which reports
    PRESENT for somebody else's row on the one scenario that actually
    happens;
  * every later pickup in that session refuses before its take
    (``cell_disagrees_with_the_database``), so one bad write does not become
    a session of silently diverging bags.  ~~"When it is PRESENT, the cell
    and the database agree again and the session simply continues"~~ IS
    STRUCK AS FALSE (pf-adversary, third pass, measured): the cell holds the
    row it took, the database holds whatever it holds, and they are not equal
    in any of the cases -- the safety net fires in all of them.  What differs
    between the cases is what an OPERATOR should do, which is what the lines
    say.

THE QUESTION THAT IS STILL OPEN, and it is the chief's to answer at the call
site rather than this module's: what the PLAYER is told when that happens.
The delta bytes for the item are composed before the take (``mob_pickup``
does that deliberately), so a client can be told it gained an item whose row
does not exist.  ``mob_pickup``'s NONCLAIM 16 already says the call site must
decide what the player gets; this module makes the event loud and named, and
decides nothing about the resync.

NO FLAG.  ``production_allowed = True``: this is not a scenario, not a
hypothesis, and there is no opt-in kwarg anywhere in it.

THE ONE LINE THIS LANE HANDS THE CHIEF is :data:`MOB_PICKUP_PERSIST_HEADLINE_
CALL`, and it is pinned as an EXECUTED test rather than only described --
``tests/test_mob_pickup_persist.py`` runs the exact text of it.  What is still
NOT closed by this file, stated where a reader will see it and not in a
footnote: ``runtime.py`` has no inbound pickup opcode call site at all
(``GT-124``), so no player has yet caused any of this to run.  This module
changes what happens WHEN that line is added; it does not add it, and the file
it would be added to is the chief's.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import mob_pickup


#: Shippable, no scenario flag, same convention as every other lane module.
production_allowed = True


#: The line the chief adds at the inbound pickup opcode, once ``GT-124``'s
#: call site exists.  ONE call: precheck, dispatch, persist.
MOB_PICKUP_PERSIST_HEADLINE_CALL = (
    "mob_pickup_persist.pickup_and_persist(store, sid, character_id, "
    "bag_cell, drop_ledger_cell, legacy, identity, x, y, z, object_ref_u32, "
    "opaque_u8)"
)

REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_CELL_IS_ANOTHER_CHARACTERS = "cell_is_another_characters"
REFUSE_CELL_DISAGREES_WITH_THE_DATABASE = "cell_disagrees_with_the_database"
REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS = "identity_would_not_be_the_columns"
#: The session does not have this character selected.  Its own name, not
#: ``store_cannot_be_asked``: an operator reading a log has to be able to tell
#: a client asking for a character it does not own from a disk that will not
#: answer, and the first draft of this module reported both under the second
#: name (pf-adversary, this round).
REFUSE_SESSION_DOES_NOT_OWN_THIS_CHARACTER = (
    "session_does_not_own_this_character")
REFUSE_STORE_CANNOT_BE_ASKED = "store_cannot_be_asked"
#: The one refusal in this module that means A PLAYER LOST AN ITEM: the drop
#: is off the ground and the write failed anyway.  Named separately from every
#: refusal above precisely because those all leave the world unchanged and
#: this one does not.
REFUSE_WRITE_FAILED_AFTER_THE_TAKE = "write_failed_after_the_take"

MOB_PICKUP_PERSIST_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_CELL_IS_ANOTHER_CHARACTERS,
    REFUSE_CELL_DISAGREES_WITH_THE_DATABASE,
    REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS,
    REFUSE_SESSION_DOES_NOT_OWN_THIS_CHARACTER,
    REFUSE_STORE_CANNOT_BE_ASKED,
    REFUSE_WRITE_FAILED_AFTER_THE_TAKE,
)


#: The store's own wording for "this session does not have this character
#: selected" (``store._require_selected_session``), matched on the two words
#: that carry the meaning rather than on the whole sentence, so a rewording
#: there degrades to the catch-all instead of to a wrong assertion.  COUPLING
#: HELD BY A STRING, and named as such: ``tests/test_mob_pickup_persist.py``
#: drives the real store to produce the real exception, so the day store.py
#: rewords it, that test goes red rather than the log going quietly wrong.
def _reads_as_an_ownership_refusal(exc: Any) -> bool:
    text = str(exc).lower()
    # ~~"selected" as a third disjunct~~ REMOVED (pf-adversary, third pass):
    # the shipped store emits "stale or non-owning character session" and
    # never the word "selected", so that disjunct matched nothing real while
    # matching a Windows path segment named `selected` happily.  A term that
    # can only produce false positives is not a widening, it is surface.
    return "session" in text and ("non-owning" in text or "stale" in text)


def console_safe(text: str) -> str:
    """ASCII, always, for a string this module did not compose.

    The bridge console is cp874 with ``errors='strict'``: one unmappable
    character in a ``print()`` raises, and the round-142 precedent in
    ``.github/workflows/gate-windows.yml`` is a tool that died having reported
    nothing.  Refusal details here interpolate ``%r`` of the STORE's exception
    and of a session id -- neither composed by this lane -- and a sqlite error
    naming a Windows path can carry anything.  Same shape as
    ``lane_hooks._console_safe``.
    """
    return text.encode("ascii", "backslashreplace").decode("ascii")


class MobPickupPersistError(ValueError):
    """A refusal from this module, named, in the shape the sibling lanes use.

    Deliberately NOT a subclass of ``mob_pickup.MobPickupContractError``: a
    caller reading that exception is reading a decision about the CLAIM, and
    every refusal in this file is about the write instead.  Merging the two
    would let a persistence problem be reported to the player as "you cannot
    pick that up".
    """

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_PICKUP_PERSIST_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class PersistedPickup:
    """One pickup that reached the database, and what the database then held.

    ``agrees`` is the answer to a question this lane cannot refuse its way out
    of: the bag ``mob_pickup`` composed in memory (``outcome.bag_after``) and
    the bag the store read back after committing are two independent
    derivations of one state, and they are compared.  A disagreement is
    REPORTED, not raised, and the reason is the same one the whole file is
    ordered around -- by the time it can be seen, the row is committed and the
    drop is gone, so raising would tell the caller "this failed" about
    something that happened.
    """

    outcome: Any
    bag_after_db: Any
    agrees: bool
    lines: tuple[str, ...]


def row_inserted_console_line(row_write: Any) -> str:
    """One ASCII line reporting the INSERT that RAN.  DID, not WOULD.

    Deliberately the same field order, and the same field names, as
    ``mob_pickup.bag_row_write_console_line``'s ``MOB_PICKUP_ROW_WOULD_INSERT``
    -- so a reader (or a ``GT-142`` grep) can put the two lines side by side
    and see that the row that was promised is the row that was written.  A
    different shape here would have made the comparison a transcription
    exercise.

    Pure: it returns the line and prints nothing, the way this project's other
    console composers do (``mob_loot.drops_console_line``).
    """
    if type(row_write) is not mob_pickup.BagRowWrite:
        raise MobPickupPersistError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a console line needs the typed mob_pickup.BagRowWrite the "
            "outcome carries")
    return (
        "MOB_PICKUP_ROW_INSERTED table=character_backpack_items "
        "claimant=0x%X character_id=%d item_identity=%d template_id=%d "
        "quantity=%d slot=%d" % (
            row_write.claimant_identity, row_write.character_id,
            row_write.item_identity, row_write.template_id,
            row_write.quantity, row_write.slot)
    )


#: What a read-back after a failed write found.  FOUR answers, and the count
#: is the whole point: an exception arriving is not evidence about what is in
#: the database, and neither is one field of one row.
AFTERMATH_ROW_ABSENT = "MOB_PICKUP_ROW_LOST"
AFTERMATH_ROW_PRESENT = "MOB_PICKUP_ROW_WROTE_THEN_FAILED"
#: Something else is wearing the identity this pickup minted.  This is the
#: state that ACTUALLY HAPPENS on the module's headline scenario -- the store's
#: post-take refusal is "identity N is not this character's next free
#: identity", which can only fire because somebody else's row already holds N
#: -- and a read-back that matched on identity alone called it PRESENT and
#: told the operator not to restore a row that was never written
#: (pf-adversary, third pass, measured).
AFTERMATH_ROW_COLLIDED = "MOB_PICKUP_ROW_COLLIDED"
AFTERMATH_UNKNOWN = "MOB_PICKUP_ROW_FATE_UNKNOWN"

AFTERMATH_TOKENS = (
    AFTERMATH_ROW_ABSENT,
    AFTERMATH_ROW_PRESENT,
    AFTERMATH_ROW_COLLIDED,
    AFTERMATH_UNKNOWN,
)


def aftermath_of_a_failed_write(store: Any, sid: Any, character_id: Any,
                                row_write: Any) -> str:
    """Which of the four the database actually says, by READING it.

    ROUND uq2lxw, pf-adversary's second and third passes, and the shape
    changed once in each.  The first version printed ``MOB_PICKUP_ROW_LOST``
    on the strength of "an exception reached me" -- an inference about the
    internals of a ``store`` this module only knows as ``Any``, measured
    lying with a store that commits and then raises on the way out.  The
    second version read the bag back but matched on ``item_identity`` alone,
    which is worse than it sounds: the post-take refusal that will actually
    happen is the store's identity check, and that check can only fail
    because ANOTHER row already holds the identity this pickup minted.  So
    the read was guaranteed to find "a" row and report PRESENT, naming this
    pickup's own template beside somebody else's row.

    THE WHOLE ROW IS COMPARED, in ``BagRowWrite``'s own column order, and a
    row wearing the identity but not matching it is its own answer
    (:data:`AFTERMATH_ROW_COLLIDED`).  Four states, because four is how many
    there are.
    """
    try:
        bag = store.get_backpack(sid, character_id)
    except Exception:   # noqa: BLE001 - a read that fails is its own answer
        return AFTERMATH_UNKNOWN
    items = getattr(bag, "items", None)
    try:
        wearing = [
            row for row in items
            if row.identity == row_write.item_identity
        ]
    except (TypeError, AttributeError):
        # TypeError: `items` is not iterable.  AttributeError: it is, but its
        # rows are not ItemAttrState.  BOTH have to be caught here, because
        # this runs inside persist_pickup's own except block, where an
        # uncaught one replaces the named refusal and buries the store's
        # exception in __context__ (pf-adversary, third pass: the guard was
        # added to the console composer on this exact argument and not here).
        return AFTERMATH_UNKNOWN
    if not wearing:
        return AFTERMATH_ROW_ABSENT
    try:
        mine = any(
            (row.identity, row.template_id, row.quantity, row.slot)
            == (row_write.item_identity, row_write.template_id,
                row_write.quantity, row_write.slot)
            for row in wearing
        )
    except AttributeError:
        return AFTERMATH_UNKNOWN
    return AFTERMATH_ROW_PRESENT if mine else AFTERMATH_ROW_COLLIDED


def row_lost_console_line(row_write: Any, exc: Any,
                          token: str = AFTERMATH_ROW_ABSENT) -> str:
    """The line for the one event in this lane that can cost a player an item.

    ``token`` is one of the three :func:`aftermath_of_a_failed_write` names,
    and the sentence after the row is written for the token that carries it.
    ``MOB_PICKUP_ROW_LOST`` means READ BACK AND NOT THERE -- it is the one an
    operator may act on, so it is the one that had to stop being a guess.
    A grep for ``MOB_PICKUP_ROW_`` finds every outcome this lane prints; a
    grep for ``MOB_PICKUP_ROW_LOST`` finds only the confirmed losses.
    """
    if type(row_write) is not mob_pickup.BagRowWrite:
        # Same guard the sibling composer has, and it matters MORE here: this
        # one runs inside persist_pickup's own except block, where an
        # AttributeError would replace the named refusal and bury the store's
        # exception in __context__ (pf-adversary, second pass).
        raise MobPickupPersistError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a console line needs the typed mob_pickup.BagRowWrite the "
            "outcome carries")
    if token not in AFTERMATH_TOKENS:
        # The token is the FIRST WORD of the line, which is the field an
        # operator greps.  A function that validates its row and then emits
        # any string at all as the token checks the wrong argument
        # (pf-adversary, third pass).
        raise MobPickupPersistError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "%r is not one of this module's aftermath tokens %r"
            % (token, AFTERMATH_TOKENS))
    tail = {
        AFTERMATH_ROW_ABSENT:
            "the drop left the ground and the row is NOT in the database "
            "(read back after the failure)",
        AFTERMATH_ROW_PRESENT:
            "the drop left the ground and the row IS in the database "
            "(read back after the failure) - do NOT insert it by hand; the "
            "caller was told the pickup failed and the client may disagree",
        AFTERMATH_ROW_COLLIDED:
            "the drop left the ground and ANOTHER row is wearing the "
            "identity this pickup minted (read back after the failure) - "
            "this item was NOT written; do not insert it under that identity",
        AFTERMATH_UNKNOWN:
            "the drop left the ground and the database could not be read "
            "back, so whether the row is there is UNKNOWN - check before "
            "changing anything",
    }[token]
    return (
        "%s table=character_backpack_items "
        "claimant=0x%X character_id=%d item_identity=%d template_id=%d "
        "quantity=%d slot=%d - %s: %r" % (
            token, row_write.claimant_identity, row_write.character_id,
            row_write.item_identity, row_write.template_id,
            row_write.quantity, row_write.slot, tail, exc)
    )


def disagreement_console_line(outcome: Any, bag_after_db: Any) -> str:
    """The line printed when the in-memory bag and the database disagree.

    This is a G-OBS line for a state that should be impossible: it names the
    two counts rather than saying "mismatch", because a reader of a console
    log cannot go and inspect either value afterwards.

    TOTAL BY CONSTRUCTION, and that is not a style choice.  It is composed on
    the one path :class:`PersistedPickup` documents as raise-proof -- the row
    is already committed by the time this is reached -- so a store that
    returned something without ``.items`` used to turn "report the
    disagreement" into ``AttributeError`` from inside a listener thread
    (pf-adversary, this round, with a store variant that commits and returns
    ``None``).  A value this cannot count is reported as a count it cannot
    read, never as a raise.
    """
    return (
        "MOB_PICKUP_PERSIST_DISAGREES character_id=%d item_identity=%d "
        "in_memory_rows=%d database_rows=%s - the pickup IS committed; this "
        "line says the two derivations of the bag differ, not that the write "
        "failed" % (
            outcome.row_write.character_id, outcome.row_write.item_identity,
            len(outcome.bag_after.items), _countable(bag_after_db))
    )


def _countable(bag: Any) -> str:
    """How many rows the store's read-back holds, or why that is unreadable."""
    items = getattr(bag, "items", None)
    try:
        return str(len(items))
    except TypeError:
        return "unreadable(%s)" % type(bag).__name__


def precheck_persistable(
        store: Any, sid: Any, character_id: Any, bag_cell: Any) -> int:
    """Ask, BEFORE the take, everything the write would refuse afterwards.

    Returns the identity the next pickup on this cell will mint, which is
    also the value ``store.commit_acquired_backpack_item`` will require --
    proven equal here rather than assumed, since that equality is the whole
    reason the two halves can be joined at all.

    THE THREE QUESTIONS, AND WHY EACH IS THE STORE'S OWN REFUSAL MOVED
    EARLIER:

    1. Does this session have this character selected?  The store asks it
       inside the transaction (``_require_selected_session``); asked here it
       costs one read and cannot eat a drop.  Asked by CALLING the store --
       ``backpack_issued_through`` performs exactly that check -- rather than
       by re-implementing it, so the two cannot drift.
    2. Is the cell's bag still the database's bag?  If they differ, something
       wrote to this character behind the session's back and the cell is
       allocating against a state that no longer exists: its next slot may be
       occupied, its next identity may be spent.  Both are store refusals,
       and both would arrive after the take.
    3. Would the identity the cell mints be the column's next free one?  This
       is the store's ``acquired identity %d is not this character's next
       free identity %d``, asked before rather than after.

    WHAT IT CANNOT PROMISE, and this is a real gap rather than a formality:
    nothing holds the database still between this check and the write.  A
    second writer for the same character in that window makes the write fail
    anyway -- and the store's own transaction is what keeps THAT case correct
    (it rolls back rather than stamping a stale number).  This check removes
    the failures that are certain, not the ones that are racing; the module
    docstring says what happens when a racing one lands.
    ~~"The ``BagCellRegistry`` claim is what makes a second writer in one
    process impossible"~~ IS STRUCK AS FALSE (pf-adversary, this round): the
    registry refuses a second CELL per character, and says so in its own
    docstring.  Two threads holding the ONE cell it handed out are two
    writers, and nothing here or there prevents that.

    THE BAG IS READ ONCE.  An earlier draft of this function took three
    separate snapshots of ``bag_cell.bag`` and compared them as if they were
    one; a ``commit_pickup`` on another thread landing between two of them
    gives an answer about a state that never existed.  One read, used for
    every question below.
    """
    if type(bag_cell) is not mob_pickup.BagCell:
        raise MobPickupPersistError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "the character's own typed mob_pickup.BagCell is what allocates "
            "the slot and the identity; a bag VALUE cannot be prechecked "
            "because it is not what the pickup will allocate against")
    if bag_cell.character_id != character_id:
        raise MobPickupPersistError(
            REFUSE_CELL_IS_ANOTHER_CHARACTERS,
            "this cell belongs to character %d and the write would be made "
            "under character %r; a row written under the wrong id is "
            "unreachable by the character that picked it up and unremovable "
            "by the one that owns it"
            % (bag_cell.character_id, character_id))
    cell_bag = bag_cell.bag
    cell_mark = bag_cell.issued_through
    try:
        issued_through = store.backpack_issued_through(sid, character_id)
        db_bag = store.get_backpack(sid, character_id)
    except PermissionError as exc:
        # The store's OWN way of saying "this session does not have this
        # character selected" (store._require_selected_session raises
        # PermissionError("stale or non-owning character session")).
        #
        # THE CLASS IS NOT ENOUGH TO TELL THEM APART, and keying on it alone
        # was this module's second draft (pf-adversary, second pass):
        # PermissionError is an OSError subclass, and WinError 32 -- "the
        # process cannot access the file because it is being used by another
        # process", the antivirus/backup case this project's own test helper
        # cites BY NAME for this very sqlite file -- arrives as one too.
        # Reporting that as "the session does not own this character" asserts
        # a specific, security-shaped, wrong cause.  So the store's own words
        # have to be in it; anything else is the catch-all below, which
        # asserts nothing.
        if not _reads_as_an_ownership_refusal(exc):
            raise MobPickupPersistError(
                REFUSE_STORE_CANNOT_BE_ASKED,
                console_safe(
                    "the store raised PermissionError for character %r on "
                    "session %r, and it does not read as an ownership "
                    "refusal (a file held by another process reaches here "
                    "the same way): %r"
                    % (character_id, sid, exc))) from exc
        raise MobPickupPersistError(
            REFUSE_SESSION_DOES_NOT_OWN_THIS_CHARACTER,
            console_safe(
                "session %r does not have character %r selected, so it may "
                "not write into that character's bag: %r"
                % (sid, character_id, exc))) from exc
    except Exception as exc:   # noqa: BLE001 - reported by name, see below
        # The store raises RuntimeError/ValueError/sqlite3 errors with ITS
        # wording.  Reaching the caller unwrapped, they read as "the pickup
        # code crashed"; wrapped here they read as "the write could not be
        # prepared, and here is what the store said".  The original is
        # chained, never swallowed.
        raise MobPickupPersistError(
            REFUSE_STORE_CANNOT_BE_ASKED,
            console_safe(
                "the store could not answer for character %r on session %r: "
                "%r" % (character_id, sid, exc))) from exc
    if cell_bag != db_bag:
        raise MobPickupPersistError(
            REFUSE_CELL_DISAGREES_WITH_THE_DATABASE,
            "this session's bag cell holds %d row(s) and the database holds "
            "%d for character %r; the cell is allocating against a bag that "
            "is no longer there, and the write it prepares would be refused "
            "after the drop has already left the ground"
            % (len(cell_bag.items), len(db_bag.items), character_id))
    # Both values are derived, neither is typed in: the left one is what the
    # cell will mint (from the cell's own bag and mark), the right one is what
    # the column will demand.
    # WRAPPED, AND THE ROUND CHANGED ITS MIND ABOUT THIS TWICE -- the record
    # of why is worth more than the line.  ``next_item_identity`` has TWO
    # raise sites, both this lane's SIBLING exception, and letting either
    # reach a caller reports a persistence problem as "you cannot pick that
    # up", which MobPickupPersistError's docstring forbids.
    #   - identity_high_water_below_the_bag: a mark that lags its own bag.
    #     THIS one really cannot arrive here -- BagCell validates the mark
    #     against the bag at construction, only moves it forward under its
    #     own lock, and the bag is read BEFORE the mark above, so the worst
    #     interleaving is an older bag with a newer mark.  That argument is
    #     load-bearing and unprotected by anything but itself, so a test
    #     reads this function's source and pins the two lines in that order
    #     (test_the_bag_is_read_before_the_mark_and_that_is_the_argument).
    #   - identity_block_spent: the mark is at the column ceiling.  The first
    #     draft of this comment said "a branch that cannot fire" after
    #     checking only the first raise site; pf-adversary fired this one
    #     from a constructed cell.  Today it is shielded here as well -- a
    #     mark AT the ceiling can only come from a commit_pickup, which also
    #     moves the bag, so the bag-equality check above refuses first -- but
    #     that shield is made of two checks' ORDER, which is the same shape
    #     of argument this round already got wrong once.  Caught rather than
    #     argued away, and the conversion is held by a test that injects the
    #     raise (test_a_mark_at_the_identity_ceiling_is_a_persistence_refusal).
    try:
        minted = mob_pickup.next_item_identity(cell_bag, cell_mark)
    except mob_pickup.MobPickupContractError as exc:
        raise MobPickupPersistError(
            REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS,
            "this cell cannot mint an identity to write under (%s); it "
            "cannot be re-seeded past this either - the identity space "
            "itself is what has run out" % exc.args[0]) from exc
    column = issued_through + 1
    if minted != column:
        raise MobPickupPersistError(
            REFUSE_IDENTITY_WOULD_NOT_BE_THE_COLUMNS,
            "the next pickup would mint identity %d and the database's next "
            "free identity is %d; the store would refuse the row after the "
            "take.  Re-seed the cell at character select from "
            "store.backpack_issued_through" % (minted, column))
    return minted


def persist_pickup(
        store: Any, sid: Any, character_id: Any, outcome: Any,
        *, echo: bool = True) -> PersistedPickup:
    """Write the row the outcome already promised.  The drop is already gone.

    Takes the ``PickupOutcome`` ``mob_pickup`` returned and hands its
    ``item`` -- unchanged, the same ``ItemAttrState`` whose identity is
    already on the wire in ``outcome.delta`` -- to
    ``store.commit_acquired_backpack_item``.  Nothing is recomposed here: a
    row rebuilt from the outcome's fields could differ from the one the client
    was told about, and this module would be the only place that could not
    see it.

    ``echo`` prints the ``MOB_PICKUP_ROW_INSERTED`` line (and the
    disagreement line, if any).  It is a KEYWORD-ONLY flag about the CONSOLE
    and about nothing else -- there is no mode of this function that writes
    less or checks less -- so it cannot become the opt-in gate this lane is
    forbidden to ship.  The lines are returned either way, so a caller that
    wants them somewhere other than stdout does not have to capture stdout.
    IT DOES NOT REACH THE FAILURE PATH: the aftermath line for a write that
    failed after the take is printed with ``echo`` off as well, and
    ``test_the_loss_report_is_printed_even_with_echo_off`` says so.  A caller
    quieting its console must not be quietly deciding that a possibly
    destroyed item goes unrecorded.
    """
    if type(outcome) is not mob_pickup.PickupOutcome:
        raise MobPickupPersistError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "persist_pickup needs the typed mob_pickup.PickupOutcome that "
            "dispatch_pickup_request returned")
    row_write = outcome.row_write
    if row_write.character_id != character_id:
        # NOT unreachable, and not decoration: ``persist_pickup`` is public
        # and a caller may hold an outcome from one character's cell and a
        # character id from a session -- which is the mix that writes a row
        # nobody can reach.  ``pickup_and_persist`` refuses this earlier, on
        # the CELL; this refuses it on the OUTCOME, which is the only thing
        # this function is given.  Exercised directly in the tests, because
        # an AST walk proving a raise statement exists proves nothing about
        # whether it runs (pf-adversary, this round).
        raise MobPickupPersistError(
            REFUSE_CELL_IS_ANOTHER_CHARACTERS,
            "this outcome's row is claimed under character %d and the write "
            "would be made under character %r"
            % (row_write.character_id, character_id))
    try:
        bag_after_db = store.commit_acquired_backpack_item(
            sid, character_id, outcome.item)
    except Exception as exc:   # noqa: BLE001 - the drop is already gone
        # THE ONE PATH IN THIS LANE THAT CAN COST A PLAYER AN ITEM.  The take
        # happened inside dispatch_pickup_request; this write raised.  What
        # the database actually holds is READ BACK rather than inferred -- see
        # aftermath_of_a_failed_write for the measurement that made that
        # necessary -- and the line names which of the three answers it got.
        #
        # PRINTED WHATEVER ``echo`` SAYS.  ``echo`` is a console preference
        # for the ordinary path; an item that may have been destroyed is not
        # a preference, and a caller quieting its logs must not be quietly
        # deciding that this goes unrecorded too.
        lost = console_safe(row_lost_console_line(
            row_write, exc,
            aftermath_of_a_failed_write(store, sid, character_id, row_write)))
        print(lost)
        raise MobPickupPersistError(
            REFUSE_WRITE_FAILED_AFTER_THE_TAKE, lost) from exc
    lines = [row_inserted_console_line(row_write)]
    agrees = bag_after_db == outcome.bag_after
    if not agrees:
        lines.append(disagreement_console_line(outcome, bag_after_db))
    if echo:
        for line in lines:
            print(line)
    return PersistedPickup(outcome, bag_after_db, agrees, tuple(lines))


def pickup_and_persist(
        store: Any, sid: Any, character_id: Any, bag_cell: Any,
        ledger_cell: Any, legacy: Any, claimant_identity: Any,
        x: Any, y: Any, z: Any, object_ref_u32: Any, opaque_u8: Any = 0,
        *, echo: bool = True) -> PersistedPickup:
    """Precheck, dispatch, persist.  THE line for the inbound pickup opcode.

    The order is the whole content of this function and it is not
    interchangeable:

      1. :func:`precheck_persistable` -- while the drop is still on the
         ground, so a write that cannot succeed refuses a pickup instead of
         eating it.
      2. ``mob_pickup.dispatch_pickup_request`` -- unchanged, uncalled-into,
         and still the only thing that decides whether the claim is granted.
         Its ``MOB_PICKUP_ROW_WOULD_INSERT`` line is still printed by it; the
         two lines together are the before/after a reader can compare.
      3. :func:`persist_pickup` -- the write.

    Every refusal from step 1 and step 2 is raised with the drop still on the
    ground.  A failure in step 3 leaves the drop gone and the database in one
    of the states :func:`aftermath_of_a_failed_write` reads back and names --
    ~~"nothing written"~~ IS STRUCK, it was the two-outcome claim this
    round's own read-back exists to retract.  That window is real;
    :func:`precheck_persistable` documents what is and is not removed from
    it.

    The caller still owns ``outcome.delta`` (step 4 of ``MOB_PICKUP_WIRING``)
    and gets it from ``result.outcome.delta``.  This function does not send
    bytes: it has no socket, exactly like the two modules it joins.
    """
    precheck_persistable(store, sid, character_id, bag_cell)
    outcome = mob_pickup.dispatch_pickup_request(
        bag_cell, ledger_cell, legacy, claimant_identity, x, y, z,
        object_ref_u32, opaque_u8)
    return persist_pickup(store, sid, character_id, outcome, echo=echo)
