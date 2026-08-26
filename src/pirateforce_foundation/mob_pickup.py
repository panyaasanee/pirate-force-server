"""LANE-B / MOB-PICKUP-001: the drop a monster left becomes a row in the bag.

WHAT THIS MODULE IS FOR.  ``BUILD-006`` / M5 is "loot drops, you pick it up, it
is in your bag after a relog".  ``mob_loot`` (MOB-LOOT-001, round g627j0) built
the FIRST half and stopped exactly at the ledger, on purpose.  This module is
the SECOND half's server side: one claim against one row of that ledger becomes
one item in one bag slot, atomically, once.

    claim     <- who is claiming what, and from where they are standing
    resolve   <- which live ledger row that claim names, or a refusal
    commit    <- take it off the ground THROUGH the cell, then place it
    write     <- the exact row store.py must INSERT for the relog to keep it
    delta     <- the bytes that tell a client already in the world about it

WHAT IT DOES NOT DO, AND WHERE THE LANE ACTUALLY STOPS TODAY.  It does not
write to the database and it does not send anything: it has no connection, no
cursor, no clock and no socket, and ``runtime.py`` / ``store.py`` are the
chief's files.  It produces the row and the bytes; the chief wires them.  And
there is a REAL WALL past that, which this module refuses to hide (see THE
WALL below): the persisted bag is content-governed, so a bag holding an item
this lane created is REFUSED on the next login by
``inventory.require_known_backpack``.  Until that allowlist is widened by the
lane that owns it, "relog and it is still there" CANNOT be true, and no test,
report or PR from this lane may say it is.  ``tests/test_mob_pickup.py`` pins
that wall as a test rather than a sentence, so it turns red the day it moves.

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True.  There is no
scenario id, no dispatch kwarg, no unlock object and no allowlisted profile in
this file.  The client-outbound producer of a pickup was proven by GT-046 and
its server-side strict decoder lives in a scenario-gated probe lane
(HYP-PF-036, deliberately not named here: the sibling lane pins the list of
files allowed to even say its name, and this one has no business on it).
THIS MODULE IMPORTS NEITHER.
The transaction below is not a function of the opcode: an opcode is a way in,
and this module takes a decoded claim from whoever decoded it.  The day the
real vital id is known, one dispatch line changes and nothing here does.

WHAT IS PROVEN, AND BY WHOM
---------------------------
  * GT-046 (2026-08-23) proved the CLIENT-OUTBOUND producer exists: a left
    click on an in-range ground object builds a ``PickupTerrainThing`` at
    0x006B0639, copies ONE DWORD out of the selected live runtime drop-object
    (pointer [esi+0x7C], then dword [pointer+0x10]) into object+0x14, and
    queues it.  So the client is the first range authority, and it hands the
    server one dword that identifies the object it clicked.
  * GT-045 CLOSED-ANSWERED (chief R163) measured what the ground row looks
    like on screen: a floating NAME LABEL in red text at the coordinate the
    server sent, life 0.2-0.4 s, NO MODEL under the label that was seen.
  * The persisted shapes are real and shipped: ``character_backpack_items``
    (migration 003) is keyed ``(character_id, item_identity)`` and carries
    exactly the seven columns ``inventory.ItemAttrState`` carries.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  1. NOTHING DISPATCHES THIS MODULE.  ``MOB_PICKUP_WIRING`` is a request to
     the chief, not a call site.  No player has picked anything up.
  2. THE OBJECT REFERENCE IS AN ASSUMPTION, AND IT IS TAGGED AS ONE.
     [LANE-B ASSUMPTION - awaiting COO/RE confirmation] GT-046 proves only
     that the client copies the dword at [drop-object+0x10]; it does NOT
     prove that that dword is the element key this project writes at element
     +0x10.  This lane assumes they are the same value and RESOLVES rather
     than TRUSTS: the claimed dword must equal a key that is live in the
     ledger and inside this lane's key block, or the claim is refused.  If
     the assumption is wrong, every claim refuses by name and nothing is
     granted wrongly -- the failure mode is "pickup never works", never
     "pickup works on the wrong object".  The ticket that answers it is
     RE-082 (opened by this round).
  3. NOBODY HAS SEEN A CLIENT ACCEPT ``bag_delta_pc``.  It is the ItemOperate
     result shape that the item lane pinned against frozen V141 for a MOVE of
     an item the client already had.  Using it to announce an item the client
     did NOT already have is this lane's choice, cross-pinned byte-for-byte
     against that lane's own composer so drift is caught, and UNMEASURED as
     behaviour.  It may be ignored or refused by a real client.
  4. THE KILLER-ONLY RULE IS THIS LANE'S, NOT THE GAME'S.
     [LANE-B ASSUMPTION - awaiting COO confirmation] Nothing measured says
     who the original server let pick a drop up.  This lane takes the
     strictest reversible option: only the identity recorded as the killer of
     that drop's monster may claim it.  Widening it later is one predicate.
  5. THE PICKUP RADIUS IS ARITHMETIC, NOT A MEASUREMENT.  See PICKUP_RADIUS.
  6. NOTHING STACKS.  A claim always takes a FREE SLOT, even when the bag
     already holds the same template.  Merging is HYP-PF-010 / HYP-PF-008
     governed in the item lane and the stack ceiling of any template is
     unmeasured; a lane that guessed it would silently destroy quantity.
  7. MONEY IS NOT PICKED UP.  ``mob_loot`` never places money on the ground
     (it has no element), so there is no money row to claim, and this module
     refuses a money item id by name rather than inventing a currency path.
  8. A CRASH BETWEEN THE TAKE AND THE INSERT LOSES THE ITEM.  It is written
     down rather than solved because the ground itself does not persist
     (``mob_loot.GROUND_DROP_DOES_NOT_PERSIST``): a crash loses every drop on
     the ground anyway, so the window costs nothing that surviving it would
     have saved.  The order is still chosen for it -- everything that can
     refuse, refuses BEFORE the row leaves the ground.

THE WALL (read this before promising a relog)
---------------------------------------------
``inventory.require_known_backpack`` accepts exactly two CONTENT snapshots:
the shipped initial four items and the post-V111-merge three.  A bag with a
fifth, newly created item is outside both.  THREE gates read that judgement,
all of them on the ONE production character-select path
(``runtime.py`` -> ``session.select_and_start``), in the order they bite:

    1. store._load_backpack  -> require_known_backpack -> ValueError
    2. session.select_and_start -> is_unmoved_baseline -> PermissionError
    3. legacy_bridge.start_game -> make_backpack_attr -> require_known_backpack

And the two exceptions are answered DIFFERENTLY, which is worth knowing before
anyone debugs it: ``runtime.py`` wraps that call in
``except (KeyError, PermissionError)`` and answers a refusal by appending an
event and sending NO REPLY -- a client left at "connecting" -- while gate 1's
``ValueError`` is not caught there at all and unwinds the connection's
listener thread instead.

So persisting a picked-up item without widening that judgement does not
"mostly work": it makes the character UNABLE TO ENTER THE WORLD, loudly or
silently depending on which gate is reached first.  None of those three files
belongs to this lane, so this module does not touch them.  What it does
instead is produce ``BagRowWrite``, which names the exact INSERT, and refuse
to pretend the round after it is free.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from typing import Any

from . import field_drop_tables
from . import mob_loot
from .inventory import (
    BACKPACK_BASE_IDENTITY,
    BACKPACK_BASE_MASK,
    BackpackState,
    ItemAttrState,
)


MOB_PICKUP_MILESTONE = "MOB-PICKUP-001"
MOB_PICKUP_BUILD_ORDER = "BUILD-006 / M5 second half"
MOB_PICKUP_LANE = "B_COMBAT"

MOB_PICKUP_WIRING = (
    "runtime.py.  The scene already holds ONE mob_loot.DropLedgerCell (see "
    "mob_loot.MOB_LOOT_WIRING).  This lane adds no second owner.\n"
    "  When an inbound pickup request has been decoded to (claimant identity, "
    "claimant position, object reference dword):\n"
    "  1. claim = mob_pickup.PickupClaim(identity, x, y, z, object_ref_u32)\n"
    "  2. outcome = mob_pickup.commit_pickup(cell, backpack_now, claim)\n"
    "     - backpack_now is what store.get_backpack() returned for that "
    "character in THIS session; a stale bag allocates a slot somebody else "
    "already filled, so read it inside the same transaction that writes.\n"
    "     - every refusal is a MobPickupContractError whose first argument is "
    "one of MOB_PICKUP_REFUSAL_REASONS.  drop_taken_by_another_claim means "
    "another claimant won the race and you must NOT retry.  Every refusal "
    "leaves the drop ON THE GROUND except that one, which means it is "
    "already gone.\n"
    "  3. PERSIST outcome.row_write with ONE INSERT into "
    "character_backpack_items, in the same transaction as the ack.  The "
    "column order is BagRowWrite.COLUMNS and the values are "
    "outcome.row_write.values(character_id).\n"
    "     - INSIDE that transaction, after re-reading the bag and BEFORE the "
    "INSERT, call outcome.row_write.require_fits(bag_read_in_this_"
    "transaction).  The primary key catches a stale IDENTITY on its own; it "
    "does NOT catch a stale SLOT, because the slot is not in the key, and two "
    "rows in one slot are only discovered on the next login, as a bag that no "
    "longer parses.\n"
    "     - STOP: THIS INSERT IS NOT SAFE TO MAKE YET.  See THE WALL in the "
    "module docstring: the next login refuses a bag holding it.  The item "
    "lane must widen inventory.require_known_backpack FIRST.  Until then, "
    "wire steps 1, 2 and 4 and log step 3 rather than running it.\n"
    "  4. send mob_pickup.bag_delta_pc(legacy, outcome.item) to the claimant "
    "so a client already in the world sees the row without relogging.  It is "
    "one pc; frame it the way every other vitals pc is framed.\n"
    "  5. nothing else.  There is no ground object to delete: the label lives "
    "0.2-0.4 s and expires by itself, and taking the row through the cell "
    "stops mob_loot.refresh_frames from re-emitting it."
)

production_allowed = True
test_only = False


# ---------------------------------------------------------------------------
# Lane constants.  Every one of them either comes from a shipped shape or is
# arithmetic over another lane's constant, and says which in one line.
# ---------------------------------------------------------------------------

# The visible bag is 40 slots: inventory.require_known_backpack accepts slots
# 0..39 and migration 003 CHECKs the same span.  Not a guess of this lane's.
BAG_SLOT_COUNT = 40

# character_backpack_items.item_identity is a SQLite INTEGER with an explicit
# CHECK between 0 and 9223372036854775807 (migration 003).
MAX_ITEM_IDENTITY = 0x7FFFFFFFFFFFFFFF

# The three raw columns every shipped baseline row carries.  Pinned against
# inventory.INITIAL_BACKPACK in the tests rather than typed from memory: no
# lane has measured what else they may be, so a new row copies what exists.
NEW_ROW_RAW_U8_38 = 0
NEW_ROW_RAW_U8_39 = 0xFF
NEW_ROW_DETAIL_PRESENT = 0

# The ItemAttr quantity column is a u16 on the wire (inventory serializes it
# with u16tag 0x0F), so a slot cannot carry more than 0xFFFF.  There is NO
# separate "quantity overflows a slot" refusal: mob_loot.GroundDrop already
# caps a ground quantity at the same u16, so such a branch would be a named
# refusal no code path can reach -- exactly the defect the round-g627j0
# adversarial pass found three of.  An out-of-range quantity arriving any
# other way is refused as value_out_of_range, by the same guard as every
# other integer in this file.
MAX_SLOT_QUANTITY = 0xFFFF

# [LANE-B ASSUMPTION - awaiting COO confirmation] ARITHMETIC, NOT A
# MEASUREMENT.  Nothing in this project has measured the original server's
# pickup range, and the CLIENT is the first range authority anyway (GT-046:
# the producer only fires for an in-range object).  This gate exists to refuse
# an absurd claim -- a client asking for an object across the map -- and it is
# deliberately GENEROUS rather than tight, because a tight guess refuses
# legitimate pickups and a generous one refuses only what no honest client
# sends.  The number is the width of ONE KILL's own scatter: mob_loot places
# object N at DROP_SCATTER_STEP * N on X, up to MAX_DROPS_PER_KILL objects, so
# a player standing where the monster fell can reach every object that kill
# produced and nothing beyond it.
PICKUP_RADIUS = mob_loot.DROP_SCATTER_STEP * mob_loot.MAX_DROPS_PER_KILL

# mob_loot never places money on the ground; this is the id it records money
# under, refused here by name so a money claim cannot fall through to "unknown".
MONEY_ITEM_ID = mob_loot.MONEY_ITEM_ID

PIN_ID = "port_royal_field_mob_pickup_001"
PIN_BUILD_ORDER = MOB_PICKUP_BUILD_ORDER
PIN_LANE = MOB_PICKUP_LANE

# The one thing on the far side of this lane that is NOT this lane's to move.
GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE = True
GOVERNED_BAG_ALLOWLIST_OWNER = "inventory.require_known_backpack (item lane)"

MOB_PICKUP_NONCLAIMS = (
    "1. Nothing dispatches this module.  MOB_PICKUP_WIRING is a request to "
    "the chief, not a call site.  No player has picked anything up.",
    "2. The object reference is an ASSUMPTION [LANE-B ASSUMPTION - awaiting "
    "COO/RE confirmation]: GT-046 proves the client copies the dword at "
    "[drop-object+0x10], not that it is the key this project writes at "
    "element +0x10.  The claim is RESOLVED against the live ledger, never "
    "trusted, so a wrong assumption refuses every claim and grants none.  "
    "RE-082 is the ticket that answers it.",
    "3. Nobody has seen a client accept bag_delta_pc.  It is the item lane's "
    "ItemOperate result shape, pinned byte-for-byte against that lane's own "
    "composer, used for an item the client did not already have -- which is "
    "UNMEASURED behaviour.",
    "4. The killer-only rule is this lane's, not the game's [LANE-B "
    "ASSUMPTION - awaiting COO confirmation].",
    "5. PICKUP_RADIUS is arithmetic over mob_loot's scatter, not a measured "
    "game range.  The client is the first range authority.",
    "6. Nothing stacks.  A claim always takes a free slot; stack ceilings are "
    "unmeasured and a guess would destroy quantity silently.",
    "7. Money is never on the ground and is refused by name here.",
    "8. A crash between the take and the INSERT loses the item.  The ground "
    "does not persist either, so the window costs nothing a crash would not "
    "have cost anyway.",
    "9. STOP: RELOG IS NOT CLOSED BY THIS ROUND.  The persisted bag is content-"
    "governed by inventory.require_known_backpack, which belongs to the "
    "item lane.  Persisting a picked-up item BEFORE that allowlist is widened "
    "does not merely fail to persist: it makes the character unable to enter "
    "the world at all.",
    "10. Nothing here writes a database row, opens a socket, reads a clock or "
    "reads a file.  It is a pure transaction over values plus one take "
    "through mob_loot's cell.",
    "11. THE BAG IS TAKEN BY VALUE AND THIS LANE IS NOT ITS LOCK.  Two "
    "pickups resolved against one stale bag pick the same slot, and the "
    "primary key does not catch that -- it keys identity, not slot.  The "
    "writer's own transaction is the lock; BagRowWrite.require_fits is the "
    "check it must run there, and the wiring line says so as an instruction "
    "rather than a suggestion.",
)


# ---------------------------------------------------------------------------
# Refusals.  Every name below is raised somewhere in this file; the test suite
# compares the SET of names actually raised against this tuple, in the shape
# tests/test_mob_combat.py proved and tests/test_mob_loot.py inherited.
# ---------------------------------------------------------------------------
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_POSITION_NOT_FINITE = "position_not_finite"
REFUSE_OBJECT_REF_NOT_ON_THE_GROUND = "object_ref_not_on_the_ground"
REFUSE_CLAIMANT_OUT_OF_RANGE = "claimant_out_of_range"
REFUSE_NOT_THE_KILLER = "not_the_killer"
REFUSE_MONEY_HAS_NO_GROUND_OBJECT = "money_has_no_ground_object"
REFUSE_ITEM_HAS_NO_NAME = "item_has_no_name"
REFUSE_BAG_ROW_COLLIDES = "bag_row_collides"
REFUSE_BAG_IS_FULL = "bag_is_full"
REFUSE_IDENTITY_BLOCK_SPENT = "identity_block_spent"
REFUSE_DROP_TAKEN_BY_ANOTHER_CLAIM = "drop_taken_by_another_claim"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"

MOB_PICKUP_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_OBJECT_REF_NOT_ON_THE_GROUND,
    REFUSE_CLAIMANT_OUT_OF_RANGE,
    REFUSE_NOT_THE_KILLER,
    REFUSE_MONEY_HAS_NO_GROUND_OBJECT,
    REFUSE_ITEM_HAS_NO_NAME,
    REFUSE_BAG_ROW_COLLIDES,
    REFUSE_BAG_IS_FULL,
    REFUSE_IDENTITY_BLOCK_SPENT,
    REFUSE_DROP_TAKEN_BY_ANOTHER_CLAIM,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
)


class MobPickupContractError(ValueError):
    """A refusal from this module, always with a reason as its first argument."""


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        raise MobPickupContractError(
            REFUSE_VALUE_NOT_INT, "%s must be an exact int, got %s"
            % (label, type(value).__name__))
    if not minimum <= value <= maximum:
        raise MobPickupContractError(
            REFUSE_VALUE_OUT_OF_RANGE, "%s must be in [%d,%d], got %d"
            % (label, minimum, maximum, value))
    return value


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, 0xFFFFFFFF)
    if identity <= 0:
        raise MobPickupContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise MobPickupContractError(
            REFUSE_POSITION_NOT_FINITE, "%s must be a finite number" % label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
        raise MobPickupContractError(
            REFUSE_POSITION_NOT_FINITE, "%s must be a finite float32 value"
            % label)
    return result


def _require_named_item(item_id: int) -> str:
    """The name a player would read, or a refusal.  Never an empty label."""
    if item_id == MONEY_ITEM_ID:
        raise MobPickupContractError(
            REFUSE_MONEY_HAS_NO_GROUND_OBJECT,
            "money is never placed on the ground by mob_loot and has no "
            "object to claim; a currency path is not this lane's to invent")
    row = field_drop_tables.ITEMS.get(item_id)
    if row is None or not row[2]:
        raise MobPickupContractError(
            REFUSE_ITEM_HAS_NO_NAME,
            "item %d has no readable name; the client resolves the name "
            "itself from the id and an unnamed row would put a blank in a bag"
            % item_id)
    return row[2]


# ---------------------------------------------------------------------------
# The claim
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PickupClaim:
    """One decoded pickup request.  No opcode, on purpose.

    ``object_ref_u32`` is the dword GT-046 proved the client copies out of the
    live drop-object it clicked.  This lane RESOLVES it against the ledger --
    see NONCLAIM 2 -- and never treats it as authority for anything.
    """

    claimant_identity: int
    x: float
    y: float
    z: float
    object_ref_u32: int

    def __post_init__(self) -> None:
        _require_identity(self.claimant_identity, "claimant identity")
        for label, value in (("x", self.x), ("y", self.y), ("z", self.z)):
            _require_finite(value, "claimant %s" % label)
        _require_int(self.object_ref_u32, "object reference", 0, 0xFFFFFFFF)

    @property
    def position(self) -> tuple:
        return (float(self.x), float(self.y), float(self.z))


def squared_distance(here: Any, there: Any) -> float:
    """Full 3D, squared, the way the aggro lane compares distances."""
    ax, ay, az = (_require_finite(value, "position component") for value in here)
    bx, by, bz = (_require_finite(value, "position component") for value in there)
    return (ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2


def within_pickup_radius(here: Any, there: Any) -> bool:
    """Inclusive boundary, matching the aggro lane's stated convention."""
    return squared_distance(here, there) <= PICKUP_RADIUS ** 2


