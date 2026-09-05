"""LANE-B / MOB-PICKUP-REQUEST-001: the click that asks for a ground drop,
read in PRODUCTION -- no flag, no scenario, no opt-in object.

WHY THIS FILE EXISTS.  ``NOW.md`` P-1 is "a dropped thing stays on the floor
long enough to be seen AND PICKED UP".  The take-it transaction has been
finished and tested for days (one call composes the claim, takes the row
through the ground cell, places it in the bag slot and composes the client
delta; a sibling module adds the database write around it).  ~~NOTHING CALLS
IT~~ and ~~A real client that clicks a ground object today has its frame fall
through to the frozen v141 default path, unread and unlogged~~ ARE STRUCK,
round ``91tlkk``: both were true when this file was written and both stopped
being true on 2026-09-02 (see
:data:`PICKUP_REQUEST_DISPATCH_CALL_SITE_LANDED`).  What COO-DECISION
20260902_0254 named as the reason this file exists -- that in production mode
no code in ``src/`` could read one byte of an inbound pickup request -- is
the history that produced it, not the state of the tree.  TODAY THE BRANCH
EXISTS: ``runtime.py`` reaches this module on any frame whose NESTED id is
``PICKUP_REQUEST_VITAL_ID``.
!! AND NOT ONE INCH FURTHER (pf-adversary D12, round 91tlkk).  ~~every ground
click reaches this module through runtime.py's dispatch~~ IS STRUCK BEFORE IT
EVER SHIPPED: that is a WIRE claim built out of a SOURCE fact, and it
contradicts the sentence this lane's own test forces the chief to keep beside
his call -- 0x4543 is DERIVED on the static-image layer and HAS NEVER BEEN
OBSERVED ON ANY WIRE (NONCLAIM 1, RE-125).  If that nonclaim is right, a real
click may wear some other id and reach the unchanged unknown-vital path
instead.  What landed is a BRANCH; which frames enter it is a question only
an attended capture answers.
This module is still that one half and only that
half: it READS the request.  It grants nothing, takes nothing off the ground,
writes no row and sends no byte.

THE SPLIT, IN ONE LINE.  wire bytes -> (object_ref_u32, opaque_u8) is this
file's own work.  (object_ref_u32, opaque_u8) -> item in a bag slot + delta
bytes belongs to the two transaction modules, which this file CALLS and does
not reimplement one line of.  What is left for ``runtime.py`` -- the chief's
file -- was a single call: see ``MOB_PICKUP_REQUEST_WIRING`` at the bottom.
It was HELD; COO-DECISION 20260902_0541 cleared it to land and
~~NOTHING HAS LANDED YET~~ IS STRUCK, round ``91tlkk``: IT LANDED, and the
note at the bottom is now a RECORD of a call site rather than a request for
one (NONCLAIM 5, NONCLAIM 7,
:data:`PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS`).

WHAT IS PROVEN, AND BY WHOM (do not re-prove)
---------------------------------------------
Both facts below were re-read from the committed artifacts on this round
rather than copied out of another module's comment:

  * THE BODY GEOMETRY IS STATICALLY CLOSED.  ``PF_SERIALIZER_FIELDS.tsv``
    (the other repository, ``external/``) carries FOUR byte-symmetric rows
    for this message against serializer span [0x005E5E30, 0x005E5E83),
    length 83, span sha256 8e439d4f..73066, source IMAGE:

        W order 1 / R order 1 : tag 0x14, object +0x14, len 4, gate ALWAYS
        W order 2 / R order 2 : tag 0x08, object +0x18, len 1, gate ALWAYS

    W and R agree row for row, so the codec is closed: seven bytes, always,
    in that order, and there is no third field to miss.
  * GT-046 (2026-08-23, PASS/DONE, layer STATIC-ON-BRIDGE -- its own header
    says "No LOCK_GAME/LOCK_GIT, server, client, or DB was used", so it is
    NOT an attended observation and nothing here may call it one) traced the
    CLIENT-OUTBOUND producer in the shipped image: the left-click path
    builds the request object at 0x006B0639, reads pointer [esi+0x7C] then
    dword [pointer+0x10], and copies THAT dword into object+0x14 before
    queueing it (letter ``20260823_1435_GT046-PASS-outbound-mouseclick-
    runtime-drop-object``).  Its own first nonclaim: static presence of the
    outbound path does not prove it ran in any captured session.  RE-082
    (PASS/DONE, 2026-08-26, also STATIC-ON-BRIDGE) traced that same dword,
    instruction by instruction, to the value this project writes at
    list-element +0x10.
  * THE BYTE COUNT IS AN INFERENCE, NOT A TABLE ROW.  The four rows state
    tags, object offsets, widths and gates; "seven bytes on the wire"
    follows from this project's [tag][value] scalar codec convention
    applied to those rows, and is labelled as an inference here rather
    than presented as something the table says.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  1. THE VITAL ID IS NOW OBSERVED ON THE WIRE.  ~~"THE VITAL ID HAS NEVER
     BEEN SEEN ON ANY WIRE, AND THE NEGATIVE IS BOUNDED"~~ IS STRUCK by the
     attended capture of 20260902_1755 (R303): 46 inbound 0x4543 frames, 2
     completed takes, confirmed again in R306, and COO-DECISION
     20260905_0249 item 1 closed GT-146 as covered by it.  The bounded
     negative below was true of the corpus audit that produced it and is
     kept, struck, so a reader can see what changed and on what evidence;
     the call-site restriction is retained for its own reasons (0249 item
     2).  ~~"0x4543 comes from the validated project name-hash only"~~
     IS STRUCK, and so is RE-125's premise behind it: the Codex checkpoint
     of 2026-08-31 (P06-DROP-TRANSPORT, item 2) closed 0x4543 as the
     ASSIGNED NESTED RUNTIME TYPE ID on the successful 519-stub
     registration path (519 names / 519 ids / collision 0, IMAGE layer),
     and forbade using it as a TOP-LEVEL opcode -- which is why this lane
     keys on the NESTED id and nothing else.  ~~"What stands unchanged: no
     capture holds a frame of it in either direction"~~ IS STRUCK TOO -- it
     was the surviving half of the old negative and R303 ended it; a
     paragraph may not carry a claim and its negation five lines apart.
     What DOES stand: the audit that produced the zero
     (PF_FIELD_VALIDATION rows 102-103, status NOT_OBSERVED) reached 0
     among the nested frames it parsed and left a residue of fail-closed
     frames never parsed at all, so that zero was always bounded rather
     than absolute -- and R303 is the frame it did not reach.  Being
     always-on still does not upgrade anything by one inch.  WHAT ALWAYS-ON ACTUALLY COSTS, stated
     plainly: if the real runtime id is 0x4543 this branch fires on real
     clicks, and if it is not, this branch never fires and the frame keeps
     the exact pre-existing fall-through behavior.  A THIRD case exists and
     is the one worth naming: some OTHER message whose real id happens to
     be 0x4543 would now be read as a pickup request.  It would have to
     also carry our exact envelope and our exact 7-byte body, and even then
     the only consequence is a claim against a ledger key -- which the
     transaction refuses unless that key is live on this scene's ground.
     The failure mode stays "pickup never works", never "the wrong thing is
     granted".
  2. THE ENVELOPE WAS NEVER CAPTURED FOR THIS VITAL.  The accepted wrapper
     -- one-vital client request, outer version 0, outer mask 0x02, count 1,
     nested version 0 -- is OUR ACCEPTANCE DESIGN, copied from what every
     captured client request of OTHER vitals uses.  It fails closed.
  3. ``object_ref_u32`` IS NAMED FOR ITS SOURCE, NOT ITS MEANING.  GT-046
     proves where the client copies it from; RE-082 proves it equals the
     element key we write.  This module still only READS it and hands it on;
     the transaction downstream RESOLVES it against live ledger rows and
     refuses by name when it matches none.
  4. ``opaque_u8`` HAS NO KNOWN MEANING.  It is carried through unchanged
     and is never interpreted here or anywhere.
  5. NOTHING HERE IS EVIDENCE THAT A PLAYER PICKED ANYTHING UP, AND THAT
     STILL STANDS -- BUT NOT FOR THE REASON IT USED TO.  ~~No call site
     exists yet: ``MOB_PICKUP_REQUEST_WIRING`` is a request to the chief,
     now cleared to land by COO-DECISION 20260902_0541 but still not landed
     by anyone.  Until that line is in ``runtime.py``, this module decodes
     nothing on any running server~~ IS STRUCK, round ``91tlkk``: the line
     IS in ``runtime.py`` and this module decodes on every running server
     (:data:`PICKUP_REQUEST_DISPATCH_CALL_SITE_LANDED`).  What survives the
     strike is the sentence that was always the point: READING A FRAME IS
     NOT A PLAYER HOLDING AN ITEM, so no round may report P-1's "picked up"
     half as done on the strength of this file.  The evidence that would
     settle it is attended and client-observable -- ``GT-204``'s
     ``MOB_PICKUP_ROW_INSERTED`` beside a bag that grew on the owner's own
     screen -- and it is measured there, never here.
     !! AND READ THE STRIKE THE RIGHT WAY ROUND.  It does not upgrade this
     lane by one inch; it downgrades the excuse.  A reader who takes the old
     sentence at face value goes looking for a MISSING CALL SITE, and there
     is none missing: whatever is costing the owner clicks is on this side of
     a branch that exists, which is a different search.
     !! AND THE NUMBER THAT SENT THIS ROUND HERE IS NOT A FACT ABOUT THIS
     TREE (pf-adversary D13, round 91tlkk).  ``NOW.md`` P-1 records "2 of 46
     clicks reached the decoder, ``reason=vital_count_not_one`` 42 times" --
     measured on the tree of 2026-09-02 morning.  ``vital_count_not_one`` is
     RETIRED on this tree (see ``MOB_PICKUP_REQUEST_RETIRED_REASONS``, whose
     own rule is that a retired name is produced by NOTHING), so a reader
     sent after that reason today is sent after a word this code cannot
     emit.  The count is kept as the history that motivated the strike, never
     as a measurement of what refuses clicks now; what refuses them now is
     re-derived per round or it is not claimed.
  6. THE MONSTER-DROP FAMILY IS STILL UNDECODED.  A separate client-side
     module family may carry monster-drop pickup instead of this message.
     This lane is not claimed to explain that path.
  7. THE CALL SITE THIS LANE PUBLISHES WAS HELD, AND IS NOW CLEARED BY
     COO-DECISION 20260902_0541 -- WHICH DOES NOT MAKE THE ID OBSERVED.
     Read the paragraph below as the history it is: it is kept, not
     rewritten, because the reason the hold existed is the reason the
     clearance had to be a decision rather than a lane's own judgement.
     0541 takes option 1 of the ASK-COO letter of round h6bl53: the
     prohibitions in 0245 and 20260830_1145 are withdrawn, RE-125's red
     header is excepted for exactly the published line, and the FACT it
     records stays true and must be written at the call site.  What follows
     is what stood before that decision:
     RE-125
     (CLOSED BOUNDED-NEGATIVE) and COO-DECISION 20260901_0245 both forbid a
     production call site for the pickup transaction keyed on 0x4543 until
     an attended click capture exists; GT-146 (attended, the owner driving)
     then measured ZERO frames of any unknown id across every click, and
     carries a standing owner order that no further click-capture round
     opens until a dropped element stays on screen longer than the under-
     one-second life it had.  COO-DECISION 20260902_0254 ordered THIS
     module and a request to the chief; it does not mention 0245, RE-125 or
     GT-146.  This lane did not get to resolve that by writing code, so it
     did not: the decoder was landed (nothing forbids reading), and the
     wiring below was published as HELD -- specified, executable, and not to
     be landed until COO reconciled the two.  COO-DECISION 20260902_0541 is
     that reconciliation, and it also records that 0254/0348 were written
     without sight of the three older tickets.
  8. RELOG PERSISTENCE IS NOT THIS TICKET.  P-1 closes at "seen and picked
     up in one session"; the persisted-bag question belongs to M5 and its
     own tickets, and no line here may be read as answering it.

WHY A SECOND DECODER RATHER THAN "TURNING THE PROBE ONE ON"
-----------------------------------------------------------
The probe lane that first read this body is scenario-gated and test-only by
construction: its module constant says so, its scenario file is a permission
token validated against an exact allowlist, and a production lane may not
import a scenario-gated probe (a tripwire test in this lane enforces that,
and this file's own test re-enforces it).  So the production reader is
written here, from the delivery table re-read on this round, and the two
files are free to disagree -- which is itself a test in this lane: if the
probe lane's pinned bytes and this decoder ever disagree about the same
seven bytes, one of them moved.

FAIL-CLOSED CONTRACT
--------------------
Every refusal is one of ``MOB_PICKUP_REQUEST_REFUSAL_REASONS``, carried as
``args[0]`` of ``MobPickupRequestRefused`` and as ``.reason`` on the read
result.  There is no partial result: a refused read carries ``fields=None``.
Nothing in this file touches a socket, a database, a clock or a scenario
file.

WHERE THE SECOND DERIVATION LIVES, AND WHY IT IS NOT IN HERE
------------------------------------------------------------
This lane composes bytes elsewhere by deriving them twice and comparing.
For a body this small the second derivation cannot disagree in production:
a fixed-layout unpack of seven bytes and a tag walk over the same seven
bytes are the same arithmetic written twice, so a runtime comparison would
be a branch no input can reach -- and an unreachable safety branch is a
comment pretending to be a guard.  The second derivation is therefore a
TEST: the test file unpacks the fixed layout independently and compares it
against this decoder over a corpus that includes every one-byte mutation of
an accepted body.  The comparison is executed on every run; it is simply not
executed on the wire.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import mob_ground_persistence
from . import mob_pickup
from . import mob_pickup_persist

#: THE SECOND READER OF THE SAME FRAME (round ``di7ers``).  ``vital_walk``
#: landed on ``main`` with ``R309`` while round ``t8z97r`` was writing the
#: relaxed tail rule below, and a pf-adversary pass on the MERGE of the two
#: measured what the pair does that neither does alone: every frame this
#: lane newly accepts on the relaxed path is a frame the walker examined and
#: refused BY NAME (``unknown_vital_id``, ``truncated_vital``,
#: ``trailing_bytes_after_last_vital``).  A tail of seven noise bytes that
#: merely OPENS like a vital was granted a take.  So the walker's refusal is
#: now this lane's refusal: see :func:`walk_agrees_with_the_frame`.
#:
#: Imported defensively rather than plainly because the answer to "the
#: walker is not here" must be a REFUSAL, not an ImportError out of a module
#: the inbound dispatch imports at boot.
try:                                              # pragma: no cover - trivial
    from . import vital_walk as _vital_walk
except Exception:                                 # pragma: no cover - trivial
    _vital_walk = None                            # noqa: N816


MOB_PICKUP_REQUEST_CHECKPOINT = "MOB-PICKUP-REQUEST-001"
MOB_PICKUP_REQUEST_LANE = "B_COMBAT"
MOB_PICKUP_REQUEST_BUILD_ORDER = "P-1 second half / BUILD-006 approach"

production_allowed = True
test_only = False


# ---------------------------------------------------------------------------
# Static pins.  Documentation-grade constants, never dereferenced, each one
# re-read from the committed delivery table on the round this file was
# written rather than copied from another module.
# ---------------------------------------------------------------------------

# DERIVED, AND NOW OBSERVED ON THE WIRE -- see NONCLAIM 1.  The day a capture
# would contradict this arrived: R303, 46 inbound frames, 2 completed takes.
# Kept as a constant so that day cost one line here and none in the chief's
# file, which is exactly what it was written for.
PICKUP_REQUEST_VITAL_ID = 0x4543
PICKUP_REQUEST_VITAL_ID_PROVENANCE = (
    "assigned_nested_runtime_type_id_image_layer_observed_on_wire_r303"
)
#: OBSERVED.  R303 (attended capture 20260902_1755) carries 46 inbound
#: 0x4543 frames and 2 completed takes, confirmed again in R306.  The older
#: bounded negative -- zero among the nested frames the PF_FIELD_VALIDATION
#: audit (rows 102-103, NOT_OBSERVED) reached, with a residue of fail-closed
#: frames it never parsed -- remains a true statement about THAT audit and
#: is not what this constant reports any more.  NONCLAIM ON THIS SENTENCE:
#: which of the two came first is NOT claimed here -- no dating of those
#: rows was found in either repository, so "the audit simply never reached
#: R303's frames" is the bounded reading, not a chronology.  Carried as a constant so a reader who only skims the constants
#: still meets the evidence.
PICKUP_REQUEST_CAPTURE_STATUS = (
    "observed_on_wire_r303_46_inbound_frames_2_completed_takes"
)
#: THE HOLD IS LIFTED.  Round h6bl53 published this ask as HELD because
#: RE-125, COO-DECISION 20260901_0245 and GT-146 forbade a production call
#: site keyed on this id while COO-DECISION 20260902_0254 and 20260902_0348
#: ordered one, and a lane does not settle a contradiction between its own
#: instructions by writing code.  COO-DECISION 20260902_0541 answers the
#: ASK-COO letter of that round and takes option 1: the two prohibitions are
#: WITHDRAWN and the exception is granted for exactly the line this module
#: publishes.  The FACT 0541 required at the call site has since CHANGED, and
#: COO-DECISION 20260905_0249 item 2 approved the new wording: 0x4543 is now
#: OBSERVED on the wire (R303, 46 inbound frames, 2 completed takes).  The
#: call-site restriction 0541 imposed is retained for its own reasons, and
#: the ask below still carries the fact - the current one.
PICKUP_REQUEST_WIRING_STATUS = "approved_by_coo_20260902_0541"
PICKUP_REQUEST_WIRING_APPROVAL = (
    "COO-DECISION 20260902_0541 (answering the ASK-COO letter of round "
    "h6bl53): option 1, the prohibitions of COO-DECISION 20260901_0245 and "
    "20260830_1145 are withdrawn, RE-125's red header is excepted for this "
    "one line by COO ruling, and the substitution of the persist-and-"
    "dispatch call for the dispatch-only one is endorsed"
)
#: EACH ONE STRUCK THROUGH IN PLACE, with what lifted it and the whole of
#: what it used to say after "-- was:": the project's rule is that history is
#: crossed out rather than erased, and a reader who lands on RE-125 next month
#: must see both that it once blocked this line and by whose decision it
#: stopped blocking it.  What the paragraph ABOVE this tuple used to say is
#: not preserved word for word - it was a "this is HELD and here is why"
#: comment that no longer describes anything, and the sentences it carried are
#: all in the four entries below plus NONCLAIM 7.  Said plainly rather than
#: claimed away: pf-adversary round okdfge caught an earlier draft of this
#: comment asserting "nothing was deleted", which was not true to the letter.
PICKUP_REQUEST_WIRING_BLOCKERS = (
    "LIFTED by COO-DECISION 20260902_0541 -- was: RE-125 CLOSED "
    "BOUNDED-NEGATIVE: no production call site keyed on this id until an "
    "attended click capture exists.  The negative itself stands; only the "
    "prohibition it carried was excepted, and only for this line.",
    "WITHDRAWN by COO-DECISION 20260902_0541 -- was: COO-DECISION "
    "20260901_0245: the pickup transaction stays unwired until GT-124 "
    "captures a real opcode",
    "REREAD by COO-DECISION 20260902_0541 -- was: GT-146 (attended): zero "
    "unknown frames on every click; standing owner order that a dropped "
    "element must stay on screen first.  0541 reads that order as being "
    "about the ORDER OF ATTENDED ROUNDS, not about landing code, and notes "
    "that one attended round can now answer both questions at once.",
    "ANSWERED by COO-DECISION 20260902_0541 -- was: COO-DECISION "
    "20260902_0254 and 20260902_0348 order this module and the chief's "
    "line, and do not mention the three above",
)
#: DID THE CALL SITE LAND, weakest evidence first.  Registered so a word that
#: is not one of these three cannot end up in the wiring note and be searched
#: for in vain.
#:
#: THREE WORDS AND NOT TWO (pf-adversary D10, round 91tlkk).  The first draft
#: had two and counted only a call expression, so a lookup by string --
#: ``getattr(mob_pickup_request, "dispatch_inbound_pickup_request")(...)``, a
#: name bound to the function and called later, a dict of handlers -- scored
#: "nothing calls it".  That is the same blind spot
#: ``mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUSES`` was hardened
#: against last round after LANE-A measured it on a real hook, and shipping
#: the pre-hardened version of it in a commit about stale claims would have
#: been this lane repeating its own scar.
PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUSES = (
    "requested_not_landed",
    "wired_by_name_lookup",
    "landed",
)
#: WHY THIS CONSTANT EXISTS, and it is the whole of this round's change:
#: everything above and below it was WRITTEN while the branch was still a
#: request, and on 2026-09-02 the branch LANDED without one of those
#: sentences changing.  For a full day this file's docstring, NONCLAIM 5,
#: NONCLAIM 7 and the wiring note all told a reader "nothing calls it" and
#: "no round may report P-1's picked-up half as done on the strength of this
#: file" about a tree where every ground click a player makes goes through
#: :func:`dispatch_inbound_pickup_request`.  That is not a cosmetic staleness
#: on this lane: ``NOW.md`` P-1's open number is "clicks that reached the
#: decoder, 2 of 46", and a reader who believes this file has no call site
#: reads those 44 as "the branch never fired" when they are "the branch fired
#: and refused".  The same lie, in a different file, is what
#: ``mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS`` was built to end
#: last round; this is that shape, applied to the file that owns the click.
#:
#: IT IS NOT A LABEL A HUMAN KEEPS UP TO DATE -- that is precisely what
#: failed.  ``tests/test_mob_pickup_request.py`` RE-DERIVES it from the AST
#: of every production file in ``src/`` on every run.  And it is not
#: decoration either: :data:`MOB_PICKUP_REQUEST_WIRING` -- the note the chief
#: and an operator actually read -- is COMPOSED from it through
#: :func:`wiring_headline`, so the document cannot say "cleared to land"
#: about a branch that landed a day ago.
#:
#: !! WHAT THE WORD DOES AND DOES NOT ANSWER, and ~~red in BOTH directions:
#: too low after a call site lands, too high after one is reverted~~ IS
#: STRUCK AS OVERSTATED (pf-adversary D7, round 91tlkk, measured).  The scan
#: sees LEXICAL PRESENCE of a call expression in a production module.  It
#: OVER-COUNTS a dead wrapper nobody invokes, a call under ``if False``, and
#: a call on an unrelated object whose method shares the name -- so the day a
#: lane adds a replay helper that names this entry point and never runs it, a
#: reverted runtime branch would still score "landed".  The direction that IS
#: reliable is the one that actually failed here: a call site that lands
#: cannot go on being reported as absent.
#:
#: !! AND WHEN THE SCAN IS THE ONE THAT IS LYING (pf-adversary's closing
#: question, round 91tlkk).  The failure message offers two moves, raise the
#: label or lower it, and both change what a human reads about the wire.
#: Neither is the answer when the tree and the scan disagree: the answer is
#: to WIDEN THE SCAN or add a word to the vocabulary -- which is how the
#: middle word above got here -- and, when neither is possible in that round,
#: to strike the sentence in place and say so, the way this block does.
#: Moving the label to make a test green is the failure this constant was
#: built to end, arriving from the other side.
PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS = "landed"
#: When, and in which commit, so a reader who lands on the struck sentences
#: below can date them rather than wonder.  Documentation only: nothing
#: dereferences it and no test derives anything FROM it (the status above is
#: derived from the tree; this is the human note beside it).
PICKUP_REQUEST_DISPATCH_CALL_SITE_LANDED = (
    "2026-09-02T00:35Z, runtime.py, commit 3e8541e "
    "(R300, answering CORE-REQUEST 20260902_0443)"
)
PICKUP_REQUEST_RUNTIME_ID_SLOT_VA = 0x0108202C      # zero on disk

# OUR ACCEPTANCE DESIGN -- see NONCLAIM 2.
PICKUP_REQUEST_VITAL_VERSION = 0
PICKUP_REQUEST_VITAL_VERSION_PROVENANCE = (
    "our_acceptance_design_no_capture_or_static_pin_fixes_it"
)
PICKUP_REQUEST_OUTER_VERSION = 0
PICKUP_REQUEST_OUTER_MASK = 0x02
#: THE MINIMUM, NOT THE ONLY VALUE, since round t8z97r: the request this lane
#: composes still carries exactly one vital, and R303 measured real inbound
#: packets carrying five.  An equality gate on this number refused 42 of the
#: 46 pickup frames that reached this lane; see
#: :func:`_vital_count_is_positive`.
#:
#: WHAT THAT RATIO IS OVER, AND IT IS NOT "THE OWNER'S CLICKS"
#: (pf-adversary, round t8z97r, D4 -- the first draft of this comment said
#: "the request the real client SENDS carries ours first", which is a
#: conclusion drawn from a counter that cannot see the other case).  The 46
#: is a count of ``MOB_PICKUP_REQUEST_*`` console lines, and those only
#: exist for frames ``runtime.py`` dispatched to this lane, which it does on
#: ``parse_outer``'s FIRST nested id.  So the denominator is "clicks whose
#: pickup vital arrived first".  ka1-A's own letter says in prose that the
#: click "usually arrives as vital 2..5"; if that is right, the clicks this
#: round recovers are a fraction of a fraction, and the rest are refused
#: earlier as ``not_the_pickup_vital`` -- still LANE-E's multi-vital walk to
#: fix, not this gate.  NOBODY HAS COUNTED THE CLICKS THEMSELVES.
#:
#: AND A RECOVERED CLICK IS NOT YET A TAKE.  The same letter's section (b):
#: ``last_target_pos`` is written only when TargetPosVital is FIRST, so in
#: exactly the packets this gate now accepts -- ours first, movement behind
#: it -- the stored position is the stale one, and R303 refused 2 of its 4
#: decoded clicks as ``claimant_out_of_range`` for that reason.  The honest
#: prediction is that some of the 42 move from a count refusal to a range
#: refusal, and the owner still clicks and nothing happens.  That half is
#: LANE-E's walk as well; this lane may not fix it and does not claim to.
#:
#: WHAT ROUND ``di7ers`` MEASURED, AND IT DEMOTES EVERYTHING ABOVE FROM A
#: RESULT TO A HISTORY NOTE.  ``R309``'s ``vital_walk`` reached ``main``
#: while the paragraphs above were being written, and a pf-adversary pass on
#: the MERGE booted a real session and measured the pair: the dispatcher
#: isolates the pickup vital before this lane sees it, handing over
#: ``vital_count`` 1 and a body bounded at seven bytes, so ON TODAY'S TREE
#: AN EQUALITY GATE HERE WOULD REFUSE NONE OF THE OWNER'S CLICKS.  The
#: "42 of 46" is a true fact about the tree of 2026-09-02 morning and is not
#: re-derivable at this commit; the recovery it names is delivered by the
#: walker, not by this constant.  What this constant still decides is the
#: frames the walker REFUSES and the dispatcher falls back on -- and there
#: the answer is now a refusal too, by :func:`walk_agrees_with_the_frame`.
#: A number kept as a justification after its tree is gone is the shape this
#: lane has been caught by twice.
PICKUP_REQUEST_VITAL_COUNT = 1

# The statically closed body, exactly as the four symmetric rows state it.
# The trailing u8 carries tag 0x08 -- NOT the 0x0B a reader who pattern-
# matched other lanes would expect.  The delivery table says 0x08 twice (W
# order 2 and R order 2) and the delivery table wins.
PICKUP_REQUEST_OBJECT_REF_TAG = 0x14
PICKUP_REQUEST_OPAQUE_U8_TAG = 0x08
PICKUP_REQUEST_OBJECT_REF_OBJECT_OFFSET = 0x14
PICKUP_REQUEST_OPAQUE_U8_OBJECT_OFFSET = 0x18
PICKUP_REQUEST_OBJECT_REF_WIDTH = 4
PICKUP_REQUEST_OPAQUE_U8_WIDTH = 1
# tag+4 then tag+1, both gates ALWAYS: seven bytes, never more, never fewer.
PICKUP_REQUEST_PAYLOAD_SIZE = 7

PICKUP_REQUEST_SERIALIZER_VA = 0x005E5E30
PICKUP_REQUEST_SERIALIZER_END_VA = 0x005E5E83
PICKUP_REQUEST_SERIALIZER_LEN = 83
PICKUP_REQUEST_SERIALIZER_SHA256 = (
    "8e439d4f3ff1479e723b220d8dd78a262b41df3b74839da9d4cb728f69773066"
)
PICKUP_REQUEST_DELIVERY_ROWS = (
    "PF_SERIALIZER_FIELDS.tsv PickupTerrainThing W1/W2/R1/R2, gate ALWAYS, "
    "source IMAGE"
)
PICKUP_REQUEST_PRODUCER_VA = 0x006B0639          # GT-046 job 5
PICKUP_REQUEST_PRODUCER_SOURCE = (
    "client_reads_pointer_esi_0x7C_then_dword_at_pointer_0x10"
)

# The two console tokens.  ASCII by rule: the bridge console is cp874 and a
# non-ASCII byte in a token is a red gate, not a cosmetic problem.
MOB_PICKUP_REQUEST_DECODED_TOKEN = "MOB_PICKUP_REQUEST_DECODED"
MOB_PICKUP_REQUEST_REFUSED_TOKEN = "MOB_PICKUP_REQUEST_REFUSED"
#: ROUND t8z97r.  Said when a click was read out of a packet that carried
#: MORE THAN ONE nested vital -- the shape that cost the owner 42 of her 46
#: clicks in R303.  It is a COUNT LINE, printed every time and not once:
#: whether the outer parser is still handing this lane a tail is the single
#: fastest way to tell, from the console alone, whether the multi-vital walk
#: has landed upstream.  Many of them means this lane is the only thing
#: reading past the first vital.
#:
#: ZERO OF THEM HAS FOUR CAUSES, NOT TWO (pf-adversary, round t8z97r, D13 --
#: the first draft listed the first two and stopped, which is the arm that
#: would mislead the reader this token exists for): every click arrived
#: alone; the upstream walk landed and bounds each body, so there is no
#: tail; the count said more than one and the body arrived bounded anyway;
#: or -- the one that matters -- THE PICKUP VITAL WAS NOT FIRST, so
#: ``runtime.py``'s dispatch never reached this lane at all and the click
#: was never counted anywhere.
#:
#: THAT LIST IS NOW WRONG IN BOTH DIRECTIONS AND ROUND ``di7ers`` REPLACES
#: IT RATHER THAN EDITING IT, so a reader can see what changed.  ``R309`` is
#: on ``main``: cause 2 is PERMANENTLY true for every frame the dispatcher
#: hands over, which makes zero the ordinary reading forever; and cause 4 --
#: the one the old text called the one that matters -- was MEASURED FALSE on
#: the merged tree, because ``runtime.py`` now isolates on ``leads_with_
#: pickup or selected is not None`` and a click behind a movement vital does
#: reach this lane.  What the token means today: a frame walked cleanly,
#: carried more than our vital, AND was handed over WITHOUT being isolated
#: -- i.e. by a caller that is not the production dispatcher.  On the wire
#: this lane expects to print it never, and one appearing is worth reading
#: as "somebody is calling this lane around the walker", not as a click
#: being recovered.
MOB_PICKUP_REQUEST_MULTIVITAL_TOKEN = "MOB_PICKUP_REQUEST_MULTIVITAL"
#: ROUND ``di7ers``.  Said when the relaxed tail path was asked for and
#: ``vital_walk`` refused the frame, carrying the WALKER's name (``walk=``)
#: because "this lane refused" and "the frame is not vitals at all" are
#: different things to the operator holding the console.
MOB_PICKUP_REQUEST_TAIL_REFUSED_TOKEN = "MOB_PICKUP_REQUEST_TAIL_REFUSED"
#: ROUND lh21ua.  The outcomes of the removal publisher, one ASCII line each,
#: so an operator watching a cp874 console can tell them apart without a
#: debugger.  HELD: nothing remained, so the only available generation is the
#: empty one, which RE-082 read as a client no-op -- ~~"the last object keeps
#: today's behaviour and RE-208 owns the question"~~ IS NARROWED, round
#: ewq4js: RE-208 still owns the question of a message that removes ONE
#: object, but the last object is no longer left to whatever happens to come
#: along.  The bag delta one frame earlier now carries v141's clearing derived
#: mask on exactly this case -- the transaction lane decides it, inside the
#: same lock as the take, and this file neither passes that decision nor
#: reimplements it -- and a floor with no rows left is what that mask
#: truthfully describes.  What is still unanswered is a scene where a row
#: remains and the publication refuses.  REFUSED: the publication
#: could not be composed; the pickup still stands, because the item is in the
#: bag and in the database before this runs, and a floor that redraws late is
#: not worth undoing that.
#:
#: !! THE SUCCESS TOKEN NAMES WHAT ACTUALLY HAPPENED, NOT WHAT WAS INTENDED,
#: and that is pf-adversary's first finding on this round: the first draft
#: printed PUBLISHED on a boot where ``runtime.py`` has no line that sends the
#: frames, so the bytes were composed and dropped inside the process.  A GT
#: round grading on console lines would have read "the server published the
#: removal and the client ignored it" off a boot that never sent a byte -- a
#: FALSE NEGATIVE against the CLIENT.  Same defect and same fix as R302's
#: LANE_A_UIA_NOTICE_NOT_THIS_BOOT (commit 005caea, eight hours earlier).
#: Which token fires is decided by :data:`GROUND_AFTER_CALL_SITE_STATUS`, and
#: a test re-derives that constant from ``runtime.py``'s own source, so the
#: day the chief's line lands the word changes with it and not before.
MOB_PICKUP_GROUND_REMOVAL_PUBLISHED_TOKEN = "MOB_PICKUP_GROUND_REMOVAL_PUBLISHED"
MOB_PICKUP_GROUND_REMOVAL_COMPOSED_TOKEN = (
    "MOB_PICKUP_GROUND_REMOVAL_COMPOSED_NOT_SENT_NO_CALL_SITE")
MOB_PICKUP_GROUND_REMOVAL_HELD_TOKEN = "MOB_PICKUP_GROUND_REMOVAL_HELD_LAST_OBJECT"
MOB_PICKUP_GROUND_REMOVAL_REFUSED_TOKEN = "MOB_PICKUP_GROUND_REMOVAL_REFUSED"

#: ROUND veby94, and it is the chief's finding (letter 2026-09-02T15:35+07:00,
#: item (b)) paid in this lane's own file rather than in his.  THE BYTES WERE
#: NEVER WRONG AND ARE NOT TOUCHED HERE; the CONSOLE was.  Three lines above
#: print ``key=0x...`` next to ``rows_left=...``, and until this round those
#: two numbers were not stated to be about the same ground:
#: ``DropLedgerCell.take`` cuts by KEY across the whole register without
#: asking which scene the row fell in (``mob_loot.DropLedgerCell.take`` ->
#: ``take_drop``), while ``frames_after_a_row_left`` publishes
#: ``for_scene(self._scene)`` only.  A line reading
#: ``HELD_LAST_OBJECT key=0x1234 rows_left=0`` therefore says "0" about the
#: scene the session is STANDING in, and a GT round grading on console lines
#: would read it as "the ground that key was on is now empty".
#:
#: SO EVERY LINE NAMES BOTH SCENES NOW, plus ``same_ground=`` -- the verdict
#: itself, because two scene words printed raw are a comparison the reader has
#: to make, and the comparison this file makes is CASEFOLDED (pf-adversary D3b
#: of this round measured a real dispatch printing ``taken_scene=bg0001
#: scene=Bg0001`` on one same-ground take: no token, two visibly different
#: words).  When the verdict is 0 a fourth token says so by name as well.
#:
#: [MEASURED, and re-derived rather than quoted, because the first draft of
#: this comment leaned on a document that says something else]: the
#: cross-scene case is UNREACHABLE through
#: :func:`dispatch_inbound_pickup_request` on this tree.  The reason is the
#: SCENE VIEW, not serialness: ``mob_pickup`` resolves every claim against
#: ``ledger_cell.publication()``'s view and raises
#: ``REFUSE_DROP_IS_IN_ANOTHER_SCENE`` for a key that is in the ledger but not
#: in the view; ``DropLedger.for_scene`` keeps only rows whose
#: ``scene_key`` equals the cell's; and ``mob_loot.scene_key`` is
#: ``_require_scene(...).casefold()``, which returns the value unchanged after
#: rejecting non-str, empty, over-long, non-ASCII, whitespace-bearing and
#: non-printable names.  So every row that survives the view is casefold-equal
#: to ``current_scene``, and that equality -- ONE ``.casefold()`` deep, and
#: one roster spelling away -- is the whole of the unreachability.
#: ~~"the session is strictly serial (FINDINGS_R18)"~~ IS STRUCK (pf-adversary
#: D8): that report records serial accept as a ``known_limitation`` with
#: HYP-PF-011 open to REMOVE it, so it is not a guarantee to lean on.
#:
#: [PROPOSED, this lane's judgement, not a measurement]: naming the
#: disagreement is worth its lines anyway, for the day a second pickup door, a
#: second cell, or a boundary crossing inside one dispatch exists.  WHAT THE
#: TOKEN DOES NOT DO, stated because pf-adversary asked it as the round's open
#: question: it does not REFUSE.  It narrates.  A cross-ground take that the
#: view stops today would, on that day, still complete with this line printed
#: next to it -- the refusal belongs to whoever opens that second door, and to
#: the ground-publication sink of the design letter, not to a console token.
MOB_PICKUP_GROUND_REMOVAL_CROSS_SCENE_TOKEN = (
    "MOB_PICKUP_GROUND_REMOVAL_KEY_IS_ANOTHER_SCENES")

#: ROUND ewq4js, step 3 of COO-DECISION 2026-09-02T10:44+07:00.  Which of the
#: two composed bag deltas this reply carries -- a different question from the
#: tokens above, decided by :func:`_the_delta_that_matches_the_floor` AFTER
#: them.  KEPT: the delta carries the ground list present-and-empty, so the
#: floor survives the frame and the removal generation in the same reply is
#: what takes the taken row off it.  CLEARED: the delta carries v141's empty
#: derived mask, which wipes the client's ground pool -- and that is the RIGHT
#: answer, not a failure, whenever nothing in this reply would reconcile the
#: floor afterwards: no rows left (where wiping is the truth, and the only
#: DELIBERATE removal of the last object's label this project has -- other
#: frames clear the pool too, see D3 below), a publication that refused, or a
#: boot where ``runtime.py`` does not send the generation yet.
#:
#: A KEPT line is therefore a promise about a frame that IS sent -- the bag
#: delta is returned by the chief's branch (``MOB_PICKUP_REQUEST_DELTA``,
#: landed in #549) -- AND about a removal that is sent with it.  Until
#: :data:`GROUND_AFTER_CALL_SITE_STATUS` reads "sent", every line here says
#: CLEARED, which is exactly what a boot with no removal call site does.
MOB_PICKUP_DELTA_GROUND_KEPT_TOKEN = "MOB_PICKUP_DELTA_GROUND_KEPT"
MOB_PICKUP_DELTA_GROUND_CLEARED_TOKEN = "MOB_PICKUP_DELTA_GROUND_CLEARED"

#: Does the chief's file SEND what this lane composes?  ``"sent"`` only when
#: ``runtime.py`` names ``ground_after``; ``"composed_not_sent"`` otherwise.
#: NOT a preference and not a flag: it is a statement about another file, and
#: ``test_the_ground_after_call_site_status_is_re_derived_from_runtime``
#: re-derives it from that file's AST on every run, so it cannot drift in
#: either direction -- a status left at "sent" after the line is reverted is
#: as red as one left at "composed_not_sent" after it lands.
#:
#: MOVED TO "sent" BY THE CHIEF, R304, in the same PR that landed the call
#: site in ``runtime.py`` -- LANE-B's own letter (2026-09-02T13:34+07:00)
#: hands this one line to whichever round lands the branch, and
#: COO-DECISION 2026-09-02T14:46+07:00 orders it into that same PR so no
#: boot ever exists where the two files disagree.
GROUND_AFTER_CALL_SITE_STATUS = "sent"

#: ROUND f4oh9y, THE EXPIRY HALF, and it is a different call site from the one
#: above even though it is the same branch of ``runtime.py``.  Before round
#: 233yho a REFUSED click never reached the ``ground_after`` lines: the
#: branch returned ``[]`` the moment ``outcome.delta is None``, which every
#: refusal is.  So the removal publication this module composes for an
#: expiry (see :func:`_expiry_publication`) was composed and DROPPED.
#:
#: MOVED TO "sent" BY THE CHIEF, round 233yho, COO-DECISION
#: 2026-09-03T23:46+07:00 item 1 -- ``runtime.py``'s pickup branch now sends
#: a refusal's ``ground_after`` (an empty one still returns ``[]`` unchanged).
#: Same discipline as the constant above and for the same reason: a console
#: line saying PUBLISHED on a boot that sends nothing is a false negative
#: against the CLIENT.  ``tests/test_mob_pickup_ground_expiry.py`` re-derives
#: this value from ``runtime.py``'s own AST, so it cannot drift in either
#: direction -- a status left at "composed_not_sent" after the line lands is
#: as red as one left at "sent" before it does.
EXPIRY_PUBLICATION_CALL_SITE_STATUS = "sent"

#: What the console says when a refused click carried a removal the sweep
#: owed.  PUBLISHED only while :data:`EXPIRY_PUBLICATION_CALL_SITE_STATUS`
#: says the frames really leave.
MOB_PICKUP_GROUND_EXPIRY_PUBLISHED_TOKEN = "MOB_PICKUP_GROUND_EXPIRY_PUBLISHED"
MOB_PICKUP_GROUND_EXPIRY_COMPOSED_TOKEN = (
    "MOB_PICKUP_GROUND_EXPIRY_COMPOSED_NOT_SENT_NO_CALL_SITE")
#: The sweep took the scene's LAST row, so there is no nonempty generation to
#: compose and RE-130 says an empty one removes nothing.  The debt is NOT
#: cleared (see ``DropLedgerCell.frames_after_rows_expired``): the next kill
#: or arrival in that scene pays it.
MOB_PICKUP_GROUND_EXPIRY_HELD_TOKEN = (
    "MOB_PICKUP_GROUND_EXPIRY_HELD_SCENE_EMPTY")
MOB_PICKUP_GROUND_EXPIRY_REFUSED_TOKEN = "MOB_PICKUP_GROUND_EXPIRY_REFUSED"

ACCEPTED = "exact_pickup_request"

# Every refusal means: no fields, no reply, nothing taken, nothing written.
# THE REGISTRY IS SPLIT BY WHAT CAN ACTUALLY PRODUCE EACH NAME, because an
# earlier draft of this comment claimed every one of them was reachable from
# a byte string a stranger could send and an adversarial pass measured that
# two of them are not: today's frame parser always hands over a bytes
# payload and always carries all seven envelope names, so those two can only
# come from a caller passing this module something else.  They are kept --
# this module is called with whatever the chief's file has, not with a
# guarantee -- but they are named honestly here rather than counted as wire
# refusals.  The lane's own test drives the wire family through the public
# entry point and the API family through the API.
MOB_PICKUP_REQUEST_API_ONLY_REASONS = (
    "parse_object_missing_fields",
    "payload_not_bytes",
    "parse_object_refused_to_answer",
    "legacy_module_missing_fields",
    # API-ONLY AND MEASURED SO, round t8z97r, not assumed: ``parse_outer``
    # reads the nested id only ``if vital_count:``, so a frame claiming zero
    # vitals arrives with ``nested_id`` None and is refused one check earlier
    # as ``not_the_pickup_vital``.  The name is what a CALLER handing this
    # lane its own parse object gets -- and it is worth keeping for exactly
    # that reader, because "the count is not a count" and "this is somebody
    # else's vital" are different holes.
    "vital_count_not_positive",
    # API-ONLY AND MEASURED SO, round di7ers second pass: the only walker
    # verdict that binds this lane is ``envelope_reread_disagrees``, and both
    # readers read the same offsets of the same bytes, so a frame that comes
    # off the wire through ``parse_outer`` can never produce it.  What CAN is
    # a caller handing over a parse object whose fields describe one frame
    # and whose ``raw_pc`` is another -- which is exactly the hole D4 found
    # in the first version of this gate, now closed by the same name.
    "tail_refused_by_vital_walk",
)
MOB_PICKUP_REQUEST_REFUSAL_REASONS = (
    "parse_object_missing_fields",
    "parse_object_refused_to_answer",
    "legacy_module_missing_fields",
    "session_has_no_bag_cell",
    "session_has_no_ground_cell",
    "not_a_runtime_protocol_req",
    "wrong_outer_version",
    "wrong_outer_mask",
    # ~~"vital_count_not_one"~~ IS NO LONGER EMITTED (round t8z97r): a
    # multi-vital packet whose FIRST vital is ours is a pickup click and is
    # now read as one.  THE NAME STAYS REGISTERED, and not out of sentiment:
    # it is in R303's console, in ka1-A's tally and in the events trail of
    # every boot before this one, and a name that is deleted is a name a
    # reader of those artifacts can no longer look up.
    "vital_count_not_one",
    "vital_count_not_positive",
    # ROUND ``di7ers``: the relaxed tail path was asked for and ``vital_walk``
    # refused the frame.  The walker is the second reader of the same bytes
    # and its refusal wins -- see :func:`walk_agrees_with_the_frame`.
    "tail_refused_by_vital_walk",
    "not_the_pickup_vital",
    "wrong_vital_version",
    "payload_not_bytes",
    "truncated_payload",
    "wrong_object_ref_tag",
    "wrong_opaque_u8_tag",
    "trailing_bytes_after_object",
)

#: NAMES THIS LANE NO LONGER PRODUCES, kept in the registry so the artifacts
#: that carry them stay readable.  A retired name must be produced by
#: NOTHING -- not by the wire, not by an API caller -- and the lane's own test
#: drives every family to prove which is which.  ``vital_count_not_one``
#: retired in round ``t8z97r`` when the equality gate on the outer vital count
#: became a "at least one" gate (NOW.md P-1; ka1-A's R303 tally: it refused 42
#: of the owner's 46 clicks).
MOB_PICKUP_REQUEST_RETIRED_REASONS = (
    "vital_count_not_one",
)

# The two session-readiness names above are NOT wire refusals: they mean the
# frame was fine and the SESSION was not ready for it (no character selected
# yet, or no ground cell for the scene).  Every neighbouring inbound lane in
# the chief's file carries such a guard; publishing a branch without one is
# how a well-formed frame from a connection that has not selected a
# character reaches a transaction with None in its arguments.
MOB_PICKUP_REQUEST_READINESS_REASONS = (
    "session_has_no_bag_cell",
    "session_has_no_ground_cell",
)


class MobPickupRequestRefused(ValueError):
    """A named refusal.  ``args[0]`` is always a registered reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in MOB_PICKUP_REQUEST_REFUSAL_REASONS:
            raise RuntimeError(
                "MOB-PICKUP-REQUEST-001 unregistered refusal reason")
        super().__init__(reason, detail)

    @property
    def reason(self) -> str:
        return self.args[0]


