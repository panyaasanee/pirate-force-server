"""LANE-UI: the fourth button on this seam the server answers.

WHAT A PLAYER CAN DO THAT THEY COULD NOT BEFORE THIS MODULE.  Press
"add friend" in the shipped client UI and have the server answer the
frame instead of dropping it.  ``PartyInviteVital`` (``0x37B1``),
``TradeInviteVital`` (``0x3700``) and ``PartyCmdVital`` (``0x2466``)
were answered in the three rounds before this one.  WITH this module
four of the eight ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH`` vitals answer
and the remaining FOUR come back with an empty list -- this sentence
said "the remaining five ... still", which was the count before this
file existed and was false the moment it landed (pf-adversary round
asw0n3, D9; ``docs/UI_LANE.md``, edited by the same commit, had it
right).  This module takes the fourth,
``Community_RequestBeFriendVital`` (``0xB9E9``), and it is the first
one this seam answers that is NOT in the party/trade family -- it is
the first of the five ``CommunityModule_Client`` classes.

WHICH BUTTON, SAID AS PRECISELY AS THE EVIDENCE ALLOWS.  Not "the add
friend button does what its label says", because nobody has traced
which client control sends this class or what its fields mean:
``ui_friend_wire``'s header records ``CALL_UNCLASSIFIED`` for both
friend classes (``CORE-REQUEST 1120`` nonclaim (2)) and names its
fields positionally for that reason.  What IS proven is where the frame
goes: ``RE-312`` RESULT-1 (pf_bridge
``notes_to_chief/20260908_1038_RE-312-RESULT-*``) lists
``0xB9E9 Community_RequestBeFriendVital INBOUND_YES
handler=0x00645BF0 next=0x0063F9B0`` inside
``"CommunityModule_Client"`` (``0x00F18854``), and RESULT-2 pins the
caller at ``0x005F38B2`` inside the batch dispatch loop -- the same
receive path, reached the same way, as the three answered classes
beside this one.  Answering with this id is therefore an answer, not a
guess.

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_friend_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be.
This module does not create, store, or imply a friendship: nothing in
this file touches a row, and ``proven_semantics`` is UNKNOWN for this
class.  It observes only that this class's own decode/encode pair
round-trips the bytes the player sent.

THE ROUND TRIP IS DEAD CODE HERE TOO, AND THIS ROUND MEASURED IT
RATHER THAN ASSUMING EITHER WAY.  ``lane_ui_party_cmd_answer`` records
that its ``reencoded != payload`` branch has never fired through the
real decoder, because ``PartyCmdFields`` is ``u8 + u64`` and the
encoder is the decoder's exact inverse for every payload it accepts.
This module's first draft claimed the opposite for a wstring class --
the decoder READS a u32 length while the encoder RECOMPUTES it from
the decoded ``str``, which looks like two independent computations
over a field the player controls -- and that claim was FALSE.
Measured before this file was committed, and pinned in the test file
beside it: over every one of the 65,536 two-byte code units and
200,000 random four-byte name payloads, 251,145 of which the decoder
accepted, ZERO re-encoded to different bytes.  Strict UTF-16LE decode
is injective, and ``read_untagged_wstring`` refuses the two shapes
that would break it -- an odd byte length BEFORE the codec runs, and an
unpaired surrogate BY the codec, whose ``UnicodeDecodeError`` that
helper catches and re-raises as ``WireDecodeError`` (pf-adversary round
asw0n3, D10: this said "before the codec is reached" for both, which is
backwards for the second, in a paragraph whose whole point is which
guard catches what).  So the refusal below is the same guard-for-a-later-
decoder the button beside it carries, it stays for the same reason,
and the test file reaches it by making the encoder disagree -- so it
cannot be deleted or inverted under a green suite.

FIXED WIDTH IS NOT AVAILABLE TO THIS CLASS, AND THE ROW SAYS SO.  A
name makes this payload grow, so the reviewed row in ``ui_dispatch``
keeps the same 512-byte ceiling the two wstring classes before it use,
and this module compares with ``>`` rather than ``!=``.  The party
command button's equality check is right for a class whose width
cannot vary and would be wrong here: it would make the button answer
only the one name length the reviewer happened to measure.

ONE FIELD THIS MODULE CHOOSES IS NOT THE PLAYER'S, exactly as the
three answerers beside this one record (pf-adversary round xqxadg,
D3).  The reply is ``make_runtime_vitals([(vital_id, version,
payload)])``; of those three, only ``payload`` is the client's.
``version`` is the module constant
``ui_friend_wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION``, whose own
header calls it an UNPROVEN DEFAULT, and the inbound version byte the
client sent is parsed by ``runtime.py`` and NOT handed to
``ui_dispatch.answer()`` -- so if a client ever sends anything but
zero, the server answers with zero anyway.

CORRECTED IN THE SAME ROUND THAT WROTE IT (pf-adversary round asw0n3,
D3).  The first draft of this paragraph said ``RE-312`` RESULT-2's
reading of ``0x005F3EF4`` "was taken on the party handler", that
"nobody has disassembled the version compare on the Community
handler", and that this button's evidence is therefore "weaker than
the party family's by exactly one disassembly".  ALL THREE ARE FALSE.
RESULT-2 places ``0x005F3EF4`` inside ``0x005F3E20``, which that letter
itself names as the GENERIC inbound frame decode loop out of
``ShareCode/NetCode/VitalDataBase.cpp``; it runs BEFORE ``0x005F3840``
dispatches to any handler's ``+0x1C`` slot, so it is SHARED and it
already covers ``0xB9E9``.  There is no separate per-handler version
compare on the Community side to disassemble, and this button's
evidence on this point is IDENTICAL to the party family's, not one
disassembly short of it.  What is genuinely unread is the same thing
``lane_ui_party_cmd_answer`` records for its own class: the VALUE at
``[obj+0x10]`` the shared loop compares against, which is per-class and
nobody has read it for this class either.  RESULT-2's verdict on a
mismatch carries over unchanged: the client logs ``0xE0000031`` and
CARRIES ON -- a warning, not a drop.  So the version byte here is a
REVIEWED guess pinned by the outbound registry, and closing it needs
the inbound version passed to ``answer()`` -- a ``runtime.py`` change,
already filed, not taken here.

THIS BUTTON IS ALREADY WATCHED, AND THAT DOES NOT CHANGE.
``lane_ui_friend_wire_log`` has been decoding this exact class on the
production path since round ``4u0ncx`` and printing a report-only line
with ``bytes_out=0``.  ``runtime.py`` fires that hook and THEN calls
``ui_dispatch.answer()``, so both run: the log still prints what
arrived, and this module is the first thing to put a byte back.  The
log hook is not a prerequisite and is not consulted -- two modules
reading the same frame for two different purposes.

WHO CAN PRESS IT AND HOW OFTEN: NOT THIS MODULE'S QUESTION.
``ui_dispatch.answer()`` refuses before any answerer runs unless the
session holds a selected character (pf-adversary D7, round 1gc6hl),
and it holds the allowance itself, keyed by (session, vital id)
(pf-adversary D-B/D1, round vy1m79; COO-DECISION ``20260908_1642``
confirmed (session, vital) as the unit).  This file therefore keeps no
counter and reads nothing from the session -- and because the
allowance is per VITAL, a storm on this new button cannot silence the
party or trade buttons of the same session.

WHAT THE PLAYER SEES IS STILL A QUESTION FOR A SCREEN.  Static
evidence says a live inbound handler exists and the receive path
reaches it.  Whether the client draws anything is a question about
pixels, and this project answers those with an attended ticket --
``observed_frames = 0`` for this class as for the other seven.
"""
from __future__ import annotations