def resolve_claim(ledger: Any, claim: Any) -> Any:
    """Which live ground row this claim names.  Pure: nothing is removed.

    Refuses, in this order, so the most specific message wins: a reference
    that is not a live key at all, then a claimant who is not the killer, then
    a claimant who is too far away.  Every refusal here leaves the drop ON THE
    GROUND -- this function cannot lose anybody's loot because it takes
    nothing.
    """
    if type(ledger) is not mob_loot.DropLedger:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "resolve_claim needs a typed mob_loot.DropLedger")
    if type(claim) is not PickupClaim:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "claim must be a typed PickupClaim")
    drop = None
    for row in ledger.drops:
        if row.drop_key == claim.object_ref_u32:
            drop = row
            break
    if drop is None:
        raise MobPickupContractError(
            REFUSE_OBJECT_REF_NOT_ON_THE_GROUND,
            "object reference 0x%X is not a live drop key; either it was "
            "already taken, or [drop-object+0x10] is not the element key "
            "(see NONCLAIM 2 and RE-082)" % claim.object_ref_u32)
    if drop.killer_identity != claim.claimant_identity:
        raise MobPickupContractError(
            REFUSE_NOT_THE_KILLER,
            "drop 0x%X belongs to the kill by identity 0x%X; 0x%X did not "
            "make that kill" % (drop.drop_key, drop.killer_identity,
                                claim.claimant_identity))
    if not within_pickup_radius(claim.position, (drop.x, drop.y, drop.z)):
        raise MobPickupContractError(
            REFUSE_CLAIMANT_OUT_OF_RANGE,
            "the claimant is %.1f away from drop 0x%X and this lane's gate is "
            "%.1f" % (math.sqrt(squared_distance(
                claim.position, (drop.x, drop.y, drop.z))),
                drop.drop_key, PICKUP_RADIUS))
    return drop