@dataclass(frozen=True)
class PickupRequestFields:
    """The two decoded values, named by proven SOURCE and width only.

    ``object_ref_u32`` is the dword GT-046 proved the client copies out of
    the live ground object it clicked.  ``opaque_u8`` has no known meaning
    (NONCLAIM 4) and is carried, never read.
    """

    object_ref_u32: int
    opaque_u8: int


@dataclass(frozen=True)
class PickupRequestRead:
    """One inbound frame, classified.  ``fields`` is None unless accepted."""

    accepted: bool
    reason: str
    fields: PickupRequestFields | None


# ---------------------------------------------------------------------------
# The body.
# ---------------------------------------------------------------------------

def _decode_by_tag_walk(payload: bytes) -> PickupRequestFields:
    """Walk the two records the delivery table declares, in its order.

    Every tag byte is checked at its position, every truncation refuses, and
    one byte left over after the trailing u8 refuses -- a malformed copy of
    the accepted request must never be granted on the strength of its
    prefix.

    THE ONE PLACE THAT MAY LEAVE BYTES OVER is
    :func:`decode_pickup_request_body_with_vital_tail`, and it may only do it
    when the OUTER frame says the tail belongs to another vital.  Everything
    else in this lane, this function included, still refuses a prefix.
    """
    if len(payload) < 1 + PICKUP_REQUEST_OBJECT_REF_WIDTH:
        raise MobPickupRequestRefused(
            "truncated_payload", "object_ref record is short")
    if payload[0] != PICKUP_REQUEST_OBJECT_REF_TAG:
        raise MobPickupRequestRefused(
            "wrong_object_ref_tag", "tag byte 0 is not 0x14")
    object_ref = int.from_bytes(payload[1:5], "little")
    cursor = 1 + PICKUP_REQUEST_OBJECT_REF_WIDTH
    if len(payload) - cursor < 1 + PICKUP_REQUEST_OPAQUE_U8_WIDTH:
        raise MobPickupRequestRefused(
            "truncated_payload", "opaque_u8 record is short")
    if payload[cursor] != PICKUP_REQUEST_OPAQUE_U8_TAG:
        raise MobPickupRequestRefused(
            "wrong_opaque_u8_tag", "tag byte 5 is not 0x08")
    opaque = payload[cursor + 1]
    cursor += 1 + PICKUP_REQUEST_OPAQUE_U8_WIDTH
    if cursor != len(payload):
        raise MobPickupRequestRefused(
            "trailing_bytes_after_object", "bytes remain after the body")
    return PickupRequestFields(object_ref, opaque)


