"""LANE-UI: the second button on this branch the server answers.

WHAT A PLAYER CAN DO THAT THEY COULD NOT BEFORE THIS MODULE.  Send a
TRADE invite from the shipped client UI and have the server answer it.
The round before this one made the party-invite button the first of the
eight ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH`` vitals to get a frame back;
the other seven still answered with an empty list.  This module takes
the second one, ``TradeInviteVital`` (``0x3700``).

WHY THIS ONE NEEDED NO NEW REVERSING.  ``RE-312`` BUILD_IMPACT 2
(pf_bridge ``notes_to_chief/20260908_1038_RE-312-RESULT-*``) says
``PartyInviteVital`` and ``TradeInviteVital`` share an encoder --
``u8 + u64 + tagged wstring``, the same tags in the same order, byte for
byte.  Measured again in this round rather than taken on faith: the two
encoders, given the same three field values, produce the same 26 bytes.
And RESULT-1 counted BOTH classes among the eight ``INBOUND_YES``: each
carries a live inbound handler in vtable slot ``+0x1C``, and RESULT-2
pinned the caller at ``0x005F38B2`` inside the batch dispatch loop, so
the slot is reached by the ordinary receive path.  Answering with the
same id is therefore an answer, not a guess -- the same argument the
party module makes, resting on the same two letters.

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_trade_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be:
letter ``20260904_1120`` nonclaim (2) and ``RE-312`` nonclaim 5 both
stand, ``proven_semantics`` is UNKNOWN, and ``ui_trade_wire``'s own
header is careful to say the two classes are kept as separate types
because nothing proves they share a MEANING -- only a shape.  This
module inherits that care: it does not treat a trade invite as a party
invite, it only observes that the same decode/encode pair round-trips
it.

!! ONE BYTE THAT LEAVES IS NOT THE PLAYER'S, AND pf-adversary (round
xqxadg, D3) is why this paragraph says so.  The reply is
``make_runtime_vitals([(vital_id, version, payload)])``.  Only
``payload`` is the client's.  ``version`` is the module constant
``ui_trade_wire.TRADE_INVITE_VITAL_VERSION``, whose own header calls it
an UNPROVEN DEFAULT, and the inbound version the client sent is parsed
by ``runtime.py`` and NOT passed to ``ui_dispatch.answer()`` -- so if a
client sends anything but zero the server answers with zero anyway.
Worse, the letter this module cites says that byte is CHECKED:
``RE-312`` RESULT-2 reads ``0x005F3EF4`` comparing the u8 after the id
against ``[obj+0x10]`` and logging ``0xE0000031`` on a mismatch, and
nobody has read ``[obj+0x10]`` for this class.  So the version byte is
a REVIEWED guess (``ui_dispatch``'s outbound registry pins the set to
what ships), not a derived value, and closing it needs the inbound
version handed to ``answer()`` -- a ``runtime.py`` change, filed, not
taken here.

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

WHAT THE PLAYER SEES IS STILL A QUESTION FOR A SCREEN.  Static evidence
says the client has a live handler that will run.  Whether it draws a
dialog, a row, or nothing is a question about pixels, and this project
answers those with an attended ticket, not with a docstring.

THE BUDGET IS NO LONGER THIS MODULE'S AT ALL, and the paragraph that
stood here is worth keeping as a record of how a true sentence produced
a wrong design.  It read: two answerers sharing one counter would let a
storm on either vital silence the other, and a per-session budget would
need a reviewed widening of ``_SESSION_VIEW_FIELDS`` because the seam
hands an answerer no session identity.  Both halves were true; the
conclusion -- therefore a process-wide counter per module -- was not,
because it only ever asked what a LANE can see.  ``ui_dispatch`` sees
the session, so it holds the allowance -- per session AND per vital.
!! THE FIRST DRAFT OF THIS PARAGRAPH SAID "through the label registry"
AND WAS FALSE.  The registry separates SHAPES, not allowances, and
pf-adversary (round vy1m79, D1) measured what that cost: 32 trade
answers on one session, then the party button on that same session
returned nothing.  The allowance is now keyed by (session, vital id),
which is the property the two separate module counters used to have and
this file had claimed to keep without keeping it.

WHY THIS IS A SEPARATE FILE AND NOT A SHARED FACTORY.  A factory that
built both answerers would put the body that runs in one module and the
registration in another, and ``ui_dispatch``'s gate reads the flag of
every module on the registration stack for exactly that reason
(COO-DECISION ``20260908_1142`` item 7, D-zeta: the witness is the
module that defines the body that RUNS).  Two short, self-contained
answerers each carrying their own flag is the shape that gate was built
for.  ``tests/test_lane_ui_trade_invite_answer.py`` pins the two modules
refusing on the same six grounds, so the duplication cannot drift
silently.
"""
from __future__ import annotations