# ---------------------------------------------------------------------------
# The bag.  This lane validates the SHAPE of a bag and never its CONTENTS: the
# content allowlist belongs to the item lane and weakening another lane's
# tripwire is exactly the defect an adversarial pass caught in round g627j0.
# ---------------------------------------------------------------------------
def require_bag_shape(value: Any) -> BackpackState:
    """Structural validation only.  Deliberately NOT require_known_backpack.

    The item lane's function additionally requires the CONTENTS to be one of
    two shipped snapshots.  This lane cannot use it -- a bag with a picked-up
    item is by definition outside those snapshots -- and it must not relax it
    either.  So it validates what is structurally true of any bag the shipped
    schema can hold, and THE WALL in the module docstring records the rest.
    """
    if type(value) is not BackpackState:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "bag must be an exact BackpackState")
    _require_int(value.base_mask, "bag base mask", 0, 0xFF)
    _require_int(value.base_identity, "bag base identity", 0, MAX_ITEM_IDENTITY)
    _require_int(value.range_mask, "bag range mask", 0, 0xFF)
    if type(value.items) is not tuple:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "bag items must be an exact tuple")
    identities = set()
    slots = set()
    for item in value.items:
        if type(item) is not ItemAttrState:
            raise MobPickupContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "every bag row must be an exact ItemAttrState")
        _require_int(item.identity, "item identity", 0, MAX_ITEM_IDENTITY)
        _require_int(item.template_id, "item template", 0, 0xFFFFFFFF)
        _require_int(item.quantity, "item quantity", 0, MAX_SLOT_QUANTITY)
        _require_int(item.slot, "item slot", 0, BAG_SLOT_COUNT - 1)
        _require_int(item.raw_u8_38, "item raw +0x38", 0, 0xFF)
        _require_int(item.raw_u8_39, "item raw +0x39", 0, 0xFF)
        _require_int(item.detail_present, "item detail presence", 0, 1)
        if item.identity in identities or item.slot in slots:
            raise MobPickupContractError(
                REFUSE_BAG_ROW_COLLIDES,
                "item identity and slot are the two keys a bag has; identity "
                "%d / slot %d collides with a row already in this bag"
                % (item.identity, item.slot))
        identities.add(item.identity)
        slots.add(item.slot)
    return value


