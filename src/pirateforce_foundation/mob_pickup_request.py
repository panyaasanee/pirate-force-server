"""LANE-B / MOB-PICKUP-REQUEST-001: the click that asks for a ground drop,
read in PRODUCTION -- no flag, no scenario, no opt-in object.

WHY THIS FILE EXISTS.  ``NOW.md`` P-1 is "a dropped thing stays on the floor
long enough to be seen AND PICKED UP".  The take-it transaction has been
finished and tested for days (one call composes the claim, takes the row
through the ground cell, places it in the bag slot and composes the client
delta; a sibling module adds the database write around it).  NOTHING CALLS
IT, and COO-DECISION 20260902_0254 named the reason exactly: in production
mode no code in ``src/`` could read one byte of an inbound pickup request.
A real client that clicks a ground object today has its frame fall through
to the frozen v141 default path, unread and unlogged.  This module is that
missing half and only that half: it READS the request.  It grants nothing,
takes nothing off the ground, writes no row and sends no byte.

THE SPLIT, IN ONE LINE.  wire bytes -> (object_ref_u32, opaque_u8) is this
file's own work.  (object_ref_u32, opaque_u8) -> item in a bag slot + delta
bytes belongs to the two transaction modules, which this file CALLS and does
not reimplement one line of.  What is left for ``runtime.py`` -- the chief's
file -- is a single call: see ``MOB_PICKUP_REQUEST_WIRING`` at the bottom,
which is a REQUEST, never a call site.  It was HELD; COO-DECISION
20260902_0541 cleared it to land and NOTHING HAS LANDED YET (NONCLAIM 5,
NONCLAIM 7).

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
  1. THE VITAL ID HAS NEVER BEEN SEEN ON ANY WIRE, AND THE NEGATIVE IS
     BOUNDED.  ~~"0x4543 comes from the validated project name-hash only"~~
     IS STRUCK, and so is RE-125's premise behind it: the Codex checkpoint
     of 2026-08-31 (P06-DROP-TRANSPORT, item 2) closed 0x4543 as the
     ASSIGNED NESTED RUNTIME TYPE ID on the successful 519-stub
     registration path (519 names / 519 ids / collision 0, IMAGE layer),
     and forbade using it as a TOP-LEVEL opcode -- which is why this lane
     keys on the NESTED id and nothing else.  What stands unchanged: no
     capture holds a frame of it in either direction, and that negative is
     bounded rather than absolute -- 0 among the nested frames the corpus
     audit actually reached, with a residue of fail-closed frames never
     parsed at all.  Being always-on does not
     upgrade that by one inch.  WHAT ALWAYS-ON ACTUALLY COSTS, stated
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
  5. NOTHING HERE IS EVIDENCE THAT A PLAYER PICKED ANYTHING UP.  No call
     site exists yet: ``MOB_PICKUP_REQUEST_WIRING`` is a request to the
     chief, now cleared to land by COO-DECISION 20260902_0541 but still not
     landed by anyone.  Until that line is in ``runtime.py``, this module
     decodes nothing on any running server, and no round may report P-1's
     "picked up" half as done on the strength of this file.
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

from . import mob_pickup
from . import mob_pickup_persist


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

# DERIVED, NEVER OBSERVED -- see NONCLAIM 1.  Kept as a constant precisely so
# the day a capture contradicts it, one line changes here and the wiring line
# in the chief's file does not.
PICKUP_REQUEST_VITAL_ID = 0x4543
PICKUP_REQUEST_VITAL_ID_PROVENANCE = (
    "assigned_nested_runtime_type_id_image_layer_never_observed_on_wire"
)
#: The capture negative is BOUNDED, not absolute: zero among the nested
#: frames the corpus audit reached, with a residue of fail-closed frames it
#: never parsed.  Carried as a constant so a reader who only skims the
#: constants still meets the qualifier.
PICKUP_REQUEST_CAPTURE_STATUS = (
    "not_observed_among_parsed_nested_frames_bounded_negative"
)
#: THE HOLD IS LIFTED.  Round h6bl53 published this ask as HELD because
#: RE-125, COO-DECISION 20260901_0245 and GT-146 forbade a production call
#: site keyed on this id while COO-DECISION 20260902_0254 and 20260902_0348
#: ordered one, and a lane does not settle a contradiction between its own
#: instructions by writing code.  COO-DECISION 20260902_0541 answers the
#: ASK-COO letter of that round and takes option 1: the two prohibitions are
#: WITHDRAWN and the exception is granted for exactly the line this module
#: publishes.  The FACT inside RE-125 is untouched and is still true - this
#: id has never been seen on any wire - and 0541 requires it to be written at
#: the call site, which the ask below does.
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
PICKUP_REQUEST_RUNTIME_ID_SLOT_VA = 0x0108202C      # zero on disk

# OUR ACCEPTANCE DESIGN -- see NONCLAIM 2.
PICKUP_REQUEST_VITAL_VERSION = 0
PICKUP_REQUEST_VITAL_VERSION_PROVENANCE = (
    "our_acceptance_design_no_capture_or_static_pin_fixes_it"
)
PICKUP_REQUEST_OUTER_VERSION = 0
PICKUP_REQUEST_OUTER_MASK = 0x02
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
    "vital_count_not_one",
    "not_the_pickup_vital",
    "wrong_vital_version",
    "payload_not_bytes",
    "truncated_payload",
    "wrong_object_ref_tag",
    "wrong_opaque_u8_tag",
    "trailing_bytes_after_object",
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

    "Never raises" is enforced rather than promised: reading a field off the
    parse object, and reading the outer id off the legacy module, are both
    done inside the guard, because an adversarial pass showed that a parse
    object whose attribute access or comparison raises walks straight out of
    this function otherwise.
    """
    try:
        if not hasattr(legacy, "GSCN_RUNTIME_PROTOCOL_REQ"):
            return "legacy_module_missing_fields"
        for name in _ENVELOPE_FIELDS:
            # hasattr only swallows AttributeError: a property that raises
            # anything else walks out of the presence check itself, which
            # is where an adversarial pass put a KeyError.  The whole read
            # of the parse object therefore sits inside this guard.
            if not hasattr(parsed, name):
                return "parse_object_missing_fields"
        return _classify_fields(legacy, parsed)
    except MobPickupRequestRefused as exc:
        return exc.reason
    except Exception:
        # A parse object that raises while being read is not our frame and
        # is certainly not a grant.  It is named, not propagated.
        return "parse_object_refused_to_answer"


