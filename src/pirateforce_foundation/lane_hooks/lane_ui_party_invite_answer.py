"""LANE-UI: the first frame this lane ever puts BACK on the wire.

WHAT A PLAYER CAN DO THAT THEY COULD NOT YESTERDAY.  Send a party
invite from the shipped client UI and have the server answer it.  Until
this module, every one of the eight ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH``
vitals was counted, logged by a report-only hook, and answered with an
empty list -- the player pressed a button and the server said nothing,
by construction (``ui_dispatch.py``'s own module docstring).  This
module registers the first answerer, for ``PartyInviteVital``
(``0x37B1``), and the server replies.

WHY ANSWERING WITH THE SAME ID IS AN ANSWER AND NOT A GUESS.  RE-312
(pf_bridge ``notes_to_chief/20260908_1038_RE-312-RESULT-*`` and its
RESULT-2 at ``20260908_1105_*``) settled the question this lane had been
blocked on -- "what does the client DO when it RECEIVES one of these
eight" -- from the shipped image:

* all eight classes are ``INBOUND_YES``: each carries a real inbound
  handler in vtable slot ``+0x1C`` (RESULT-1 section 1 reads the slot
  map off three vtables and cross-checks it against ``RE-303``, which
  had already disassembled ``TeleportCheckVital``'s ``+0x1C`` and
  watched it open a window on screen);
* the party family's handler is ``0x0062EA70``: it looks up the
  ``"PartyModule_Client"`` window, type-checks it, and hands the
  decoded vital to ``0x0062D0E0``;
* RESULT-2 pinned the caller -- ``0x005F38B2``, ``call eax`` with
  ``eax = [vtable+0x1C]``, inside the batch dispatch loop at
  ``0x005F3840`` -- so the slot is reached by the ordinary receive
  path, not by a route nobody walks.

WHAT IT SENDS: THE PLAYER'S OWN BYTES, AND NOTHING ELSE.  The payload
is decoded with ``ui_party_wire``'s pinned field shape and then
RE-ENCODED, and the reply is refused unless the re-encoding is
byte-identical to what arrived.  So every byte that leaves is a byte
the client itself just produced, in the order it produced them.  This
lane invents no field value, and it cannot: letter ``20260904_1120``
nonclaim (2) still stands -- the three fields have a proven wire shape
and zero proven MEANING, and RE-312's own nonclaim 5 repeats it
(``proven_semantics`` UNKNOWN).  Naming ``field2_u64`` "the invited
player" and routing the invite to them would be the guess this project
forbids; ``/warp x y`` (pf_bridge letter 1744) is what guessing bytes
costs.
!! ONE BYTE THAT LEAVES IS NOT THE PLAYER'S, AND pf-adversary (round
xqxadg, D3) is why this paragraph now says so.  The reply is
``make_runtime_vitals([(vital_id, version, payload)])``.  Only
``payload`` is the client's.  ``version`` is the module constant
````ui_party_wire.PARTY_INVITE_VITAL_VERSION````, whose own header calls it an UNPROVEN DEFAULT --
no capture has ever pinned a version byte for this class -- and the
inbound version the client sent is parsed by ``runtime.py`` and NOT
passed to ``ui_dispatch.answer()``, so if a client sends anything but
zero the server answers with zero anyway.  Worse, the letter this
module cites says that byte is CHECKED: ``RE-312`` RESULT-2 reads
``0x005F3EF4`` comparing the u8 after the id against ``[obj+0x10]`` and
logging ``0xE0000031`` on a mismatch, and nobody has read ``[obj+0x10]``
for this class.  That sentence used to end "a mutation of the constant
leaves the suite green because the constant sits on both sides of every
assertion", and pf-adversary (round 1gc6hl, D-G) is why it no longer
says so: the outbound registry pins the reviewed version SET as a
literal, and ``TheReviewedShapesArePinnedTests`` pins the registry's own
numbers against literals a test file owns, so mutating the constant now
turns the suite red.  What is still true is the part that matters: the
version byte is a REVIEWED guess (``ui_dispatch``'s outbound registry
pins the set to what ships), not a derived value, and closing it needs
the inbound version handed to ``answer()`` -- a ``runtime.py`` change,
filed, not taken here.

WHO CAN PRESS THIS BUTTON: SOMEBODY WHO LOGGED IN -- AND THAT IS NEW
(pf-adversary D7, paid round 1gc6hl).  This paragraph used to end
"named because it is measured, not because it is fixed", and it is now
fixed: ``ui_dispatch.answer()`` refuses before any answerer runs unless
the session holds a selected character, the same precondition
``runtime.py`` already applies to in-game frames.  So a peer that never
logged in reaches neither these bytes nor an allowance.

AND THE ALLOWANCE IS NOW THE SESSION'S, NOT THE SERVER'S (pf-adversary
D-B, paid round vy1m79).  This module used to keep its own process-wide
counter; the sentence above used to end "one logged-in player can still
spend the whole process budget", and that was measured, not theoretical
-- session A answered 32 invites and session B, a different account on a
different socket, got nothing until the server was restarted.  The
counter is gone from this file.  ``ui_dispatch`` keeps it instead, keyed
by the session's identity (``SESSION_ANSWER_BUDGET``), because the seam
is where a session is visible and a frame storm runs between the server
and ONE socket.  A refusal costs nothing: the seam charges at its send
point, and only for a batch that carries bytes.


SO WHAT DOES THE PLAYER SEE?  THIS MODULE DOES NOT CLAIM TO KNOW.  The
static evidence says the client has a live handler that will run and
that it addresses the party window.  Whether that draws a dialog, a
list row, or nothing visible is a question about pixels, and this
project answers those on a screen: the GT ticket filed with this round
is what decides it.  This module's claim is bounded to what it can
prove -- the server now answers, with bytes the client sent, on the
production path with no flag to flip.

THE STORM GUARD IS PROCESS-WIDE, AND THAT IS A LIMITATION, NAMED.  If a
client were ever to answer this answer with the same vital, the two
would trade frames forever.  Nothing measured says it does (a UI module
window handler needs a human click; RE-312 traced the handler to a
window lookup, not to a send), but the cost of being wrong is a frame
storm on a live socket, so there is a budget.  It counts answers for
the whole process, NOT per session, because ``ui_dispatch`` deliberately
hands an answerer no session identity at all (its ``_SESSION_VIEW_FIELDS``
is the empty tuple, and pf-adversary rounds 3 and 4 are why).  A
per-session budget therefore needs a reviewed widening of that tuple,
which is a separate edit with its own argument; this one caps the blast
radius today without asking for any reach.
"""
from __future__ import annotations

