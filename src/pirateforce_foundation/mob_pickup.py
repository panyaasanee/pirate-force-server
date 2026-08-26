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
this lane created is REFUSED at the next character SELECT by
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
    queues it.  It hands the server one dword that identifies the object it
    clicked, and a u8 beside it.  ~~"So the client is the first range
    authority"~~ IS STRUCK: that is a reading of a STATIC finding about which
    callback builds the request, and nothing here measures a range or measures
    a client enforcing one.
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
     RE-082, opened by this round in the OTHER repository
     (``pf_bridge/CLIENT_RE_QUEUE.md``), which is why grepping for it here
     finds only this file.
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
     (it has no element), so there is no money row to claim.  ~~"and this
     module refuses a money item id by name"~~ IS STRUCK: ``GroundDrop``
     refuses item id 0 in its own constructor, so such a refusal here could
     never fire and would be a name with no code path.
  8. A CRASH OR A FAILED WRITE BETWEEN THE TAKE AND THE INSERT LOSES THE
     ITEM, AND THERE IS NO PUT-BACK.  ~~"a crash loses every drop on the
     ground anyway, so the window costs nothing"~~ IS STRUCK AS TOO NARROW:
     it holds for a crash and for nothing else.  A rolled-back transaction, a
     refused session or a UNIQUE violation leaves the server running and every
     other drop on the ground, and destroys only this player's item.  Nor can
     it be handed back: ``mob_loot`` never reuses a key, so a taken row cannot
     return to the ground under the key the client was shown.  The order is
     still chosen to make this window as small as it can be -- everything that
     can refuse, refuses BEFORE the row leaves the ground.

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

GATE 1 IS UNCONDITIONALLY FIRST, so 2 and 3 are unreachable while it stands;
they are listed because they are the same judgement read again, and relaxing
only gate 1 would walk into them.  Its ``ValueError`` is the one that matters:
``runtime.py`` wraps that call in ``except (KeyError, PermissionError)``, which
does NOT catch it, so it unwinds the connection's listener thread.  (Gate 2's
``PermissionError`` IS caught there, and answered by appending an event and
sending no reply -- a client left at "connecting".)

Note the stage: this is character SELECT, not login.  The account is already
logged in and the character is already marked selected in the database by the
time the bag is read.