def decode_pickup_request_payload(payload: Any) -> PickupRequestFields:
    """Read one request body into the declared pair, or refuse by name.

    A body that is not a byte string refuses before anything is indexed: an
    inbound payload is whatever the frame parser handed over, and a lane
    that assumes it is bytes crashes the session on the day it is not.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise MobPickupRequestRefused(
            "payload_not_bytes", "inbound body is not a byte string")
    return _decode_by_tag_walk(bytes(payload))


#: The tag byte every nested vital record starts with: ``12 <id u16>``, the
#: same tag ``pf_login_game_server_v141.parse_outer`` reads the nested id
#: with.  RE-DERIVED, not assumed: the R303 capture in ka1-A's CORE-REQUEST
#: (``pf_bridge/notes_to_chief/20260902_1800_*``) shows frame #714 carrying
#: five vitals, each one opening ``12 B4 1E 0B 00`` / ``12 90 2A 0B 00``.
PICKUP_REQUEST_NESTED_VITAL_TAG = 0x12
#: The shortest thing that can be a nested vital: the id record (tag + u16)
#: and the version record (tag + u8).  A "tail" shorter than this cannot be
#: the vital the outer count promised.
PICKUP_REQUEST_NESTED_VITAL_MIN = 5
#: The version record's tag, at offset 3 of every nested vital, read by
#: ``parse_outer`` as ``c.u8(0x0B)`` right after the id.  Checked as well as
#: the leading 0x12 because one byte is a coin flip and two are a shape
#: (pf-adversary, round t8z97r, D9).
PICKUP_REQUEST_NESTED_VERSION_TAG = 0x0B
PICKUP_REQUEST_NESTED_VERSION_TAG_OFFSET = 3


def decode_pickup_request_body_with_vital_tail(payload: Any) -> tuple:
    """``(fields, tail_length)`` for a body followed by ANOTHER VITAL.

    WHY THIS EXISTS, AND IT IS THE OWNER'S 42 THROWN-AWAY CLICKS.
    ``pf_login_game_server_v141.parse_outer`` slices ``nested_payload = pc[
    c.p:]`` -- everything to the end of the packet -- and then reads only the
    FIRST nested vital (its own comment says "all client packets seen so far
    contain one nested vital", which R303 measured false: the real client
    batches up to five).  So when the pickup vital arrives FIRST in a
    multi-vital packet, the body handed to this lane is our seven bytes
    followed by the other vitals' bytes, and the strict walk refuses it as
    ``trailing_bytes_after_object``.  R303: 46 pickup frames, 42 refused
    before they were ever decoded, 2 takes completed -- 4.3%.

    WHAT IT ACCEPTS, AND WHAT IT REFUSES BY NAME.  The two records are read
    at their declared positions with the same tag and width checks as the
    strict walk -- nothing about OUR body is relaxed.  What is relaxed is
    only the "no bytes left over" rule, and only when what is left over
    BEGINS WITH A VITAL HEADER: at least
    :data:`PICKUP_REQUEST_NESTED_VITAL_MIN` bytes, opening with
    :data:`PICKUP_REQUEST_NESTED_VITAL_TAG` and carrying
    :data:`PICKUP_REQUEST_NESTED_VERSION_TAG` where a vital's version record
    stands.  A tail that is shorter, or shaped otherwise, is
    ``trailing_bytes_after_object`` exactly as before.

    ~~"this lane does not grant a take on the strength of a prefix followed
    by rubbish"~~ IS STRUCK, and the strike is the honest version
    (pf-adversary, round t8z97r, D9): THE TAIL IS NOT PARSED.  Two header
    bytes are checked and the rest is passed over, so a tail that begins
    like a vital and continues as noise IS accepted, and a ``vital_count``
    that says five while a seven-byte body arrives alone is accepted too --
    the count selects the rule, and nothing cross-checks the two.  What
    bounds that is not this function: an accepted read is permission to ASK
    the transaction, which resolves ``object_ref`` against the live ground
    and refuses anything that matches no standing row.  A tail check that
    claimed more than two bytes of evidence would be the convenient
    sentence this lane keeps getting caught by.

    ~~AN EMPTY TAIL WITH A COUNT ABOVE ONE IS DELIBERATELY ACCEPTED, and it
    is not laxity: that is the shape LANE-E's multi-vital walk will hand over
    once it bounds each vital's body.~~ STRUCK IN ROUND ``di7ers``, AND IT
    WAS A PREDICTION ABOUT SOMEBODY ELSE'S FILE.  The walk landed as
    ``R309`` and does the opposite: ``vital_walk`` sets ``vital_count`` to 1
    on every isolated vital, deliberately, saying in its own docstring that
    "saying 5 would be a lie".  So that shape is handed over by nobody, and
    an envelope claiming five vitals over one bounded body is now what it
    always looked like -- a frame whose two readings disagree.  The walk
    gate refuses it as ``tail_refused_by_vital_walk``.

    IT DOES NOT PARSE THE TAIL and it never will -- walking every nested
    vital is the outer parser's job, and as of ``R309`` that walk exists.
    ~~when that walk lands ... the strict path takes it and this function is
    never reached~~ IS HALF TRUE and the half that is false is the one that
    mattered: the dispatcher falls back to the unbounded parse precisely on
    the frames the walk REFUSED, which is how this function acquired its
    only production path -- and a pf-adversary pass measured it granting
    clicks out of frames the walker had named ``unknown_vital_id``.  Since
    round ``di7ers`` it is reached only when the walk ACCEPTS the frame and
    the caller did not isolate it, which on the production dispatcher is
    never.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise MobPickupRequestRefused(
            "payload_not_bytes", "inbound body is not a byte string")
    body = bytes(payload)
    head = body[:PICKUP_REQUEST_PAYLOAD_SIZE]
    tail = body[PICKUP_REQUEST_PAYLOAD_SIZE:]
    if not tail:
        # Nothing left over: the strict walk is the whole answer, and it is
        # the one that runs, so a body of exactly seven bytes decodes
        # identically whatever the outer count said.
        return _decode_by_tag_walk(body), 0
    if (len(tail) < PICKUP_REQUEST_NESTED_VITAL_MIN
            or tail[0] != PICKUP_REQUEST_NESTED_VITAL_TAG
            or tail[PICKUP_REQUEST_NESTED_VERSION_TAG_OFFSET]
            != PICKUP_REQUEST_NESTED_VERSION_TAG):
        raise MobPickupRequestRefused(
            "trailing_bytes_after_object",
            "bytes remain after the body and they do not begin a vital")
    # The head is walked STRICTLY, so every tag and width check still fires
    # and a short head is still ``truncated_payload``.
    return _decode_by_tag_walk(head), len(tail)