def first_free_slot(bag: Any) -> int:
    """The lowest empty slot.  LOWEST, so the same bag always answers the same.

    A bag that is full refuses by name: the alternative -- dropping the item,
    or overwriting a slot -- destroys something a player owns.
    """
    bag = require_bag_shape(bag)
    taken = {item.slot for item in bag.items}
    for slot in range(BAG_SLOT_COUNT):
        if slot not in taken:
            return slot
    raise MobPickupContractError(
        REFUSE_BAG_IS_FULL,
        "all %d slots are occupied; the drop stays on the ground"
        % BAG_SLOT_COUNT)


def next_item_identity(bag: Any) -> int:
    """One past the highest identity in the bag.

    HIGHEST + 1, never "count + 1": the primary key is
    (character_id, item_identity) and a merge or a delete leaves gaps, so a
    count would hand out an identity a surviving row already holds and the
    INSERT would fail -- or worse, an UPDATE elsewhere would hit two rows.
    """
    bag = require_bag_shape(bag)
    highest = 0
    for item in bag.items:
        if item.identity > highest:
            highest = item.identity
    if highest >= MAX_ITEM_IDENTITY:
        raise MobPickupContractError(
            REFUSE_IDENTITY_BLOCK_SPENT,
            "item identity %d is at the column ceiling" % highest)
    return highest + 1