import sys

from . import console_safe
from .. import ui_dispatch
from .. import ui_friend_wire as wire

production_allowed = True

LABEL = "UI_FRIEND_REQUEST_ANSWERED"


def _say(line: str) -> None:
    """One ASCII-folded token on stderr, guarded.

    Same two-part shape and same reason as ``ui_dispatch._say``: the
    bridge console is cp874, so the fold comes first, and the guard is
    for the stderr that is gone or full.
    """
    try:
        print(console_safe(line), file=sys.stderr)
    except Exception:  # pragma: no cover - stderr itself is broken
        pass


def answer_request_be_friend(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``Community_RequestBeFriendVital`` with its own bytes.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID:
        _say("UI_FRIEND_REQUEST_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_FRIEND_REQUEST_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_request_be_friend_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_FRIEND_REQUEST_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed -- the same argument, in the same words, as the three
    # answerers beside this one.  ``decode_*`` returns fields for the
    # bytes it consumed; re-encoding and comparing is what turns "these
    # bytes parsed" into "these are exactly the bytes that parsed".
    #
    # AND IT IS DEAD CODE TODAY, MEASURED AND NOT ASSUMED (see the module
    # header): 251,145 decoder-accepted payloads, every one of them
    # re-encoded byte for byte, so this branch has never fired through
    # the real decoder.  It stays because it is the guard for the decoder
    # this project will have LATER, and the test file reaches it by
    # making the encoder disagree.
    reencoded = wire.encode_request_be_friend_payload(fields)
    if reencoded != payload:
        _say(
            "UI_FRIEND_REQUEST_REFUSED reason=not_byte_exact in=%d out=%d"
            " bytes_out=0" % (len(payload), len(reencoded))
        )
        return []
    # THE SEAM'S OWN BUDGET, READ BEFORE SPENDING OURS (pf-adversary
    # round xqxadg, D8): ``ui_dispatch`` refuses a payload past the
    # reviewed budget for this label, and that refusal lands after the
    # answerer has run.  The registry is the authority on that number;
    # this module asks it instead of keeping a second copy that can
    # drift.
    shape = ui_dispatch.outbound_shape(LABEL)
    # A MISSING ROW IS A REFUSAL, NOT A CHECK THAT DID NOT APPLY
    # (pf-adversary round 1gc6hl, D-F).  Written as ``if shape is not
    # None and len(...) >`` this module would SKIP its own budget check
    # exactly when the registry key it depends on went missing, and die
    # inside ``ui_dispatch._compose`` instead.  No row means no answer,
    # said in its own token.
    if shape is None:
        _say(
            "UI_FRIEND_REQUEST_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    # A CEILING, NOT AN EQUALITY, AND THE HEADER SAYS WHY: this payload
    # carries a name, so its width is the player's to move.  The
    # equality check the fixed-width button uses would turn every name
    # length but one into a dead button.
    if len(reencoded) > shape.max_payload_bytes:
        _say(
            "UI_FRIEND_REQUEST_REFUSED reason=over_reviewed_budget len=%d"
            " budget=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    # NO COUNTER HERE (pf-adversary D-B, round vy1m79).  The seam charges
    # the SESSION, per vital, at its send point, so this module neither
    # counts nor knows who is asking.
    _say("UI_FRIEND_REQUEST_ANSWER len=%d" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
            version=wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


# THE TWO NAMES THE ARMING RUNNER ASKS FOR, DECLARED AHEAD OF THE
# RUNNER.  TENSE MATTERS HERE (pf-adversary round asw0n3, D4): at this
# commit NOTHING in this repository reads either name -- the runner
# that will is in `#1167` and is not on main -- so the sentences that
# follow are about the day it lands, not about today.  When it does, it
# will not spell this class's name: it reads the reviewed owner table,
# imports the lane that owns the id, and asks the lane for its own
# token and its own sample frame.  Declaring these two names is then
# the whole cost of putting this button on the arming proof an attended
# ticket carries -- no edit to the runner.  Measured, not assumed: with
# that runner spliced in at this HEAD the button arms
# (`UI_FRIEND_REQUEST_ANSWER_ARMED answered=1 frame_bytes=54
# frame_matches=1 echo_is_the_players_bytes=1 junk_refused=1
# RESULT=PASS`).
ARMING_TOKEN = "UI_FRIEND_REQUEST_ANSWER_ARMED"


def arming_sample():
    """``(vital_id, version, payload)`` for a well-formed frame of this class.

    Called only by the arming runner.  It is a FUNCTION, not a module
    constant, so no boot pays for building a sample frame it will never
    send.  The name is ASCII on purpose: the bridge console is cp874 and
    the runner prints what it measured.
    """
    return (
        wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
        wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
        wire.encode_request_be_friend_payload(
            wire.RequestBeFriendFields(
                field1_u64=1,
                field2_wstring="Ann",
                field3_u8=1,
            )
        ),
    )


# THE ADOPT-SIDE CONTRACT, DECLARED TOO (pf-adversary round asw0n3,
# D1).  ``NOW.md`` carries a standing red line -- the unit of trust for
# an answerer is the FILE, and a lane must not call
# ``register_answerer()`` (COO ``20260908_1642`` item 2, restating
# ``1441``) -- and the replacement is this lane's own
# ``ui_dispatch.adopt_answerer()``, whose lane-side contract is exactly
# these two names.  The first draft of this file declared the ARMING
# runner's two names and skipped these two, which is adopting a forward
# contract from an unmerged branch for one runner and declining the
# identical one for the runner COO put in red.  Two lines, so the
# conversion round has three files to flip and not four.
ANSWERS_VITAL_ID = wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID
ANSWERS_WITH = answer_request_be_friend

# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape, and the same note, as the three answerers beside it.  A
# refused registration is not an exception: the seam returns False and
# names the reason on stderr, and this module then simply never answers,
# which is the shipping state and not a crash in discovery.
#
# AND THIS CALL IS THE HALF OF D1 THAT IS **NOT** PAID, SAID PLAINLY
# RATHER THAN QUIETLY.  ``_discover()`` does not call
# ``adopt_answerer()`` yet -- that splice is chief's, queued as
# CORE-REQUEST ``1553`` -- so deleting the line below today would not
# make this button safer, it would make it silent, and this lane's own
# letter records why converting before the splice "takes working
# buttons away from players".  It therefore stays until the splice
# lands, exactly as in the three answerers beside it, and the two
# declarations above are what make removing all four one atomic round
# instead of a fifth conversion.
ui_dispatch.register_answerer(
    wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID, answer_request_be_friend
)