import sys

from . import console_safe
from .. import ui_dispatch
from .. import ui_party_wire as wire

production_allowed = True

LABEL = "UI_PARTY_INVITE_ANSWERED"



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


def answer_party_invite(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``PartyInviteVital`` with the bytes it arrived as.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.PARTY_INVITE_VITAL_ID:
        _say("UI_PARTY_INVITE_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_PARTY_INVITE_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_party_invite_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_PARTY_INVITE_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed.  ``decode_*`` in this project returns fields for the bytes
    # it consumed; re-encoding and comparing is what turns "these bytes
    # parsed" into "these are exactly the bytes that parsed".  A payload
    # with an unexplained trailer, or any field this lane's model rounds,
    # fails here and is answered with nothing.
    reencoded = wire.encode_party_invite_payload(fields)
    # AND IT IS DEAD CODE TODAY, SAID OUT LOUD (pf-adversary D5).  The
    # decoder above calls ``require_exhausted``, and the encoder is its
    # exact inverse for every payload it accepts: measured over 4,000
    # structurally valid payloads in this module's own test file, every
    # one that decoded re-encoded byte for byte, so the refusal below has
    # never fired through the real decoder.  It stays because it is the
    # guard for the decoder this project will have LATER, not the one it
    # has today, and the test file reaches it by making the encoder
    # disagree -- so the comparison cannot be deleted or inverted under a
    # green suite.
    if reencoded != payload:
        _say(
            "UI_PARTY_INVITE_REFUSED reason=not_byte_exact in=%d out=%d"
            " bytes_out=0" % (len(payload), len(reencoded))
        )
        return []
    # THE SEAM'S OWN BUDGET, READ BEFORE SPENDING OURS (pf-adversary
    # round xqxadg, D8).  ``ui_dispatch`` refuses a payload past the
    # reviewed budget for this label, and the refusal happens AFTER this
    # module has already counted an answer -- so a client sending
    # well-formed invites with a very long name could burn the whole
    # process allowance with zero bytes ever reaching anybody.  The
    # registry is the authority on that number; this module asks it
    # rather than keeping a second copy that can drift.
    shape = ui_dispatch.outbound_shape(LABEL)
    # A MISSING ROW IS A REFUSAL, NOT A CHECK THAT DID NOT APPLY
    # (pf-adversary round 1gc6hl, D-F).  This read `if shape is not None
    # and len(...) > ...`, so if the registry key were ever renamed this
    # module would SKIP its own budget check and go on to die inside
    # `ui_dispatch._compose` instead -- a guard that disappears exactly
    # when the thing it guards has gone missing.  The registry is the
    # authority on whether this label may leave at all, so no row means
    # no answer, said in its own token.
    if shape is None:
        _say(
            "UI_PARTY_INVITE_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    if len(reencoded) > shape.max_payload_bytes:
        _say(
            "UI_PARTY_INVITE_REFUSED reason=over_reviewed_payload_budget"
            " len=%d budget=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    # NO COUNTER HERE ANY MORE (pf-adversary D-B).  The seam charges the
    # SESSION at its send point, so this module neither counts nor knows
    # who is asking -- and it stays that way: the fix bought a per-player
    # bound without widening `_SESSION_VIEW_FIELDS` by one field.
    _say("UI_PARTY_INVITE_ANSWER len=%d" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.PARTY_INVITE_VITAL_ID,
            version=wire.PARTY_INVITE_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]

# THE ARMING SAMPLE, DECLARED BY THE LANE THAT OWNS THE CLASS
# (round ly40b5).  ``ui_party_invite_answer_headless.py`` is the runner
# that produces the ``HEADLESS_PROOF:`` token every attended ticket on
# this seam needs (``NOW.md``, PANYA ``0159``).  It used to hard-code one
# class, so two answered buttons had no token and no ticket; making it
# name all three would have put this family's vocabulary into a
# top-level Foundation module, which ``tests/test_npc_interaction_wire``
# guards against by design -- and taking the exemption that guard offers
# would have been buying a green with an allowlist entry, which
# ``NOW.md`` ``2050`` forbids outright.
#
# So the runner asks instead of naming: the lane that owns a class is the
# only place that already legitimately spells it, and it is also the only
# place that knows what a well-formed frame of that class looks like.
# A new answerer becomes measurable by declaring these two names, and
# ``tests/test_ui_dispatch.py`` makes an answerer that declares neither a
# red test rather than a button that quietly cannot be proven.
ARMING_TOKEN = "UI_PARTY_INVITE_ANSWER_ARMED"


def arming_sample():
    """``(vital_id, version, payload)`` for a well-formed frame of this class.

    Called only by the arming runner.  It is a FUNCTION, not a module
    constant, so no boot pays for building a sample frame it will never
    send.
    """
    return (
        wire.PARTY_INVITE_VITAL_ID,
        wire.PARTY_INVITE_VITAL_VERSION,
        wire.encode_party_invite_payload(
            wire.PartyInviteFields(
                field1_u8=1,
                field2_u64=0x1122334455667788,
                field3_wstring="Panya",
            )
        ),
    )




# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS.
# ``ui_dispatch`` is safe to import at module level here today because it
# no longer imports ``lane_hooks`` at module level itself (the circular
# half-built import its own header comment records was the reason that
# was ever a problem).  A refused registration is not an exception: the
# seam returns False and names the reason on stderr, and this module then
# simply never answers -- which is the shipping state, not a crash in
# discovery.
ui_dispatch.register_answerer(
    wire.PARTY_INVITE_VITAL_ID, answer_party_invite
)