@dataclass(frozen=True)
class BagRowWrite:
    """The exact INSERT store.py must make.  This lane does not make it.

    It is a VALUE, not a call: this module has no cursor and no connection,
    and the file that has both belongs to the chief.  ``COLUMNS`` is the
    column order of ``character_backpack_items`` as migration 003 declares it.
    """

    COLUMNS = (
        "character_id", "item_identity", "template_id", "quantity", "slot",
        "raw_u8_38", "raw_u8_39", "detail_present",
    )

    claimant_identity: int
    item_identity: int
    template_id: int
    quantity: int
    slot: int
    raw_u8_38: int = NEW_ROW_RAW_U8_38
    raw_u8_39: int = NEW_ROW_RAW_U8_39
    detail_present: int = NEW_ROW_DETAIL_PRESENT

    def __post_init__(self) -> None:
        _require_identity(self.claimant_identity, "claimant identity")
        _require_int(self.item_identity, "item identity", 1, MAX_ITEM_IDENTITY)
        _require_int(self.template_id, "template id", 1, 0xFFFFFFFF)
        _require_int(self.quantity, "quantity", 1, MAX_SLOT_QUANTITY)
        _require_int(self.slot, "slot", 0, BAG_SLOT_COUNT - 1)
        _require_int(self.raw_u8_38, "raw +0x38", 0, 0xFF)
        _require_int(self.raw_u8_39, "raw +0x39", 0, 0xFF)
        _require_int(self.detail_present, "detail presence", 0, 1)

    def fits(self, bag_now: Any) -> bool:
        """Whether this row can still be inserted into the bag as it is NOW.

        THE THING A VALUE CANNOT DO, AND WHY THIS EXISTS.  ``commit_pickup``
        takes a bag by VALUE, and the lesson mob_loot's ledger learned twice is
        that a caller holding a value cannot compare-and-swap against it.  The
        bag's real owner is the database, in a file this lane does not own, so
        this lane cannot BE the lock -- what it can do is hand the writer a
        cheap check to run INSIDE its own transaction, against the bag it just
        read there.

        It matters more than the primary key does.  ``character_backpack_items``
        is keyed ``(character_id, item_identity)``, so a stale identity is
        rejected by the database itself -- loudly, and nothing is lost.  THE
        SLOT IS NOT IN THAT KEY.  Two pickups resolved against one stale bag
        therefore insert two rows in one slot, the database accepts both, and
        the damage surfaces on the next login as a bag that no longer parses.
        """
        try:
            bag_now = require_bag_shape(bag_now)
        except MobPickupContractError:
            return False
        for item in bag_now.items:
            if item.identity == self.item_identity or item.slot == self.slot:
                return False
        return True

    def require_fits(self, bag_now: Any) -> None:
        """:meth:`fits`, as a refusal by name.  Call it inside the write."""
        if not self.fits(bag_now):
            raise MobPickupContractError(
                REFUSE_BAG_ROW_COLLIDES,
                "identity %d / slot %d is no longer free in this bag; the bag "
                "moved between the pickup and the write, and inserting anyway "
                "would put two rows in one slot -- which the primary key does "
                "NOT catch, because the slot is not in it"
                % (self.item_identity, self.slot))

    def values(self, character_id: Any) -> tuple:
        """The row, in COLUMNS order, for the character the caller resolved.

        The character id is the CALLER's to supply: this lane knows an actor
        identity on a wire, and only the session layer knows which persisted
        character that is.  Guessing the mapping here would write another
        player's bag.
        """
        _require_int(character_id, "character id", 1, MAX_ITEM_IDENTITY)
        return (
            character_id, self.item_identity, self.template_id, self.quantity,
            self.slot, self.raw_u8_38, self.raw_u8_39, self.detail_present,
        )


