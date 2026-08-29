"""LANE-B / BAG-ADMISSION-001: tell a picked-up item apart from a governed
hypothesis post-state, at the character-select gate.

WHAT THIS MODULE IS FOR.  ``BUILD-006`` / M5 is "loot drops, you pick it up,
it is in your bag after a relog".  ``mob_loot`` built the roll and the ground,
``mob_pickup`` built the bag row -- and then both stopped at the same wall,
which ``mob_pickup``'s THE WALL section names in full.  Three gates on the one
production character-select path used to refuse a bag whose contents are not
one of two golden snapshots.  Two of them have been widened:

    1. ``store._load_backpack``  -> ``require_backpack_shape``    (widened)
    2. ``session.select_and_start`` -> ``may_enter_world``        (widened)
    3. ``legacy_bridge.start_game`` -> ``make_backpack_attr``     (widened)

~~"Gate 2 is the one that still stops the relog, and it is the only one
left"~~ IS STRUCK, AND SO IS ~~"-> is_unmoved_baseline (UNCHANGED)"~~ ABOVE:
chief wired gate 2 to ``may_enter_world`` in pirate-force-server PR #233
(COO-DECISION 20260829_0441 item 1), merged as ``e15bcac``, and
``session.py`` line 96 is the call site.  All three gates now admit a
golden-plus-acquired bag.  COO-DECISION 20260827_1350 deferred this
redesign with a date on it -- "นำงานออกแบบด่านที่ 2 เข้าคิว M5 ... revisit
ต้นสัปดาห์ M5 (30-31 ส.ค.)" -- and COO-DECISION 20260828_0844, which granted
this lane the gate-3 edit, was silent on gate 2 (see NONCLAIM 7: silence,
not a statement); 20260829_0441 is what ended that silence.

WHAT STOPS A RELOG TODAY IS NOT A GATE.  It is that nothing INSERTs the bag
row on a PICKUP path.  ~~"``store.py`` has no backpack INSERT"~~ IS STRUCK AS
FALSE -- pf-adversary refuted it in the round that wrote it, from this repo's
own committed evidence: ``store._insert_initial_backpack`` DOES
``INSERT INTO character_backpack_items``, at character creation, and
``tests/test_bag_admission_expiry.py`` has pinned exactly that all along
(``inserters == {"_insert_initial_backpack"}``).  The true statement is
narrower and is the one to quote: ``store.py``'s only backpack INSERT is
``_insert_initial_backpack`` at character creation, there is no INSERT on any
pickup path, and nothing anywhere advances
``character_backpacks.next_item_identity`` -- the character-creation INSERT
does not set it either, so it comes from migration 005's DEFAULT.  That is
chief's ticket ``STORE-INSERT-001``, and it is also the expiry condition
NONCLAIM 8 records for this whole module.

THIS MODULE IS THAT REDESIGN, AND IT IS NOW THE GATE.  It is still a pure
predicate and it still does not import ``session`` -- the dependency runs one
way, ``session`` -> here -- but ~~"it is not called by anything on the
production path yet, and it changes no behaviour on its own"~~ IS STRUCK.
A change in this file is a change to who can enter the world.  The round that
wrote it removed the reason the redesign was deferred -- "การรีบแยกด่านโดยไม่มี
metadata เพิ่มเสี่ยงพังเทส HYP ที่มีอยู่จริง"
-- by showing that the separation needs no new metadata and breaks no HYP
test.  See ``BAG_ADMISSION_WIRING`` for the one line that turns it on.

WHY THE LAST ATTEMPT FAILED, AND WHY THIS ONE IS SHAPED DIFFERENTLY.  The
previous attempt narrowed ``is_unmoved_baseline`` itself to "just the slot-2
case".  That silently let every OTHER governed mutation back in unguarded,
and pf-adversary caught it against
``tests/test_item_move_generalized.py::
test_moved_state_reconnect_is_opt_in_and_baseline_fails_closed``.  The lesson
is in that failure: ``is_unmoved_baseline`` is load-bearing for the whole
HYP-PF-008/010/017/018 family and must not be narrowed at all.

So this module does not narrow anything.  It ADDS a second, positive
admission path beside the existing one, and leaves ``is_unmoved_baseline``
exactly as it is:

    admissible  <=>  is_unmoved_baseline(bag)          # unchanged, first
                     or allow_hypothesized_item_move   # unchanged, second
                     or is_golden_plus_acquired(bag)   # NEW, third

THE DISCRIMINATOR, AND WHY IT IS NOT A GUESS.  Every governed mutation in the
family RELOCATES OR ALTERS AN ITEM THE GOLDEN ALREADY HAS:

    HYP-PF-008  move slot 0 -> slot 2      an existing item's slot changes
    HYP-PF-010  move to a free slot        an existing item's slot changes
    HYP-PF-017  swap with an occupied slot two existing items' slots change
    HYP-PF-018  merge into an occupied slot one item leaves, one's quantity
                                           changes
    V111 merge  initial -> merged          one item leaves, one's quantity
                                           changes

A pickup does none of those.  ``mob_pickup`` places one NEW row in a slot the
bag had FREE and touches nothing that was already there -- its
``BagRowWrite`` is an INSERT, and the only INSERT this lane has.  So the
question "is this drift real gameplay or an un-opted-in hypothesis state?"
has an answer already present in the bag -- which matters because the metadata
risk is the reason COO gave for deferring.  It is NOT that the project has no
provenance anchor: it has one (NONCLAIM 1), it is simply not advanced yet.
What this rule needs is only what a bag already carries:

    IS EVERY GOLDEN ITEM STILL PRESENT, UNCHANGED, IN ITS GOLDEN SLOT?

If yes, and the only difference is extra items in slots the golden left free,
the bag is a golden bag that ACQUIRED something.  If no, some existing item
moved or changed, and that is the governed family, refused exactly as today.

[MEASURED] ``tests/test_bag_admission.py`` does not sample this.  It
enumerates the governed family -- both goldens x every item x every one of
the 40 slots, through the three real ``inventory`` mutators, plus the one
shipped post-state constant (``HYPOTHESIZED_V111_SLOT2_BACKPACK``) -- and
requires every state it reaches to be refused, with ONE exemption it pins by
name: the V111 merge, whose post-state IS ``MERGED_V111_BACKPACK``.  That one
is admitted, today and after, because ``is_unmoved_baseline`` admits it;
refusing it would be a regression.  Exact counts, printed by the test:
HYP-PF-010 255 states, HYP-PF-017 18, HYP-PF-018 1 (the exemption),
HYP-PF-008 1.

[MEASURED, and it is the reason not to read the line above as a proof]
HYP-PF-018 contributes exactly ONE state and it is the exempted one, so the
enumeration asserts NOTHING about merges.  It is not that merges are
unchecked -- ``merge_known_item_into_occupied_slot`` refuses 24 of the 25
(item, slot) pairs inside ``require_known_backpack``, so no other merge
post-state exists to reach -- but this file cannot tell "no state reached"
from "state reached and refused", and its coverage assertion is green either
way.  The real closure came from pf-adversary, who composed the mutators to
DEPTH 3: 278,616 distinct reachable states, of which the ones
``is_unmoved_baseline`` refuses and ``may_enter_world`` admits number ZERO.

THE SECOND HALF OF THE DISCRIMINATOR: WHICH IDENTITIES AN ACQUIRED ITEM MAY
CARRY.  ``mob_pickup.next_item_identity`` is "HIGHEST + 1, never count + 1".
[DERIVED, not measured] an item this server minted into a bag that still
holds every golden row therefore carries an identity strictly greater than
every identity that golden holds.  The premise matters and is stated here
because that function's own text refutes derived-highest in GENERAL -- a bag
that SHRANK can reissue a freed identity -- and this module is only entitled
to the conclusion because it evaluates the identity rule solely on bags where
no golden row is missing.

NONCLAIMS -- read these before quoting this module as a safety argument.

 1. THIS IS A SHAPE TEST, NOT A PROVENANCE PROOF, AND THE PROVENANCE FACT
    ALREADY EXISTS IN THE SCHEMA.  ~~A provenance proof needs a column
    nobody has yet.~~ THAT WAS FALSE and it was the premise of the first
    draft of this module and of the letter to COO built on it.
    ``migrations/005_character_backpack_identity_counter.sql`` added
    ``character_backpacks.next_item_identity`` -- monotonic per character,
    NOT NULL, backfilled by the migration itself, tested at
    ``tests/test_item_lifecycle.py::
    test_migration_005_backfills_next_item_identity_per_character`` -- and
    its own header earmarks it for "the item lane (mob_pickup.py) [to] mark
    new issuance through".  (The stale sentence traces to
    ``mob_pickup``'s NONCLAIM 14, which still says migration 003 has no such
    column; true of 003, untrue since 005.)
    So the honest statement of this module's limit is not "the fact is
    unavailable" but "this module does not ask for it": it reads the bag and
    nothing else, so a hand-edited row that ADDS a well-formed item with a
    high enough identity is admitted.  Today gate 2 admits neither that nor a
    real pickup; wired, it would admit both.  ~~Why the counter is not used
    HERE, measured: nothing advances it yet -- ``MOB_PICKUP_ROW_WOULD_INSERT``
    is a log, not an INSERT -- so for every character alive today it still
    reads its backfilled value, and a real pickup's identity would be refused
    by a counter check.  It becomes the right question the day something
    advances it, and WHO advances it is the open question this round hands to
    COO rather than answers.~~  SUPERSEDED IN ROUND 4gqnwm, AND THE STRUCK
    TEXT IS LEFT VISIBLE BECAUSE IT IS WHAT A READER OF THIS FILE BELIEVED
    UNTIL TODAY.  ``store.commit_acquired_backpack_item`` (STORE-INSERT-001)
    now performs the INSERT and advances the counter in one transaction, and
    COO-DECISION 20260829_0441 item 3 answered who owns it.  Why the counter
    is STILL not used here is a different reason, and it is nonclaim 9: used
    ALONE it admits the HYP-PF-008 and HYP-PF-010 bags, which move a golden
    row without minting any identity.
 2. IT DOES NOT COVER SHRINKAGE, AND "nothing can consume an item" WOULD BE
    THE WRONG REASON.  ~~Nothing in this project can consume an item yet.~~
    It can: ``merge_known_item_into_occupied_slot`` takes a bag from four
    rows to three, and ``store.py`` DELETEs backpack rows on both merge
    paths (``merge_v111_stack``, ``merge_backpack_item_into_occupied_slot``).
    Consumption is how the merged golden comes into existence.  The scope
    limit stands on a narrower and true fact instead: the only shrinkage any
    code path can currently produce LANDS ON A GOLDEN, so refusing shrinkage
    costs nothing today.  A round that adds real consumption must revisit
    this, and must not quote a "nothing can consume" that was never true.
 3. ~~IT CHANGES NOTHING ON ITS OWN.  No production caller.  Gate 2 is
    byte-identical after this round.  The relog still fails today, exactly
    as it failed before this round, and any report that says otherwise is
    reading this module as wired when it is not.~~  TRUE OF THE ROUND THAT
    WROTE IT.  RETIRED, PAST TENSE.  COO-DECISION 20260829_0441 item 1
    tasked chief with the one-line wire in ``session.select_and_start``
    per ``BAG_ADMISSION_WIRING``; it landed as ``pirate-force-server``
    PR #233, merge ``e15bcac`` on main, and ``session.select_and_start``
    calls ``may_enter_world`` today.  THIS MODULE IS LOAD-BEARING ON THE
    CHARACTER-SELECT PATH, and anyone reading it as inert is reading a
    sentence that stopped being true.
    ~~"that work is in flight as PR #233"~~ and ~~"read this nonclaim
    against the head you are on"~~ -- both struck by pf-adversary, and
    both for the same reason: the first was already stale when it was
    written (one command would have said #233 had merged), and the second
    told the reader to go and check instead of checking.  The check is
    executable now --
    ``tests/test_bag_admission_expiry.py``'s
    ``test_the_wire_this_nonclaim_describes_is_actually_there`` reads
    ``session.py`` and goes red if the call is reverted, so this paragraph
    cannot drift out of true in either direction.
    Lane B does not own that wire and did not make it; lane B owns
    nonclaim 8 below, which is the condition COO attached to letting it
    happen at all.
 4. THE THREE NEW-ROW CONSTANTS ARE DUPLICATED, ON PURPOSE.  Importing
    ``mob_pickup`` here would pull ``field_drop_tables`` and ``mob_loot``
    onto the character-select path to read three integers.  They are
    declared locally instead, and ``tests/test_bag_admission.py`` asserts
    each one equals ``mob_pickup``'s, so a drift fails the suite rather than
    silently splitting the definition.
 5. ~~[สมมติของสาย B - รอ COO ยืนยัน] That "golden items unchanged + extra
    items above the golden's highest identity" is the RIGHT admission rule
    for gate 2 is this lane's reading, not a ruling.~~  ANSWERED.  It is a
    ruling now: ``COO-DECISION 20260829_0441`` question A, "ใช่ ... เป็นกฎ
    รับที่ยอมรับได้ของด่าน 2 วันนี้".  The ask was
    ``notes_to_chief/20260829_0353_LANE-B-ASK-COO-gate-2-admission-rule.md``
    and the answer is
    ``notes_to_chief/20260829_0441_COO-DECISION-gate-2-shape-rule-approved-as-interim-with-an-expiry.md``
    -- both IN THE pf_bridge REPOSITORY; this repository has no
    ``notes_to_chief``.  What that ruling is NOT is an endorsement of this
    rule as final: read nonclaim 8.
 6. WHAT IT DOES NOT CHECK ABOUT AN ACQUIRED ROW, AND WHY THAT IS A CHOICE.
    A real ``place_in_bag`` output is fully determined -- lowest free slot,
    ``highest + 1``, a template from ``field_drop_tables.ITEMS`` -- and three
    of those four are visible in the bag, so the admitted set here is far
    wider than the produced set (any of 36 slots, any template, any quantity
    from 1 up).  This module deliberately does not pin them: an acquired item
    that a player later MOVES or stacks is still legitimately theirs, and a
    rule keyed to "the slot a pickup would have chosen" would refuse that
    bag on the day item movement becomes real.  The identity floor is kept
    because it cannot drift that way.  Say "this module does not look", not
    "the bag cannot tell".
 7. THE COO CITATIONS IN THIS FILE, STATED AT THEIR REAL STRENGTH.
    COO-DECISION 20260828_0844 grants the gate-3 wire-encoder scope and
    ~~holds gate 2 out in as many words~~ DOES NOT MENTION GATE 2 AT ALL --
    the carve-out is by silence, and the "explicitly out of scope" wording
    traces to this lane's own prose in ``docs/FUNCTIONAL_COVERAGE.json``,
    which is the lane citing itself.  It is still a real limit on this lane's
    write zone; it is not a sentence COO wrote.  COO-DECISION 20260827_1350
    gives TWO reasons for deferring (not a priority, and the metadata risk);
    this module answers the second only, and it is dated two days before the
    "revisit ต้นสัปดาห์ M5 (30-31 ส.ค.)" that decision names.
 8. THIS RULE IS INTERIM AND ITS EXPIRY IS WRITTEN HERE, NOT IMPLIED.
    Required by ``COO-DECISION 20260829_0441`` item 2, in the same round
    chief wires the gate.  The full sentence of that decision:

        "เขียนวันหมดอายุลงในโมดูลเลย -- กฎรูปร่างถูกแทนด้วยเกณฑ์ที่มา
        ทันทีที่ ``store.py`` ทำ INSERT จริงและเดินตัวนับ ตอนนั้น
        ``_classify_against`` ตัดทิ้ง ไม่ใช่ต่อเติม"

    So, stated as a condition a later round can evaluate rather than a
    date:

      ~~EXPIRY CONDITION.  This shape rule is superseded on the day
      ``store.py`` performs a real backpack INSERT for a pickup AND advances
      ``character_backpacks.next_item_identity`` past it.~~  IS STRUCK:
      both halves came true (round 4gqnwm) and COO-DECISION 20260829_0848
      then CANCELLED the supersession itself -- there is no expiry on this
      rule any more.  Kept as the record of what was evaluated.  ~~Until then the
      counter cannot be the criterion -- ``MOB_PICKUP_ROW_WOULD_INSERT`` is
      a log, so every live character still reads migration 005's backfilled
      value and a real pickup's identity would be REFUSED by a counter
      check.  That is why COO took the shape rule today and not the counter:
      taking the counter today fails M5 outright.~~  THAT DAY WAS ROUND
      4gqnwm: both halves are true now.  What the condition did not
      anticipate is that the counter answers a NARROWER question than the
      shape rule -- "was this identity issued" cannot see a golden row that
      moved -- so meeting the expiry did not by itself authorise the
      deletion it prescribed.  Nonclaim 9 carries the measurement; the ask
      is closed -- COO-DECISION 20260829_0848 ruled on it.

      ~~WHAT THE SUPERSEDING ROUND MUST DO.  Replace, not extend.
      ``_classify_against`` is DELETED and the admission term becomes the
      counter question -- "was this identity issued by this server to this
      character?" -- read from the row the INSERT wrote.~~  IS STRUCK:
      COO-DECISION 20260829_0848 revoked exactly that sentence of 0441
      item 2 against nonclaim 9's measurement.  The ruling is route 1: the
      shape rule STAYS, and the acquired-row criterion becomes the counter
      question -- golden's highest < identity <= ``issued_through`` -- as a
      TIGHTENING beside it, threaded through ``may_enter_world``'s new
      ``issued_through`` parameter.  Keeping ``_classify_against`` is now
      the instruction, not a violation of one.

      WHO OWNS THE TRIGGER.  Not this lane.  ``COO-DECISION 20260829_0441``
      item 3 makes chief the owner of the "real INSERT + advance the counter
      in ``store.py``" ticket, queued to open by 30 ส.ค. 12:00 so the
      replacement criterion arrives just after M5.  ``store.py`` is not in
      lane B's write zone, and this lane must not pre-empt it here.

      THE COST COO ACCEPTED, IN ONE LINE, SO NOBODY RE-DISCOVERS IT AS A
      BUG.  ~~Nonclaim 1's hole stays open for the interim: a backpack row
      hand-edited into the right shape with a high enough identity is
      admitted.~~  NARROWED by 0848's ceiling (round hsz32u): a merely-HIGH
      identity is now exactly what the counter refuses.  What remains open
      is nonclaim 1's residue -- a hand-edited row that REUSES an
      already-issued identity in the right shape.  COO's stated reason
      still stands for that residue -- gate 2 is regression protection, not
      a defence against an untrusted client, and whoever can hand-edit the
      DB is already running the server.  A decision on record, not an
      oversight; ~~it EXPIRES with this rule~~ nothing expires any more.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .inventory import (
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    BackpackState,
    ItemAttrState,
    require_backpack_shape,
)


#: The snapshots ``is_unmoved_baseline`` admits.  This is a SECOND copy of a
#: list that lives inside that function, and the honest way to hold it is not
#: a subset assertion.  The first draft guarded it with
#: "GOLDEN_BACKPACKS is a subset of baseline", which cannot see the case that
#: matters: add
#: a THIRD baseline to ``is_unmoved_baseline`` and this module silently becomes
#: STRICTLY NARROWER than the gate it claims to reproduce, with the guard still
#: green -- measured by pf-adversary, who added one and watched the test pass
#: while ``may_enter_world`` refused a bag today's gate admits.
#:
#: ``inventory.py`` is outside this lane's write zone, so the fix is not to
#: export a shared constant from there.  Instead
#: ``test_the_goldens_are_exactly_the_ones_is_unmoved_baseline_compares_against``
#: reads ``is_unmoved_baseline``'s own source with ``ast`` and requires the
#: names in its comparison tuple to be EXACTLY these, in this order.  A third
#: baseline added there fails this file instead of quietly shrinking the gate.
GOLDEN_BACKPACKS: tuple[BackpackState, ...] = (
    INITIAL_BACKPACK, MERGED_V111_BACKPACK,
)

#: See NONCLAIM 4: duplicated from ``mob_pickup`` rather than imported, and
#: pinned equal to it by the test file.  ``BAG_SLOT_COUNT`` is here because
#: the TEST enumerates all 40 slots with it; the module itself does not read
#: it, and it is exported rather than hidden so the enumeration and the
#: pickup path cannot disagree about how big a bag is.
NEW_ROW_RAW_U8_38 = 0
NEW_ROW_RAW_U8_39 = 0xFF
NEW_ROW_DETAIL_PRESENT = 0
BAG_SLOT_COUNT = 40
MAX_SLOT_QUANTITY = 0xFFFF

VERDICT_GOLDEN = "golden"
VERDICT_GOLDEN_PLUS_ACQUIRED = "golden_plus_acquired"
VERDICT_REFUSED = "refused"
#: Separate from VERDICT_REFUSED on purpose.  ``may_enter_world`` has to treat
#: "this is not a Backpack" differently from every other refusal (it must not
#: be admitted even by the opt-in), and keying that on a shared ``reason``
#: string means any future refusal that reuses the constant silently inherits
#: the special case.  A verdict cannot be reused by accident.
VERDICT_MALFORMED = "malformed"

REASON_MALFORMED = "malformed"
REASON_GOLDEN_ITEM_MOVED_OR_ALTERED = "golden_item_moved_or_altered"
REASON_GOLDEN_ITEM_MISSING = "golden_item_missing"
REASON_ACQUIRED_IDENTITY_NOT_ABOVE_GOLDEN = "acquired_identity_not_above_golden"
REASON_ACQUIRED_IDENTITY_NOT_ISSUED = "acquired_identity_not_issued"
REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED = "acquired_row_not_pickup_shaped"
REASON_NO_GOLDEN_MATCHES = "no_golden_matches"
REASON_BAG_HEADER_DIFFERS = "bag_header_differs"
REASON_ITEM_ORDER_DIFFERS = "item_order_differs"


@dataclass(frozen=True)
class BagAdmission:
    """What ``classify`` concluded, and enough of why to print or assert on."""

    verdict: str
    golden_index: int | None = None
    acquired: tuple[ItemAttrState, ...] = ()
    reason: str | None = None
    detail: str = ""

    @property
    def admissible(self) -> bool:
        return self.verdict in (VERDICT_GOLDEN, VERDICT_GOLDEN_PLUS_ACQUIRED)


def _describe_row_difference(
    expected: ItemAttrState, present: ItemAttrState,
) -> str:
    """Name only the fields that actually differ.

    The first draft printed slot and quantity unconditionally, so the
    flagship refusal (the HYP-PF-008 post-state, which changes a SLOT and no
    quantity at all) came out reading ``quantity 1 -> 2`` -- a delta that
    belongs to the V111 merge and that HYP-PF-008 never performed.  A message
    that names an unchanged field as changed is worse than no message.
    """
    changed = [
        f"{field} {getattr(expected, field)} -> {getattr(present, field)}"
        for field in (
            "template_id", "quantity", "slot",
            "raw_u8_38", "raw_u8_39", "detail_present",
        )
        if getattr(expected, field) != getattr(present, field)
    ]
    return (
        f"identity {expected.identity} differs from the golden row "
        f"({', '.join(changed)})"
    )


def _classify_against(
    value: BackpackState, golden: BackpackState, index: int,
    issued_through: int | None = None,
) -> BagAdmission:
    """Classify ``value`` as a possible ``golden``-plus-acquisitions bag.

    ``issued_through`` is the character's inclusive identity counter
    (``store.backpack_issued_through``), threaded in by the caller because
    this module must not import ``store``.  With it, an acquired row is
    admitted only when its identity lies in the interval the counter has
    actually issued: above the golden's highest (the counter's own floor --
    ``mob_pickup.next_item_identity`` only ever mints above it) AND at or
    below ``issued_through``.  The two bounds together are the counter
    question COO-DECISION 20260829_0848 approved as route 1: "was this
    identity issued by this server to this character?"  ``None`` means the
    caller has no counter (diagnostics, tests of the shape rule alone); the
    production gate, ``may_enter_world``, always passes it.
    """
    if value == golden:
        return BagAdmission(VERDICT_GOLDEN, golden_index=index)

    # THE HEADER IS CHECKED FIRST, ON EVERY PATH, AND THAT ORDER IS A FIX.
    # The first draft checked these three fields only on the branch where
    # nothing had been acquired -- so the moment a bag carried one added row,
    # the new admission path returned GOLDEN_PLUS_ACQUIRED without ever
    # looking at them.  pf-adversary built the bag: INITIAL_BACKPACK's four
    # rows, byte-identical, plus exactly what place_in_bag mints, with
    # base_mask 255->0, base_identity 0->999, range_mask 1->127.  Admitted,
    # while gate 2 refuses it today.  One bit of drift in any of the three
    # was enough, and the file's own header test was green over all of it
    # because it only ever exercised the branch that already refused.
    # ``place_in_bag`` copies all three from the bag it was given, so no
    # golden-rooted pickup can move them.
    if (
        value.base_mask != golden.base_mask
        or value.base_identity != golden.base_identity
        or value.range_mask != golden.range_mask
    ):
        return BagAdmission(
            VERDICT_REFUSED, golden_index=index,
            reason=REASON_BAG_HEADER_DIFFERS,
            detail=(
                "the bag's own fields differ from the golden "
                f"(mask {golden.base_mask} -> {value.base_mask}, identity "
                f"{golden.base_identity} -> {value.base_identity}, range "
                f"{golden.range_mask} -> {value.range_mask})"
            ),
        )

    by_identity = {item.identity: item for item in value.items}
    highest_golden_identity = max(
        (item.identity for item in golden.items), default=0,
    )

    for expected in golden.items:
        present = by_identity.get(expected.identity)
        if present is None:
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_GOLDEN_ITEM_MISSING,
                detail=f"identity {expected.identity} is not in the bag",
            )
        if present != expected:
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_GOLDEN_ITEM_MOVED_OR_ALTERED,
                detail=_describe_row_difference(expected, present),
            )

    # ORDER IS CHECKED ON EVERY PATH, AND THAT ORDER IS A FIX -- the same
    # defect shape as the header fix above, in the same function, found by
    # chief's R222 letter (2026-08-29T05:10+07:00, item 4) after this module
    # was already wired.  ~~The order question was asked only inside
    # ``if not acquired:``~~ IS STRUCK: a bag whose golden rows are reordered
    # AND which carries one acquired row skipped the question entirely and
    # came back GOLDEN_PLUS_ACQUIRED.  MEASURED before the fix, on
    # INITIAL_BACKPACK with rows 1 and 2 swapped plus exactly what
    # ``place_in_bag`` mints.
    #
    # Ascending identity order is the invariant, not "the golden's own
    # order", because both producers of a real bag emit it: ``place_in_bag``
    # sorts the whole tuple by identity, and ``store._load_backpack`` reads
    # ORDER BY item_identity.  A bag in any other order came from neither.
    # It gets its own reason because order is load-bearing: reporting this as
    # "an item moved or was altered" would send a reader hunting a row that
    # is byte-identical.
    if tuple(value.items) != tuple(
        sorted(value.items, key=lambda row: row.identity)
    ):
        return BagAdmission(
            VERDICT_REFUSED, golden_index=index,
            reason=REASON_ITEM_ORDER_DIFFERS,
            detail=(
                "the bag's rows are not in ascending identity order, which is "
                "the only order place_in_bag and store._load_backpack produce"
            ),
        )

    golden_identities = {item.identity for item in golden.items}
    acquired = tuple(
        item for item in value.items if item.identity not in golden_identities
    )
    # THERE IS NO ``if not acquired:`` BRANCH HERE ANY MORE, AND IT RESTS ON
    # TWO PREMISES, NOT ONE.  Past this point the header is equal, every
    # golden row is present and byte-identical, and the rows ascend by
    # identity.
    #   (1) ``require_backpack_shape`` (gate 1, run by ``classify`` before
    #       this function, on every path including ``may_enter_world``)
    #       refuses duplicate identities, so ascending order is unique.
    #   (2) EACH GOLDEN'S OWN ``items`` TUPLE IS ITSELF ASCENDING.  This one
    #       was left unstated in the first draft and pf-adversary supplied
    #       the counter-example: hand an UNSORTED golden to this function and
    #       a sorted bag comes back GOLDEN_PLUS_ACQUIRED with nothing
    #       acquired -- through the branch this comment calls unreachable.
    #       The invariant lives in ``inventory.py``, outside this lane's
    #       write zone, so it is not asserted there; it is asserted from
    #       here, in ``tests/test_bag_admission.py::
    #       test_the_no_acquired_branch_is_unreachable_and_that_is_measured``,
    #       which also fails if a golden stops being sorted.
    # With both premises a bag with no acquired rows is byte-equal to the
    # golden and returned at the top of this function.  The branch was
    # written, measured unreachable, and removed rather than left reading
    # like a second line of defence.

    for item in acquired:
        if item.identity <= highest_golden_identity:
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_ACQUIRED_IDENTITY_NOT_ABOVE_GOLDEN,
                detail=(
                    f"identity {item.identity} is not above the golden's "
                    f"highest ({highest_golden_identity}); "
                    "mob_pickup.next_item_identity only ever mints above it"
                ),
            )
        if issued_through is not None and item.identity > issued_through:
            # Route 1 (COO-DECISION 20260829_0848): the counter's ceiling.
            # The floor above is the counter's own floor, so past both
            # checks the identity is one the counter actually issued.  This
            # is the check whose absence let HYP-PF-008/010-shaped bags be
            # admitted when _classify_against was deleted (the measurement
            # nonclaim 9 records) -- kept HERE, beside the shape rule, not
            # instead of it.
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_ACQUIRED_IDENTITY_NOT_ISSUED,
                detail=(
                    f"identity {item.identity} is above issued_through "
                    f"({issued_through}); the counter never issued it"
                ),
            )
        # THERE IS NO "is this slot free in the golden?" CHECK HERE, AND
        # THAT IS DELIBERATE.  By this point every golden item has been
        # proven present AND unchanged, so the golden's slots are exactly
        # occupied by the golden's own rows; ``require_backpack_shape`` above
        # has already refused any bag with two rows in one slot.  An acquired
        # row in a golden slot is therefore unreachable.  A guard for it was
        # written, measured to be unreachable, and removed rather than left
        # reading like a second line of defence.
        # Only the LOWER bound is checked.  ``require_backpack_shape`` above
        # already caps quantity at MAX_SLOT_QUANTITY, so an upper-bound test
        # here can never fire -- it was written, measured unreachable, and
        # reduced rather than left looking like a range check.
        if item.quantity < 1:
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED,
                detail=f"quantity {item.quantity} is not a pickup quantity",
            )
        if item.template_id < 1:
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED,
                detail="template id 0 is not a pickup template",
            )
        if (
            item.raw_u8_38 != NEW_ROW_RAW_U8_38
            or item.raw_u8_39 != NEW_ROW_RAW_U8_39
            or item.detail_present != NEW_ROW_DETAIL_PRESENT
        ):
            return BagAdmission(
                VERDICT_REFUSED, golden_index=index,
                reason=REASON_ACQUIRED_ROW_NOT_PICKUP_SHAPED,
                detail=(
                    f"identity {item.identity} does not carry mob_pickup's "
                    "new-row constants"
                ),
            )

    return BagAdmission(
        VERDICT_GOLDEN_PLUS_ACQUIRED, golden_index=index, acquired=acquired,
    )


def classify(
    value: Any, *, issued_through: int | None = None,
) -> BagAdmission:
    """Say what kind of bag this is, without raising for a bad one.

    Pass ``issued_through`` (the character's inclusive identity counter)
    whenever you have one -- the verdict then also refuses an acquired row
    the counter never issued.  ``None`` runs the shape rule alone; the
    production gate never calls with ``None`` (``may_enter_world`` requires
    the counter), so a bare ``classify(bag)`` is a diagnostic or a test of
    the shape rule, not the gate's answer.

    Fail-closed: a structurally malformed bag comes back REFUSED with the
    exception type named, rather than propagating.  Gate 1
    (``store._load_backpack`` -> ``require_backpack_shape``) is the gate whose
    job it is to raise on that, and it runs first; this module refusing
    quietly behind it must never be the thing that turns a load error into a
    dropped listener thread.
    """
    try:
        value = require_backpack_shape(value)
    except ValueError as error:
        # ValueError only: ``require_backpack_shape`` raises nothing else on
        # any path (``_require_int`` checks the type before it compares, so
        # no TypeError escapes it).  The first draft also caught TypeError --
        # a named catch nothing can produce.
        return BagAdmission(
            VERDICT_MALFORMED, reason=REASON_MALFORMED,
            detail=f"{type(error).__name__}: {error}",
        )

    refusals: list[tuple[tuple, BagAdmission]] = []
    for index, golden in enumerate(GOLDEN_BACKPACKS):
        admission = _classify_against(value, golden, index, issued_through)
        if admission.admissible:
            return admission
        refusals.append((_golden_match_score(value, golden), admission))

    # Explain the refusal in terms of the golden the bag is actually built on,
    # MEASURED (see ``_golden_match_score``), rather than guessed from which
    # check happened to fire.  The first draft ranked the REASONS instead, and
    # reported a bag that had simply lost one initial item as "moved or
    # altered", because the merged golden's quantity check fires later than the
    # initial golden's missing check.  The verdict was right either way; the
    # sentence a reader gets was not.
    best_score, best = max(refusals, key=lambda entry: entry[0])
    if best_score[0] == 0 and best_score[1] == 0:
        # Shares neither a row nor even an identity with either snapshot.
        # "identity 4 is missing" would send a reader after one row when the
        # bag is not built on a golden at all.
        return BagAdmission(
            VERDICT_REFUSED, reason=REASON_NO_GOLDEN_MATCHES,
            detail="the bag is not built on either golden snapshot",
        )
    return best


def _golden_match_score(value: BackpackState, golden: BackpackState) -> tuple:
    """How close this bag is to ``golden``, most decisive term first.

    Byte-identical rows alone is not enough to pick a golden, and the state
    it fails on is the most important one in the module: the HYP-PF-008
    post-state keeps two rows byte-identical against BOTH goldens, so a
    single-term score ties and the tie fell to tuple order -- which reported
    the state as built on INITIAL when it is built on MERGED.  Identity
    membership breaks that tie honestly (HYP-PF-008's identities are exactly
    the merged golden's), and row count settles the rest.
    """
    rows = {item.identity: item for item in value.items}
    identical = sum(1 for item in golden.items if rows.get(item.identity) == item)
    shared = len({item.identity for item in golden.items} & set(rows))
    return (identical, shared, -abs(len(value.items) - len(golden.items)))


def is_golden_plus_acquired(
    value: Any, *, issued_through: int | None = None,
) -> bool:
    """The NEW third admission path, and only that one.

    Deliberately False for a plain golden bag: this is the term that gets
    OR-ed beside ``is_unmoved_baseline``, not a replacement for it, and a
    reader of the wired condition should be able to see both terms doing
    their own work.
    """
    return (
        classify(value, issued_through=issued_through).verdict
        == VERDICT_GOLDEN_PLUS_ACQUIRED
    )


def may_enter_world(
    value: Any, *, allow_hypothesized_item_move: bool, issued_through: int,
) -> bool:
    """The whole of the proposed gate-2 condition, in one place.

    The first two terms are the gate as it stood before this module, in that
    order.  The third is this module.  ~~"``session.select_and_start`` is
    NOT calling this yet"~~ IS STRUCK: it calls this, since PR #233
    (``session.py`` line 96, COO-DECISION 20260829_0441 item 1).  THIS IS
    THE PRODUCTION GATE-2 PREDICATE -- a change here changes who can enter
    the world, not what a document says.

    ONE DELIBERATE DIFFERENCE FROM TODAY'S CONDITION, found by this module's
    own test before it was wired anywhere.  Today's second term is a bare
    ``or allow_hypothesized_item_move``, so with the opt-in on, gate 2 admits
    a value that is not a Backpack at all.  That is unreachable in production
    -- gate 1 raises on such a value first -- but it is fail-OPEN, and this
    function is the wrong place to carry a fail-open term forward.  A
    structurally malformed value is refused here whatever the opt-in says.
    Every value the opt-in admits today that PASSES
    ``require_backpack_shape`` is still admitted.  Not "that is a
    BackpackState": ``store.swap_backpack_item_with_occupied_slot`` parks a
    row at slot 65535, which is a BackpackState the shape gate refuses, so
    the wider wording was false as written.
    """
    # ``issued_through`` is REQUIRED here, with no default, on purpose: this
    # is the production gate-2 predicate, and COO-DECISION 20260829_0848
    # (route 1) makes the counter part of the criterion.  A caller that has
    # no counter has no business answering "may this character enter the
    # world" -- session.select_and_start reads it from
    # store.backpack_issued_through and this module stays store-free.
    admission = classify(value, issued_through=issued_through)
    if admission.verdict == VERDICT_MALFORMED:
        return False
    if admission.verdict == VERDICT_GOLDEN:
        return True
    if allow_hypothesized_item_move:
        return True
    return admission.verdict == VERDICT_GOLDEN_PLUS_ACQUIRED


#: Names for the two snapshots, index-aligned with ``GOLDEN_BACKPACKS``, so
#: a console line survives the tuple being reordered.
GOLDEN_NAMES: tuple[str, ...] = ("initial", "merged_v111")


def golden_name(index: int | None) -> str:
    """``GOLDEN_NAMES[index]``, or ``none`` for a refusal with no golden."""
    if index is None or not 0 <= index < len(GOLDEN_NAMES):
        return "none"
    return GOLDEN_NAMES[index]


def console_line(admission: BagAdmission) -> str:
    """The greppable token an attended run reads to see which path was taken.

    One token, ``BAG_ADMISSION``, so a tester greps one word and gets the
    verdict, the golden it was judged against, how many rows were acquired,
    and the refusal reason when there is one.
    """
    # The golden is named, not numbered.  An index into a module-level tuple
    # means whatever the tuple order means that day: reorder
    # ``GOLDEN_BACKPACKS`` and ``golden=0`` silently changes which snapshot it
    # refers to, while every grep of the token keeps matching.  A greppable
    # token whose meaning depends on declaration order is not a report.
    parts = [
        "BAG_ADMISSION",
        f"verdict={admission.verdict}",
        f"golden={golden_name(admission.golden_index)}",
        f"acquired={len(admission.acquired)}",
    ]
    if admission.reason is not None:
        parts.append(f"reason={admission.reason}")
    return " ".join(parts)


#: The one line that turned this on.  ~~"It is written here rather than done
#: here because ``session.py`` carries gate 2"~~ IS STRUCK: chief did it in
#: PR #233 on COO-DECISION 20260829_0441 item 1.  Kept as the record of what
#: was asked for and what landed -- read it against ``session.py`` line 96,
#: not as an outstanding request.  ``tests/test_gate2_bag_admission_wiring.py``
#: is what holds the call site in place now.
BAG_ADMISSION_WIRING = (
    "GATE 2 REDESIGN, one line, for whoever holds the grant.  In "
    "session.Session.select_and_start, replace\n"
    "    if not is_unmoved_baseline(backpack) "
    "and not self.allow_hypothesized_item_move:\n"
    "with\n"
    "    if not bag_admission.may_enter_world(\n"
    "        backpack, "
    "allow_hypothesized_item_move=self.allow_hypothesized_item_move,\n"
    "    ):\n"
    "and leave the PermissionError and the rest of the method alone.  may_enter_world's first two terms ARE today's condition, "
    "in today's order, so every state refused today except a "
    "golden-plus-acquired bag is refused after the swap for the same reason "
    "at the same line.  inventory.is_unmoved_baseline is not modified: the "
    "move/swap/merge family keeps the guard it has.\n"
    "PRINT bag_admission.console_line(bag_admission.classify(backpack)) ON "
    "THE REFUSAL PATH -- not optionally, and not only for attended runs.  "
    "The PermissionError says 'HYP-PF-008 post-state requires its explicit "
    "opt-in scenario', which is the WRONG sentence for two of the refusals "
    "this predicate can return: a malformed bag (a real bug -- gate 1 should "
    "have raised first) and a bag whose header drifted.  Without the line, "
    "a structural fault reaches the operator misattributed to a hypothesis "
    "that had nothing to do with it."
)

BAG_ADMISSION_NONCLAIMS = (
    "1. Shape plus the counter, still not full provenance: since "
    "COO-DECISION 20260829_0848 (route 1) an acquired row must also carry "
    "an identity the counter actually issued (golden's highest < identity "
    "<= issued_through), which closes the 'high enough identity' half of "
    "the old hole.  A hand-edited row that REUSES an already-issued "
    "identity in the right shape is still admitted: the counter answers "
    "'was this identity issued', not 'is this the row that was issued'.",
    "2. Shrinkage is refused.  Not because nothing can consume an item -- a "
    "merge can -- but because the only shrinkage reachable today lands on a "
    "golden.",
    "3. Not wired by lane B.  Byte-identical after the round that added "
    "this; COO-DECISION 20260829_0441 item 1 gives chief the wire, so check "
    "session.select_and_start on the head you are reading.",
    "4. The three new-row constants are duplicated from mob_pickup and pinned "
    "equal to it by the test file.",
    "5. The admission rule is APPROVED by COO-DECISION 20260829_0441 as an "
    "interim, not endorsed as final -- see nonclaim 8.",
    "6. An acquired row's slot, template and quantity are NOT pinned, on "
    "purpose; only its identity interval is (above the golden's highest, "
    "at or below issued_through).",
    "7. COO-DECISION 20260828_0844 is silent on gate 2 rather than explicit "
    "about it.",
    "8. NO LONGER INTERIM.  The written expiry this nonclaim used to carry "
    "(COO-DECISION 20260829_0441 item 2: 'delete _classify_against when the "
    "INSERT lands') was CANCELLED by COO-DECISION 20260829_0848, which "
    "revoked exactly that sentence after the measurement in nonclaim 9: "
    "the shape rule stays, the counter tightens it.  There is no pending "
    "expiry condition on this module any more; a new one requires a new "
    "measurement and a new COO decision.",
    "9. THE MEASUREMENT THAT DECIDED IT.  STORE-INSERT-001 landed the "
    "INSERT and the counter advance, meeting 0441's literal expiry -- and "
    "deleting _classify_against to admit on the counter alone was measured "
    "to ADMIT the HYPOTHESIZED_V111_SLOT2 (HYP-PF-008) and free-slot-move "
    "(HYP-PF-010) bags, which every family test requires this gate to keep "
    "refusing: those bags move a golden row without minting any identity, "
    "so a rule that only asks 'was this identity issued' cannot see them.  "
    "COO-DECISION 20260829_0848 ruled on that number: route 1, keep the "
    "shape rule AND require an acquired identity the counter issued "
    "(identity <= issued_through, threaded from "
    "store.backpack_issued_through -- the inclusive reading of "
    "character_backpacks.next_item_identity -- via "
    "session.select_and_start; this module still imports no store).  "
    "Wired in round hsz32u.",
)

#: The expiry that nonclaim 8 used to carry, kept as the record of what was
#: evaluated.  Both halves became true in round 4gqnwm (STORE-INSERT-001),
#: and COO-DECISION 20260829_0848 then CANCELLED the deletion this expiry
#: prescribed -- the counter tightens the shape rule (route 1) instead of
#: replacing it.  Deliberately not a runtime check: this module must
#: not import ``store``, and a stale True here would be worse than no
#: constant at all -- the test file asserts the flag against
#: ``mob_pickup``'s own text instead.
BAG_ADMISSION_EXPIRY_CONDITION = (
    "store.py INSERTs a real backpack row for a pickup",
    "that INSERT advances character_backpacks.next_item_identity",
)