import sys

from . import console_safe
from .. import ui_dispatch
from .. import ui_trade_wire as wire

production_allowed = True

LABEL = "UI_TRADE_INVITE_ANSWERED"



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


def answer_trade_invite(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``TradeInviteVital`` with the bytes it arrived as.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.TRADE_INVITE_VITAL_ID:
        _say("UI_TRADE_INVITE_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_TRADE_INVITE_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_trade_invite_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_TRADE_INVITE_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed.  ``decode_*`` returns fields for the bytes it consumed;
    # re-encoding and comparing is what turns "these bytes parsed" into
    # "these are exactly the bytes that parsed".  A payload with an
    # unexplained trailer, or any field this lane's model rounds, fails
    # here and is answered with nothing.
    reencoded = wire.encode_trade_invite_payload(fields)
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
            "UI_TRADE_INVITE_REFUSED reason=not_byte_exact in=%d out=%d"
            " bytes_out=0" % (len(payload), len(reencoded))
        )
        return []
    # THE SEAM'S OWN BUDGET, READ BEFORE SPENDING OURS (pf-adversary
    # round xqxadg, D8).  ``ui_dispatch`` refuses a payload past the
    # reviewed budget for this label, and that refusal lands AFTER this
    # module has already counted an answer -- so well-formed invites
    # with a very long name could burn the whole process allowance with
    # zero bytes ever reaching anybody.  The registry is the authority
    # on that number; this module asks it instead of keeping a second
    # copy that can drift.
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
            "UI_TRADE_INVITE_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    if len(reencoded) > shape.max_payload_bytes:
        _say(
            "UI_TRADE_INVITE_REFUSED reason=over_reviewed_payload_budget"
            " len=%d budget=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    # NO COUNTER HERE ANY MORE (pf-adversary D-B).  The seam charges the
    # SESSION at its send point, so this module neither counts nor knows
    # who is asking -- and it stays that way: the fix bought a per-player
    # bound without widening `_SESSION_VIEW_FIELDS` by one field.
    _say("UI_TRADE_INVITE_ANSWER len=%d" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.TRADE_INVITE_VITAL_ID,
            version=wire.TRADE_INVITE_VITAL_VERSION,
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
ARMING_TOKEN = "UI_TRADE_INVITE_ANSWER_ARMED"


def arming_sample():
    """``(vital_id, version, payload)`` for a well-formed frame of this class.

    Called only by the arming runner.  It is a FUNCTION, not a module
    constant, so no boot pays for building a sample frame it will never
    send.
    """
    return (
        wire.TRADE_INVITE_VITAL_ID,
        wire.TRADE_INVITE_VITAL_VERSION,
        wire.encode_trade_invite_payload(
            wire.TradeInviteFields(
                field1_u8=1,
                field2_u64=0x1122334455667788,
                field3_wstring="Panya",
            )
        ),
    )




# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape, and the same header note, as the party answerer beside
# it.  A refused registration is not an exception: the seam returns False
# and names the reason on stderr, and this module then simply never
# answers, which is the shipping state and not a crash in discovery.
ui_dispatch.register_answerer(
    wire.TRADE_INVITE_VITAL_ID, answer_trade_invite
)