# ---------------------------------------------------------------------------
# The envelope.
# ---------------------------------------------------------------------------

_ENVELOPE_FIELDS = (
    "outer_id", "outer_version", "outer_mask", "vital_count",
    "nested_id", "nested_version", "nested_payload",
)


def classify_pickup_request(legacy: Any, parsed: Any) -> str:
    """Classify one parsed inbound frame.  Returns a reason, never raises.

    ``ACCEPTED`` means: this is our envelope, carrying our vital id, and the
    body decoded cleanly.  Everything else is a registered refusal name and
    means no reply.  Order matters for the NAME only, never for the verdict:
    the id check comes before the version and mask checks so that a frame of
    some other vital is reported as somebody else's frame rather than as a
    malformed pickup.

    EVERY ENVELOPE FIELD IS READ EXACTLY ONCE, into a snapshot, before any
    of them is judged (pf-adversary, round t8z97r, D10).  The round-
    ``h6bl53`` rule -- "ONE read of the payload, not two, so a parse object
    that answers differently the second time cannot turn an accepted verdict
    into an exception" -- covered the payload and left ``vital_count`` read
    five times across classify and :func:`read_inbound_pickup_request`; a
    count that changed between the third and the fourth read had classify
    accept a frame the decode then refused.  In production ``ParsedOuter``
    is a plain dataclass and cannot do that; the guarantee is now the one
    that is written down.

    "Never raises" is enforced rather than promised: reading a field off the
    parse object, and reading the outer id off the legacy module, are both
    done inside the guard, because an adversarial pass showed that a parse
    object whose attribute access or comparison raises walks straight out of
    this function otherwise.
    """
    return _classify_snapshot(legacy, parsed)[0]


def _snapshot_envelope(parsed: Any) -> dict:
    """Every envelope field, read ONCE, or a refusal name in its place.

    Returns ``{"reason": <name>}`` when the parse object cannot be read at
    all, and the seven fields otherwise.  ``getattr`` rather than ``hasattr``
    plus a second read, which is the whole point: the presence check and the
    value used to be two reads of the same property.
    """
    fields: dict = {}
    for name in _ENVELOPE_FIELDS:
        try:
            fields[name] = getattr(parsed, name)
        except AttributeError:
            # Exactly what ``hasattr`` used to answer for.
            return {"reason": "parse_object_missing_fields"}
        except Exception:
            # A property that raises anything else is a parse object that
            # refuses to answer -- named, never propagated (an adversarial
            # pass put a KeyError here).
            return {"reason": "parse_object_refused_to_answer"}
    return fields


def _classify_snapshot(legacy: Any, parsed: Any) -> tuple:
    """``(reason, snapshot, gate)``.  The snapshot is ``None`` unless read.

    :func:`read_inbound_pickup_request` decodes from the SAME snapshot this
    verdict was reached on, so the two cannot disagree about a field -- and
    from the SAME :class:`WalkGate`, so the walker is asked once per frame
    and cannot answer the verdict and the decode differently (round
    ``di7ers``; the identical shape was closed for the payload in ``h6bl53``
    and for the count in ``t8z97r``).
    """
    gate = WalkGate(legacy, parsed)
    try:
        if not hasattr(legacy, "GSCN_RUNTIME_PROTOCOL_REQ"):
            return "legacy_module_missing_fields", None, gate
        snapshot = _snapshot_envelope(parsed)
        if "reason" in snapshot:
            return snapshot["reason"], None, gate
        gate = WalkGate(legacy, parsed, snapshot)
        return _classify_fields(legacy, snapshot, gate), snapshot, gate
    except MobPickupRequestRefused as exc:
        return exc.reason, None, gate
    except Exception:
        # A parse object that raises while being read is not our frame and
        # is certainly not a grant.  It is named, not propagated.
        return "parse_object_refused_to_answer", None, gate