def _classify_fields(legacy: Any, parsed: Any) -> str:
    if parsed.nested_id != PICKUP_REQUEST_VITAL_ID:
        return "not_the_pickup_vital"
    if parsed.outer_id != legacy.GSCN_RUNTIME_PROTOCOL_REQ:
        return "not_a_runtime_protocol_req"
    if parsed.outer_version != PICKUP_REQUEST_OUTER_VERSION:
        return "wrong_outer_version"
    if parsed.outer_mask != PICKUP_REQUEST_OUTER_MASK:
        return "wrong_outer_mask"
    if parsed.vital_count != PICKUP_REQUEST_VITAL_COUNT:
        return "vital_count_not_one"
    if parsed.nested_version != PICKUP_REQUEST_VITAL_VERSION:
        return "wrong_vital_version"
    try:
        decode_pickup_request_payload(parsed.nested_payload)
    except MobPickupRequestRefused as exc:
        return exc.reason
    return ACCEPTED


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
    reason = classify_pickup_request(legacy, parsed)
    if reason == ACCEPTED:
        # ONE read of the payload, not two: the accepted body is decoded
        # from the snapshot taken here, so a parse object that answers
        # differently the second time cannot turn an accepted verdict into
        # an exception out of this function (adversarial pass, round
        # h6bl53).
        try:
            snapshot = bytes(parsed.nested_payload)
            fields = decode_pickup_request_payload(snapshot)
        except MobPickupRequestRefused as exc:
            read = PickupRequestRead(False, exc.reason, None)
        except Exception:
            read = PickupRequestRead(
                False, "parse_object_refused_to_answer", None)
        else:
            read = PickupRequestRead(True, ACCEPTED, fields)
    else:
        if reason not in MOB_PICKUP_REQUEST_REFUSAL_REASONS:
            raise RuntimeError(
                "MOB-PICKUP-REQUEST-001 classifier returned an "
                "unregistered reason")
        read = PickupRequestRead(False, reason, None)
    if echo:
        print(pickup_request_console_line(read))
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
    the claimant, and is None unless ``handled``.
    """

    handled: bool
    reason: str
    read: PickupRequestRead
    result: Any = None
    delta: Any = None


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
    try:
        result = mob_pickup_persist.pickup_and_persist(
            store, sid, character_id, bag_cell, drop_ledger_cell, legacy,
            identity, x, y, z, read.fields.object_ref_u32,
            read.fields.opaque_u8, echo=echo)
    except (mob_pickup.MobPickupContractError,
            mob_pickup_persist.MobPickupPersistError) as exc:
        return _refused_after_read(read, str(exc.args[0]), echo)
    return PickupRequestOutcome(
        True, ACCEPTED, read, result, result.outcome.delta)


def _refused_after_read(
        read: PickupRequestRead, reason: str, echo: bool
) -> PickupRequestOutcome:
    """One console line per refusal that happens AFTER a clean decode.

    The decode line is already printed by then and says the frame was fine;
    without this second line an operator watching the console would see an
    accepted read and no outcome at all.
    """
    if echo:
        print("%s reason=%s" % (MOB_PICKUP_REQUEST_REFUSED_TOKEN, reason))
    return PickupRequestOutcome(False, reason, read)


# ---------------------------------------------------------------------------
# THE REQUEST TO THE CHIEF.  Not a call site -- see NONCLAIM 5 -- and no
# longer held: authorized by COO-DECISION 20260902_0541, see NONCLAIM 7 and
# PICKUP_REQUEST_WIRING_STATUS, which is the value this comment defers to.
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

MOB_PICKUP_REQUEST_WIRING = (
    "STATUS: " + PICKUP_REQUEST_WIRING_STATUS + ".  THIS BRANCH IS CLEARED "
    "TO LAND.  " + PICKUP_REQUEST_WIRING_APPROVAL + ".  What each former "
    "blocker was and what lifted it is kept, struck through, in "
    "PICKUP_REQUEST_WIRING_BLOCKERS.\n"
    "  WRITE THIS FACT AT THE CALL SITE -- 0541 makes it a CONDITION of the "
    "exception it grants, not advice, and this lane's test enforces it the "
    "moment runtime.py names this module: the id 0x4543 has NEVER been "
    "observed on any wire.  A comment carrying the words 'never been "
    "observed on any wire' (any casing) must sit within ten lines of the "
    "call, or tests/test_mob_pickup_request.py goes red on the gate and the "
    "PR carrying the call site cannot merge.  The branch is landed on a "
    "static-image reading, so if the id is wrong the branch never fires and "
    "every frame keeps today's behaviour.\n"
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
    "already composed and validated -- and nothing else.\n"
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
    "  WHAT THIS BRANCH MUST NOT DO: answer the request with a frame of "
    "its own, delete a ground object (the floating label expires by itself "
    "and taking the row through the cell stops the ground lane re-emitting "
    "it), or write a row of its own.\n"
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