@dataclass(frozen=True)
class PickupOutcome:
    """What one accepted claim produced.  The drop is already off the ground."""

    drop: Any
    item: ItemAttrState
    bag_before: BackpackState
    bag_after: BackpackState
    row_write: BagRowWrite

    @property
    def display_name(self) -> str:
        return _require_named_item(self.item.template_id)

    @property
    def persisted(self) -> bool:
        """Always False.  This module has never written a row.

        It is a property rather than an absent field so a caller that wants to
        report "it is in the bag after a relog" has to read the word False
        first, and so a test can pin it.
        """
        return False


def place_in_bag(bag: Any, drop: Any) -> tuple:
    """``(bag_after, item)`` for one ground row.  Pure; takes nothing.

    Everything that can refuse a pickup on the BAG side happens here, and
    :func:`commit_pickup` calls it BEFORE the row leaves the ground.  That
    order is the whole reason a full bag does not eat a drop.
    """
    bag = require_bag_shape(bag)
    if type(drop) is not mob_loot.GroundDrop:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a pickup places a typed mob_loot.GroundDrop")
    # This call is what makes PickupOutcome.display_name -- and therefore
    # pickup_report -- INCAPABLE of raising afterwards.  mob_loot's GroundDrop
    # checks the same table today, so it is redundant today; it is the
    # invariant of THIS lane, established where the item is created rather
    # than assumed from a sibling module's constructor.
    _require_named_item(drop.item_id)
    _require_int(drop.quantity, "drop quantity", 1, MAX_SLOT_QUANTITY)
    slot = first_free_slot(bag)
    identity = next_item_identity(bag)
    item = ItemAttrState(
        identity, drop.item_id, drop.quantity, slot,
        NEW_ROW_RAW_U8_38, NEW_ROW_RAW_U8_39, NEW_ROW_DETAIL_PRESENT,
    )
    # Order is the bag's own: rows are sorted by identity, which is the order
    # store._load_backpack reads them back in (ORDER BY item_identity).  A bag
    # that comes back in a different order than it went in is a difference a
    # test cannot see but a serializer can.
    after = BackpackState(
        bag.base_mask, bag.base_identity, bag.range_mask,
        tuple(sorted(bag.items + (item,), key=lambda row: row.identity)),
    )
    return require_bag_shape(after), item