def _classify_fields(legacy: Any, parsed: Any, walk_gate: Any = None) -> str:
    """The verdict, read off a SNAPSHOT (a mapping), never off the parse
    object: by the time this runs every field has been read exactly once."""
    if parsed["nested_id"] != PICKUP_REQUEST_VITAL_ID:
        return "not_the_pickup_vital"
    if parsed["outer_id"] != legacy.GSCN_RUNTIME_PROTOCOL_REQ:
        return "not_a_runtime_protocol_req"
    if parsed["outer_version"] != PICKUP_REQUEST_OUTER_VERSION:
        return "wrong_outer_version"
    if parsed["outer_mask"] != PICKUP_REQUEST_OUTER_MASK:
        return "wrong_outer_mask"
    if not _vital_count_is_positive(parsed["vital_count"]):
        # ~~"vital_count_not_one"~~ IS STRUCK AS THE WIRE ANSWER, round
        # t8z97r, NOW.md item P-1 ("LANE-B takes its own vital_count_not_one
        # gate in parallel") and ka1-A's CORE-REQUEST 20260902_1800.  A
        # packet carrying our vital FIRST and four movement vitals behind it
        # is a pickup click, and refusing it on the COUNT threw away 42 of
        # the owner's 46 clicks in R303.  What is still refused is a count
        # that is not a positive number at all -- a frame claiming zero
        # vitals while handing one over is not a frame this lane can read.
        return "vital_count_not_positive"
    if parsed["nested_version"] != PICKUP_REQUEST_VITAL_VERSION:
        return "wrong_vital_version"
    try:
        _decode_body_for_count(
            parsed["nested_payload"], parsed["vital_count"], walk_gate)
    except MobPickupRequestRefused as exc:
        return exc.reason
    return ACCEPTED


def _vital_count_is_positive(vital_count: Any) -> bool:
    """Is the outer count a real count of at least one vital?

    ``bool`` is not a count (``True`` reaching this field means somebody
    passed a "are there vitals?" answer into a "how many?" field, and reading
    it as one vital would turn a caller's type error into a granted take --
    the same rule, and the same reason, as ``mob_loot.
    ground_liveness_is_readable``).  Every other ``int`` subclass counts.
    """
    return (isinstance(vital_count, int)
            and not isinstance(vital_count, bool)
            and vital_count >= PICKUP_REQUEST_VITAL_COUNT)


class _WalkView:
    """The snapshot this lane already read, wearing a parse object's face.

    THE SECOND READER MAY NOT BE A SECOND READ OF THE CALLER'S OBJECT.  This
    lane's rule since round ``h6bl53`` is that every envelope field is read
    exactly ONCE, so that a parse object which answers differently the second
    time cannot be accepted by the classifier and refused by the decode.
    Handing ``vital_walk`` the caller's object would have re-read four of
    those fields and thrown that rule away in the same commit that added a
    guard for the caller's benefit.  So the walker is handed the values this
    lane already has, plus ``raw_pc`` read once -- and it still does the part
    that makes it a second READER: it re-derives the envelope from the
    frame's own bytes and refuses when the two readings disagree.
    """

    __slots__ = _ENVELOPE_FIELDS + ("raw_pc",)

    def __init__(self, snapshot: dict, raw_pc: Any) -> None:
        for name in _ENVELOPE_FIELDS:
            setattr(self, name, snapshot[name])
        self.raw_pc = raw_pc


class WalkGate:
    """Asks ``vital_walk`` about ONE frame, at most once, and remembers.

    WHY A CACHING OBJECT AND NOT A CALL.  The walk is asked only on the
    relaxed path, so a single-vital frame never pays for it.  ~~which is
    every frame the production dispatch hands this lane~~ IS STRUCK: it was
    measured false in the same pass that measured D1 (round ``di7ers``,
    second pass, D3).  ``runtime.py``'s fallback -- ``if pickup_parsed is
    None and leads_with_pickup`` -- hands this lane the UNBOUNDED parse,
    ``vital_count`` and all, exactly when ``isolate_vital`` refused; that set
    is not empty, it is where every batched click with an untabled sibling
    lands, and it is the set this gate is judged on.  And
    it is asked ONCE per frame: the classifier and
    :func:`read_inbound_pickup_request` both consult the same gate, and a
    walker answering differently the second time would be exactly the
    classify-says-yes / decode-says-no shape this lane already spent a round
    closing for the payload and the count.

    ``ok`` is False until :meth:`__call__` has run, and False is the answer
    for every way of not knowing: no snapshot, no ``raw_pc``, no
    ``vital_walk`` module, a walker that raises, a walk that refuses.  A gate
    nobody consulted refuses.
    """

    __slots__ = ("legacy", "parsed", "snapshot", "asked", "ok", "reason")

    def __init__(self, legacy: Any, parsed: Any,
                 snapshot: Any = None) -> None:
        self.legacy = legacy
        self.parsed = parsed
        self.snapshot = snapshot
        self.asked = False
        self.ok = False
        self.reason = "vital_walk_not_consulted"

    def __call__(self) -> bool:
        if self.asked:
            return self.ok
        self.asked = True
        if self.snapshot is None:
            self.ok, self.reason = False, "walk_view_unavailable"
            return self.ok
        try:
            raw_pc = self.parsed.raw_pc
        except Exception:                         # noqa: BLE001 - fail closed
            self.ok, self.reason = False, "raw_pc_unavailable"
            return self.ok
        try:
            view = _WalkView(self.snapshot, raw_pc)
        except Exception:                         # noqa: BLE001 - fail closed
            self.ok, self.reason = False, "walk_view_unavailable"
            return self.ok
        self.ok, self.reason = walk_agrees_with_the_frame(self.legacy, view)
        return self.ok


def walk_agrees_with_the_frame(legacy: Any, parsed: Any) -> tuple:
    """``(ok, reason)``: does the WHOLE frame walk as nested vitals?

    THE RULE THIS ANSWERS, and it is the question a pf-adversary pass on the
    merge said neither lane had answered: WHEN THE WALKER AND THIS LANE
    DISAGREE ABOUT ONE FRAME, THE REFUSAL WINS.  ``vital_walk`` reads the
    frame's own bytes and refuses by name when a vital's id is undeclared,
    when a body is short, when bytes are left over, or when the envelope's
    count disagrees with what the bytes carry.  This lane's relaxed tail rule
    checks two bytes of the tail and passes over the rest -- deliberately,
    and it says so -- so on their own the two disagree about frames like
    ``[pickup][12 AA BB 0B FF FF FF]``: the walker names it
    ``unknown_vital_id`` and the relaxed rule decoded the click anyway.  That
    is a fail-OPEN, and it was measured, not imagined.

    It also restores something ``R309`` wrote and the merge had taken away:
    ``runtime.py``'s leading-pickup fallback exists so that "a walk this
    module refuses still prints its named refusal instead of turning a loud
    line into silence".  With this gate the refusal is loud again -- as
    ``tail_refused_by_vital_walk``, carrying the walker's own name on the
    console beside it.

    NEVER RAISES.  Every way of not knowing is False: no walker, a walker
    that raises, a walk with no name.  The second reader disagreeing with the
    first is a refusal; the second reader being unavailable is also a refusal.
    """
    if _vital_walk is None:
        return False, "vital_walk_unavailable"
    try:
        walk = _vital_walk.walk_nested_vitals(legacy, parsed)
        walked = bool(walk.walked)
        named = str(walk.reason or "")
    except Exception:                             # noqa: BLE001 - see above
        return False, "vital_walk_refused_to_answer"
    if walked:
        return True, ""
    return False, named or "vital_walk_refused_without_a_name"


#: THE ONLY WALKER VERDICTS THIS LANE TREATS AS ITS OWN REFUSAL, and the
#: list is short on measured grounds rather than cautious ones (pf-adversary,
#: round ``di7ers``, SECOND pass, D1).
#:
#: The first version of this gate refused every frame ``vital_walk`` refused.
#: An adversarial pass then booted a session and measured what that costs:
#: the walker's length table has FOUR rows and ``legacy.NAMES`` carries 49
#: ids, so 46 ids stop the walk -- and one of them, ``UPDATE_SERVER_SETTING_
#: VITAL`` 0x0F01, is in v141's own ``CAPTURE_NOISE_IDS``, the ids it says
#: the client sends CONTINUOUSLY.  A real click batched behind one of those
#: was read before the gate and thrown away after it.  Same for a frame
#: composed under the OTHER reading of ``TARGET_POS_VITAL``'s width, which
#: ``vital_walk``'s own docstring says it cannot settle.  A fail-closed fix
#: that costs the owner her clicks is worse than the hole it closes.
#:
#: So the split is by WHAT THE VERDICT IS ABOUT.  ``unknown_vital_id``,
#: ``truncated_vital`` and ``trailing_bytes_after_last_vital`` are verdicts
#: about SOMEBODY ELSE'S vital, reached with a table that admits it is
#: missing 46 ids and unsure about one of the four it has.  They are not
#: evidence about our seven bytes, which this lane validates itself, tag by
#: tag, and they are not a reason to refuse a click.  What IS about this
#: frame's own envelope is ``envelope_reread_disagrees``: the header read
#: from the raw bytes disagrees with the parse object handed over, which
#: means the two readers do not even agree what frame this is.
#:
#: AND THE FAIL-OPEN THE FIRST PASS FOUND IS ANSWERED BY LOUDNESS, NOT BY A
#: REFUSAL.  A ``[pickup][noise]`` frame is read again -- and it says so, on
#: the console, with the walker's own name (``MOB_PICKUP_REQUEST_TAIL_
#: REFUSED`` for the refusals above, ``MOB_PICKUP_REQUEST_WALK_DISAGREES``
#: for the rest).  Nobody has been able to name the harm such a frame does
#: that ``mob_pickup``'s object_ref resolution against the live ground does
#: not already stop: an accepted read is permission to ASK the transaction,
#: never a take.  If somebody names one, it belongs here, next to this list.
MOB_PICKUP_REQUEST_WALK_REFUSALS_THAT_BIND = (
    "envelope_reread_disagrees",
)


#: EVERY NAME THIS LANE CAN PRINT AFTER ``walk=``, registered rather than
#: invented at the call site (pf-adversary, round ``di7ers``, second pass,
#: D6).  Six names were being formatted onto the operator's console from
#: nowhere, so a reader could not tell ``walk=unknown_vital_id`` -- a name
#: ``vital_walk`` owns and registers -- from a name this lane made up on the
#: spot.  The two families are printed and tested as one union, and a name
#: outside it is a bug in this file, not a fact about a frame.
MOB_PICKUP_REQUEST_WALK_GATE_NAMES = (
    # This lane's own, for the ways of not knowing.
    "vital_walk_not_consulted",
    "walk_view_unavailable",
    "raw_pc_unavailable",
    "vital_walk_unavailable",
    "vital_walk_refused_to_answer",
    "vital_walk_refused_without_a_name",
)
#: Said when the walker disagreed about a frame this lane READ ANYWAY.  It is
#: the loud half of the answer to the fail-open: R309's fallback exists so
#: that "a walk this module refuses still prints its named refusal instead of
#: turning a loud line into silence", and after the second adversary pass
#: this lane keeps that promise with a LINE rather than with a verdict --
#: because the verdict was measured to cost real clicks.
MOB_PICKUP_REQUEST_WALK_DISAGREES_TOKEN = "MOB_PICKUP_REQUEST_WALK_DISAGREES"


def _walk_disagreement_line(walk_gate: Any) -> str:
    """One ASCII line, or an empty string when there is nothing to say.

    Never raises: a console line may cost the LINE and never the FRAME, the
    rule this lane arrived at the hard way in round ``t8z97r``.
    """
    try:
        if walk_gate is None or walk_gate():
            return ""
        name = str(walk_gate.reason)
        if name not in MOB_PICKUP_REQUEST_WALK_GATE_NAMES:
            try:
                registered = _vital_walk.VITAL_WALK_REFUSAL_REASONS
            except Exception:                     # noqa: BLE001 - see above
                registered = ()
            if name not in registered:
                name = "unregistered_walk_reason"
        return "%s walk=%s" % (
            MOB_PICKUP_REQUEST_WALK_DISAGREES_TOKEN,
            mob_pickup_persist.console_safe(name)[:48])
    except Exception:                             # noqa: BLE001 - see above
        return "%s walk=unprintable" % (
            MOB_PICKUP_REQUEST_WALK_DISAGREES_TOKEN,)


def _decode_body_for_count(payload: Any, vital_count: Any,
                           walk_gate: Any = None) -> tuple:
    """``(fields, tail_length)``: the body rule THIS outer count implies.

    One vital -> the strict walk, byte for byte what this lane has always
    done: seven bytes, nothing left over.  More than one -> :func:`decode_
    pickup_request_body_with_vital_tail`, which relaxes NOTHING about our
    own two records and only allows a tail that begins another vital --
    UNLESS the walker says the two readings of this frame's ENVELOPE
    disagree, which is the one verdict of its that is about our frame rather
    than somebody else's vital.  See
    :data:`MOB_PICKUP_REQUEST_WALK_REFUSALS_THAT_BIND` for why that list is
    one name long and what it cost to find out.

    ``walk_gate`` defaults to None, and None means the walker was never
    asked -- which is NOT a refusal here.  It cannot be: refusing on "not
    asked" is the same rule as refusing on "the walker does not know that
    id", and the second was measured to throw the owner's clicks away.  A
    caller that skips the gate gets the tail rule, and the tail rule was
    never the thing that granted a take.

    Split out so the classifier and :func:`read_inbound_pickup_request` read
    the body under the SAME rule.  Two copies of this decision would be two
    chances for a frame to be accepted by one and refused by the other, and
    that shape (classify says yes, decode says no) is how a lane starts
    answering clicks with silence.
    """
    if vital_count == PICKUP_REQUEST_VITAL_COUNT:
        return decode_pickup_request_payload(payload), 0
    if walk_gate is not None and not walk_gate():
        if walk_gate.reason in MOB_PICKUP_REQUEST_WALK_REFUSALS_THAT_BIND:
            raise MobPickupRequestRefused(
                "tail_refused_by_vital_walk",
                "the two readings of this frame's envelope disagree")
    return decode_pickup_request_body_with_vital_tail(payload)


