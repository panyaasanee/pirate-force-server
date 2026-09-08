"""Persisted structural Backpack states at the exact V111 boundary.

The item contents are limited to the exact initial or post-merge snapshots.
HYP-PF-010 permits those known items to move between free Backpack slots while
preserving every other ItemAttr field.  Occupied-slot behavior, item creation,
equipment, and ownership semantics remain outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


BACKPACK_BASE_MASK = 0xFF
BACKPACK_BASE_IDENTITY = 0
BACKPACK_RANGE_MASK = 1


@dataclass(frozen=True)
class ItemAttrState:
    identity: int
    template_id: int
    quantity: int
    slot: int
    raw_u8_38: int = 0
    raw_u8_39: int = 0xFF
    detail_present: int = 0


@dataclass(frozen=True)
class BackpackState:
    base_mask: int
    base_identity: int
    range_mask: int
    items: tuple[ItemAttrState, ...]


INITIAL_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        ItemAttrState(1, 2600001, 1, 0),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(3, 2600001, 1, 2),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

MERGED_V111_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        ItemAttrState(1, 2600001, 2, 0),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

# PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
HYPOTHESIZED_V111_SLOT2_BACKPACK = BackpackState(
    BACKPACK_BASE_MASK,
    BACKPACK_BASE_IDENTITY,
    BACKPACK_RANGE_MASK,
    (
        # Identity order is retained from the exact merged snapshot.  Its
        # reconnect use after the move is part of HYP-PF-008, not original
        # server evidence.
        ItemAttrState(1, 2600001, 2, 2),
        ItemAttrState(2, 2400901, 1, 1),
        ItemAttrState(4, 2200002, 1, 3),
    ),
)

#: The slot HYP-PF-008 moves the surviving identity-1 stack to -- the one
#: identity 3 vacates when the V111 merge folds it away.  Named rather than
#: spelled 2 at the call site so ``hypothesized_v111_slot2_state`` and the
#: constant below cannot drift apart silently; pinned against
#: ``HYPOTHESIZED_V111_SLOT2_BACKPACK`` by
#: ``tests/test_starting_bag_gates.py::
#: test_the_slot2_move_derives_the_golden_it_used_to_compare_against``.
V111_SLOT2_DESTINATION = 2

V111_MERGE_REQUEST_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
    "ED 4B 0B 00 0B 04 14 00 00 00 00 32 03 00 00 00 "
    "00 00 00 00"
)
V111_MERGE_FIELDS = (4, 0, 3)
V111_MERGE_PAYLOAD = V111_MERGE_REQUEST_PC[20:]


def _item_content_signature(item: ItemAttrState) -> tuple[int, ...]:
    return (
        item.identity, item.template_id, item.quantity,
        item.raw_u8_38, item.raw_u8_39, item.detail_present,
    )


#: Every bag a character can be BORN holding.  One tuple, read by all three
#: content gates below and -- through them -- by the gate-2 admission module
#: and by ``store.apply_v111_stack_merge``.
#:
#: IT IS NOT YET EVERY GATE, and the first draft of this comment claimed it
#: was.  pf-adversary found three more comparisons against the singular
#: ``MERGED_V111_BACKPACK`` in ``runtime.py`` (the committed-merge check, the
#: item-move capture, the HYP-PF-008 move), one of which RAISES AFTER the
#: merge is committed.  ``runtime.py`` is chief's file, outside this lane's
#: write zone, so those three are a CORE-REQUEST, not an edit -- see
#: ``notes_to_chief/20260908_0206_LANE-DB-CORE-REQUEST-*``.  Until that lands,
#: widening the set below is NOT safe on its own.  COO-DECISION 20260907_2342 made this lane the
#: owner of that widening.
#:
#: Today it holds ONE bag, which is the same bag it held when the gates
#: compared against ``INITIAL_BACKPACK`` by name: this commit changes the
#: SHAPE of the rule ("is the bag in the starting set") without changing the
#: set, so no character's answer moves.  LANE-CS owns the contents:
#: ``class_starting_gear.starting_backpack_states()`` (their PR #1091, NOT on
#: main at the time of writing) returns five, one per class in
#: ``class_catalog.CLASS_IDS`` order.
#:
#: ~~"their letter pins that its FIRST entry is this very object rather than
#: an equal copy -- which is what keeps every character alive today admitted
#: by identity"~~ IS STRUCK AS FALSE OF THIS CODE (pf-adversary): every gate
#: here compares with ``==``, and a deep-equal but distinct first entry passes
#: the whole suite.  Their identity pin is a good thing for them to hold; this
#: lane must not make it load-bearing for something it does not use.
STARTING_BACKPACKS: tuple[BackpackState, ...] = (INITIAL_BACKPACK,)


def merged_v111_state(before: BackpackState) -> BackpackState:
    """The exact V111 post-merge state for one starting bag.

    The merge is "identity 3's stack folds into identity 1, and identity 3
    goes"; it touches neither the weapon row nor the base fields.  DERIVING
    the post-state instead of comparing against one constant is what lets the
    starting set grow: the day a class is born holding a different weapon, its
    merged bag differs from ``MERGED_V111_BACKPACK`` in exactly that row, and
    a constant post-state check would reject a merge it had just performed --
    leaving the row already written.  Pinned against the measured constant
    end to end by ``tests/test_starting_bag_gates.py::
    test_the_stack_merge_follows_the_set_from_inventory_alone`` (there is no
    ``test_inventory_starting_set`` module; this docstring named one for
    three rounds and `git grep` returns nothing for it).

    Raises ``ValueError`` if the rows the merge needs are not both present,
    or if the summed stack leaves the u16 range ``require_backpack_shape``
    enforces, rather than silently returning a state no loadable bag can ever
    equal.  A caller asking for the post-state of a bag that cannot merge has
    a bug, and a quiet answer here becomes a post-state check that passes on
    an unchanged row.  ``can_merge_v111`` is the question to ask first.
    """
    by_identity = {item.identity: item for item in before.items}
    target = by_identity.get(1)
    source = by_identity.get(3)
    if target is None or source is None:
        raise ValueError("the V111 merge needs identities 1 and 3")
    if target.template_id != source.template_id:
        raise ValueError("the V111 merge needs one template on both rows")
    total = target.quantity + source.quantity
    if not 0 <= total <= 0xFFFF:
        # The sibling mutator (merge_known_item_into_occupied_slot) refuses
        # here too.  Without this the derived state is one no bag can ever
        # equal, because require_backpack_shape rejects the quantity -- a
        # silently dead entry in the golden set rather than a loud refusal.
        raise ValueError("merged stack leaves the u16 quantity range")
    merged_rows = tuple(
        replace(item, quantity=total) if item.identity == 1 else item
        for item in before.items
        if item.identity != 3
    )
    return replace(before, items=merged_rows)


def can_merge_v111(before: BackpackState) -> bool:
    """Whether ``merged_v111_state`` can answer for this bag.

    A starting bag with no identity 3 has no V111 merged counterpart, and
    that is a FACT about the bag, not an error: it can never reach one, so
    there is nothing for a gate to admit.  Asking this first is what keeps
    one such bag in LANE-CS's table from being a package-wide import failure
    -- which is what the first draft of this module shipped, because it
    derived the merged tuple at import time and let the ValueError escape.
    pf-adversary measured it: one three-item bag and `import
    pirateforce_foundation.session` dies, so nobody logs in at all, instead
    of one gate refusing one bag.
    """
    try:
        merged_v111_state(before)
    except ValueError:
        return False
    return True


def merged_v111_states() -> tuple[BackpackState, ...]:
    """The post-merge counterpart of every starting bag that has one.

    A FUNCTION, and computed per call, for two measured reasons.  It reads
    ``STARTING_BACKPACKS`` live, so a reader cannot hold a stale copy of a
    set that is about to become LANE-CS's call; and it cannot fail at import
    time, which is what an import-time derivation did the moment a starting
    bag had no identity 3 (see ``can_merge_v111``).

    Bags that cannot merge are OMITTED rather than raising: they have no
    merged state to admit, so omitting one narrows nothing.  It is therefore
    NOT always index-aligned with ``STARTING_BACKPACKS`` -- ``golden_names``
    in the admission module derives its two halves from the two real lengths
    for exactly this reason.
    """
    return tuple(
        merged_v111_state(state)
        for state in STARTING_BACKPACKS
        if can_merge_v111(state)
    )


# HYP-PF-008 (the ledger annotation for this file sits on the constant above:
# docs/HYPOTHESIS_LEDGER.json declares one emitter per file per hypothesis).
def hypothesized_v111_slot2_state(merged: BackpackState) -> BackpackState:
    """The HYP-PF-008 post-state for ONE already-merged bag.

    The move is "the surviving identity-1 stack goes to the slot identity 3
    vacated"; it touches no other row and no base field.  DERIVING it is the
    same lesson ``merged_v111_state`` records one screen up, arriving one
    gate later: ``store.apply_hypothesized_v111_slot2_move`` compared its
    pre-state and its post-state against the single
    ``HYPOTHESIZED_V111_SLOT2_BACKPACK``/``MERGED_V111_BACKPACK`` pair, so
    the day a class is born holding a different weapon the move it had just
    performed failed its own post-state check and rolled back.  chief's
    ``R404`` letter (``notes_to_chief/20260908_1703_FROM_CHIEF_R404-*``)
    named those two comparisons as the half of CORE-REQUEST ``0206`` that
    stayed in this lane's zone.

    Raises the same way ``move_known_item_to_free_slot`` does -- ``KeyError``
    when identity 1 is not in the bag, ``FileExistsError`` when slot 2 is
    still occupied -- rather than answering with a state no bag can equal.
    ``can_move_v111_slot2`` is the question to ask first.
    """
    transition = move_known_item_to_free_slot(merged, 1, V111_SLOT2_DESTINATION)
    if transition is None:
        raise ValueError("the HYP-PF-008 move needs identity 1 off slot 2")
    after, _moved = transition
    return after


def can_move_v111_slot2(merged: BackpackState) -> bool:
    """Whether ``hypothesized_v111_slot2_state`` can answer for this bag.

    A merged bag whose identity 1 is already on slot 2, or that has no
    identity 1 at all, has no HYP-PF-008 counterpart -- a FACT about the bag.
    Asking this first is what keeps one such bag in LANE-CS's five-class
    table from turning ``hypothesized_v111_slot2_states`` into a raise, the
    failure mode ``can_merge_v111`` was written for one function earlier.
    """
    try:
        hypothesized_v111_slot2_state(merged)
    except (ValueError, KeyError, FileExistsError):
        return False
    return True


def hypothesized_v111_slot2_states() -> tuple[BackpackState, ...]:
    """The HYP-PF-008 counterpart of every merged bag that has one.

    A FUNCTION, computed per call, for the reasons ``merged_v111_states``
    states: it reads the live starting set, and it cannot fail at import.
    Bags without a counterpart are OMITTED, so it is NOT index-aligned with
    ``merged_v111_states()``.
    """
    return tuple(
        hypothesized_v111_slot2_state(state)
        for state in merged_v111_states()
        if can_move_v111_slot2(state)
    )


def _content_allowlist() -> tuple[tuple[tuple[int, ...], ...], ...]:
    """The content signatures ``require_known_backpack`` admits.

    Computed per call rather than frozen at import, for the same reason
    ``merged_v111_states`` is a function: a module-level snapshot keeps
    answering with the set that existed at import time.
    """
    return tuple(
        tuple(_item_content_signature(item) for item in state.items)
        for state in STARTING_BACKPACKS + merged_v111_states()
    )


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in [{minimum},{maximum}]")
    return value


def require_backpack_shape(value: Any) -> BackpackState:
    """Accept any structurally well-formed Backpack, regardless of contents.

    This is the character-select load gate (``store._load_backpack``).  It
    used to be ``require_known_backpack`` below, which also rejects any
    content outside the two exact golden snapshots -- meaning a real player
    whose bag no longer matches either snapshot (a picked-up item, a used
    consumable) could never load their own character again.  Structure
    (column types, bounds, unique identity/slot) is everything this gate is
    allowed to demand; content is this function's business, not this one's.
    """
    if type(value) is not BackpackState:
        raise ValueError("backpack must be an exact BackpackState")
    _require_int(value.base_mask, "backpack base mask", 0, 0xFF)
    _require_int(value.base_identity, "backpack base identity", 0, 0xFFFFFFFFFFFFFFFF)
    _require_int(value.range_mask, "backpack range mask", 0, 0xFF)
    if type(value.items) is not tuple:
        raise ValueError("backpack items must be an exact tuple")
    identities: set[int] = set()
    slots: set[int] = set()
    for item in value.items:
        if type(item) is not ItemAttrState:
            raise ValueError("backpack item must be an exact ItemAttrState")
        _require_int(item.identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF)
        _require_int(item.template_id, "item template", 0, 0xFFFFFFFF)
        _require_int(item.quantity, "item quantity", 0, 0xFFFF)
        _require_int(item.slot, "item slot", 0, 39)
        _require_int(item.raw_u8_38, "item raw +0x38", 0, 0xFF)
        _require_int(item.raw_u8_39, "item raw +0x39", 0, 0xFF)
        _require_int(item.detail_present, "item detail presence", 0, 1)
        if item.identity in identities or item.slot in slots:
            raise ValueError("backpack identity/slot must be unique")
        identities.add(item.identity)
        slots.add(item.slot)
    return value


def require_known_backpack(value: Any) -> BackpackState:
    """Accept exact known contents with unique slots in the visible 40-slot bag.

    Still the gate for every item-content-aware operation (moving, merging,
    swapping a known item) -- HYP-PF-010/017/018 stay scoped to the two exact
    snapshots below until a real item model lands (``M5``).  It is no longer
    the gate the character-select LOAD path (``store._load_backpack``) runs
    (that is ``require_backpack_shape`` above), and, per COO-DECISION
    20260828_0844 (mob-pickup gate-3 scope grant to lane B), it is no longer
    the gate ``make_backpack_attr``'s wire encoder runs either -- that
    function now calls ``require_backpack_shape`` directly so it can
    serialize a structurally valid bag holding a picked-up item.  This
    function's own two-golden restriction is unchanged for the move/swap/
    merge family; widening it further is still out of scope.
    """
    value = require_backpack_shape(value)
    content = tuple(_item_content_signature(item) for item in value.items)
    if content not in _content_allowlist():
        raise ValueError("backpack contents are outside the governed V111 allowlist")
    return value


def is_unmoved_baseline(value: Any) -> bool:
    """Return whether a state is one of the production-neutral snapshots.

    "The two snapshots" was true while every character was born holding the
    same bag.  It is now every starting bag and its merged counterpart.  The
    gate-2 admission module builds its goldens from these same two tuples
    rather than keeping a second copy, so the two gates cannot drift apart
    the way the ``ast`` guard over this function's source used to watch for.
    """
    return value in STARTING_BACKPACKS or value in merged_v111_states()


# PF-HYPOTHESIS-LEDGER: HYP-PF-010 active
def move_known_item_to_free_slot(
    value: BackpackState, item_identity: int, destination_slot: int,
) -> tuple[BackpackState, ItemAttrState] | None:
    """Purely move one known item, rejecting unknown or occupied destinations.

    ``None`` is the exact same-slot no-op.  The caller persists and emits only
    after this pure transition has passed all structural checks.
    """
    value = require_known_backpack(value)
    item_identity = _require_int(
        item_identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF,
    )
    destination_slot = _require_int(destination_slot, "destination slot", 0, 39)
    matches = [item for item in value.items if item.identity == item_identity]
    if len(matches) != 1:
        raise KeyError(f"unknown Backpack item identity: {item_identity}")
    current = matches[0]
    if current.slot == destination_slot:
        return None
    if any(item.slot == destination_slot for item in value.items):
        raise FileExistsError(f"Backpack slot is occupied: {destination_slot}")
    moved = replace(current, slot=destination_slot)
    after = replace(
        value,
        items=tuple(moved if item.identity == item_identity else item for item in value.items),
    )
    return require_known_backpack(after), moved


# PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
def swap_known_item_with_occupied_slot(
    value: BackpackState, item_identity: int, destination_slot: int,
) -> tuple[BackpackState, ItemAttrState, ItemAttrState]:
    """Purely swap one known item with the different item occupying the target.

    This transition owns only the occupied-destination case: the same-slot
    no-op and every free destination belong to ``move_known_item_to_free_slot``
    (HYP-PF-010) and never reach this function.  Both items keep every
    ItemAttr field except ``slot``; the destination occupant moves to the
    source's previous slot.  Unknown identities, out-of-range slots, same-slot
    requests, and unoccupied destinations all raise and therefore fail closed
    at the caller with no write and no reply.
    """
    value = require_known_backpack(value)
    item_identity = _require_int(
        item_identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF,
    )
    destination_slot = _require_int(destination_slot, "destination slot", 0, 39)
    matches = [item for item in value.items if item.identity == item_identity]
    if len(matches) != 1:
        raise KeyError(f"unknown Backpack item identity: {item_identity}")
    current = matches[0]
    if current.slot == destination_slot:
        raise ValueError("same-slot request is owned by the free-slot no-op lane")
    occupants = [item for item in value.items if item.slot == destination_slot]
    if len(occupants) != 1:
        raise LookupError(f"Backpack slot is not occupied: {destination_slot}")
    occupant = occupants[0]
    moved = replace(current, slot=destination_slot)
    displaced = replace(occupant, slot=current.slot)
    after = replace(
        value,
        items=tuple(
            moved if item.identity == current.identity
            else displaced if item.identity == occupant.identity
            else item
            for item in value.items
        ),
    )
    return require_known_backpack(after), moved, displaced


# PF-HYPOTHESIS-LEDGER: HYP-PF-018 active
def merge_known_item_into_occupied_slot(
    value: BackpackState, item_identity: int, destination_slot: int,
) -> tuple[BackpackState, ItemAttrState, ItemAttrState]:
    """Purely merge one known item into the same-template occupant of its target.

    This transition owns only the occupied-destination case whose occupant
    carries the same template and identical variant bytes: the occupying
    target survives with the summed quantity and the source item is consumed.
    The same-slot no-op and every free destination belong to
    ``move_known_item_to_free_slot`` (HYP-PF-010) and never reach this
    function; a different-template or different-variant occupant raises, as
    do unknown identities, out-of-range slots, same-slot requests,
    unoccupied destinations, quantity sums beyond the u16 wire bound, and
    any post-state outside the governed allowlist (which is what keeps the
    reversed merge direction fail-closed).  Every raise fails closed at the
    caller with no write and no reply.
    """
    value = require_known_backpack(value)
    item_identity = _require_int(
        item_identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF,
    )
    destination_slot = _require_int(destination_slot, "destination slot", 0, 39)
    matches = [item for item in value.items if item.identity == item_identity]
    if len(matches) != 1:
        raise KeyError(f"unknown Backpack item identity: {item_identity}")
    current = matches[0]
    if current.slot == destination_slot:
        raise ValueError("same-slot request is owned by the free-slot no-op lane")
    occupants = [item for item in value.items if item.slot == destination_slot]
    if len(occupants) != 1:
        raise LookupError(f"Backpack slot is not occupied: {destination_slot}")
    occupant = occupants[0]
    if occupant.template_id != current.template_id:
        raise ValueError("occupied destination holds a different template")
    if (current.raw_u8_38, current.raw_u8_39, current.detail_present) != (
        occupant.raw_u8_38, occupant.raw_u8_39, occupant.detail_present
    ):
        raise ValueError("occupied destination holds a different item variant")
    merged_quantity = occupant.quantity + current.quantity
    if merged_quantity > 0xFFFF:
        raise ValueError("merged quantity exceeds the u16 wire bound")
    merged = replace(occupant, quantity=merged_quantity)
    after = replace(
        value,
        items=tuple(
            merged if item.identity == occupant.identity else item
            for item in value.items
            if item.identity != current.identity
        ),
    )
    return require_known_backpack(after), merged, current


def make_item_move_delta_response(
    legacy: Any, moved_item: ItemAttrState,
) -> tuple[bytes, bytes]:
    """Serialize the exact ItemOperate result shape for one complete ItemAttr.

    The serializer is independently pinned against frozen V141 for the accepted
    identity-1/slot-2 golden.  Other known items reuse the same exact structural
    codec; original-server selection policy remains HYP-PF-008.
    """
    if type(moved_item) is not ItemAttrState:
        raise TypeError("moved item must be an exact ItemAttrState")
    _require_int(moved_item.identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF)
    _require_int(moved_item.template_id, "item template", 0, 0xFFFFFFFF)
    _require_int(moved_item.quantity, "item quantity", 0, 0xFFFF)
    _require_int(moved_item.slot, "item slot", 0, 39)
    _require_int(moved_item.raw_u8_38, "item raw +0x38", 0, 0xFF)
    _require_int(moved_item.raw_u8_39, "item raw +0x39", 0, 0xFF)
    _require_int(moved_item.detail_present, "item detail presence", 0, 1)
    item_wire = (
        legacy.qwordtag(0x32, moved_item.identity)
        + legacy.u32tag(0x14, moved_item.template_id)
        + legacy.u16tag(0x0F, moved_item.quantity)
        + legacy.u16tag(0x0F, moved_item.slot)
        + legacy.u8tag(0x08, moved_item.raw_u8_38)
        + legacy.u8tag(0x08, moved_item.raw_u8_39)
        + legacy.u8tag(0x0B, moved_item.detail_present)
    )
    item_bag = (
        legacy.u8tag(0x0B, BACKPACK_BASE_MASK)
        + legacy.qwordtag(0x32, BACKPACK_BASE_IDENTITY)
        + legacy.u16tag(0x0F, 1)
        + item_wire
        + legacy.u16tag(0x0F, 0)
    )
    payload = (
        legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 1)
        + item_bag
        + legacy.u8tag(0x08, 0)
    )
    result = legacy.make_runtime_vitals([(
        legacy.ITEM_OPERATE_RES_VITAL, 2, payload,
    )])
    if moved_item == HYPOTHESIZED_V111_SLOT2_BACKPACK.items[0]:
        expected = legacy.make_item_operate_move_delta_success(2, 2)
        if result != expected:
            raise RuntimeError("generic item-move response drifted from V141 golden")
    return result


def _item_attr_wire(legacy: Any, item: ItemAttrState) -> bytes:
    """Serialize one complete ItemAttr with the frozen tagged primitives."""
    if type(item) is not ItemAttrState:
        raise TypeError("item must be an exact ItemAttrState")
    _require_int(item.identity, "item identity", 0, 0x7FFFFFFFFFFFFFFF)
    _require_int(item.template_id, "item template", 0, 0xFFFFFFFF)
    _require_int(item.quantity, "item quantity", 0, 0xFFFF)
    _require_int(item.slot, "item slot", 0, 39)
    _require_int(item.raw_u8_38, "item raw +0x38", 0, 0xFF)
    _require_int(item.raw_u8_39, "item raw +0x39", 0, 0xFF)
    _require_int(item.detail_present, "item detail presence", 0, 1)
    return (
        legacy.qwordtag(0x32, item.identity)
        + legacy.u32tag(0x14, item.template_id)
        + legacy.u16tag(0x0F, item.quantity)
        + legacy.u16tag(0x0F, item.slot)
        + legacy.u8tag(0x08, item.raw_u8_38)
        + legacy.u8tag(0x08, item.raw_u8_39)
        + legacy.u8tag(0x0B, item.detail_present)
    )


def make_item_swap_delta_response(
    legacy: Any, moved_item: ItemAttrState, displaced_item: ItemAttrState,
) -> tuple[bytes, bytes]:
    """Serialize the ItemOperate result shape carrying both swapped ItemAttrs.

    The structure is byte-identical to the accepted single-item delta response
    except that the first ItemBag collection carries exactly two complete
    ItemAttr payloads (moved item first, displaced occupant second) and its
    count word says 2.  The exact client response-apply loop
    (ITEM-MOVE-CONSUMER-001) applies each ItemAttr of the first collection as
    a complete replacement -- clear-by-identity then place-by-slot -- so both
    swapped items are re-placed in either order without an occupancy gate.
    Whether the original server ever answered an occupied-destination move
    this way is explicitly not claimed (HYP-PF-017).
    """
    if type(moved_item) is not ItemAttrState or type(displaced_item) is not ItemAttrState:
        raise TypeError("swap response requires two exact ItemAttrState items")
    if moved_item.identity == displaced_item.identity:
        raise ValueError("swap response requires two distinct item identities")
    if moved_item.slot == displaced_item.slot:
        raise ValueError("swap response requires two distinct destination slots")
    item_bag = (
        legacy.u8tag(0x0B, BACKPACK_BASE_MASK)
        + legacy.qwordtag(0x32, BACKPACK_BASE_IDENTITY)
        + legacy.u16tag(0x0F, 2)
        + _item_attr_wire(legacy, moved_item)
        + _item_attr_wire(legacy, displaced_item)
        + legacy.u16tag(0x0F, 0)
    )
    payload = (
        legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 1)
        + item_bag
        + legacy.u8tag(0x08, 0)
    )
    return legacy.make_runtime_vitals([(
        legacy.ITEM_OPERATE_RES_VITAL, 2, payload,
    )])


def make_item_merge_delta_response(
    legacy: Any, merged_item: ItemAttrState, consumed_identity: int,
) -> tuple[bytes, bytes]:
    """Serialize the ItemOperate merge result: one survivor, one removal.

    The structure is byte-identical to the live-accepted V111 stack-merge
    response: the first ItemBag collection carries exactly one complete
    ItemAttr payload (the surviving target with the summed quantity, count
    word 1) and the second collection removes exactly the consumed source
    identity (count word 1, one identity).  For the exact V111 case
    (identity 3 into identity 1 at slot 0) the result is pinned byte for
    byte against the frozen V141 golden that the real client accepted at
    runtime; other governed cases reuse the same exact structural codec
    (HYP-PF-018).
    """
    if type(merged_item) is not ItemAttrState:
        raise TypeError("merge response requires an exact ItemAttrState")
    consumed_identity = _require_int(
        consumed_identity, "consumed item identity", 0, 0x7FFFFFFFFFFFFFFF,
    )
    if consumed_identity == merged_item.identity:
        raise ValueError("merge response requires two distinct item identities")
    if merged_item.quantity < 2:
        raise ValueError("merged quantity must cover at least two stacks")
    item_bag = (
        legacy.u8tag(0x0B, BACKPACK_BASE_MASK)
        + legacy.qwordtag(0x32, BACKPACK_BASE_IDENTITY)
        + legacy.u16tag(0x0F, 1)
        + _item_attr_wire(legacy, merged_item)
        + legacy.u16tag(0x0F, 1)
        + legacy.qwordtag(0x32, consumed_identity)
    )
    payload = (
        legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 1)
        + item_bag
        + legacy.u8tag(0x08, 0)
    )
    result = legacy.make_runtime_vitals([(
        legacy.ITEM_OPERATE_RES_VITAL, 2, payload,
    )])
    if (
        merged_item == MERGED_V111_BACKPACK.items[0]
        and consumed_identity == 3
    ):
        expected = legacy.make_item_operate_stack_merge_success()
        if result != expected:
            raise RuntimeError(
                "generic item-merge response drifted from the V111 golden"
            )
    return result


def make_backpack_attr(legacy: Any, state: BackpackState) -> bytes:
    """Serialize any structurally valid Backpack using frozen tagged primitives.

    COO-DECISION 20260828_0844 widened this encoder's gate from
    ``require_known_backpack`` (the two exact V111 golden snapshots only) to
    ``require_backpack_shape`` (structure only, same gate ``store.
    _load_backpack`` already runs) -- the narrow scope that decision granted:
    generalize the WIRE ENCODER past the two goldens, nothing more.  Drift in
    ``INITIAL_BACKPACK`` still byte-pins below exactly as before (the inline
    check against ``legacy.make_backpack_attr_four_items()``); drift in
    ``MERGED_V111_BACKPACK`` is caught one layer out, by
    ``tests/test_item_lifecycle.py``'s own golden-hash comparison against
    ``tests/golden/item_lifecycle_v1.json`` -- that asymmetry predates this
    round and this round does not change it.  This does NOT by itself make a
    picked-up item survive a relog: ``session.select_and_start``'s
    ``is_unmoved_baseline`` gate (Gate 2, mob_pickup.py's THE WALL) still
    refuses any non-baseline bag before this encoder would ever run for one,
    and that gate is unchanged and out of this decision's scope.  Persisting
    a claimed item (an actual ``character_backpack_items`` INSERT) is a
    separate decision this round does not make either -- ``mob_pickup.
    dispatch_pickup_request`` keeps logging ``MOB_PICKUP_ROW_WOULD_INSERT``
    rather than writing one.
    """
    state = require_backpack_shape(state)
    required = {
        "BACKPACK_ATTR": 0x1F81,
        "V103_ITEM_SEQUENCE": 1,
        "V103_ITEM_TEMPLATE": 2600001,
        "V110_CASK_SEQUENCE": 2,
        "V110_CASK_TEMPLATE": 2400901,
        "V111_STACK_SOURCE_SEQUENCE": 3,
        "V123_BLADE_SEQUENCE": 4,
        "V123_BLADE_TEMPLATE": 2200002,
        "V120_BACKPACK_BASE_RANGE_MASK": 1,
    }
    for name, expected in required.items():
        if getattr(legacy, name, None) != expected:
            raise ValueError(f"frozen inventory constant drift: {name}")

    output = bytearray()
    output += legacy.u8tag(0x0B, state.base_mask)
    output += legacy.qwordtag(0x32, state.base_identity)
    output += legacy.u16tag(0x0F, len(state.items))
    for item in state.items:
        output += legacy.qwordtag(0x32, item.identity)
        output += legacy.u32tag(0x14, item.template_id)
        output += legacy.u16tag(0x0F, item.quantity)
        output += legacy.u16tag(0x0F, item.slot)
        output += legacy.u8tag(0x08, item.raw_u8_38)
        output += legacy.u8tag(0x08, item.raw_u8_39)
        output += legacy.u8tag(0x0B, item.detail_present)
    output += legacy.u16tag(0x0F, len(state.items))
    for item in state.items:
        output += legacy.qwordtag(0x32, item.identity)
    output += legacy.u8tag(0x0B, state.range_mask)
    result = bytes(output)
    if state == INITIAL_BACKPACK and result != legacy.make_backpack_attr_four_items():
        raise RuntimeError("typed initial Backpack drifted from frozen V141")
    return result


def parse_merge_candidate(legacy: Any, parsed: Any) -> tuple[int, int, int] | None:
    """Recognize the exact tuple as a candidate, never as authorization.

    A trailing suffix is deliberately still a candidate so a malformed copy of
    the accepted request cannot fall through to the broader frozen handler.
    The separate exact-request predicate rejects that suffix.
    """
    if parsed.nested_id != legacy.ITEM_OPERATE_REQ_VITAL:
        return None
    payload = bytes(parsed.nested_payload)
    if payload.startswith(V111_MERGE_PAYLOAD):
        return V111_MERGE_FIELDS
    try:
        fields = legacy.parse_item_operate_req(parsed)
    except (ValueError, TypeError):
        return None
    return fields if fields == V111_MERGE_FIELDS else None


def is_exact_merge_request(legacy: Any, parsed: Any) -> bool:
    """Require the complete accepted 36-byte request, not just the field tuple."""
    return (
        parse_merge_candidate(legacy, parsed) == V111_MERGE_FIELDS
        and parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_version == 0
        and parsed.raw_pc == V111_MERGE_REQUEST_PC
    )