def commit_pickup(cell: Any, bag: Any, claim: Any) -> PickupOutcome:
    """Take one drop off the ground and put it in one bag.  Once.

    THE RACE, AND WHY A SNAPSHOT IS ENOUGH HERE.  This function resolves the
    claim against a SNAPSHOT of the ledger and then takes through the cell,
    which looks like the check-then-act ``mob_loot.commit_drops`` was rewritten
    to avoid.  It is not, and the reason is a property of that lane rather than
    a hope: KEYS ARE NEVER REUSED (``DropLedger.next_key`` is a high-water
    mark, and ``commit_drops`` refuses any key below ``issued_through``).  So a
    key that is still in the ledger when ``take`` runs names the same
    ``GroundDrop`` it named in the snapshot -- it cannot have become a
    different object.  Two claimants racing the same key therefore both
    validate, both call take, and exactly ONE of them gets the row; the loser
    is refused by name, having changed nothing.

    THE ORDER, AND WHY IT IS THIS ONE.  Everything that can refuse -- the
    reference, the killer, the range, the item name, the free slot, the next
    identity -- is evaluated BEFORE the take.  A lane that took first and
    allocated a slot second would answer "your bag is full" by deleting the
    object the player was reaching for.
    """
    if type(cell) is not mob_loot.DropLedgerCell:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "commit_pickup needs the scene's mob_loot.DropLedgerCell")
    if type(claim) is not PickupClaim:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "claim must be a typed PickupClaim")
    bag = require_bag_shape(bag)
    drop = resolve_claim(cell.ledger, claim)
    bag_after, item = place_in_bag(bag, drop)
    row_write = BagRowWrite(
        claim.claimant_identity, item.identity, item.template_id,
        item.quantity, item.slot,
    )
    try:
        taken = cell.take(drop.drop_key)
    except mob_loot.MobLootContractError as exc:
        raise MobPickupContractError(
            REFUSE_DROP_TAKEN_BY_ANOTHER_CLAIM,
            "drop 0x%X left the ground under this claim (%s); do NOT retry -- "
            "somebody else has it" % (drop.drop_key, exc.args[0])) from None
    if taken != drop:
        raise MobPickupContractError(
            REFUSE_DROP_TAKEN_BY_ANOTHER_CLAIM,
            "drop key 0x%X named a different object at take time than at "
            "resolve time; this lane's key-reuse argument is broken and the "
            "row is NOT granted" % drop.drop_key)
    return PickupOutcome(taken, item, bag, bag_after, row_write)


# ---------------------------------------------------------------------------
# The bytes.  Two derivations of the same delta, compared on every call, in
# the shape mob_loot uses: if the item lane's composer ever drifts from this
# one, the lane stops emitting rather than emitting something unpinned.
# ---------------------------------------------------------------------------
ITEM_ATTR_FIELD_ORDER = (
    ("identity", 0x32, "Q"),
    ("template_id", 0x14, "I"),
    ("quantity", 0x0F, "H"),
    ("slot", 0x0F, "H"),
    ("raw_u8_38", 0x08, "B"),
    ("raw_u8_39", 0x08, "B"),
    ("detail_present", 0x0B, "B"),
)


def _item_attr_via_tags(legacy: Any, item: ItemAttrState) -> bytes:
    return (
        legacy.qwordtag(0x32, item.identity)
        + legacy.u32tag(0x14, item.template_id)
        + legacy.u16tag(0x0F, item.quantity)
        + legacy.u16tag(0x0F, item.slot)
        + legacy.u8tag(0x08, item.raw_u8_38)
        + legacy.u8tag(0x08, item.raw_u8_39)
        + legacy.u8tag(0x0B, item.detail_present)
    )


def _item_attr_via_struct(item: ItemAttrState) -> bytes:
    """The same seven fields, derived without the legacy helpers at all.

    Two derivations exist for the reason mob_loot has two: the tag helpers
    live in a file this lane does not own, and a shim that quietly changed one
    of them would otherwise send bytes no client has ever accepted, with every
    test still green because every test went through the same shim.
    """
    out = bytearray()
    for name, tag, code in ITEM_ATTR_FIELD_ORDER:
        out += bytes((tag,)) + struct.pack("<" + code, getattr(item, name))
    return bytes(out)