def pickup_request_console_line(read: PickupRequestRead) -> str:
    """One ASCII line per inbound frame this lane looked at.

    G-OBS: a lane that fires on a real click has to be greppable in the
    console the owner is already watching, without a debugger and without a
    capture.  The accepted line carries the two decoded values so a run can
    be compared against the ledger keys the ground lane published.
    """
    if type(read) is not PickupRequestRead:
        raise RuntimeError("MOB-PICKUP-REQUEST-001 console line needs a read")
    if not read.accepted or read.fields is None:
        return "%s reason=%s" % (
            MOB_PICKUP_REQUEST_REFUSED_TOKEN, read.reason)
    return "%s object_ref=0x%08X opaque_u8=%d" % (
        MOB_PICKUP_REQUEST_DECODED_TOKEN,
        read.fields.object_ref_u32,
        read.fields.opaque_u8,
    )


def read_inbound_pickup_request(
        legacy: Any, parsed: Any, *, echo: bool = True) -> PickupRequestRead:
    """THE production entry point.  One parsed frame in, one verdict out.

    This is the call ``MOB_PICKUP_REQUEST_WIRING`` asks the chief to put in
    ``runtime.py``.  It never raises for wire reasons: a frame this lane
    cannot accept comes back as a refused read, because a listener that
    throws on a malformed inbound frame hands a stranger the session.

    It also never grants anything.  An accepted read is permission to ASK
    the transaction, and the transaction is where the object reference is
    resolved against the live ground and refused when it matches nothing.
    """
    reason, snapshot, walk_gate = _classify_snapshot(legacy, parsed)
    if reason == ACCEPTED:
        # ONE read of every envelope field, not several: the accepted body
        # is decoded from the SAME snapshot the verdict was reached on, so a
        # parse object that answers differently the second time cannot turn
        # an accepted verdict into an exception out of this function
        # (adversarial pass, round h6bl53 for the payload; round t8z97r, D10,
        # for the count that was still being re-read five times).
        tail = 0
        try:
            body = bytes(snapshot["nested_payload"])
            fields, tail = _decode_body_for_count(
                body, snapshot["vital_count"], walk_gate)
        except MobPickupRequestRefused as exc:
            read = PickupRequestRead(False, exc.reason, None)
        except Exception:
            read = PickupRequestRead(
                False, "parse_object_refused_to_answer", None)
        else:
            read = PickupRequestRead(True, ACCEPTED, fields)
        if tail:
            # OUTSIDE the decode guard, and that is the lane's own rule
            # restated (pf-adversary, round t8z97r, D8): formatting a
            # console line used to sit inside the try whose except turns
            # into a refusal, so a count whose ``__int__`` raised cost the
            # FRAME for a body that had already decoded cleanly.  A console
            # line may cost a LINE and nothing else.
            try:
                line = "%s vitals=%s tail=%d" % (
                    MOB_PICKUP_REQUEST_MULTIVITAL_TOKEN,
                    mob_pickup_persist.console_safe(
                        str(snapshot["vital_count"]))[:32], tail)
            except Exception:                    # noqa: BLE001 - see above
                line = "%s vitals=unprintable tail=%d" % (
                    MOB_PICKUP_REQUEST_MULTIVITAL_TOKEN, tail)
            _say(echo, line)
            disagreement = _walk_disagreement_line(walk_gate)
            if disagreement:
                _say(echo, disagreement)
    else:
        if reason not in MOB_PICKUP_REQUEST_REFUSAL_REASONS:
            raise RuntimeError(
                "MOB-PICKUP-REQUEST-001 classifier returned an "
                "unregistered reason")
        read = PickupRequestRead(False, reason, None)
        if reason == "tail_refused_by_vital_walk":
            # THE WALKER'S OWN NAME, beside this lane's.  R309 built the
            # leading-pickup fallback so that "a walk this module refuses
            # still prints its named refusal instead of turning a loud line
            # into silence"; the gate keeps that promise, and an operator
            # reading the console has to see WHICH refusal it was without a
            # debugger (G-OBS).  Formatting sits in its own guard: a console
            # line may cost a LINE and never a frame.
            line = _walk_disagreement_line(walk_gate).replace(
                MOB_PICKUP_REQUEST_WALK_DISAGREES_TOKEN,
                MOB_PICKUP_REQUEST_TAIL_REFUSED_TOKEN, 1)
            _say(echo, line or "%s walk=unprintable" % (
                MOB_PICKUP_REQUEST_TAIL_REFUSED_TOKEN,))
    # ROUND lh21ua: through _say, not print.  This line sits inside the
    # never-raises path too, and the bridge console is cp874 with
    # errors='strict' -- a print() is a statement that can throw.  MEASURED
    # this round by a test that drives a stdout which refuses every write:
    # before this change the decode line took the whole inbound dispatch down
    # with it, which is the one thing this lane promised it would never do.
    _say(echo, pickup_request_console_line(read))
    return read


# ---------------------------------------------------------------------------
# THE WHOLE INBOUND STEP, AS CODE RATHER THAN AS A PARAGRAPH
# ---------------------------------------------------------------------------
# WHY THIS FUNCTION EXISTS AT ALL, since the first draft of this module did
# not have it.  That draft published the branch -- the readiness check, the
# "if not accepted: return []", the order of the two calls -- as PROSE in
# MOB_PICKUP_REQUEST_WIRING, and exec'd only the two call lines in a test.
# An adversarial pass then mutated the prose: inverting the accepted check,
# deleting it, keying the branch on the outer id instead of the nested one,
# and emptying the whole string -- and the suite stayed GREEN through every
# one of them, because a paragraph is not executed.  It then sent the
# accepted body plus one trailing byte through the published branch as
# written-without-the-guard and got AttributeError on None, out of the
# inbound dispatch, unnamed.  Prose cannot carry a fail-closed contract, so
# the contract moved into this function, where the tests execute it and a
# mutation turns red.  What is left for the chief is one call.


@dataclass(frozen=True)
class PickupRequestOutcome:
    """What one inbound frame did.  Never an exception, always a name.

    ``handled`` is True only when an item actually moved into the bag.
    ``reason`` is ``ACCEPTED`` in that case and a named refusal otherwise --
    from this lane's own registry, or, unchanged and unwrapped, from the
    transaction lanes underneath.  ``delta`` is the (pc, frame) pair to send
    the claimant, and is None unless ``handled``.  ROUND ewq4js: the
    transaction composes TWO of them and this field carries the one that
    matches what else is in this reply -- see
    :func:`_the_delta_that_matches_the_floor`.  A caller sends this and reads
    nothing else; the choice is not the caller's.

    ``ground_after`` (round lh21ua) is the REMOVAL PUBLICATION: the (pc,
    frame) pairs that tell the client the taken object is gone, by publishing
    the scene's remaining rows without it (RE-082: a nonempty generation
    erases the keys it omits).  ~~It is ``()`` on every refusal~~ IS STRUCK,
    ROUND f4oh9y: a refusal that happens after a clean decode now carries the
    removal an EXPIRY SWEEP owed, when one is owed and the scene still has a
    row to compose from (:func:`_expiry_publication`, KA1A R307's seven
    ghost clicks).  The row the click ASKED for is still refused and is never
    in that generation -- it is gone, which is why it is owed.  A refusal
    before the decode, or with no ground cell, still carries ``()``.  It is
    also ``()`` when the
    taken row was the scene's LAST one -- the hole RE-208 is open on, where no
    known message removes one object and an empty generation is a client
    no-op by RE-082's static reading -- and ``()`` when the publication itself
    refused, which never undoes the pickup.

    ``ground_rows_left`` is how many rows the scene has after the take.
    ~~"``-1`` when nothing was taken: read WITH ``ground_after`` it separates
    'nothing left to say' (0, ()) from 'could not say it' (>0, ())"~~ IS
    STRUCK BEFORE IT SHIPPED (pf-adversary D7 of this round): THAT PAIR IS
    UNREACHABLE.  Every failure returns ``(-1, ())`` and a success returns
    empty frames only when ``rows_left`` is 0, so ``-1`` means "no
    publication was composed" and covers BOTH "nothing was taken" and "the
    publication itself refused".  What tells those two apart is the console
    line -- ``MOB_PICKUP_GROUND_REMOVAL_REFUSED`` is printed for the second
    and nothing at all for the first -- and ``handled``, which is False only
    for the first.  A caller must not read the count as a refusal reason.

    ROUND f4oh9y NARROWS THAT ONE MORE TIME rather than widening it: on a
    refusal carrying an expiry publication the count is that scene's
    remaining rows, so ``handled`` False no longer implies ``-1``.  What
    ``-1`` still means everywhere is "no generation was composed", and the
    console line still says which of the reasons it was.
    """

    handled: bool
    reason: str
    read: PickupRequestRead
    result: Any = None
    delta: Any = None
    ground_after: tuple = ()
    ground_rows_left: int = -1


def dispatch_inbound_pickup_request(
        legacy: Any, parsed: Any, store: Any, sid: Any, character_id: Any,
        bag_cell: Any, drop_ledger_cell: Any, identity: Any,
        x: Any, y: Any, z: Any, *, echo: bool = True
) -> PickupRequestOutcome:
    """THE ONE CALL for the inbound pickup branch.  Read, guard, transact.

    In order, and the order is the content:

      1. read the frame (this lane).  Not accepted -> return, no reply.
      2. READINESS GUARD.  A connection that has not selected a character
         has no bag cell, and a scene with no ground cell has nothing to
         claim from; both are None at the call site and neither is a wire
         problem.  Refused by their own names so an operator can tell "the
         client sent nonsense" from "the session was not ready".
      3. the transaction, unchanged and uncalled-into: precheck, dispatch,
         persist, exactly as the sibling lane publishes it.

    NEVER RAISES.  A refusal from the transaction lanes is caught HERE and
    returned by its own name, because this function sits directly under an
    inbound frame from a stranger: a listener that throws on one hands over
    the session.  Nothing is swallowed -- the reason string is the same one
    the transaction raised, and it is printed on the console line too.

    ``identity``, ``x``, ``y``, ``z`` are the claimant's own, out of
    authenticated session state, NEVER out of the request: the body carries
    seven bytes and neither of them is a position (RE-125 closed that
    question in the same words).
    """
    read = read_inbound_pickup_request(legacy, parsed, echo=echo)
    if not read.accepted or read.fields is None:
        return PickupRequestOutcome(False, read.reason, read)
    if bag_cell is None:
        return _refused_after_read(read, "session_has_no_bag_cell", echo)
    if drop_ledger_cell is None:
        return _refused_after_read(read, "session_has_no_ground_cell", echo)
    # THE WORLD DECIDES THE TAKE FIRST, round 59iqwi (pf-adversary D1, which
    # measured one drop becoming two items before this shape existed).  A row
    # that fell in this scene belongs to the world, so two logins standing
    # here can hold one row and each cell is authority over its own ledger
    # alone.  The claim is atomic and exactly one caller wins it; a caller
    # that loses is refused BY ITS OWN NAME, and a row the world has no
    # opinion about (never on its floor, or swept off it) is NOT refused --
    # the cell's own rules answer, exactly as they did before this round.
    claim = mob_ground_persistence.claim_for_pickup(
        drop_ledger_cell, read.fields.object_ref_u32)
    if claim.refused:
        return _refused_after_read(
            read, claim.reason, echo, legacy, drop_ledger_cell)
    try:
        result = mob_pickup_persist.pickup_and_persist(
            store, sid, character_id, bag_cell, drop_ledger_cell, legacy,
            identity, x, y, z, read.fields.object_ref_u32,
            read.fields.opaque_u8, echo=echo)
    except (mob_pickup.MobPickupContractError,
            mob_pickup_persist.MobPickupPersistError) as exc_named:
        exc = exc_named
        # THE REFUSAL THAT R307 MEASURED ARRIVES HERE.  A click on a row the
        # sweep already retired refuses ``drop_already_taken`` out of the
        # transaction, and until this round that was the end of it: the
        # client kept drawing a label nothing would ever answer for.  The
        # cell is passed so the refusal can carry what the SWEEP owes -- the
        # scene's remaining ground, which removes the ghost by omission.
        # THE CLAIM GOES BACK -- BUT ONLY IF THE TAKE DID NOT HAPPEN.
        # pf-adversary pass 2, D2, MEASURED with a store that raises on
        # ``commit_acquired_backpack_item``: the bag cell has already put
        # the item in the session's bag BEFORE ``persist_pickup`` runs, so a
        # refusal named ``write_failed_after_the_take`` describes a player who
        # is holding the object.  Re-flooring it there hands the next session
        # a second copy -- the duplication this whole claim layer exists to
        # end, arriving through the repair path.
        #
        # THE AMBIGUOUS NAME IS TREATED AS POST-TAKE ON PURPOSE:
        # ``cell_is_another_characters`` is raised in the precheck AND again
        # after the take, and the two are indistinguishable from here.  The
        # two mistakes are not symmetric -- keeping a row off the floor costs
        # one object nobody can pick up, re-flooring a taken one mints an
        # item -- so the tie goes to the cheaper failure.
        reason = str(exc.args[0])
        # The persist lane appends its own detail after a colon (``write_
        # failed_after_the_take: MOB_PICKUP_ROW_LOST ...``), the same split
        # ``runtime.py`` already takes to compose its event name.  Comparing
        # the whole string would silently never match, which is the direction
        # that mints an item.
        if reason.split(":")[0] not in POST_TAKE_REFUSALS:
            mob_ground_persistence.return_claim(claim)
        return _refused_after_read(
            read, reason, echo, legacy, drop_ledger_cell)
    except Exception:                            # noqa: BLE001 - see below
        # ANY OTHER ESCAPE GIVES THE ROW BACK BEFORE IT LEAVES (pf-adversary
        # pass 2, D3, MEASURED with a transaction raising ``RuntimeError``).
        # This function does not promise to swallow an unknown exception --
        # it never did, and turning one into a silent refusal would hide a
        # bug this lane needs to see -- but before this round an escape cost
        # a frame and touched nothing shared.  With a claim held it destroys
        # a world row AND records it taken, and the guard then refuses the
        # owner's own clicks (their cell still holds that very object) for
        # the row's whole remaining life: R307's unclickable ghost, rebuilt
        # by the guard meant to stop duplication.  The row goes back and the
        # exception carries on unchanged.
        mob_ground_persistence.return_claim(claim)
        raise
    rows_left, ground_after = _ground_after_the_take(
        legacy, drop_ledger_cell, result, echo)
    delta = _the_delta_that_matches_the_floor(
        result.outcome, ground_after, read.fields.object_ref_u32, echo)
    # THE DURABLE DOOR LEARNS THE ROW IS GONE, round 59iqwi.  The world's own
    # floor gave the row up at the claim above; what is left is the table, and
    # only once the take and its removal publication have both happened
    # (`COO-DECISION 2026-09-01T02:53+07:00` -- a row is removed when a
    # publisher has said so).  THE ROW COMES FROM THE TRANSACTION, never from
    # ``read.fields`` (pf-adversary D9, and round veby94's D7 one file over:
    # what the stranger asked for is not what was taken).  It cannot refuse a
    # click: the pickup has already succeeded by this line, the call never
    # raises, and its answer is not read.
    mob_ground_persistence.note_taken_in_the_durable_door(
        getattr(result.outcome, "drop", None), store=store)
    return PickupRequestOutcome(
        True, ACCEPTED, read, result, delta, ground_after, rows_left)


