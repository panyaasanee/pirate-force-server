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
  * the console gets ``MOB_PICKUP_ROW_LOST`` FIRST, naming the row that is
    gone from the ground and absent from the database -- the one event in
    this lane that costs a player an item, printed rather than inferred;
  * every later pickup in that session refuses before the take
    (``cell_disagrees_with_the_database``), so one lost drop does not become
    a session of silently diverging bags.

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


def row_lost_console_line(row_write: Any, exc: Any) -> str:
    """The line for the one event in this lane that costs a player an item.

    LOST, not REFUSED: everything else this module says no to leaves the drop
    on the ground.  This line means the drop is off the ground and the row is
    not in the database, and it names the row so an operator can put it back
    by hand if the owner ever asks.  Its token is deliberately unlike the
    other two -- a grep for ``MOB_PICKUP_ROW_`` finds all three, and a grep
    for ``MOB_PICKUP_ROW_LOST`` finds only the losses.
    """
    return (
        "MOB_PICKUP_ROW_LOST table=character_backpack_items "
        "claimant=0x%X character_id=%d item_identity=%d template_id=%d "
        "quantity=%d slot=%d - the drop left the ground and the write "
        "failed: %r" % (
            row_write.claimant_identity, row_write.character_id,
            row_write.item_identity, row_write.template_id,
            row_write.quantity, row_write.slot, exc)
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
        # character selected" (store._require_selected_session).  Reported
        # under its own name because it is the one answer here that may mean
        # a client asked for somebody else's character, rather than a machine
        # having a bad day.
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
    # NOT WRAPPED IN A try, AND THE REASON IS THE READ ORDER ABOVE.
    # ``next_item_identity`` raises this lane's SIBLING exception
    # (identity_high_water_below_the_bag) when a mark lags its own bag, and
    # letting that reach a caller would report a persistence problem as "you
    # cannot pick that up" -- which MobPickupPersistError's docstring
    # forbids.  It cannot happen here: ``BagCell`` validates the mark against
    # the bag at construction and only ever moves it FORWARD under its own
    # lock, and the bag is read BEFORE the mark above, so the only
    # interleaving a concurrent ``commit_pickup`` can produce is an older bag
    # with a newer mark -- never the reverse.  A try/except here would be a
    # branch that cannot fire, which is the same defect as a gate that does
    # nothing.  ``test_a_cell_whose_mark_lags_its_own_bag_is_refused_at
    # _seeding`` pins where that refusal really lives.
    minted = mob_pickup.next_item_identity(cell_bag, cell_mark)
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
        # THE ONE PATH IN THIS LANE THAT COSTS A PLAYER AN ITEM.  The take
        # happened inside dispatch_pickup_request; this write did not.  The
        # store's transaction means nothing was half-written, so the loss is
        # exactly one item and not a corrupt bag -- but it IS a loss, and it
        # is printed before it is raised, because an operator reading the
        # console afterwards has no other way to know which row went missing.
        lost = console_safe(row_lost_console_line(row_write, exc))
        if echo:
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
    ground.  A failure in step 3 leaves the drop gone and nothing written, and
    that window is real; :func:`precheck_persistable` documents what is and is
    not removed from it.

    The caller still owns ``outcome.delta`` (step 4 of ``MOB_PICKUP_WIRING``)
    and gets it from ``result.outcome.delta``.  This function does not send
    bytes: it has no socket, exactly like the two modules it joins.
    """
    precheck_persistable(store, sid, character_id, bag_cell)
    outcome = mob_pickup.dispatch_pickup_request(
        bag_cell, ledger_cell, legacy, claimant_identity, x, y, z,
        object_ref_u32, opaque_u8)
    return persist_pickup(store, sid, character_id, outcome, echo=echo)