def bag_delta_pc(legacy: Any, item: Any) -> Any:
    """One ItemOperate result carrying exactly one complete ItemAttr.

    SEE NONCLAIM 3 BEFORE BELIEVING THIS DOES ANYTHING ON A SCREEN.  The shape
    is the item lane's, pinned by that lane against frozen V141 for a MOVE of
    an item the client already had.  Announcing a NEW item with it is this
    lane's decision and is unmeasured.
    """
    if type(item) is not ItemAttrState:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a bag delta carries an exact ItemAttrState")
    # NO NAME CHECK HERE, and it is deliberate: a bag delta serializes ANY row
    # a bag can hold, and the four rows a character ships with are not in this
    # lane's drop tables at all.  Requiring a drop-table name here would make
    # this composer unable to describe the very items the item lane pinned it
    # against.  The name is required where an item is CREATED (place_in_bag)
    # and where one is READ OUT to a person (PickupOutcome.display_name).
    _require_int(item.identity, "item identity", 1, MAX_ITEM_IDENTITY)
    _require_int(item.template_id, "item template", 1, 0xFFFFFFFF)
    _require_int(item.quantity, "item quantity", 1, MAX_SLOT_QUANTITY)
    _require_int(item.slot, "item slot", 0, BAG_SLOT_COUNT - 1)
    _require_int(item.raw_u8_38, "item raw +0x38", 0, 0xFF)
    _require_int(item.raw_u8_39, "item raw +0x39", 0, 0xFF)
    _require_int(item.detail_present, "item detail presence", 0, 1)
    item_wire = _item_attr_via_tags(legacy, item)
    if item_wire != _item_attr_via_struct(item):
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the tagged primitives and this lane's own derivation disagree "
            "about one ItemAttr; the lane stops rather than emitting bytes "
            "nothing has accepted")
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
    return legacy.make_runtime_vitals([(
        legacy.ITEM_OPERATE_RES_VITAL, 2, payload,
    )])


def pin_document(legacy: Any) -> dict:
    """What this lane produces, computed rather than typed, for scenarios/."""
    # 2400046 is the most common drop of the bg0001 roster (30 pct) and the
    # id mob_loot's own pin document samples; the two documents describe the
    # two halves of one kill and are easier to read side by side for it.
    sample_drop = mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE, 2400046, 1,
        mob_loot.as_wire_float(1.0), mob_loot.as_wire_float(2.0),
        mob_loot.as_wire_float(3.0), 0x201F, 0x0101,
    )
    sample_bag = BackpackState(
        BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())
    _bag_after, item = place_in_bag(sample_bag, sample_drop)
    # make_runtime_vitals returns (pc, frame); the pc is what is pinned here
    # because the framing is the same framing every other vitals pc gets.
    body = bag_delta_pc(legacy, item)[0]
    return {
        "schema": 1,
        "id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_PICKUP_MILESTONE,
        "test_only": False,
        "production_allowed": True,
        "scenario": None,
        "transaction": {
            "resolves_object_ref_against_the_ledger": True,
            "killer_only": True,
            "pickup_radius": PICKUP_RADIUS,
            "pickup_radius_is_arithmetic_not_measured": True,
            "stacks": False,
            "slot_policy": "lowest free slot",
            "identity_policy": "highest identity in the bag plus one",
            "everything_that_refuses_refuses_before_the_take": True,
        },
        "bag_row": {
            "table": "character_backpack_items",
            "columns": list(BagRowWrite.COLUMNS),
            "raw_u8_38": NEW_ROW_RAW_U8_38,
            "raw_u8_39": NEW_ROW_RAW_U8_39,
            "detail_present": NEW_ROW_DETAIL_PRESENT,
            "slots": BAG_SLOT_COUNT,
            "sample_row": [
                item.identity, item.template_id, item.quantity, item.slot,
                item.raw_u8_38, item.raw_u8_39, item.detail_present,
            ],
        },
        "wire": {
            "shape": "ITEM_OPERATE_RES, one complete ItemAttr, bag count 1",
            "pc_size": len(body),
            "pc_sha256": hashlib.sha256(bytes(body)).hexdigest().upper(),
            "ever_observed_for_a_new_item": False,
        },
        "blocked": {
            "relog_persistence": GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE,
            "blocked_by": GOVERNED_BAG_ALLOWLIST_OWNER,
            "what_happens_if_wired_anyway": (
                "the character cannot enter the world: both the login load "
                "and the world-entry attr build run the content allowlist"
            ),
        },
        "nonclaims": list(MOB_PICKUP_NONCLAIMS),
        "refusals": list(MOB_PICKUP_REFUSAL_REASONS),
    }


def pickup_report(outcome: Any) -> dict:
    """One accepted pickup, in the words a person would use to check it."""
    if type(outcome) is not PickupOutcome:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a report describes a typed PickupOutcome")
    return {
        "milestone": MOB_PICKUP_MILESTONE,
        "claimed_by": outcome.row_write.claimant_identity,
        "from_the_kill_of": outcome.drop.mob_identity,
        "drop_key": outcome.drop.drop_key,
        "item_id": outcome.item.template_id,
        "item_name": outcome.display_name,
        "quantity": outcome.item.quantity,
        "slot": outcome.item.slot,
        "item_identity": outcome.item.identity,
        "rows_in_the_bag": len(outcome.bag_after.items),
        "persisted": outcome.persisted,
        "survives_a_relog": False,
    }