def _the_delta_that_matches_the_floor(
        outcome: Any, ground_after: Any, taken_key: int, echo: bool) -> Any:
    """Which of the two composed deltas this reply actually carries.

    ROUND ewq4js, and the shape is pf-adversary's correction of its first
    draft.  KEEPING THE FLOOR IS RIGHT ONLY WHEN SOMETHING IN THE SAME REPLY
    TAKES THE TAKEN ROW OFF IT.  Two conditions, both about what is really
    going out, and neither of them knowable inside the transaction:

      1. A removal generation was actually COMPOSED (``ground_after`` is not
         empty).  It is empty when the scene had no row left -- where the
         clearing delta is the truth and is the only thing that removes the
         last object's label ~~"in this project"~~ ON PURPOSE, IN THE SAME
         REPLY (pf-adversary D3 of this round: `mob_combat`'s own measured
         cadence table has three frames per non-lethal hit -- bar, dying,
         dead -- carrying derived mask 0x02, and every one of them clears the
         whole pool, last object included.  So the honest claim is about
         intent and timing, never about being alone) -- and when the
         publication REFUSED, where nothing else in this reply removes it
         either.
      2. ``runtime.py`` SENDS what this lane composes
         (:data:`GROUND_AFTER_CALL_SITE_STATUS`).  Until the chief's line
         lands, a kept floor would be a floor nobody ever reconciles: the
         player would keep seeing a label for an object already in their bag.
         The sibling round learned the same lesson one console token earlier.

    The first draft decided this inside the transaction from a row count
    taken before the take, and pf-adversary measured two ways to a permanent
    ghost with it: a row expiring between the count's sweep and the take's
    sweep (two separate acquisitions of the GROUND cell's lock -- the bag
    cell's lock does not span them), and a publication that refuses after a
    floor was kept for it.  Both end here instead: no publication, no kept
    floor, whatever the count said.
    """
    keep = bool(ground_after) and GROUND_AFTER_CALL_SITE_STATUS == "sent"
    delta = outcome.delta_floor_kept if keep else outcome.delta
    _say(echo, "%s key=0x%X" % (
        # READ OFF THE BYTES that are about to leave, never off ``keep``:
        # the composer falls back to v141's own frame when the preserve
        # composer refuses, and a line that reported the intention would tell
        # an operator the floor was kept on the exact frame that cleared it.
        MOB_PICKUP_DELTA_GROUND_KEPT_TOKEN
        if delta is not None
        and delta[0].endswith(mob_pickup.DELTA_PC_PRESERVE_SUFFIX_PIN)
        else MOB_PICKUP_DELTA_GROUND_CLEARED_TOKEN,
        taken_key))
    return delta


def _ground_after_the_take(
        legacy: Any, drop_ledger_cell: Any, transacted: Any, echo: bool
) -> tuple:
    """The removal publication for a pickup that already succeeded.

    ROUND lh21ua, COO-DECISION 2026-09-02T02:53+07:00 (the removal publisher)
    in the order COO-DECISION 2026-09-02T10:44+07:00 set: carrier composer,
    THEN this, then the bag delta.

    AFTER THE TRANSACTION, NEVER INSIDE IT, and the order is the content: the
    item is in the bag and in the database by the time this runs, so nothing
    here can cost a player their item.  The reverse order -- compose the
    floor, then transact -- would compose a generation for a take that had
    not happened yet, which is the one thing
    ``DropLedgerCell.frames_after_a_row_left`` refuses by name.

    IT CANNOT RAISE, and that is not politeness: this sits under
    :func:`dispatch_inbound_pickup_request`, whose never-raises promise is
    what lets the chief's branch sit under a stranger's frame.  A publication
    that cannot be composed costs a redraw, and the console says which of the
    three things happened.  ``Exception`` is caught rather than the two named
    contract errors, because ``legacy`` is a module this lane does not own:
    ``AttributeError`` out of a moved serializer is exactly the case that
    must not reach the session.

    THE KEY COMES OUT OF THE TRANSACTION, NOT OUT OF THE REQUEST, and that is
    pf-adversary's D7 on this round: the first draft passed
    ``read.fields.object_ref_u32`` -- what the STRANGER asked for -- and two
    mutants that passed a constant 0 or the unrelated ``opaque_u8`` byte
    survived the whole suite, because the composed frames do not depend on
    the key at all and no test read it back.  ``transacted.outcome.drop`` is
    the row the ground cell actually handed over, so the console line now
    names what left the ground rather than what was asked for, and a test
    reads that number back out.  The read happens INSIDE the try for the same
    never-raises reason as everything else here.

    ROUND veby94: THE KEY AND THE COUNT ARE ABOUT TWO DIFFERENT GROUNDS AND
    THE LINE NOW SAYS SO (the chief's letter 2026-09-02T15:35+07:00, item
    (b), paid in this lane's file).  ``take`` cuts by key across the whole
    register; this publisher speaks for ``current_scene`` only.  No byte
    changes -- see :data:`MOB_PICKUP_GROUND_REMOVAL_CROSS_SCENE_TOKEN` for
    what is measured, what is merely guarded, and why the guard is worth its
    six lines anyway.
    """
    try:
        taken_key = transacted.outcome.drop.drop_key
        rows_left, frames = drop_ledger_cell.frames_after_a_row_left(
            legacy, taken_key)
    except Exception as exc:                     # noqa: BLE001 - see docstring
        _say(echo, "%s reason=%s" % (
            MOB_PICKUP_GROUND_REMOVAL_REFUSED_TOKEN,
            mob_pickup_persist.console_safe(str(
                exc.args[0] if exc.args else type(exc).__name__))[:120]))
        return -1, ()
    # ROUND veby94, the chief's item (b).  Both names, on every line, in the
    # same order every time -- ``taken_scene`` is where the row that LEFT was
    # standing, ``scene`` is the ground ``rows_left`` and the frames are
    # about -- and then ``same_ground``, which is the VERDICT rather than the
    # evidence (pf-adversary D3b: the comparison below is casefolded, the two
    # words printed are raw, and a real dispatch prints ``bg0001`` next to
    # ``Bg0001`` on one same-ground take).  ``console_safe`` is belt and
    # braces rather than a guard on a reachable case: ``mob_loot`` validates
    # both names ASCII, printable and whitespace-free before either can be
    # stored -- a mutant deleting both calls survives the suite.
    #
    # !! EVERY READ FOR THIS LINE IS BELOW THE PUBLICATION AND IN ITS OWN
    # GUARD, and pf-adversary D1 is why the rule is written twice: the first
    # draft of this round read ``drop.scene`` up in the block above, where a
    # raising ``.scene`` turns a successful publication into ``(-1, ())`` --
    # measured, and it changes the BYTES (an empty ``ground_after`` flips
    # ``_the_delta_that_matches_the_floor`` to the clearing delta and drops
    # the removal actions).  A NAME FOR THE CONSOLE MAY NEVER COST A FRAME.
    try:
        taken_scene = getattr(transacted.outcome.drop, "scene", None)
    except Exception:                            # noqa: BLE001 - see above
        taken_scene = None
    try:
        published_scene = drop_ledger_cell.current_scene
    except Exception:                            # noqa: BLE001 - see above
        published_scene = None
    # THREE STATES, NOT TWO: the same ground, a different ground, and a name
    # that could not be read at all.  ``same_ground=?`` is the third, and it
    # exists because printing 0 for an unknown would be the same class of
    # false line this whole block removes.  ``None`` on failure, and the
    # comparison itself is guarded: every value here comes from outside this
    # file, and a name for the console may never raise into a listener
    # thread.
    try:
        if taken_scene is None or published_scene is None:
            same_ground = None
        else:
            same_ground = (str(taken_scene).casefold()
                           == str(published_scene).casefold())
    except Exception:                            # noqa: BLE001 - see above
        same_ground = None
    scenes = "taken_scene=%s scene=%s same_ground=%s" % (
        _scene_word(taken_scene), _scene_word(published_scene),
        "?" if same_ground is None else ("1" if same_ground else "0"))
    if frames:
        _say(echo, "%s key=0x%X %s rows_left=%d frames=%d" % (
            MOB_PICKUP_GROUND_REMOVAL_PUBLISHED_TOKEN
            if GROUND_AFTER_CALL_SITE_STATUS == "sent"
            else MOB_PICKUP_GROUND_REMOVAL_COMPOSED_TOKEN,
            taken_key, scenes, rows_left, len(frames)))
    else:
        # rows_left == 0 is the only way a composed publication is empty:
        # frames_after_a_row_left raises rather than returning () for every
        # other case.  RE-208 is open on this one.
        _say(echo, "%s key=0x%X %s rows_left=%d" % (
            MOB_PICKUP_GROUND_REMOVAL_HELD_TOKEN, taken_key, scenes,
            rows_left))
    # AND THE DISAGREEMENT ITSELF GETS A NAME, for the operator who greps
    # instead of reading.  CASEFOLDED, and that is the property the whole
    # token rests on rather than a nicety (pf-adversary D3 killed a mutant
    # that dropped it): ``bg0001`` and ``Bg0001`` are ONE scene to
    # ``DropLedger.for_scene``, so a case-only difference is an ordinary
    # pickup, and a token that fired on it would fire on every pickup the day
    # one roster module spells a folder differently from another -- which is
    # exactly the noise this token must not become.  BOTH NAMES MUST BE
    # KNOWN: an unreadable name is not a disagreement.
    if same_ground is False:
        _say(echo, "%s key=0x%X %s rows_left_is_about=%s" % (
            MOB_PICKUP_GROUND_REMOVAL_CROSS_SCENE_TOKEN, taken_key, scenes,
            _scene_word(published_scene)))
    return rows_left, tuple(frames)


def _scene_word(value: Any) -> str:
    """One scene name, safe for a cp874 console and for a hostile __str__.

    ROUND veby94.  Every value this composes is a name from outside this
    file, and the function it prints from may not raise into a v141 listener
    thread.  ``console_safe`` covers the encoding; this covers the rest --
    an object whose ``__str__`` raises costs the WORD, never the frames.
    """
    try:
        return mob_pickup_persist.console_safe(str(value))[:32]
    except Exception:                            # noqa: BLE001 - see docstring
        return "scene_unreadable"


def _say(echo: bool, line: str) -> bool:
    """Print one line, and LOSE THE LINE rather than the frames if it fails.

    The bridge console is cp874 with ``errors='strict'``, so a ``print`` is a
    statement that can raise -- and this one sits inside a function whose
    whole promise is that it does not.  ``console_safe`` already makes the
    text ASCII; this covers what it cannot: a closed, redirected or broken
    stdout, which is a property of the process and not of the string.  The
    sibling lane learned this on its own PRESERVE fall back in round jysbar:
    a console that cannot be written to costs a LINE, never a FRAME.

    Returns whether the line was printed, so a test can prove the loss is the
    line rather than assume it.
    """
    if not echo:
        return False
    try:
        print(line)
    except Exception:                            # noqa: BLE001 - see docstring
        return False
    return True


#: The refusal reasons that mean "the row you clicked is gone from THIS
#: ground" -- the only ones an expiry publication may ride.  pf-adversary of
#: round f4oh9y: the cell's scene only advances on a kill or a GM warp, so a
#: player who WALKED across a boundary can click a stale label of the scene
#: they left; publishing "the cell's scene" on that refusal would send scene
#: A's ground to a client standing in scene B.  ``drop_is_in_another_scene``
#: is that refusal by name and is deliberately NOT here.  This narrows the
#: exposure; it does not close it, because a server that never learns about a
#: walked crossing cannot -- see the CORE-REQUEST letter, which says so to the
#: chief before he lands the line that makes these frames travel.
EXPIRY_PUBLICATION_REASONS = (
    "drop_already_taken",
    "drop_expired",
    "drop_not_in_ledger",
    # ROUND 59iqwi (pf-adversary pass 2, D8).  The world-claim refusal belongs
    # on this list for exactly the reason the other three are on it: it fires
    # when another session carried the object away, which is precisely when
    # THIS player's cell still holds the row and their client is still drawing
    # its label.  Without the publication the loser keeps a ghost that refuses
    # every click until their own sweep retires it -- the R307 shape, arriving
    # through a refusal invented this round.
    mob_ground_persistence.REFUSE_TAKEN_BY_ANOTHER_SESSION,
)

#: The refusals that mean THE TAKE ALREADY HAPPENED, so a claimed row must not
#: go back on the world's floor (pf-adversary pass 2, D2).  Named from the
#: sibling lane's own constants rather than typed out, so a rename there is a
#: NameError here instead of a silent duplication path.
POST_TAKE_REFUSALS = (
    mob_pickup_persist.REFUSE_WRITE_FAILED_AFTER_THE_TAKE,
    mob_pickup_persist.REFUSE_CELL_IS_ANOTHER_CHARACTERS,
)


