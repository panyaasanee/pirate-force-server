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
this lane created was REFUSED at the next character SELECT by THREE gates,
one of which (the wire encoder) COO-DECISION 20260828_0844 has now widened --
the other two still refuse, so "relog and it is still there" STILL CANNOT be
true, and no test, report or PR from this lane may say it is.
``tests/test_mob_pickup.py`` pins the wall as a test rather than a sentence,
so it turns red the day any gate moves -- Gate 3 moved this round and that
test was updated in the SAME round.

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
  * RE-082 PICKUP-OBJECT-REF-SOURCE-001 PASS/DONE (RE runner, 2026-08-26
    10:17 +07:00, STATIC-ON-BRIDGE, image sha ``96272114...b623``) proved
    the field-14 dword GT-046 pinned IS the wire element key: an
    instruction-exact data-flow trace ties the list codec's write of
    ``element+0x10`` (``0x005F8779``) straight through to
    ``PickupTerrainThing+0x14`` (``0x006B0649``) with no arithmetic, table
    lookup, hash or index between them.  This closes NONCLAIM 2 below --
    see there for what it does NOT close.
  * The persisted shapes are real and shipped: ``character_backpack_items``
    (migration 003) is keyed ``(character_id, item_identity)`` and carries
    exactly the seven columns ``inventory.ItemAttrState`` carries.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  1. NOTHING DISPATCHES THIS MODULE.  ``MOB_PICKUP_WIRING`` is a request to
     the chief, not a call site.  No player has picked anything up.
     [STALE as of runtime.py CORE-REQUEST-007, PR pirate-force-server#71,
     chief round 3lzfhw, 2026-08-26] ``BagCellRegistry.claim``/``.release``
     ARE now call sites -- NOT the ``PickupClaim`` of NONCLAIM 12, a
     different sense of the word: this is the per-connection BAG-OWNERSHIP
     claim, one per character, not a player claiming a ground drop.
     [MEASURED, by call-site reading] ``runtime.py`` calls
     ``.claim(character_id, self.foundation.backpack)`` unconditionally in
     the character-select/StartGame branch (also exercised incidentally by
     the general test suite, e.g. tests that reach
     ``start_game_res_scene_identity_sent``).
     ~~[MEASURED by call-site reading, NOT by an executed test -- no test in
     ``tests/`` references ``mob_pickup_registry``/``mob_pickup_bag_cell``]~~
     IS STRUCK (LANE-B round p3olrt): ``tests/test_mob_pickup_registry_
     wiring.py`` now drives the real ``make_state_class`` dispatch (login ->
     create -> StartGame) and proves, by execution rather than reading, that
     the claim is server-wide shared state (a second session on the same
     character is refused ``mob_pickup_claim_refused_bag_already_claimed``
     while the first's claim survives untouched) and that ``.release()``
     frees the character for the next session.  The sole ``.release(...)``
     call site sits in ``runtime.py``'s ``close_connection`` wrapper, which
     every ordinary disconnect reaches (unlike the opt-in logout-hypothesis
     scenario, which closes the inner foundation object directly and relies
     on the listener's own teardown to reach the wrapper afterward) -- that
     release path is now pinned by the same file too.  What remains true for
     every OTHER symbol here: ``resolve_claim``, ``place_in_bag`` and
     ``BagCell.commit_pickup`` -- the actual ground-drop-to-bag transaction --
     have no call site anywhere, because "ON AN INBOUND PICKUP REQUEST" stays
     unwired pending RE-082's vital id.  No player has picked anything up.
  2. THE OBJECT REFERENCE WAS AN ASSUMPTION; RE-082 CONFIRMED IT AT THE
     STATIC LAYER, AND THIS MODULE'S GUARD DOES NOT RELAX BECAUSE OF THAT.
     [LANE-B ASSUMPTION - CONFIRMED by RE-082, 2026-08-26 10:17 +07:00,
     PASS/DONE, STATIC-ON-BRIDGE] GT-046 proved only that the client copies
     the dword at [drop-object+0x10]; RE-082 went further and proved, by an
     instruction-exact trace of the SAME client image, that that dword IS
     the element key this project writes at element +0x10, with no
     transform, handle, index or hash in between.  This lane still RESOLVES
     rather than TRUSTS: the claimed dword must equal a key that is live in
     the ledger and inside this lane's key block, or the claim is refused --
     that guard is cheap defense-in-depth against a future client image or a
     transcription mistake, not a hedge against this being unanswered any
     more.  If the assumption were ever wrong again, every claim would still
     refuse by name and nothing would be granted wrongly -- the failure mode
     stays "pickup never works", never "pickup works on the wrong object".
     RE-082's own nonclaims still apply and this module does not borrow past
     them: it is STATIC-ONLY (no capture, no live client), it answers for
     ONE image sha, and it does NOT lift MOB-PICKUP-001's evidence ceiling --
     no runtime transaction has run and no DB row has been written by this
     confirmation.  See ``notes_to_chief/20260826_1017_RE-082-RESULT-
     OBJECT-REF-IS-ELEMENT-KEY.md`` in the OTHER repository for the full
     trace.
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
fifth, newly created item is outside both.  THREE gates used to read that
exact judgement, all on the ONE production character-select path
(``runtime.py`` -> ``session.select_and_start``):

    1. store._load_backpack  -> require_known_backpack -> ValueError
    2. session.select_and_start -> is_unmoved_baseline -> PermissionError
    3. legacy_bridge.start_game -> make_backpack_attr -> require_known_backpack

COO-DECISION 20260826_0950 (a) narrowed gate 1 only.  pf-adversary caught the
first draft of this note claiming that alone was enough for a relog to reach
the world -- it is not, because gate 2 sits unmodified right behind it, and
a second attempt at narrowing gate 2 too turned out to be WRONG in a
different way: it is what stops
``tests/test_item_move_generalized.py::test_moved_state_reconnect_is_opt_in_and_baseline_fails_closed``
from passing a HYP-PF-010/017/018-mutated state back into a plain reconnect
without that hypothesis's own opt-in flag.  ``is_unmoved_baseline`` guards
EVERY governed mutation's post-state, not only the one HYP-PF-008 names, and
narrowing it to "just the slot-2 case" silently let every other mutated
state back in unguarded.  So gate 2 was left unchanged that round, and it
only moved:

    1. store._load_backpack now calls require_backpack_shape -- structure
       only, no content restriction.  A drifted row LOADS from the DB.
    2. session.select_and_start -> is_unmoved_baseline -> PermissionError
       is UNCHANGED.  A drifted row that reaches here (real gameplay drift,
       not a governed mutation) is STILL refused here, exactly as before --
       that round did not find a way to tell "real item event" apart from
       "governed hypothesis mutation" that doesn't also break the latter's
       own reconnect guard, so it did not try.
    3. legacy_bridge.start_game -> make_backpack_attr -> require_known_backpack
       was unchanged too then, and would still refuse a drifted bag even if
       gate 2 let one through -- there was no wire encoder for content
       outside the two goldens.

COO-DECISION 20260828_0844 (mob-pickup gate-3 scope grant, answering this
lane's own ``20260828_0740_LANE-B-ASK-COO-...`` escalation) then widened
gate 3 ONLY, narrowly: no separate "item lane" exists, no other lane holds
``inventory.py``/``legacy_bridge.py``, and the wire fields were already fully
proven (HYP-PF-010/017), so the remaining work was reusing an already-proven
encoder, not new reverse engineering.  ``inventory.make_backpack_attr`` now
calls ``require_backpack_shape`` (structure only) instead of
``require_known_backpack`` (content-restricted) -- it can serialize any
structurally valid bag, including one holding a picked-up item, while a
drift in either golden snapshot is still caught exactly as before --
``INITIAL_BACKPACK`` inline in ``make_backpack_attr`` itself,
``MERGED_V111_BACKPACK`` one layer out in ``tests/test_item_lifecycle.py``'s
own golden-hash comparison (an asymmetry that predates this round).  Gate 2
is explicitly OUT of that grant and stays
unchanged: ``is_unmoved_baseline`` still refuses any non-baseline bag at
``session.select_and_start``, before gate 3 would ever run for one.  So the
gates now read:

    1. store._load_backpack -> require_backpack_shape -- structure only,
       UNCHANGED since COO-DECISION 20260826_0950 (a).
    2. session.select_and_start -> is_unmoved_baseline -> PermissionError --
       STILL UNCHANGED.  This is the gate that actually stops a relog today.
    3. legacy_bridge.start_game -> make_backpack_attr -> require_backpack_shape
       -- WIDENED this round.  No longer the blocker; gate 2 is.

THE WALL MOVED ON 2026-08-29, AND ROW 2 ABOVE IS NOW HISTORY.  Chief wired
gate 2 to ``bag_admission.may_enter_world`` in PR #233 on COO-DECISION
20260829_0441 item 1, so ~~"session.select_and_start -> is_unmoved_baseline,
STILL UNCHANGED, the gate that actually stops a relog today"~~ IS STRUCK.
The three gates as they stand:

    1. store._load_backpack -> require_backpack_shape -- structure only.
    2. session.select_and_start -> bag_admission.may_enter_world -- ADMITS a
       golden-plus-acquired bag; refuses a drifted one by a named reason.
       ``is_unmoved_baseline`` itself was NOT narrowed, so every governed
       mutation's reconnect guard is untouched -- that is why the earlier
       attempt to narrow it was wrong and this one is not.
    3. legacy_bridge.start_game -> make_backpack_attr -> require_backpack_shape
       -- structure only.

So no gate blocks the relog any more.  WHAT BLOCKS IT IS THAT NO INSERT RUNS
ON A PICKUP PATH.  ~~"``store.py`` has no backpack INSERT"~~ IS STRUCK AS
FALSE: ``store._insert_initial_backpack`` INSERTs INTO
``character_backpack_items`` at CHARACTER CREATION -- pinned by
``tests/test_bag_admission_expiry.py`` before this section ever claimed
otherwise.  That creation INSERT is the ONLY one; there is none on a pickup
path; and nothing advances ``character_backpacks.next_item_identity``, not
even the creation write, which leaves it to migration 005's DEFAULT.  So a
picked-up item exists only inside the session that took it, and a relog
reloads the golden bag it always did.  A round adding the pickup INSERT has
BOTH to write the row and to reconcile that counter.
That is chief's ticket ``STORE-INSERT-001``, the closing
condition of BUILD-006, and the expiry condition of ``bag_admission``'s
NONCLAIM 8 -- one ticket, named in three places, so no reader can conclude
from this file that a gate is what they have to go and widen.
``inventory.py`` and ``legacy_bridge.py`` remain outside this lane's
ordinary write zone; the edits there were the exact narrow scope
COO-DECISION 20260828_0844 granted, nothing wider.
``MOB_PICKUP_ROW_WOULD_INSERT`` (see ``dispatch_pickup_request`` below)
stays a LOG, not an INSERT: writing that row is ``store.py``'s, which is
chief's file, not this lane's.
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

# THE EXACT HEADLINE CALL, AS ONE STRING, SO IT CAN BE PINNED RATHER THAN
# DESCRIBED.  MOB_PICKUP_WIRING below is built FROM this constant instead of
# spelling the call out a second time in its own literal text -- an
# adversarial pass proved why that separation matters: it swapped the
# drop_ledger_cell/legacy argument order in the wiring's copy of this exact
# text and the full suite stayed green, because nothing executed the string,
# only searched it for substrings.  tests/test_mob_pickup.py now does both:
# asserts this constant appears verbatim inside MOB_PICKUP_WIRING (so nobody
# can edit the wiring's copy without editing the one place this file and that
# test both read), AND execs this exact text against real fixture objects
# bound under the same names it uses, so a wrong argument order, a wrong
# argument count or a call to the wrong function name all turn red.
MOB_PICKUP_DISPATCH_HEADLINE_CALL = (
    "mob_pickup.dispatch_pickup_request(bag_cell, drop_ledger_cell, legacy, "
    "identity, x, y, z, object_ref_u32, opaque_u8)"
)

MOB_PICKUP_WIRING = (
    "runtime.py.  The scene already holds ONE mob_loot.DropLedgerCell (see "
    "mob_loot.MOB_LOOT_WIRING).  This lane adds no second owner of the ground "
    "-- but it DOES need an owner of the BAG, and the server holds ONE "
    "mob_pickup.BagCellRegistry the same way it holds that ledger cell.\n"
    "  AT CHARACTER SELECT:\n"
    "  0. bag_cell = registry.claim(character_id, store.get_backpack(...))\n"
    "     - claim() is the whole point: a SECOND live cell for one character "
    "would allocate the same slot and the same identity as the first, and "
    "both drops would leave the ground.  The second claim is refused by name "
    "(bag_already_claimed) instead.\n"
    "     - registry.release(character_id) on logout, disconnect or a "
    "character switch.  A teardown that never runs leaves the character "
    "claimed and the next select refuses out loud, which is the failure this "
    "lane wants.\n"
    "  ON AN INBOUND PICKUP REQUEST, decoded to (claimant identity, claimant "
    "position, object reference dword, the request u8):\n"
    "  outcome = " + MOB_PICKUP_DISPATCH_HEADLINE_CALL + "\n"
    "     - ONE CALL for steps 1, 2, 3 (log-only) and 4 below.  Inside it: "
    "1. claim = mob_pickup.PickupClaim(identity, x, y, z, object_ref_u32, "
    "opaque_u8); 2. outcome = bag_cell.commit_pickup(drop_ledger_cell, "
    "claim, legacy); 3. logs what outcome.row_write would have inserted "
    "instead of running it (see the STOP below); 4. returns outcome so you "
    "still send outcome.delta yourself.  Call this instead of assembling "
    "the four pieces by hand -- that recipe used to be this note's whole "
    "body and an adversarial pass still found a call site in it that could "
    "not typecheck.\n"
    "     - PASS THE LEGACY MODULE.  With it, the response bytes are composed "
    "INSIDE the transaction, before the row leaves the ground, and a byte "
    "problem refuses the pickup instead of eating it.  Composing them "
    "afterwards is how an earlier version of this very line put four "
    "refusals on the far side of the take.\n"
    "     - every refusal is a MobPickupContractError whose first argument is "
    "one of MOB_PICKUP_REFUSAL_REASONS, unchanged and unwrapped from what "
    "commit_pickup(drop_ledger_cell, claim, legacy) itself raises.  EXACTLY "
    "ONE of them means the row is gone: drop_left_the_ground.  Every other "
    "refusal, including object_ref_never_issued and drop_already_taken, "
    "leaves the ground untouched.  Do not retry drop_left_the_ground.\n"
    "     - THE LOSER OF A RACE USUALLY SEES drop_already_taken, not "
    "drop_left_the_ground: the window between resolve and take is a handful "
    "of instructions and the row is normally gone before resolve runs.  "
    "NEITHER refusal is evidence about RE-082 -- see the note on that split "
    "in resolve_claim.\n"
    "  ROUND uq2lxw SUPERSEDES THE DISPATCH CALL ABOVE AND STEP 3 BELOW "
    "WITH ONE CALL, AND THE OLD RECIPE IS KEPT ONLY AS THE RECORD OF WHY. "
    "DO NOT follow those two as written; use "
    + "mob_pickup_persist.pickup_and_persist(store, sid, character_id, "
    "bag_cell, drop_ledger_cell, legacy, identity, x, y, z, "
    "object_ref_u32, opaque_u8)" +
    " for the whole of it.  It runs the "
    "SAME dispatch, and adds the one thing this note cannot: it asks the "
    "store everything the store would refuse BEFORE the take, so a doomed "
    "write refuses the pickup instead of eating the drop.  Following the "
    "two steps as written below destroys a player's item whenever this "
    "session's bag cell has drifted from the database -- proven by "
    "execution in tests/test_mob_pickup_persist.py::test_without_the_"
    "precheck_the_same_drift_destroys_the_drop.  Then send "
    "result.outcome.delta at step 4, unchanged.\n"
    "  3. PERSIST via store.commit_acquired_backpack_item(sid, "
    "character_id, outcome.item) -- and STILL do not write an INSERT of "
    "your own.  ~~STOP: persisting is not safe yet, gate 2 "
    "(is_unmoved_baseline) refuses a bag holding it~~ is SUPERSEDED TWICE "
    "(LANE-B struck the same sentence in round 149wbp, from the gate side; "
    "this is the same correction plus the write that now exists): "
    "gate 2 asks bag_admission.may_enter_world since round 1684ra, which "
    "admits a bag place_in_bag produced, and STORE-INSERT-001 (round "
    "4gqnwm) put the row and the identity counter in one transaction "
    "behind that one store call.  The store validates the identity "
    "against character_backpacks.next_item_identity, so seed this "
    "session's BagCell from store.backpack_issued_through and never from "
    "the column directly.  A refusal from that call means the row is NOT "
    "in the bag while this process thinks it is -- the drop is already off "
    "the ground by then, so the call site owes the player a resync, which "
    "NOTHING PROVIDES YET (see NONCLAIM 16).  dispatch_pickup_request "
    "still only logs (token MOB_PICKUP_ROW_WOULD_INSERT, via "
    "bag_row_write_console_line); the write is the caller's one line, and "
    "BagRowWrite.COLUMNS/outcome.row_write.values() remain the column "
    "order if anyone needs it.\n"
    "  4. send outcome.delta to the claimant -- it is the (pc, frame) pair "
    "dispatch_pickup_request already composed and validated.  Do NOT call "
    "bag_delta_pc here.\n"
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
#
# AND THE DERIVATION IS ONE-DIMENSIONAL WHILE THE GATE IS THREE.  mob_loot
# scatters on X ONLY -- y and z are copied unchanged -- so this number
# describes a segment, and the same 450 is then allowed in Y and Z where the
# scatter is zero and the derivation says nothing at all.  Two consequences
# this lane states rather than hides: reach from the death point along +X is
# 450 of scatter plus 450 of gate, so 900; and a claimant 449 units above or
# below a drop passes on nothing.  mob_loot's own comment on the step says
# "MULTIPLYING it is ours and is measured by nobody", and multiplying it is
# now load-bearing twice over.  It stays generous on purpose (NONCLAIM 5) and
# it stays unmeasured until somebody measures it.
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

# ~~Gate 2 is what actually still blocks persistence~~ IS STRUCK, AND IT WAS
# SHIPPING AS DATA, NOT AS A COMMENT (chief's R222 letter, 2026-08-29T05:10
# +07:00, item 3): all three gates are widened now.  Gate 1 and gate 3 by
# COO-DECISION 20260826_0950 / 20260828_0844, gate 2 by chief's PR #233 on
# COO-DECISION 20260829_0441 -- session.select_and_start calls
# bag_admission.may_enter_world, which ADMITS a golden-plus-acquired bag.
#
# ~~What blocks the relog now is upstream of every gate: no INSERT runs on a
# PICKUP path, so a picked-up row never reaches the database.~~  STRUCK IN
# ROUND 4gqnwm, one round later: STORE-INSERT-001 landed
# store.commit_acquired_backpack_item, which INSERTs the row and advances the
# counter in one transaction.  What blocks a PLAYER is now the absent call
# site (GT-124) -- which is not a gate, and must not be recorded as one.
#
# ~~"store.py has no backpack INSERT"~~ IS STRUCK AS FALSE, and it was the
# first draft of this very correction (pf-adversary, round 149wbp):
# store._insert_initial_backpack DOES INSERT INTO character_backpack_items at
# character creation.  Getting THIS sentence wrong is not cosmetic -- a
# reader told the file writes nothing would add a second INSERT beside one
# they never looked at, and would not reconcile the character-creation write
# (which leaves next_item_identity to migration 005's DEFAULT) with a counter
# that now has to advance.  The value below is DERIVED from store.py's
# executed SQL by tests/test_mob_pickup.py, not asserted against this
# literal, so the day STORE-INSERT-001 lands it goes red here too.
GOVERNED_BAG_ALLOWLIST_BLOCKS_PERSISTENCE = False
GOVERNED_BAG_ALLOWLIST_OWNER = (
    "nobody: gate 2's admission predicate admits an acquired row since "
    "round 1684ra, and store.commit_acquired_backpack_item writes the row "
    "with the identity counter since round 4gqnwm; the remaining blocker "
    "is the absent call site (GT-124)"
)

MOB_PICKUP_NONCLAIMS = (
    "1. Nothing dispatches this module.  MOB_PICKUP_WIRING is a request to "
    "the chief, not a call site.  No player has picked anything up. "
    "[STALE as of runtime.py CORE-REQUEST-007, PR #71, round 3lzfhw, "
    "2026-08-26] [MEASURED, by call-site reading]: BagCellRegistry.claim/"
    ".release ARE now call sites (the per-connection bag-ownership claim, "
    "not a player's PickupClaim -- see nonclaim 12). "
    "resolve_claim/place_in_bag/BagCell.commit_pickup -- the actual "
    "ground-drop-to-bag transaction -- still have no call site anywhere, "
    "pending RE-082's vital id. No player has picked anything up.",
    "2. The object reference WAS an assumption [LANE-B ASSUMPTION - "
    "CONFIRMED by RE-082, 2026-08-26 10:17 +07:00, PASS/DONE, "
    "STATIC-ON-BRIDGE]: GT-046 proved the client copies the dword at "
    "[drop-object+0x10]; RE-082 traced the SAME client image further and "
    "proved that dword IS the key this project writes at element +0x10, "
    "no transform in between.  The claim is still RESOLVED against the "
    "live ledger, never trusted -- that does not change because the "
    "answer came back yes -- so a wrong assumption would still refuse "
    "every claim and grant none.  RE-082 is static-only and answers for "
    "one image sha; it does not lift this lane's own evidence ceiling.",
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
    "9. STOP: RELOG IS STILL NOT CLOSED, AND THE REASON CHANGED.  ~~'session."
    "select_and_start's is_unmoved_baseline (gate 2) is unchanged and still "
    "refuses any non-baseline bag'~~ IS STRUCK: chief wired gate 2 to "
    "bag_admission.may_enter_world in PR #233 (COO-DECISION 20260829_0441 "
    "item 1), so all three gates now ADMIT a golden-plus-acquired bag and "
    "~~'persisting a picked-up item makes the character unable to enter the "
    "world at all'~~ IS STRUCK WITH IT.  What is not closed is that no "
    "INSERT runs on a PICKUP path.  ~~'store.py has no backpack INSERT'~~ IS "
    "STRUCK AS FALSE TOO, and it was this lane's own first draft of this "
    "correction: store._insert_initial_backpack INSERTs INTO "
    "character_backpack_items at CHARACTER CREATION, which "
    "tests/test_bag_admission_expiry.py has pinned all along.  Precisely: "
    "that is store.py's only backpack INSERT, there is none on a pickup "
    "path, and nothing advances character_backpacks.next_item_identity -- "
    "the creation INSERT does not set it either, so it comes from migration "
    "005's DEFAULT and a round that adds the pickup INSERT has to reconcile "
    "both. That is chief's ticket STORE-INSERT-001, and it "
    "is the same condition bag_admission's NONCLAIM 8 expires on.",
    "10. Nothing here writes a database row, opens a socket, reads a clock or "
    "reads a file.  It is a pure transaction over values plus one take "
    "through mob_loot's cell.  dispatch_pickup_request is the one exception "
    "to 'nothing prints': it prints one ASCII console line reporting what an "
    "INSERT would have been (see THE WALL) -- it still does not write a "
    "database row, open a socket, read a clock or read a file.",
    "11. THE BAG NEEDS AN OWNER; BagCell IS IT AND BagCellRegistry IS WHAT "
    "MAKES IT ONE.  A BackpackState is a VALUE, and two pickups resolved "
    "against one value pick the same slot and the same identity.  ~~'the "
    "primary key does not catch that -- it keys identity, not slot'~~ IS "
    "STRUCK, AND PRECISELY: that SENTENCE is true, the INFERENCE drawn from "
    "it was false.  Migration 003 carries UNIQUE(character_id, slot) as well "
    "as the primary key, so the database refuses the second row loudly -- but "
    "AFTER the drop has left the ground, which is why the answer is a cell "
    "that refuses BEFORE the take and not a check bolted onto the write.  "
    "~~and why a cell was enough~~ IS STRUCK TOO: a constructor is not "
    "something a second caller can lose, so 'one cell per character' was an "
    "instruction exactly as unenforced as 'do not pass the value twice' had "
    "been.  The registry is where the claim is atomic and a second claimant "
    "is refused by name.",
    "12. NO PLAYER CAN ORIGINATE A CLAIM TODAY, and it is not the opcode that "
    "stops them.  GT-046's producer needs a SELECTED LIVE DROP-OBJECT to copy "
    "its dword out of, and GT-045 measured that this pipe draws a name label "
    "with NO MODEL under it -- there is nothing to click.  mob_loot's own "
    "NONCLAIM 4 says the same about GT-060's precondition.  This lane is the "
    "transaction behind a door nobody can knock on yet.",
    "13. THE REQUEST HAS TWO FIELDS AND THIS LANE ACTS ON ONE.  The proven "
    "body carries the dword at object+0x14 and a u8 at object+0x18.  "
    "PickupClaim carries both and validates both; the outcome and the report "
    "carry the u8 through so it reaches whoever reads a log.  Nothing acts on "
    "it, because nothing has measured what it means.  The first draft claimed "
    "to report it and did not -- it stopped at the claim record, which is "
    "'discarded one step past the door' rather than carried.",
    "14. THE ITEM IDENTITY IS DERIVED, NOT A HIGH-WATER MARK, and mob_loot "
    "wrote down why that shape is a bug: a bag that has ever SHRUNK hands the "
    "next pickup an identity a client may still be holding.  ~~There is "
    "nowhere to persist a high-water mark today -- neither "
    "character_backpacks nor migration 003 has a column for one -- and which "
    "lane owns that column is an open question.~~ ANSWERED AND BUILT (round "
    "4gqnwm, COO-DECISION 20260829_0441 item 3): the mark is "
    "character_backpacks.next_item_identity, owned by store.py, advanced by "
    "store.commit_acquired_backpack_item in the same transaction as the row. "
    "Seed a cell from store.backpack_issued_through (the column MINUS ONE, "
    "which is this lane's INCLUSIVE convention); the derived fallback stays "
    "for callers who have no store, and is still a fallback, not a policy.",
    "15. [MEASURED BY EXECUTION (round `bdcmkf`, tests/test_mob_pickup.py::"
    "test_nothing_binds_the_claim_identity_to_the_bagcells_own_character), "
    "not fixed; the OPEN RISK / flagged-this-round wording is from round "
    "`37ts2b` and is stale -- this claim has since been run, not merely "
    "read] NOTHING HERE BINDS bag_cell TO THE CLAIMANT IN THE REQUEST "
    "IT IS PASSED AGAINST.  dispatch_pickup_request (and BagCell.commit_pickup "
    "underneath it) checks that bag_cell is a typed BagCell -- it does not "
    "check that the bag_cell handed in is the one the connection carrying "
    "claim.claimant_identity was given at character select.  A mismatched "
    "pair (connection A's decoded claimant_identity paired with connection "
    "B's live BagCell) is not refused by anything in this module today: this "
    "is pre-existing behaviour inherited unchanged from BagCell.commit_pickup, "
    "not something this round introduced or fixed.  Whether that binding "
    "belongs to runtime.py (match the decoded identity to the caller's own "
    "claimed cell before calling in) or is an open design question for the "
    "COO is not decided here; this module provides no defense-in-depth "
    "against a mismatched pair.",
    "16. [MEASURED BY EXECUTION (round 1yj0j0, "
    "tests/test_mob_pickup_persist.py::"
    "test_without_the_precheck_every_later_pickup_keeps_failing_the_same_way), "
    "not fixed; the OPEN RISK / flagged-this-round wording is from round "
    "4gqnwm and is stale -- this claim has since been run, not merely read] "
    "A BagCell AND THE DATABASE COLUMN ARE TWO ALLOCATORS THAT AGREE ONLY "
    "WHILE EVERY COMMIT SUCCEEDS.  BagCell.commit_pickup advances "
    "_issued_through in memory after the drop leaves the ground; "
    "store.commit_acquired_backpack_item is a separate later call that can "
    "refuse (lease taken over, database locked, disk full).  ~~'After one "
    "such refusal the cell mints one above the column forever, so EVERY "
    "later pickup in that session is refused by identity'~~ IS STRUCK AS TOO "
    "BROAD: a store that is merely BEHIND (one stranger write landed while "
    "this cell was not looking, then healthy again) closes the gap after "
    "exactly one more failed attempt, because the cell's own mark advances by "
    "one on that attempt too -- round 1yj0j0 tried to prove 'forever' from "
    "exactly that drift first and measured a SECOND attempt succeed, which is "
    "what forced the correction here.  The executed test proves the "
    "store-never-recovers case only: three attempts against a store mocked to "
    "fail every call mint three distinct identities, refuse all three with the "
    "same reason, and the gap between the cell's mark and the column widens "
    "every time -- never a write that lands.  So the true shape is: this "
    "session is refused for as many further pickups as the store stays down, "
    "not unconditionally forever -- each one having already taken its drop "
    "off the ground either way.  There is no re-seed call and no compensating "
    "put-it-back.  The call site (GT-124) must decide what the player gets; "
    "until it does, this lane does not claim a pickup is atomic - only that "
    "the DATABASE write is.",
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
# that WAS evidence about RE-082 (CLOSED PASS/DONE 2026-08-26, see NONCLAIM 2:
# the answer came back yes, this distinction is kept as defense-in-depth, not
# as an open experiment).  The first draft collapsed both into one refusal
# whose message named RE-082, so every double-click in the game would have
# been logged as evidence against an assumption that ticket has since
# answered.
REFUSE_DROP_ALREADY_TAKEN = "drop_already_taken"
REFUSE_OBJECT_REF_NEVER_ISSUED = "object_ref_never_issued"
REFUSE_CLAIMANT_OUT_OF_RANGE = "claimant_out_of_range"
REFUSE_NOT_THE_KILLER = "not_the_killer"
REFUSE_BAG_ROW_COLLIDES = "bag_row_collides"
REFUSE_BAG_IS_FULL = "bag_is_full"
REFUSE_IDENTITY_BLOCK_SPENT = "identity_block_spent"
REFUSE_IDENTITY_HIGH_WATER_BELOW_THE_BAG = "identity_high_water_below_the_bag"
REFUSE_BAG_ALREADY_CLAIMED = "bag_already_claimed"
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
    REFUSE_BAG_ALREADY_CLAIMED,
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


#: The widest actor identity this lane accepts, ROUND uq2lxw2.  IT IS BOUND
#: TO MOB_LOOT'S CONSTANT, not to a copy of its number: two files that hand
#: each other the same value and disagree about its width is the defect this
#: round fixes, and two literals that must be kept equal is the same defect
#: with a longer fuse.
#:
#: WHAT THAT BINDING IS AND IS NOT (pf-adversary, round uq2lxw2): it is
#: resolved ONCE, at import.  Rebinding ``mob_loot.MAX_IDENTITY`` at run time
#: splits the two lanes again, and nothing here would notice.  What the
#: construct actually buys is that the two bounds cannot be edited apart IN
#: THE SOURCE, which is where the defect happened; it is not a live alias,
#: and ``tests/test_mob_pickup.py`` reads this module's own AST to hold it to
#: being a reference rather than a literal.
MAX_ACTOR_IDENTITY = mob_loot.MAX_IDENTITY


def _require_identity(value: Any, label: str) -> int:
    """A live actor's identity: the same width ``mob_loot`` accepts.

    ROUND uq2lxw2.  ~~``_require_int(value, label, 0, 0xFFFFFFFF)``~~ IS
    WIDENED, on a measurement chief made in round ni2wh2 and handed to this
    lane (the pf_bridge repo's ``notes_to_chief/20260829_1221_CHIEF-ASK-COO-
    gt124-opcode-forbidden-and-drops-pruned.md``, section 3 -- THAT FILE IS
    NOT IN THIS REPOSITORY and a reader here cannot open it, which is why
    the measurement itself is quoted below rather than cited):

        identity_hi==0  -> PickupClaim ACCEPTED
        identity_hi==1  -> PickupClaim REFUSED 'value_out_of_range'
                           (the same value in a GroundDrop is accepted)

    ``runtime.py`` composes a performer identity as
    ``(hi << 32) | lo`` -- 64 bits -- and hands the SAME number to
    ``mob_loot`` (which accepts it) and to this lane (which did not).  What
    keeps that from being a live bug today is an accident and not a design:
    ``lifecycle.py`` sets ``hi = 0`` for every character this server creates.
    The day an identity arrives from anywhere else, picking things up starts
    refusing with a range error nobody can explain from the message.

    WIDENED TO THE WHOLE u64 AND NOT TO 2 ** 62, which is what the first
    draft of this round did on both sides: ``runtime.py`` composes
    ``((hi & 0xFFFFFFFF) << 32) | (lo & 0xFFFFFFFF)``, so 2 ** 62 leaves
    three quarters of the composition refused -- by BOTH lanes once they
    agree, which is a tidier failure and not a fixed one (pf-adversary,
    measured).

    WHAT IS NOT WIDENED, and the distinction is the whole reason this is a
    separate function.  ``object_ref_u32`` (a drop key that travels on the
    wire as a u32), ``opaque_u8``, the item identity (``MAX_ITEM_IDENTITY``,
    a database column) and ``character_id`` all keep their own bounds -- they
    are different quantities that happened to share a validator's name.  This
    one is for ACTOR identities only: the claimant, and the killer a drop
    records.  Neither is ever packed into bytes by this module (they are
    compared and printed as ``0x%X``), which is why the width can follow the
    server's composition rather than a wire field's.
    """
    identity = _require_int(value, label, 0, MAX_ACTOR_IDENTITY)
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


UNNAMED_ITEM_LABEL = "item %d"


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


def _require_triple(value: Any, label: str) -> tuple:
    """An (x, y, z) of finite numbers, refused BY NAME when it is not.

    The first version unpacked straight into three names, so a two-element
    tuple left this public function raising a bare unpack ValueError that
    ``except MobPickupContractError`` does not catch.
    """
    try:
        parts = tuple(value)
    except TypeError:
        raise MobPickupContractError(
            REFUSE_POSITION_NOT_FINITE,
            "%s must be an (x, y, z) triple" % label) from None
    if len(parts) != 3:
        raise MobPickupContractError(
            REFUSE_POSITION_NOT_FINITE,
            "%s must be an (x, y, z) triple, got %d values"
            % (label, len(parts)))
    return tuple(
        _require_finite(part, "%s component" % label) for part in parts)


def squared_distance(here: Any, there: Any) -> float:
    """Full 3D, squared, the way the aggro lane compares distances."""
    ax, ay, az = _require_triple(here, "position")
    bx, by, bz = _require_triple(there, "position")
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
    issued is the only shape that WAS evidence about the object-reference
    assumption -- RE-082 has since closed PASS/DONE (2026-08-26, NONCLAIM 2),
    so this split is kept as defense-in-depth, not as an open experiment.
    The first draft answered both with one message that named RE-082, which
    would have made every double-click in the game look like evidence
    against an assumption that ticket has since answered.
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

    THE WORD MEANS THE OPPOSITE THING ONE MODULE OVER, SO READ THIS BEFORE
    STORING ONE.  ``mob_loot.DropLedger.issued_through`` is EXCLUSIVE -- the
    next key to hand out, and a row at or above it is refused.  The mark this
    function takes is INCLUSIVE: the highest identity ALREADY ISSUED, so it
    returns ``mark + 1``.  Two conventions under one word in one file is how
    a column gets built against the wrong one: a stored "next free" seeded
    here skips an identity per session, a stored "last issued" is correct.
    The parameter is named for what it is in the caller's world; what this
    lane needs is the LAST ISSUED value.

    ~~THERE IS NOWHERE TO PERSIST A HIGH-WATER MARK TODAY.  Neither
    ``character_backpacks`` nor migration 003 has a column for one, and adding
    one is the item lane's call, not this lane's.~~  THERE IS ONE NOW:
    ``character_backpacks.next_item_identity`` (migration 005), advanced by
    ``store.commit_acquired_backpack_item`` since round 4gqnwm.  Ask for it as
    ``store.backpack_issued_through``, which is that column MINUS ONE and is
    exactly the INCLUSIVE mark this parameter wants; the column itself is
    EXCLUSIVE and passing it here skips an identity per issuance.  This
    function still ACCEPTS a
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
    # Composed BEFORE the take and carried, never composed afterwards.  See
    # BagCell.commit_pickup: an adversarial pass followed this lane's own
    # wiring recipe and found that composing the delta at step 4 -- after the
    # step-2 take -- put four more refusals on the far side of the take, which
    # is the exact defect the round had just removed from somewhere else.
    delta: Any = None
    # The request's second field, carried through so a report can show it.
    opaque_u8: int = 0

    @property
    def display_name(self) -> str:
        """The name a person would read, and NEVER a raise.

        ``PickupOutcome`` is the one typed record in this file with no
        ``__post_init__``, and that is deliberate: it is constructed AFTER the
        row has left the ground, so a validator here would be a refusal that
        destroys what it refuses.  The cost is that this property must be
        total.  It was not -- it indexed the drop table directly, so an
        outcome naming one of the four rows a character SHIPS with (none of
        which are in this lane's drop tables) raised a bare KeyError inside a
        listener thread.  Nothing can build such an outcome today; the day
        NONCLAIM 6 is relaxed and an existing bag row becomes the subject, it
        could.
        """
        row = field_drop_tables.ITEMS.get(self.item.template_id)
        if row is None or not row[2]:
            return UNNAMED_ITEM_LABEL % self.item.template_id
        return row[2]

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


class BagCellTaken(MobPickupContractError):
    """A second cell was asked for a character that already has a live one."""


class BagCellRegistry:
    """WHO IS ALLOWED TO OWN A CHARACTER'S BAG.  One per server.

    WHY A SECOND OBJECT, AND WHY IT IS NOT CEREMONY.  ``BagCell`` was written
    to answer "a caller holding a VALUE cannot allocate against it safely".
    An adversarial pass then pointed out that the answer had only moved the
    unenforced instruction one step: the class docstring and the wiring line
    both said "one per selected character", and NOTHING made a second one
    fail.  Two cells for one character reproduce the original defect byte for
    byte -- same slot, same identity, both drops off the ground.

    ``DropLedgerCell`` earned its keep by being a thing a caller can LOSE
    access to.  A constructor is not that: no second caller can fail to call
    one.  So the claim is here, it is atomic, and a second claimant is refused
    by name until the first releases.

    Deliberately not a module global: a global is a second, invisible owner,
    and this project has spent two rounds learning what an unowned value
    costs.  The server holds this object the way it holds the scene's ledger
    cell.
    """

    def __init__(self) -> None:
        self._cells = {}
        self._lock = threading.Lock()

    def claim(self, character_id: Any, bag: Any,
              issued_through: Any = None) -> "BagCell":
        """The only way to get a cell.  A second live claim is refused."""
        character_id = _require_int(
            character_id, "character id", 1, MAX_ITEM_IDENTITY)
        # Built OUTSIDE the registry lock so a malformed bag refuses without
        # holding up every other character's claim -- and so the refusal is
        # the bag's own named one, not a lock-shaped one.
        cell = BagCell(bag, character_id, issued_through)
        with self._lock:
            live = self._cells.get(character_id)
            if live is not None:
                raise BagCellTaken(
                    REFUSE_BAG_ALREADY_CLAIMED,
                    "character %d already has a live bag cell; a second one "
                    "would allocate the same slot and the same identity as "
                    "the first, which is the defect the cell exists to "
                    "prevent.  Release the first (a logout, a disconnect, a "
                    "character switch) before claiming again"
                    % character_id)
            self._cells[character_id] = cell
            return cell

    def release(self, character_id: Any) -> bool:
        """Give the character back.  True if a cell was actually held.

        THE VALUE IN A RELEASED CELL IS DISCARDED, and that is correct rather
        than regrettable: this lane never persists, so the cell's bag is a
        projection of what the database already holds plus whatever this
        session picked up and could not write (see THE WALL).  A teardown
        that never runs -- a dropped connection -- leaves the character
        claimed, and the next select refuses by name rather than quietly
        handing out a second allocator.  A refusal a person can read beats a
        duplicate nobody can see.
        """
        character_id = _require_int(
            character_id, "character id", 1, MAX_ITEM_IDENTITY)
        with self._lock:
            return self._cells.pop(character_id, None) is not None

    def holds(self, character_id: Any) -> bool:
        character_id = _require_int(
            character_id, "character id", 1, MAX_ITEM_IDENTITY)
        with self._lock:
            return character_id in self._cells


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

    @property
    def issued_through(self) -> int | None:
        """The high-water mark this cell allocates from, or None if unseeded.

        ROUND uq2lxw.  Added for ``mob_pickup_persist.precheck_persistable``,
        which has to answer "would the identity this cell mints next be the
        one the database's column will demand" BEFORE a drop is taken off the
        ground -- and could otherwise only answer it by reaching into
        ``_issued_through``, which is a private of this class.  A reader of
        this value cannot change it: the mark moves only inside
        :meth:`commit_pickup`, under the lock, and only forward.

        WHAT THE LOCK HERE DOES AND DOES NOT DO, stated exactly because the
        first draft of this property claimed more (pf-adversary, round
        uq2lxw, twice).  Honestly: under CPython a bare read of an
        ``int | None`` attribute is already atomic, so this lock buys
        nothing a reader can name today.  It is kept because it costs one
        uncontended acquire and makes this property behave like
        :attr:`bag` beside it, not because it repairs a race.  ~~"an unlocked read of it beside a
        locked read of the bag could pair a mark with a bag it never went
        with"~~ IS STRUCK: two SEPARATE locked reads pair no better than one
        locked and one unlocked, and a caller that wants the mark and the bag
        to belong to one state cannot get that from this class today.
        ``mob_pickup_persist.precheck_persistable`` reads both, and what
        makes it safe is not this lock: every interleaving it can see is
        refused rather than written (its own docstring says which).
        """
        with self._lock:
            return self._issued_through

    def commit_pickup(self, ledger_cell: Any, claim: Any,
                      legacy: Any = None) -> PickupOutcome:
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
            # THE BYTES ARE COMPOSED HERE, BEFORE THE TAKE, and that is the
            # whole reason this method takes a ``legacy`` at all.  The wiring
            # line used to say "step 4: call bag_delta_pc(legacy, item)" --
            # after step 2's take -- and bag_delta_pc raises FOUR of this
            # lane's refusals, every one of them listed as leaving the drop on
            # the ground.  An adversarial pass ran that recipe with a shim
            # that moved one legacy constant and watched a drop leave the
            # ground, nothing get persisted and the client never get told.
            # Composing inside the transaction means a byte problem refuses
            # the pickup instead of eating it.
            delta = None if legacy is None else bag_delta_pc(legacy, item)
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
            return PickupOutcome(
                taken, item, bag, bag_after, row_write, delta,
                claim.opaque_u8)


# ---------------------------------------------------------------------------
# Dispatch.  The single call MOB_PICKUP_WIRING now hands the chief for an
# inbound pickup request: steps 1, 2, 3 (log-only) and 4, collapsed so a
# transcription slip in runtime.py has one line to happen in, not four.
# ---------------------------------------------------------------------------
def bag_row_write_console_line(row_write: Any) -> str:
    """One ASCII line reporting the INSERT a pickup WOULD have made.

    Same shape as ``mob_loot.drops_console_line``: a pure function that
    RETURNS a string rather than reaching for a console itself, so a caller
    decides whether and where it is printed.  ``dispatch_pickup_request``
    below is the one caller that does print it, and it says so in its own
    docstring.

    ``MOB_PICKUP_ROW_WOULD_INSERT`` is the token.  WOULD, not DID, and the
    WOULD is now about THIS FILE ONLY: nothing in ``mob_pickup`` ever turns
    this line into an INSERT, because this module has no cursor.

    ~~"``inventory.require_known_backpack`` refuses a bag holding a fifth
    item at the very next character select, so nothing in this file ever
    turns this line into a real INSERT"~~ IS STRUCK AS FALSE, round uq2lxw,
    measured rather than reasoned (pf-adversary): ``require_known_backpack``
    still refuses such a bag, but it is NOT on the character-select path at
    any of the three gates any more -- gate 1 (``store._load_backpack``) and
    gate 3 (``inventory.make_backpack_attr``) ask ``require_backpack_shape``,
    and gate 2 asks ``bag_admission.may_enter_world``.  A five-row bag
    holding a picked-up item passes all three today, measured end to end.
    THE STRUCK SENTENCE MATTERS BECAUSE OF WHO READS IT: an operator who
    greps this token on the console lands here, and would have reported to
    the owner both "nothing was written" and "character select would refuse
    it anyway" -- the second is false now, and since round uq2lxw the first
    is false too whenever ``mob_pickup_persist.pickup_and_persist`` is the
    call site (its ``MOB_PICKUP_ROW_INSERTED`` line is printed right after
    this one, and THAT is the DID).
    """
    if type(row_write) is not BagRowWrite:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a console line describes a typed BagRowWrite")
    return (
        "MOB_PICKUP_ROW_WOULD_INSERT table=character_backpack_items "
        "claimant=0x%X character_id=%d item_identity=%d template_id=%d "
        "quantity=%d slot=%d raw_u8_38=%d raw_u8_39=%d detail_present=%d"
        % (row_write.claimant_identity, row_write.character_id,
           row_write.item_identity, row_write.template_id,
           row_write.quantity, row_write.slot, row_write.raw_u8_38,
           row_write.raw_u8_39, row_write.detail_present)
    )


def dispatch_pickup_request(
        bag_cell: Any, ledger_cell: Any, legacy: Any,
        claimant_identity: Any, x: Any, y: Any, z: Any,
        object_ref_u32: Any, opaque_u8: Any = 0) -> PickupOutcome:
    """Steps 1, 2, 3 (log-only) and 4 of MOB_PICKUP_WIRING.  ONE call.

    THIS IS WHAT runtime.py CALLS ON AN INBOUND PICKUP REQUEST, not the four
    pieces the wiring note used to spell out by hand.  Before this function
    existed, that note asked the chief to assemble ``PickupClaim``, call
    ``commit_pickup``, remember NOT to persist ``outcome.row_write`` (see THE
    WALL), and send ``outcome.delta`` -- four places for a transcription
    slip.  ``test_the_wiring_line_this_lane_hands_the_chief_actually_runs``
    is what walked that OLD four-piece recipe and caught the transcription
    slip an adversarial pass had left in it.  This collapses all four into
    the one call the wiring note now names --
    ``MOB_PICKUP_DISPATCH_HEADLINE_CALL`` below -- and THAT call is itself
    pinned as an EXECUTED test, not only as a described paragraph:
    ``test_the_headline_dispatch_call_the_wiring_hands_the_chief_actually_runs``.
    A docstring's own example is exactly the kind of line a transcription
    slip hides in, and a test that only greps for substrings of it (as the
    older test above still does, for the OLD recipe) would not have caught a
    swapped argument order in THIS one -- an adversarial pass proved that
    concretely, by swapping ``drop_ledger_cell``/``legacy`` in the exact
    headline text and watching the full suite stay green.

    ``bag_cell`` is the character's OWN cell, the one
    ``BagCellRegistry.claim`` handed back at character select (step 0) --
    NOT the registry, and NOT re-claimed here.  ``ledger_cell`` is the
    scene's ``mob_loot.DropLedgerCell``.  Pass the real ``legacy`` module:
    with it, the response bytes are composed INSIDE the transaction, before
    the row leaves the ground, exactly as ``BagCell.commit_pickup``
    documents.

    REFUSES EXACTLY AS commit_pickup DOES, BY NOT CATCHING ANYTHING.  Every
    ``MobPickupContractError`` this raises is the SAME exception, with the
    same ``args[0]`` reason from ``MOB_PICKUP_REFUSAL_REASONS``, that
    assembling ``PickupClaim`` and calling ``commit_pickup`` by hand would
    raise for the same input.  Wrapping or swallowing it here would make a
    caller reading that reason see something this lane never produced.

    ON SUCCESS, STEP 3 IS A LOG, NOT AN INSERT.  See THE WALL in the module
    docstring.  ~~"persisting ``outcome.row_write`` is still refused at the
    very next character select by Gate 2 (``is_unmoved_baseline``)"~~ IS
    STRUCK -- gate 2 is ``bag_admission.may_enter_world`` since PR #233 and
    admits such a bag.  It stays a log because the INSERT belongs to
    ``store.py``, which has to advance
    ``character_backpacks.next_item_identity`` in the same transaction and
    is not this lane's file (``STORE-INSERT-001``).  This function never calls
    anything DB-shaped -- no cursor, no connection, no store function -- it
    prints ``bag_row_write_console_line(outcome.row_write)`` (token
    ``MOB_PICKUP_ROW_WOULD_INSERT``) and returns ``outcome`` UNCHANGED, so
    the caller still has ``outcome.delta`` to send (step 4) and
    ``outcome.row_write`` to inspect or log again itself if it wants to.

    NO FLAG.  No scenario id, no opt-in kwarg, no dispatch gate of its own --
    exactly as unconditional as every other symbol in this file.  As the
    module docstring says of the transaction underneath it: the day this is
    wired to a real opcode, one dispatch line at the call site changes and
    nothing in here does.
    """
    if type(bag_cell) is not BagCell:
        raise MobPickupContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "dispatch_pickup_request needs the character's own typed "
            "BagCell, the one BagCellRegistry.claim handed back")
    claim = PickupClaim(claimant_identity, x, y, z, object_ref_u32, opaque_u8)
    outcome = bag_cell.commit_pickup(ledger_cell, claim, legacy)
    print(bag_row_write_console_line(outcome.row_write))
    return outcome


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
# THE FRAME, RE-DERIVED, because the frame is the half that leaves the process
# and the first two drafts of this pin did not check it.
#
# Draft 1 asserted "frame is pc + 10 bytes", copying mob_loot's 54 - 44.  True
# of a 44-byte pc and false here: the body is a snappy RAW LITERAL whose tag is
# one byte below 60 bytes of payload and two above it.
#
# Draft 2 replaced that with "the header's MAGIC is right and its declared
# length matches the bytes that follow" -- and an adversarial pass showed the
# second half is CIRCULAR: frame_pc writes that length itself, so it is true of
# any body whatsoever.  A shim that framed completely different bytes passed.
#
# So the frame is now re-derived here, end to end, from the pc this lane just
# composed: the 8-byte header, then the varint length, then the literal tag,
# then the pc itself.  Nothing in it is taken on the legacy module's word.
DELTA_FRAME_MAGIC = 0x5F253EAC
DELTA_FRAME_HEADER_SIZE = 8
DELTA_LITERAL_CHUNK = 65536
DELTA_LITERAL_SHORT_LIMIT = 60


def _varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _snappy_raw_literal_via_struct(data: bytes) -> bytes:
    """The raw-literal encoding, re-derived rather than imported."""
    out = bytearray(_varint(len(data)))
    position = 0
    while position < len(data):
        chunk = data[position:position + DELTA_LITERAL_CHUNK]
        length_less_one = len(chunk) - 1
        if len(chunk) <= DELTA_LITERAL_SHORT_LIMIT:
            out.append(length_less_one << 2)
        else:
            width = max(1, (length_less_one.bit_length() + 7) // 8)
            out.append((59 + width) << 2)
            out += length_less_one.to_bytes(width, "little")
        out += chunk
        position += len(chunk)
    return bytes(out)


def _frame_via_struct(pc: bytes) -> bytes:
    body = _snappy_raw_literal_via_struct(pc)
    return struct.pack("<II", DELTA_FRAME_MAGIC, len(body)) + body

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
    expected_frame = _frame_via_struct(pc)
    if frame != expected_frame:
        raise MobPickupContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the framed bytes are not this lane's own framing of this pc "
            "(%d bytes composed, %d expected); the frame is the half that "
            "actually leaves the process"
            % (len(frame), len(expected_frame)))
    return pc, frame


def _observed_behaviour(legacy: Any = None) -> dict:
    """Run this lane against itself and report what it actually did.

    Every value here is the outcome of an executed transaction on throwaway
    records.  Nothing is asserted from memory, which is the only way a pin
    document can contradict the module it describes -- and the only way the
    test that reads it can fail.

    WIDENED after an adversarial pass: the ordering flag used to be observed
    from ONE refusal (bag-full) and reported as a statement about the whole
    lane, while four other refusals sat on the far side of the take by way of
    the wiring line.  It now walks every refusal a claim can produce and
    checks the ground after each.
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

    def refusal_of(call, *args, **kwargs):
        try:
            call(*args, **kwargs)
        except MobPickupContractError as exc:
            return exc.args[0]
        return None

    empty = BackpackState(BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1, ())
    after_one, item_one = place_in_bag(empty, first)
    _after_two, item_two = place_in_bag(after_one, second)

    full = BackpackState(
        BACKPACK_BASE_MASK, BACKPACK_BASE_IDENTITY, 1,
        tuple(ItemAttrState(slot + 1, 2400046, 1, slot)
              for slot in range(BAG_SLOT_COUNT)))

    # EVERY refusal a claim can reach, each against a fresh ground, each
    # checked for whether the ground moved.  A shim that breaks the byte
    # composer is included on purpose: that is the family the wiring line
    # used to run AFTER the take.
    class _BrokenLegacy:
        ITEM_OPERATE_RES_VITAL = 0x0000

        def __getattr__(self, name):
            return getattr(legacy, name)

    attempts = [
        ("bag_is_full", full, here, None),
        ("out_of_range", empty,
         PickupClaim(killer, 1e6, 0.0, 0.0, first.drop_key), None),
        ("not_the_killer", empty,
         PickupClaim(stranger, 0.0, 0.0, 0.0, first.drop_key), None),
        ("never_issued", empty,
         PickupClaim(killer, 0.0, 0.0, 0.0, mob_loot.DROP_KEY_LIMIT - 1),
         None),
    ]
    if legacy is not None:
        attempts.append(("composer", empty, here, _BrokenLegacy()))
    refused_before_the_take = True
    refusals_walked = []
    for name, bag, attempt, shim in attempts:
        cell = mob_loot.DropLedgerCell(ledger)
        before = cell.ledger
        reason = refusal_of(
            BagCell(bag, 1).commit_pickup, cell, attempt, shim)
        refusals_walked.append(name)
        if reason is None or cell.ledger != before:
            refused_before_the_take = False

    # And the registry: a second claim on one character must LOSE.
    registry = BagCellRegistry()
    registry.claim(1, empty)
    second_claim = refusal_of(registry.claim, 1, empty)

    return {
        "resolves_object_ref_against_the_ledger": (
            refusal_of(
                resolve_claim, ledger,
                PickupClaim(killer, 0.0, 0.0, 0.0, mob_loot.DROP_KEY_LIMIT - 1),
            ) == REFUSE_OBJECT_REF_NEVER_ISSUED
            and resolve_claim(ledger, here) is first),
        "killer_only": refusal_of(
            resolve_claim, ledger,
            PickupClaim(stranger, 0.0, 0.0, 0.0, first.drop_key),
        ) == REFUSE_NOT_THE_KILLER,
        "pickup_radius_reaches_the_furthest_object_of_one_kill": (
            within_pickup_radius(
                (0.0, 0.0, 0.0),
                (mob_loot.DROP_SCATTER_STEP
                 * (mob_loot.MAX_DROPS_PER_KILL - 1), 0.0, 0.0))),
        "stacks": item_one.slot == item_two.slot,
        "everything_that_refuses_refuses_before_the_take": (
            refused_before_the_take),
        "refusals_walked_for_that_flag": refusals_walked,
        "a_second_bag_cell_for_one_character_loses": (
            second_claim == REFUSE_BAG_ALREADY_CLAIMED),
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
    sample_row = BagRowWrite(
        0x750059, 1, item.identity, item.template_id, item.quantity,
        item.slot)
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
        # SPLIT IN TWO, because "EVERY BOOLEAN BELOW IS OBSERVED" was itself
        # a claim wider than its evidence: two of the entries under it were
        # bare literals, and one of those was the most epistemically loaded
        # flag in the document.  What is observed is observed by running the
        # lane; what is declared is declared, in its own block, where a reader
        # can tell them apart.
        "transaction_observed": _observed_behaviour(legacy),
        "transaction_declared": {
            "pickup_radius": PICKUP_RADIUS,
            "pickup_radius_is_arithmetic_not_measured": True,
            "pickup_radius_derived_on_x_only": True,
            "slot_policy": "lowest free slot",
            "identity_policy": (
                "highest identity in the bag plus one, or one past a "
                "high-water mark the caller supplies -- see NONCLAIM 14"),
            "the_one_refusal_that_means_the_row_is_gone": (
                REFUSE_DROP_LEFT_THE_GROUND),
        },
        "bag_row": {
            "table": "character_backpack_items",
            "columns": list(BagRowWrite.COLUMNS),
            "raw_u8_38": NEW_ROW_RAW_U8_38,
            "raw_u8_39": NEW_ROW_RAW_U8_39,
            "detail_present": NEW_ROW_DETAIL_PRESENT,
            "slots": BAG_SLOT_COUNT,
            # A DICT, built from the row's own values(), because the first
            # version was a hand-written list of SEVEN fields printed beside a
            # column list that had grown to EIGHT.  Every field in it misread
            # by one position, and no test could see it: the pin test compares
            # the file to the code, and both were wrong together.
            "sample_row": dict(zip(
                BagRowWrite.COLUMNS, sample_row.values())),
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
                "the character CAN enter the world carrying it, and the row "
                "persists: all three gates admit a golden-plus-acquired bag "
                "(gate 2 since PR #233), and "
                "store.commit_acquired_backpack_item writes the row with the "
                "identity counter since STORE-INSERT-001.  Both of this "
                "field's earlier answers are struck: 'the character cannot "
                "enter the world ... gate 2 still raises' was the reverse of "
                "the truth, and 'what is missing is the INSERT itself' was "
                "true for exactly one round.  What is absent is the call "
                "site (GT-124), which is not a gate"
            ),
            "open_question_for_the_item_lane": (
                "answered: character_backpacks.next_item_identity "
                "(migration 005) is the persisted high-water mark, owned by "
                "store.py -- read it as store.backpack_issued_through, "
                "which is the column MINUS ONE.  Open instead: who resyncs "
                "a BagCell whose commit was refused -- see NONCLAIM 15"
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
        # Carried, not acted on.  See NONCLAIM 13: the proven request body has
        # a second field and nothing has measured what it means, so the one
        # useful thing this lane can do with it is put it where a person
        # reading a log will see it.
        "request_u8": outcome.opaque_u8,
        "response_bytes_composed": outcome.delta is not None,
        "persisted": outcome.persisted,
        "survives_a_relog": False,
    }