So persisting a picked-up item without widening that judgement does not
"mostly work": it makes the character UNABLE TO ENTER THE WORLD.  None of
those three files belongs to this lane, so this module does not touch them.
What it does instead is produce ``BagRowWrite``, which names the exact INSERT,
and refuse to pretend the round after it is free.
"""

from __future__ import annotations

import hashlib
import math
import struct
import threading
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
    "mob_loot.MOB_LOOT_WIRING).  This lane adds no second owner of the ground "
    "-- but it DOES need an owner of the BAG, and that is BagCell, one per "
    "selected character, held for as long as the session is.\n"
    "  When an inbound pickup request has been decoded to (claimant identity, "
    "claimant position, object reference dword, the request's u8):\n"
    "  1. claim = mob_pickup.PickupClaim(identity, x, y, z, object_ref_u32, "
    "opaque_u8)\n"
    "  2. outcome = bag_cell.commit_pickup(drop_ledger_cell, claim, "
    "character_id)\n"
    "     - the bag cell is seeded ONCE from store.get_backpack() when the "
    "character is selected, and it OWNS the value afterwards.  Do NOT pass "
    "store.get_backpack() per pickup: a bag read is a VALUE, two pickups "
    "resolved against one value pick the same slot and the same identity, and "
    "the second row is then refused by the database's UNIQUE(character_id, "
    "slot) -- after its drop has already left the ground.  The cell exists so "
    "that refusal happens BEFORE the take, where it costs nothing.\n"
    "     - every refusal is a MobPickupContractError whose first argument is "
    "one of MOB_PICKUP_REFUSAL_REASONS.  EXACTLY ONE of them means the row is "
    "gone: drop_left_the_ground.  Every other refusal, including "
    "object_ref_never_issued and drop_already_taken, leaves the ground "
    "untouched.  Do not retry drop_left_the_ground.\n"
    "     - THE LOSER OF A RACE USUALLY SEES drop_already_taken, not "
    "drop_left_the_ground: the window between resolve and take is a handful "
    "of instructions and the row is normally gone before resolve runs.  Both "
    "mean the same thing operationally (somebody else has it, or the caller "
    "pruned it) and neither is evidence about RE-082.\n"
    "  3. PERSIST outcome.row_write with ONE INSERT into "
    "character_backpack_items, in the same transaction as the ack.  The "
    "column order is BagRowWrite.COLUMNS and the values are "
    "outcome.row_write.values().  A stale identity is refused by the primary "
    "key and a stale slot by UNIQUE(character_id, slot); if either fires, the "
    "bag cell was not the only writer of that bag and the session is wrong, "
    "not the row.\n"
    "     - STOP: THIS INSERT IS NOT SAFE TO MAKE YET.  See THE WALL in the "
    "module docstring: the character-select path refuses a bag holding it.  "
    "The item lane must widen inventory.require_known_backpack FIRST.  Until "
    "then, wire steps 1, 2 and 4 and log step 3 rather than running it -- "
    "which is safe precisely because the bag cell, not the database, is what "
    "keeps two pickups in one session apart.\n"
    "  4. send mob_pickup.bag_delta_pc(legacy, outcome.item) to the claimant "
    "so a client already in the world sees the row without relogging.  It is "
    "a (pc, frame) pair, already framed.\n"
    "  5. nothing else.  There is no ground object to delete: the label lives "
    "0.2-0.4 s and expires by itself, and taking the row through the cell "
    "stops mob_loot.refresh_frames from re-emitting it.\n"
    "  6. THE PRUNE mob_loot.MOB_LOOT_WIRING step 4 makes mandatory can "
    "destroy a claim in flight -- it removes the row between this lane's "
    "resolve and its take, and neither lane can tell that from a rival "
    "claimant.  Nothing here fixes it (this lane has no clock and the ground "
    "has no expiry); it is written down so whoever writes the pruner knows "
    "the window exists."
)

production_allowed = True
test_only = False


# ---------------------------------------------------------------------------
# Lane constants.  Every one of them either comes from a shipped shape or is
# arithmetic over another lane's constant, and says which in one line.
# ---------------------------------------------------------------------------

# The visible bag is 40 slots, and the source is inventory.py's own guard
# (0..39), which is a lane that measured it.  ~~"and migration 003 CHECKs the
# same span"~~ IS STRUCK: migration 003 CHECKs slot BETWEEN 0 AND 65535, which
# is WIDER on purpose -- store.py parks a row at slot 65535 while it swaps two
# items.  The number here is right; half of what this comment claimed as its
# provenance was not.  Consequence worth knowing: a bag read in the middle of
# a swap carries a row at 65535 and require_bag_shape below REFUSES it rather
# than silently treating 65535 as a 41st slot.
BAG_SLOT_COUNT = 40
SWAP_PARKING_SLOT = 0xFFFF

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
# pickup range.  ~~"the CLIENT is the first range authority anyway (GT-046:
# the producer only fires for an in-range object)"~~ IS STRUCK as a
# justification: GT-046 is a STATIC finding about which callback constructs
# the request object, and "in-range" is the sibling lane's prose about it.
# Nothing in this repository measures a range value or measures that a client
# enforces one, so that sentence was a [PROPOSED] premise carrying [MEASURED]
# weight underneath a gate.  What remains true without it is the reason the
# gate is generous rather than tight: a tight guess refuses legitimate
# pickups, and this lane has no measurement to be tight WITH.
#
# The number is the width of ONE KILL's own scatter, and the multiplier is
# MAX_DROPS_PER_KILL - 1, not MAX_DROPS_PER_KILL: mob_loot places object N at
# DROP_SCATTER_STEP * N for N in 0..len-1, so the furthest object a full kill
# can produce stands at 15 steps, not 16.  The first draft used the wrong one
# and then claimed "and nothing beyond it", which its own test disproved by
# using the right multiplier.
PICKUP_RADIUS = mob_loot.DROP_SCATTER_STEP * (mob_loot.MAX_DROPS_PER_KILL - 1)

# mob_loot never places money on the ground -- it has no element -- so no
# ledger row can carry this id and no claim can name one.  There is no "money
# is refused by name" branch here: mob_loot.GroundDrop already refuses item id
# 0 in its own constructor, so such a branch would be a named refusal nothing
# can reach.  The constant stays because the pin document reports it.
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
    "ItemOperate result shape, used for an item the client did not already "
    "have -- UNMEASURED behaviour.  The byte-for-byte pin against that lane's "
    "composer covers ONE governed row (identity 1 / template 2600001 / slot "
    "2), which is a shape this lane can never itself produce; what the pin "
    "proves is that the two composers agree, not that this lane's own rows "
    "have ever been seen.",
    "4. The killer-only rule is this lane's, not the game's [LANE-B "
    "ASSUMPTION - awaiting COO confirmation].",
    "5. PICKUP_RADIUS is arithmetic over mob_loot's scatter, not a measured "
    "game range.  ~~'The client is the first range authority'~~ IS STRUCK: "
    "GT-046 is static RE about which callback builds the request, and nothing "
    "in this project measures a range or measures a client enforcing one.",
    "6. Nothing stacks.  A claim always takes a free slot; stack ceilings are "
    "unmeasured and a guess would destroy quantity silently.",
    "7. Money is never on the ground -- it has no element -- so no claim can "
    "name it.  ~~'and is refused by name here'~~ IS STRUCK: mob_loot's own "
    "constructor refuses item id 0, so a money refusal in this file would be "
    "a named refusal nothing could reach.",
    "8. A CRASH OR A FAILED WRITE BETWEEN THE TAKE AND THE INSERT LOSES THE "
    "ITEM, AND THERE IS NO PUT-BACK.  ~~'the ground does not persist either, "
    "so the window costs nothing'~~ IS STRUCK AS TOO NARROW: it is true of a "
    "crash and false of everything else -- a rolled-back transaction, a "
    "refused session, a UNIQUE violation -- where the server keeps running, "
    "every other drop survives, and only this player's item is gone.  A "
    "put-back is not possible either: mob_loot never reuses a key, so a taken "
    "row cannot be returned to the ground under the key the client was shown.",
    "9. STOP: RELOG IS NOT CLOSED BY THIS ROUND.  The persisted bag is content-"
    "governed by inventory.require_known_backpack, which belongs to the "
    "item lane.  Persisting a picked-up item BEFORE that judgement is widened "
    "does not merely fail to persist: it makes the character unable to enter "
    "the world at all.",
    "10. Nothing here writes a database row, opens a socket, reads a clock or "
    "reads a file.  It is a pure transaction over values plus one take "
    "through mob_loot's cell.",
    "11. THE BAG NEEDS AN OWNER AND BagCell IS IT, IN THIS PROCESS ONLY.  A "
    "BackpackState is a VALUE, and two pickups resolved against one value "
    "pick the same slot and the same identity.  ~~'the primary key does not "
    "catch that -- it keys identity, not slot'~~ IS STRUCK AND WAS FALSE: "
    "migration 003 carries UNIQUE(character_id, slot) as well as the primary "
    "key, so the database refuses the second row loudly.  It refuses it AFTER "
    "the drop has left the ground, which is why the answer is a cell that "
    "refuses BEFORE the take, and not a check bolted onto the write.",
    "12. NO PLAYER CAN ORIGINATE A CLAIM TODAY, and it is not the opcode that "
    "stops them.  GT-046's producer needs a SELECTED LIVE DROP-OBJECT to copy "
    "its dword out of, and GT-045 measured that this pipe draws a name label "
    "with NO MODEL under it -- there is nothing to click.  mob_loot's own "
    "NONCLAIM 4 says the same about GT-060's precondition.  This lane is the "
    "transaction behind a door nobody can knock on yet.",
    "13. THE REQUEST HAS TWO FIELDS AND THIS LANE ACTS ON ONE.  The proven "
    "body carries the dword at object+0x14 and a u8 at object+0x18.  "
    "PickupClaim carries both, validates both and reports both, and acts on "
    "the dword only, because nothing has measured what the u8 means.  If it "
    "turns out to be a partial-take count or a target slot, this lane is "
    "carrying it rather than having discarded it.",
    "14. THE ITEM IDENTITY IS DERIVED, NOT A HIGH-WATER MARK, and mob_loot "
    "wrote down why that shape is a bug: a bag that has ever SHRUNK hands the "
    "next pickup an identity a client may still be holding.  There is nowhere "
    "to persist a high-water mark today -- neither character_backpacks nor "
    "migration 003 has a column for one -- so next_item_identity accepts one "
    "from the caller and falls back to the derived form.  Which lane owns "
    "that column is an open question and is in this round's letter to the "
    "COO, not silently decided here.",
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
# THE TWO WAYS A REFERENCE CAN FAIL TO NAME A LIVE ROW ARE DIFFERENT FACTS AND
# GET DIFFERENT NAMES.  A key BELOW the ledger's issued_through was issued by
# this lane and has since left the ground: that is an ordinary double-click, a
# lost race or the caller's own prune, and it says NOTHING about whether the
# derived object reference is the element key.  A key at or above it, or
# outside the lane's block, was never issued at all -- which is the only shape
# that is evidence about RE-082.  The first draft collapsed both into one
# refusal whose message named RE-082, so every double-click in the game would
# have been logged as evidence against the assumption that ticket exists to
# test.
REFUSE_DROP_ALREADY_TAKEN = "drop_already_taken"
REFUSE_OBJECT_REF_NEVER_ISSUED = "object_ref_never_issued"
REFUSE_CLAIMANT_OUT_OF_RANGE = "claimant_out_of_range"
REFUSE_NOT_THE_KILLER = "not_the_killer"
REFUSE_BAG_ROW_COLLIDES = "bag_row_collides"
REFUSE_BAG_IS_FULL = "bag_is_full"
REFUSE_IDENTITY_BLOCK_SPENT = "identity_block_spent"
REFUSE_IDENTITY_HIGH_WATER_BELOW_THE_BAG = "identity_high_water_below_the_bag"
# The ONLY refusal in this module that means the row is already off the ground.
REFUSE_DROP_LEFT_THE_GROUND = "drop_left_the_ground"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"

MOB_PICKUP_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_DROP_ALREADY_TAKEN,
    REFUSE_OBJECT_REF_NEVER_ISSUED,
    REFUSE_CLAIMANT_OUT_OF_RANGE,
    REFUSE_NOT_THE_KILLER,
    REFUSE_BAG_ROW_COLLIDES,
    REFUSE_BAG_IS_FULL,
    REFUSE_IDENTITY_BLOCK_SPENT,
    REFUSE_IDENTITY_HIGH_WATER_BELOW_THE_BAG,
    REFUSE_DROP_LEFT_THE_GROUND,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
)

# The refusals a caller may treat as "the row is still there, the claim was
# simply wrong".  Exactly one name is missing from it on purpose.
REFUSALS_THAT_LEAVE_THE_DROP_ON_THE_GROUND = tuple(
    reason for reason in MOB_PICKUP_REFUSAL_REASONS
    if reason != REFUSE_DROP_LEFT_THE_GROUND
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


def item_name(item_id: int) -> str:
    """The name a player would read for an id THAT CAME OFF THE GROUND.

    NO REFUSAL OF ITS OWN, and the first draft had two.  It refused money and
    it refused a nameless id -- and ``mob_loot.GroundDrop`` refuses item id 0
    and any id outside the mined table in its own constructor, so neither
    branch could be reached by anything but a hand-built record that stepped
    around every constructor.  Two named refusals nothing can produce is the
    exact defect this lane spent a paragraph promising not to add.  A KeyError
    here means a caller built a record the ledger could not have produced.
    """
    return field_drop_tables.ITEMS[item_id][2]


# ---------------------------------------------------------------------------
# The claim
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PickupClaim:
    """One decoded pickup request.  No opcode, on purpose.

    ``object_ref_u32`` is the dword GT-046 proved the client copies out of the
    live drop-object it clicked (the u32 at request object+0x14).  This lane
    RESOLVES it against the ledger -- see NONCLAIM 2 -- and never treats it as
    authority for anything.

    ``opaque_u8`` is the request's SECOND field (the u8 at object+0x18).  The
    proven body has two fields and the first draft of this record carried one,
    which is how a lane silently discards something.  Its MEANING is unknown,
    this lane acts on it nowhere, and it is carried and reported so that the
    day it turns out to be a partial-take count or a target slot, the value
    was not thrown away at the door.
    """

    claimant_identity: int
    x: float
    y: float
    z: float
    object_ref_u32: int
    opaque_u8: int = 0

    def __post_init__(self) -> None:
        _require_identity(self.claimant_identity, "claimant identity")
        for label, value in (("x", self.x), ("y", self.y), ("z", self.z)):
            _require_finite(value, "claimant %s" % label)
        _require_int(self.object_ref_u32, "object reference", 0, 0xFFFFFFFF)
        _require_int(self.opaque_u8, "request u8", 0, 0xFF)

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
    that names no live row, then a claimant who is not the killer, then a
    claimant who is too far away.  Every refusal here leaves the drop ON THE
    GROUND -- this function cannot lose anybody's loot because it takes
    nothing.

    THE TWO WAYS A REFERENCE MISSES ARE TOLD APART, and that is not a nicety.
    A key this lane ISSUED and that has since left the ground is an ordinary
    double-click, a lost race or the caller's own prune.  A key that was NEVER
    issued is the only shape that is evidence about the object-reference
    assumption.  The first draft answered both with one message that named
    RE-082, which would have made every double-click in the game look like
    evidence against the assumption that ticket exists to test.
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
        reference = claim.object_ref_u32
        was_issued = (
            mob_loot.DROP_KEY_BASE <= reference < ledger.issued_through)
        if was_issued:
            raise MobPickupContractError(
                REFUSE_DROP_ALREADY_TAKEN,
                "drop key 0x%X was issued by this lane and is no longer on "
                "the ground: somebody took it, or the caller pruned it.  This "
                "is NOT evidence about the object reference and must not be "
                "reported as any" % reference)
        raise MobPickupContractError(
            REFUSE_OBJECT_REF_NEVER_ISSUED,
            "object reference 0x%X was never a drop key of this lane (its "
            "block is [0x%X, 0x%X) and it has issued through 0x%X).  THIS is "
            "the shape that bears on whether [drop-object+0x10] is the "
            "element key -- see NONCLAIM 2 and RE-082"
            % (reference, mob_loot.DROP_KEY_BASE, mob_loot.DROP_KEY_LIMIT,
               ledger.issued_through))
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


def next_item_identity(bag: Any, issued_through: Any = None) -> int:
    """One past the highest identity this bag has ever held, if anyone knows.

    HIGHEST + 1, never "count + 1": the primary key is
    (character_id, item_identity) and a merge or a delete leaves gaps, so a
    count would hand out an identity a surviving row already holds.

    AND HIGHEST-IN-THE-BAG IS THE SHAPE mob_loot ALREADY REFUTED, WHICH IS WHY
    ``issued_through`` EXISTS.  ``DropLedger.next_key`` spends a paragraph on
    it: a derived "one past what is here" hands out a value again as soon as
    the container SHRINKS, while a client may still be holding the old one.  A
    bag shrinks every time an item is consumed, sold or dropped, so a bag that
    once held identity 5 and then lost it will hand 5 to the next pickup --
    and inventory.py records that the client's apply loop is clear-by-identity
    then place-by-slot, which is exactly the loop that confuses two things
    wearing one identity.

    THERE IS NOWHERE TO PERSIST A HIGH-WATER MARK TODAY.  Neither
    ``character_backpacks`` nor migration 003 has a column for one, and adding
    one is the item lane's call, not this lane's.  So this function ACCEPTS a
    high-water mark from a caller who has one and falls back to the derived
    form when nobody does -- the fallback is named as a fallback rather than
    presented as a policy, and NONCLAIM 14 says so where a reader will see it.
    A supplied mark BELOW what is already in the bag is refused: it would hand
    out an identity a live row holds, which is worse than the problem it is
    meant to solve.
    """
    bag = require_bag_shape(bag)
    highest = 0
    for item in bag.items:
        if item.identity > highest:
            highest = item.identity
    if issued_through is not None:
        mark = _require_int(
            issued_through, "identity high-water mark", 0, MAX_ITEM_IDENTITY)
        if mark < highest:
            raise MobPickupContractError(
                REFUSE_IDENTITY_HIGH_WATER_BELOW_THE_BAG,
                "the high-water mark %d is below identity %d, which a row in "
                "this bag already holds; a mark that lags the bag is not a "
                "mark" % (mark, highest))
        highest = mark
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
    character_id: int
    item_identity: int
    template_id: int
    quantity: int
    slot: int
    raw_u8_38: int = NEW_ROW_RAW_U8_38
    raw_u8_39: int = NEW_ROW_RAW_U8_39
    detail_present: int = NEW_ROW_DETAIL_PRESENT

    def __post_init__(self) -> None:
        _require_identity(self.claimant_identity, "claimant identity")
        _require_int(self.character_id, "character id", 1, MAX_ITEM_IDENTITY)
        _require_int(self.item_identity, "item identity", 1, MAX_ITEM_IDENTITY)
        _require_int(self.template_id, "template id", 1, 0xFFFFFFFF)
        _require_int(self.quantity, "quantity", 1, MAX_SLOT_QUANTITY)
        _require_int(self.slot, "slot", 0, BAG_SLOT_COUNT - 1)
        _require_int(self.raw_u8_38, "raw +0x38", 0, 0xFF)
        _require_int(self.raw_u8_39, "raw +0x39", 0, 0xFF)
        _require_int(self.detail_present, "detail presence", 0, 1)

    # ~~fits() / require_fits()~~ ARE REMOVED, AND THE REMOVAL IS THE RECORD.
    # They were added mid-round to catch a stale bag at the write, on the
    # stated grounds that "the slot is not in the primary key, so the database
    # accepts two rows in one slot".  THAT WAS FALSE: migration 003 line 19 is
    # UNIQUE(character_id, slot) and SQLite refuses the second row.  So the
    # check was unnecessary -- and worse than unnecessary, because the wiring
    # line told the chief to run it INSIDE the write, which is AFTER the take:
    # a refusal there destroys the drop it refuses.  A lane whose headline
    # claim is "everything that refuses, refuses before the take" had added
    # the one refusal that cannot.  The real answer is BagCell below: an owner
    # that makes the second pickup allocate a different slot in the first
    # place, so nothing has to be caught anywhere.

    def values(self) -> tuple:
        """The row, in COLUMNS order.  No arguments, and that is the point.

        The character id is FIXED WHEN THE PICKUP IS COMMITTED, by the caller
        who knows which persisted character an actor identity belongs to.  An
        earlier draft took it here as a parameter, which meant the row's own
        ``claimant_identity`` and the id it was actually written under could
        disagree with nothing raised -- ``values(999)`` on a row claimed by
        another player returned a row for character 999, and the report kept
        printing the claimant.  A value that can be contradicted by the call
        that reads it is not a record of anything.
        """
        return (
            self.character_id, self.item_identity, self.template_id,
            self.quantity, self.slot, self.raw_u8_38, self.raw_u8_39,
            self.detail_present,
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
        return item_name(self.item.template_id)

    @property
    def persisted(self) -> bool:
        """Always False.  This module has never written a row.

        It is a property rather than an absent field so a caller that wants to
        report "it is in the bag after a relog" has to read the word False
        first, and so a test can pin it.
        """
        return False


def place_in_bag(bag: Any, drop: Any, issued_through: Any = None) -> tuple:
    """``(bag_after, item)`` for one ground row.  Pure; takes nothing.

    Everything that can refuse a pickup on the BAG side happens here, and
    :meth:`BagCell.commit_pickup` calls it BEFORE the row leaves the ground.
    That order is the whole reason a full bag does not eat a drop.

    ~~a _require_named_item(drop.item_id) call, commented as "the invariant of
    THIS lane"~~ IS REMOVED.  ``mob_loot.GroundDrop`` refuses an unmined id in
    its own constructor, so the line could not refuse anything a ledger row
    could carry; deleting it left every test green, which is the definition of
    the check being decorative.
    """
    bag = require_bag_shape(bag)
    if type(drop) is not mob_loot.GroundDrop:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a pickup places a typed mob_loot.GroundDrop")
    _require_int(drop.quantity, "drop quantity", 1, MAX_SLOT_QUANTITY)
    slot = first_free_slot(bag)
    identity = next_item_identity(bag, issued_through)
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


class BagCell:
    """THE OWNER OF ONE CHARACTER'S BAG VALUE, for as long as the session is.

    WHY THIS CLASS EXISTS, AND IT IS NOT A GENERALISATION.  The first draft of
    this lane took the bag as an argument to a free function, and an
    adversarial pass did the obvious thing with it: two pickups in one session,
    both handed ``store.get_backpack()``, both allocating slot 4 and identity 5
    -- with nothing raised, both drops off the ground, and the second row then
    refused by the database's UNIQUE(character_id, slot) AFTER its drop was
    already gone.  That is the same defect ``mob_loot.DropLedgerCell`` was
    written to fix one lane over, in the same words: a caller holding a VALUE
    cannot allocate against it safely, because the value does not move when
    the caller uses it.

    IT IS NOT THE DATABASE'S REPLACEMENT AND DOES NOT PRETEND TO BE.  The
    persisted bag is owned by ``store.py``.  This cell owns the value THIS
    PROCESS allocates against, which is what keeps two pickups in one session
    apart -- and which is why the wiring line can honestly say the INSERT may
    be logged rather than run while the item lane's judgement is still in the
    way.  Seed it once at character select; do not re-seed it per pickup.

    Deliberately tiny, and it still does nothing on its own: no clock, no
    socket, no cursor, no thread.
    """

    def __init__(self, bag: Any, character_id: Any,
                 issued_through: Any = None) -> None:
        self._bag = require_bag_shape(bag)
        self._character_id = _require_int(
            character_id, "character id", 1, MAX_ITEM_IDENTITY)
        if issued_through is None:
            self._issued_through = None
        else:
            # Validated here, against this bag, so a mark that lags is refused
            # at seeding rather than at the first pickup.
            next_item_identity(self._bag, issued_through)
            self._issued_through = issued_through
        self._lock = threading.Lock()

    @property
    def bag(self) -> BackpackState:
        """The current value.  A snapshot; storing it is not owning it."""
        with self._lock:
            return self._bag

    @property
    def character_id(self) -> int:
        return self._character_id

    def commit_pickup(self, ledger_cell: Any, claim: Any) -> PickupOutcome:
        """Take one drop off the ground and put it in this bag.  Once.

        THE RACE ON THE GROUND, AND WHY A SNAPSHOT IS ENOUGH FOR IT.  The
        claim is resolved against a SNAPSHOT of the ledger and then taken
        through ``mob_loot``'s cell, which looks like the check-then-act that
        lane was rewritten to avoid.  It is not, and the reason is a property
        of that lane rather than a hope: KEYS ARE NEVER REUSED
        (``DropLedger.next_key`` is a high-water mark and ``commit_drops``
        refuses any key below ``issued_through``), so a key still in the
        ledger at take time names the same ``GroundDrop`` it named at resolve
        time.  Two claimants racing one key both validate, both take, and
        exactly ONE gets the row.

        THE ORDER, AND WHY IT IS THIS ONE.  Everything that can refuse -- the
        reference, the killer, the range, the free slot, the next identity --
        is evaluated BEFORE the take, inside this lock.  A lane that took
        first and allocated second would answer "your bag is full" by deleting
        the object the player was reaching for.

        THE ONE REFUSAL THAT MEANS THE ROW IS GONE is
        ``drop_left_the_ground``, and its message does NOT say who has it.
        The earlier wording said "somebody else has it", which is false for
        the case that will actually happen most: ``mob_loot``'s wiring makes
        pruning MANDATORY and the label lives 0.2-0.4 s, so the row is often
        removed by the caller's own pruner in exactly the window a request
        travels -- nobody has it, and this lane cannot tell the two apart.
        """
        if type(ledger_cell) is not mob_loot.DropLedgerCell:
            raise MobPickupContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "commit_pickup needs the scene's mob_loot.DropLedgerCell")
        if type(claim) is not PickupClaim:
            raise MobPickupContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "claim must be a typed PickupClaim")
        with self._lock:
            bag = self._bag
            drop = resolve_claim(ledger_cell.ledger, claim)
            bag_after, item = place_in_bag(bag, drop, self._issued_through)
            row_write = BagRowWrite(
                claim.claimant_identity, self._character_id, item.identity,
                item.template_id, item.quantity, item.slot,
            )
            try:
                taken = ledger_cell.take(drop.drop_key)
            except mob_loot.MobLootContractError as exc:
                raise MobPickupContractError(
                    REFUSE_DROP_LEFT_THE_GROUND,
                    "drop 0x%X left the ground between this claim's resolve "
                    "and its take (%s).  Do NOT retry.  This lane cannot tell "
                    "a rival claimant from the caller's own prune, and says "
                    "neither" % (drop.drop_key, exc.args[0])) from None
            # ~~a taken != drop branch~~ IS REMOVED.  Keys are never reused,
            # so a live key names one object; deleting the branch left every
            # test green.  Worse, its message said "the row is NOT granted"
            # while cell.take had already removed it -- a refusal that lied
            # about the one thing a refusal is read for.
            self._bag = bag_after
            if self._issued_through is not None:
                self._issued_through = item.identity
            return PickupOutcome(taken, item, bag, bag_after, row_write)


# ---------------------------------------------------------------------------
# The bytes.  Two derivations of the same delta, compared on every call, in
# the shape mob_loot uses: if the item lane's composer ever drifts from this
# one, the lane stops emitting rather than emitting something unpinned.
# ---------------------------------------------------------------------------
# THE ENVELOPE, AS LITERAL BYTES.  Everything in the ItemOperate result pc
# that is NOT the seven ItemAttr fields, split at the point the item goes in.
# Written as literals rather than composed from the legacy module, because the
# entire purpose is to notice the day that module moves:
#
#   12 9D 6E     u16 tag 0x12  GSCN_RunTimeProtocolRes    0x6E9D
#   14 00000000  u32 tag 0x14  (RuntimeRes id field, 0)
#   08 04        u8  tag 0x08  version 4
#   0B 02        u8  tag 0x0B  inherited VitalData change mask
#   12 01 00     u16 tag 0x12  one vital in the collection
#   12 13 4C     u16 tag 0x12  ItemOperateVitalRes        0x4C13
#   0B 02        u8  tag 0x0B  vital version 2
#   08 00        u8  tag 0x08  (payload head)
#   0B 01        u8  tag 0x0B  bag present
#   0B FF        u8  tag 0x0B  BACKPACK_BASE_MASK
#   32 00 x8     qword tag 0x32 BACKPACK_BASE_IDENTITY
#   0F 01 00     u16 tag 0x0F  one item in the bag
#   <the ItemAttr goes here>
#   0F 00 00     u16 tag 0x0F  end of the identity list
#   08 00        u8  tag 0x08  (payload tail)
#   0B 00        u8  tag 0x0B  RuntimeRes v4 derived change mask -- omitting
#                              this makes the client raise ErrorData=28317
DELTA_PC_PREFIX_PIN = bytes((
    0x12, 0x9D, 0x6E,
    0x14, 0x00, 0x00, 0x00, 0x00,
    0x08, 0x04,
    0x0B, 0x02,
    0x12, 0x01, 0x00,
    0x12, 0x13, 0x4C,
    0x0B, 0x02,
    0x08, 0x00,
    0x0B, 0x01,
    0x0B, 0xFF,
    0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0F, 0x01, 0x00,
))
DELTA_PC_SUFFIX_PIN = bytes((
    0x0F, 0x00, 0x00,
    0x08, 0x00,
    0x0B, 0x00,
))
# THE FRAME HEADER, and NOT a fixed overhead.  The first draft of this pin
# asserted "frame is pc + 10 bytes", copying mob_loot's own 54 - 44.  That is
# true of mob_loot's 44-byte pc and false here: frame_pc prefixes an 8-byte
# header and then a snappy RAW LITERAL whose own tag is one byte below 60
# bytes of payload and two above it, so the overhead is a function of the pc's
# length.  A pin has to be a fact, so the fact is the header: little-endian
# MAGIC, then the byte count of everything after it.
DELTA_FRAME_MAGIC = 0x5F253EAC
DELTA_FRAME_HEADER_SIZE = 8

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
    pc, frame = legacy.make_runtime_vitals([(
        legacy.ITEM_OPERATE_RES_VITAL, 2, payload,
    )])
    # THE ENVELOPE IS PINNED AT RUN TIME, NOT ONLY IN A TEST, and this is the
    # lesson mob_loot wrote down after its own adversarial pass: "a shim with a
    # moved constant would have shipped bytes no client has accepted, and the
    # only thing that would have gone red is a test, which does not run inside
    # a server."  The first draft of this function dual-derived the seven inner
    # ItemAttr fields and took EVERYTHING outside them -- the vital id, the
    # collection header, the trailing change mask -- on the legacy module's
    # word.  A shim that moved ITEM_OPERATE_RES_VITAL, or appended one byte
    # inside make_runtime_vitals, emitted happily.  Now the whole pc is
    # rebuilt here from literals and compared.
    if pc != DELTA_PC_PREFIX_PIN + item_wire + DELTA_PC_SUFFIX_PIN:
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the composed ItemOperate pc is not this lane's pinned envelope "
            "around this lane's ItemAttr (%d bytes composed, %d expected); "
            "the legacy module this lane does not own has moved underneath it"
            % (len(pc), len(DELTA_PC_PREFIX_PIN) + len(item_wire)
               + len(DELTA_PC_SUFFIX_PIN)))
    if len(frame) < DELTA_FRAME_HEADER_SIZE:
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "a framed pc is at least its %d-byte header; this one is %d bytes"
            % (DELTA_FRAME_HEADER_SIZE, len(frame)))
    magic, declared = struct.unpack("<II", frame[:DELTA_FRAME_HEADER_SIZE])
    if magic != DELTA_FRAME_MAGIC:
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame header carries 0x%08X and this lane pins 0x%08X"
            % (magic, DELTA_FRAME_MAGIC))
    if declared != len(frame) - DELTA_FRAME_HEADER_SIZE:
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the frame header declares %d bytes of body and carries %d"
            % (declared, len(frame) - DELTA_FRAME_HEADER_SIZE))
    return pc, frame


def _observed_behaviour() -> dict:
    """Run this lane against itself and report what it actually did.

    Every value here is the outcome of an executed transaction on throwaway
    records: a claim by the killer, a claim by somebody else, a reference that
    was never issued, two drops of one template, and a full bag against a live
    ledger.  Nothing is asserted from memory, which is the only way a pin
    document can contradict the module it describes -- and the only way the
    test that reads it can fail.
    """
    mob, killer, stranger = 0x201F, 0x750059, 0x750060
    where = (mob_loot.as_wire_float(0.0),) * 3
    first = mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE, 2400046, 1, *where, mob, killer)
    second = mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + 1, 2400046, 1, *where, mob, killer)
    ledger = mob_loot.DropLedger(
        (first, second), 1, mob_loot.DROP_KEY_BASE + 2, ())
    here = PickupClaim(killer, 0.0, 0.0, 0.0, first.drop_key)

    def refusal_of(call, *args):
        try:
            call(*args)
        except MobPickupContractError as exc:
            return exc.args[0]
        return None

    empty = BackpackState(BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())
    after_one, item_one = place_in_bag(empty, first)
    _after_two, item_two = place_in_bag(after_one, second)

    # A full bag against a live cell: does the ground move when it refuses?
    full = BackpackState(
        BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
        tuple(ItemAttrState(slot + 1, 2400046, 1, slot)
              for slot in range(BAG_SLOT_COUNT)))
    cell = mob_loot.DropLedgerCell(ledger)
    bag_cell = BagCell(full, 1)
    before = cell.ledger
    full_bag_refusal = refusal_of(bag_cell.commit_pickup, cell, here)
    ground_moved = cell.ledger != before

    return {
        "resolves_object_ref_against_the_ledger": refusal_of(
            resolve_claim, ledger,
            PickupClaim(killer, 0.0, 0.0, 0.0, mob_loot.DROP_KEY_LIMIT - 1),
        ) == REFUSE_OBJECT_REF_NEVER_ISSUED,
        "killer_only": refusal_of(
            resolve_claim, ledger,
            PickupClaim(stranger, 0.0, 0.0, 0.0, first.drop_key),
        ) == REFUSE_NOT_THE_KILLER,
        "pickup_radius": PICKUP_RADIUS,
        "pickup_radius_is_arithmetic_not_measured": True,
        "pickup_radius_reaches_the_furthest_object_of_one_kill": (
            within_pickup_radius(
                (0.0, 0.0, 0.0),
                (mob_loot.DROP_SCATTER_STEP
                 * (mob_loot.MAX_DROPS_PER_KILL - 1), 0.0, 0.0))),
        "stacks": item_one.slot == item_two.slot,
        "slot_policy": "lowest free slot",
        "identity_policy": (
            "highest identity in the bag plus one, or one past a high-water "
            "mark the caller supplies -- see NONCLAIM 14"),
        "everything_that_refuses_refuses_before_the_take": (
            full_bag_refusal == REFUSE_BAG_IS_FULL and not ground_moved),
        "the_one_refusal_that_means_the_row_is_gone": (
            REFUSE_DROP_LEFT_THE_GROUND),
    }


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
        # EVERY BOOLEAN BELOW IS OBSERVED, NOT TYPED.  The first draft wrote
        # them as literals, which made the test that reads them back a set of
        # tautologies -- and left the ordering claim reading True in a
        # document while a refusal outside its reach was destroying drops.  A
        # pin that reports what the author believes is not a pin.
        "transaction": _observed_behaviour(),
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
                "the character cannot enter the world: the character-SELECT "
                "path reads that judgement three times and the first read, "
                "store._load_backpack, raises a ValueError runtime.py does "
                "not catch"
            ),
            "open_question_for_the_item_lane": (
                "which lane owns a persisted item-identity high-water mark; "
                "there is no column for one today -- see NONCLAIM 14"
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
        "written_for_character": outcome.row_write.character_id,
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