def _expiry_publication(
        legacy: Any, drop_ledger_cell: Any, reason: Any, echo: bool
) -> tuple:
    """The removal a SWEEP owes, composed onto the click that found it gone.

    ``(rows_left, frames)``, and ``(-1, ())`` whenever nothing was composed --
    the same shape and the same convention as :func:`_ground_after_the_take`.

    WHY A REFUSED CLICK IS THE RIGHT EVENT, and it is measured rather than
    argued.  KA1A R307 (2026-09-03, the owner at her own client): two drops
    past their 120 s deadline, seven clicks, seven
    ``MOB_PICKUP_REQUEST_REFUSED reason=drop_already_taken``.  The rows had
    been swept off the server's ground inside somebody's earlier read, and
    this server publishes a ground generation on a kill, on a successful
    pickup and on a scene crossing -- so nothing was ever going to tell the
    client, and the labels stayed on her floor as ghosts that refuse every
    click.  The click IS the event: once per player action, only when a sweep
    has really retired a row that no generation has covered since.  That is
    the distinction the 2026-08-26 refusal of ``DROP_REFRESH_MS`` draws --
    an event, not a timer.

    !! AND IT DOES NOT ANSWER R307's OWN SHAPE, said here first because a
    reader who stops after the paragraph above will believe it does: those
    two drops were that scene's whole ground, so the sweep left it empty and
    ``DropLedgerCell.frames_after_rows_expired`` has nothing nonempty to
    compose.  Seven clicks there still send nothing.  What this covers is a
    scene with a row still standing.

    ONLY ON THE REFUSALS THAT MEAN "GONE FROM THIS GROUND"
    (:data:`EXPIRY_PUBLICATION_REASONS`).  A refusal that means "you are not
    where that row is" must not answer with this scene's ground.

    IT CANNOT RAISE, for the same reason as every other helper under
    :func:`dispatch_inbound_pickup_request`: this sits under an inbound frame
    from a stranger and a listener that throws hands over the session.  A
    publication that cannot be composed costs a redraw and says so.

    IT NEVER CHANGES THE REFUSAL.  The click was refused before this ran and
    is still refused after it: nothing here can turn a "gone" into an item,
    and the reason string is untouched.
    """
    if drop_ledger_cell is None:
        return -1, ()
    if str(reason) not in EXPIRY_PUBLICATION_REASONS:
        return -1, ()
    try:
        expired, rows_left, frames = (
            drop_ledger_cell.frames_after_rows_expired(
                legacy, EXPIRY_PUBLICATION_CALL_SITE_STATUS == "sent"))
    except Exception as exc:                     # noqa: BLE001 - see docstring
        _say(echo, "%s reason=%s" % (
            MOB_PICKUP_GROUND_EXPIRY_REFUSED_TOKEN,
            mob_pickup_persist.console_safe(str(
                exc.args[0] if exc.args else type(exc).__name__))[:120]))
        return -1, ()
    if not expired:
        # Nothing was owed.  NO LINE ON PURPOSE: this runs on every refused
        # click, and a token printed on the ordinary case is a token a
        # grader learns to ignore on the interesting one.
        return -1, ()
    if not frames:
        # HELD, AND AT MOST ONCE PER DEBT.  The design holds this debt for
        # ever when the scene emptied, so an unconditional line here is one
        # console line per click for the rest of the session (measured 7/7 in
        # R307's own shape).  The cell answers whether this exact held set
        # has been announced already.
        try:
            fresh = drop_ledger_cell.note_held_debt_announced()
        except Exception:                        # noqa: BLE001 - never raise
            fresh = False
        if fresh:
            _say(echo, "%s expired=%d rows_left=%d" % (
                MOB_PICKUP_GROUND_EXPIRY_HELD_TOKEN, len(expired), rows_left))
        return -1, ()
    _say(echo, "%s expired=%d rows_left=%d frames=%d" % (
        (MOB_PICKUP_GROUND_EXPIRY_PUBLISHED_TOKEN
         if EXPIRY_PUBLICATION_CALL_SITE_STATUS == "sent"
         else MOB_PICKUP_GROUND_EXPIRY_COMPOSED_TOKEN),
        len(expired), rows_left, len(frames)))
    return rows_left, frames


def _refused_after_read(
        read: PickupRequestRead, reason: str, echo: bool,
        legacy: Any = None, drop_ledger_cell: Any = None,
) -> PickupRequestOutcome:
    """One console line per refusal that happens AFTER a clean decode.

    The decode line is already printed by then and says the frame was fine;
    without this second line an operator watching the console would see an
    accepted read and no outcome at all.

    ROUND f4oh9y: a refusal may now carry a GROUND GENERATION -- not for the
    row the click asked for, which is refused either way, but for rows an
    EXPIRY SWEEP retired with nobody told.  See :func:`_expiry_publication`.
    The two arguments default to ``None`` so a caller that has no cell (or no
    serializer) refuses exactly as it did before this round.
    """
    _say(echo, "%s reason=%s" % (MOB_PICKUP_REQUEST_REFUSED_TOKEN, reason))
    rows_left, frames = _expiry_publication(
        legacy, drop_ledger_cell, reason, echo)
    return PickupRequestOutcome(
        False, reason, read, ground_after=frames, ground_rows_left=rows_left)


# ---------------------------------------------------------------------------
# WHAT THIS LANE ASKED THE CHIEF FOR, AND WHAT HE LANDED.  ~~THE REQUEST TO
# THE CHIEF.  Not a call site -- see NONCLAIM 5~~ IS STRUCK, round 91tlkk:
# there IS a call site and it is in runtime.py.  Authorized by COO-DECISION
# 20260902_0541 (see NONCLAIM 7 and PICKUP_REQUEST_WIRING_STATUS, the value
# the AUTHORIZATION half of the note below defers to); landed per
# PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS, the value the LANDING half
# defers to.  Two different questions, two different constants, and this
# lane just spent a day proving what happens when one of them is missing:
# "approved" was read as "present" by nobody and as "absent" by everybody,
# because the only word in the file was the approval one.
# ---------------------------------------------------------------------------

# The line, as a string, so a test can EXECUTE it instead of a reader
# checking it by eye.  An adversarial pass has proved on this lane twice
# that a wiring note which is only searched for substrings will happily
# carry a swapped argument order for days; this string is exec'd against
# real fixture objects bound under exactly these names.
MOB_PICKUP_REQUEST_HEADLINE_CALL = (
    "mob_pickup_request.dispatch_inbound_pickup_request("
    "legacy, parsed, store, sid, character_id, bag_cell, drop_ledger_cell, "
    "identity, x, y, z)"
)

# The read half on its own, for a call site that wants to look before it
# transacts.  It is the same read the headline call makes internally.
MOB_PICKUP_REQUEST_READ_ONLY_CALL = (
    "mob_pickup_request.read_inbound_pickup_request(legacy, parsed)"
)

#: One sentence per registered word; the note picks by CALLING
#: :func:`wiring_headline`.  A FUNCTION AND NOT A LOOKUP AT IMPORT TIME
#: (pf-adversary D1/D2/D3 of round 91tlkk, all three measured GREEN on the
#: first draft): that draft selected the sentence at import, so the module
#: only ever held the SELECTED STRING.  Every branch but today's was dead
#: code no test could reach, the whole composition could be replaced by a
#: hand-typed literal with a green suite, and deleting a key -- also green --
#: turned the recovery the failing test PRESCRIBES ("lower the constant")
#: into a ``KeyError`` at import that made the file uncollectable.
_WIRING_HEADLINES = {
    "requested_not_landed": "THIS BRANCH IS CLEARED TO LAND AND HAS NOT "
                            "LANDED.  The block below is a REQUEST.",
    "wired_by_name_lookup": "THIS BRANCH IS REACHED ONLY BY A NAME LOOKUP: "
                            "somebody fetches the entry point by string.  "
                            "That is evidence somebody FETCHES it, never "
                            "that a frame goes through it.",
    "landed": "THIS BRANCH HAS LANDED (see "
              "PICKUP_REQUEST_DISPATCH_CALL_SITE_LANDED).  The block below "
              "is no longer a request: it is the RECORD of what runtime.py "
              "must keep containing, and tests/test_mob_pickup_request.py "
              "compares the landed call against it argument for argument.",
}


def wiring_headline(status: str) -> str:
    """The note's head sentence for one registered status word.

    IT CANNOT RAISE, for the reason D3 measured rather than for politeness:
    this runs at import time, and the one moment it would blow up is the
    moment somebody is halfway through changing the vocabulary -- which is
    exactly when a reader needs the file to still import so they can read
    what it says.  A word this table does not know is REPORTED as unknown,
    which a human notices, instead of a traceback that hides the note.
    """
    return _WIRING_HEADLINES.get(
        status,
        "THE LANDING STATUS OF THIS BRANCH IS NOT A REGISTERED WORD (%r).  "
        "Read nothing into it: this note cannot say whether the branch "
        "landed." % (status,))


MOB_PICKUP_REQUEST_WIRING = (
    "STATUS: " + PICKUP_REQUEST_WIRING_STATUS + " / "
    + PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS + ".  "
    + wiring_headline(PICKUP_REQUEST_DISPATCH_CALL_SITE_STATUS)
    + "  " + PICKUP_REQUEST_WIRING_APPROVAL + ".  What each former "
    "blocker was and what lifted it is kept, struck through, in "
    "PICKUP_REQUEST_WIRING_BLOCKERS.\n"
    "  WRITE THIS FACT AT THE CALL SITE -- 0541 makes it a CONDITION of the "
    "exception it grants, not advice, and this lane's test enforces it the "
    "moment runtime.py names this module: the id 0x4543 is NOW OBSERVED on "
    "the wire (R303, 46 inbound frames, 2 completed takes), which is the "
    "wording COO-DECISION 20260905_0249 item 2 approved in place of the "
    "struck ~~'has NEVER been observed on any wire'~~.  A comment carrying "
    "the words 'now observed on the wire (r303' (any casing) must sit "
    "within ten lines of the "
    "call, or tests/test_mob_pickup_request.py goes red on the gate and the "
    "PR carrying the call site cannot merge.  ~~The branch is landed on a "
    "static-image reading, so if the id is wrong the branch never fires and "
    "every frame keeps today's behaviour.~~ IS STRUCK, round 91tlkk "
    "(pf-adversary D11): runtime.py struck that same sentence at its own "
    "call site after measuring it FALSE, and this note went on carrying it.  "
    "The branch claims on the NESTED ID ALONE, before any shape check, so a "
    "wrong id means this branch SWALLOWS whatever really wears 0x4543 -- "
    "measured on a flagless boot as one frame of deferral each for the world "
    "census, the server-online line and the music control (latched, so a "
    "deferral and not a loss).  The cost of a wrong id is small and bounded.  "
    "It is not zero, and WHO WITHDRAWS THIS BRANCH if 0x4543 turns out to be "
    "another live message is still an open question with no named owner "
    "(raised with COO in the R300 handback).\n"
    "  WHERE: runtime.py, in the inbound runtime-request dispatch, as a "
    "PRODUCTION branch -- no scenario object in the condition, no flag, no "
    "allowlisted profile -- keyed on the NESTED vital id and never on the "
    "outer one (the outer runtime ids are the two gameplay/login values; "
    "keying on this id at the top level is a layer error):\n"
    "  if nested_id == mob_pickup_request.PICKUP_REQUEST_VITAL_ID:\n"
    "      outcome = " + MOB_PICKUP_REQUEST_HEADLINE_CALL + "\n"
    "      if outcome.delta is None:\n"
    "          return []   # no reply, exactly as an unknown vital gets\n"
    "      then send outcome.delta -- the (pc, frame) pair the transaction "
    "already composed and validated -- ~~and nothing else~~.\n"
    "  ROUND lh21ua ADDS EXACTLY ONE THING TO SEND, and it is the only line "
    "this lane asks the chief for this round (COO-DECISION 2026-09-02T02:53"
    "+07:00, the removal publisher; ordered second by COO-DECISION "
    "2026-09-02T10:44+07:00).  After the delta, send the ground publication "
    "the same outcome carries -- the scene's REMAINING rows, which is what "
    "removes the taken object from the client's list (RE-082: a nonempty "
    "generation erases the keys it omits).  It is composed inside the "
    "never-raises call, it is ALREADY EMPTY whenever there is nothing to "
    "send, so the call site needs no condition of its own:\n"
    "      out = [(\"MOB_PICKUP_REQUEST_DELTA\", pc, frame, 0.0)]\n"
    "      out += [(\"MOB_PICKUP_GROUND_AFTER\", gpc, gframe, 0.0)\n"
    "              for gpc, gframe in outcome.ground_after]\n"
    "      return out\n"
    "  ORDER MATTERS ONE WAY ONLY: the ground publication must not be sent "
    "BEFORE the delta, because the delta is the answer to the click and the "
    "floor is the consequence of it.  Both carry delay 0.0 and ride the same "
    "return, so nothing else about the ordering is this lane's to promise.\n"
    "  WITHOUT THAT LINE the item is in the bag and in the database and the "
    "LABEL IS STILL ON THE FLOOR until the next kill or the next scene entry "
    "publishes that ground -- a wait with no upper bound, which is what P-1 "
    "is about.\n"
    "  ONE CALL, AND THE GUARDS ARE INSIDE IT.  The readiness check (no "
    "bag cell before character select, no ground cell for the scene), the "
    "refusal path, the order of precheck/dispatch/persist and the catch of "
    "every named transaction refusal are all in the function, not in this "
    "paragraph.  An earlier draft published them here as prose; an "
    "adversarial pass inverted, deleted and emptied that prose and the "
    "suite stayed green, then crashed the branch with one trailing byte.\n"
    "  WHERE THE NAMES COME FROM, so none of them is invented at the call "
    "site: 'store' and 'sid' are the session's own; 'character_id' is the "
    "selected character; 'bag_cell' is the cell the bag registry handed "
    "back at character select (already wired) or None before that; "
    "'drop_ledger_cell' is the scene's ONE ground cell; 'identity, x, y, z' "
    "are the claimant's own actor identity and position as this session "
    "already knows them -- NOT anything out of the request, which carries "
    "no position at all.\n"
    "  WHAT THIS BRANCH MUST NOT DO: COMPOSE a frame of its own, delete a "
    "ground object, or write a row of its own.  ~~'the floating label "
    "expires by itself and taking the row through the cell stops the ground "
    "lane re-emitting it'~~ IS STRUCK, round lh21ua: not re-emitting a row "
    "is not the same as removing it.  WHAT IS MEASURED, on this side of the "
    "wire, is that the transaction lanes compose ONE thing, the bag delta, "
    "and it carries no ground key at all -- so until this round a successful "
    "pickup said nothing about that floor until the next kill or scene entry "
    "(tests/test_mob_pickup_request.py::TheGroundAfterTheTakeTests::"
    "test_the_transaction_alone_says_nothing_about_the_floor drives the real "
    "transaction and reads what came out).  "
    "WHAT THE CLIENT DOES WITH A LABEL NOBODY WITHDREW IS "
    "NOT MEASURED -- RE-082 says a nonempty generation erases the keys it "
    "omits, which is why the fix takes this shape.  The publication above is "
    "the "
    "answer, and the branch only FORWARDS it -- every byte of it is composed "
    "in this lane, behind the same never-raises promise.\n"
    "  WHAT 'NEVER RAISES' COVERS AND WHAT IT DOES NOT, round lh21ua, "
    "because pf-adversary MEASURED the gap rather than argued it: every "
    "console line in this lane and in the two transaction lanes now goes "
    "through mob_pickup.say, which loses the LINE and never the ROW.  "
    "Before that fix, a stdout that refuses every write (the cp874 "
    "console is one bad byte from being one) raised out of the bare "
    "print BETWEEN the take and the database write: the drop had left "
    "the ground, no row had been written, and the exception unwound into "
    "the connection listener -- a DESTROYED item, not a failed pickup.  "
    "The promise now holds for every line this lane prints; what it "
    "still cannot cover is a caller that raises AFTER this returns.\n"
    "  WHY THE SIBLING LANE'S OWN HEADLINE IS NOT THE ONE PUBLISHED HERE: "
    "COO-DECISION 20260902_0254 named the dispatch-only call, and this lane "
    "publishes the persist-and-dispatch one instead, because the "
    "transaction lane itself measured that following the dispatch-only "
    "recipe destroys a player's item whenever the session's bag cell has "
    "drifted from the database.  The substitution is deliberate, it is "
    "named here rather than made silently, it was put in front of COO by "
    "the ASK-COO letter of round h6bl53, and COO-DECISION 20260902_0541 "
    "item 2 ENDORSED it: the dispatch-only recipe is not to be followed.\n"
    "  IF THE VITAL ID IS WRONG (NONCLAIM 1) this branch simply never "
    "fires and every frame keeps today's fall-through behavior."
)
