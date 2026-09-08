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

WHO CAN PRESS THIS BUTTON: ANYONE WITH A SOCKET (pf-adversary D7).  The
eight-vital branch sits ABOVE ``runtime.py``'s login and start-game
guards, so a session that never logged in gets an answer, and with a
PROCESS-WIDE budget an unauthenticated peer can replay one captured
payload until the allowance is spent and the button is silent for every
legitimate player until restart.  Named because it is measured, not
because it is fixed.

WHAT THE PLAYER SEES IS STILL A QUESTION FOR A SCREEN.  Static evidence
says the client has a live handler that will run.  Whether it draws a
dialog, a row, or nothing is a question about pixels, and this project
answers those with an attended ticket, not with a docstring.

THE BUDGET IS THIS MODULE'S OWN.  ``ANSWER_BUDGET`` is a separate
process-wide counter from the party module's: two answerers sharing one
counter would let a storm on either vital silence the other, which is a
coupling nobody asked for.  Process-wide and not per session, for the
reason ``ui_dispatch`` gives: the seam deliberately hands an answerer no
session identity at all (``_SESSION_VIEW_FIELDS`` is empty), so a
per-session budget would need a reviewed widening of that tuple.

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

# Answers per process before this module stops answering.  Same number
# and same reason as the party answerer's: the first attended run needs
# a handful of presses, and anything past that on one boot is a loop,
# not a player.
ANSWER_BUDGET = 32

_answers_sent = 0


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
    global _answers_sent

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
    if shape is not None and len(reencoded) > shape.max_payload_bytes:
        _say(
            "UI_TRADE_INVITE_REFUSED reason=over_reviewed_payload_budget"
            " len=%d budget=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    if _answers_sent >= ANSWER_BUDGET:
        _say(
            "UI_TRADE_INVITE_REFUSED reason=budget_spent budget=%d bytes_out=0"
            % (ANSWER_BUDGET,)
        )
        return []
    _answers_sent += 1
    _say(
        "UI_TRADE_INVITE_ANSWER n=%d/%d len=%d"
        % (_answers_sent, ANSWER_BUDGET, len(reencoded))
    )
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.TRADE_INVITE_VITAL_ID,
            version=wire.TRADE_INVITE_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


def reset_budget_for_tests():
    """Put the process budget back to zero.  Tests only."""
    global _answers_sent
    _answers_sent = 0


# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape, and the same header note, as the party answerer beside
# it.  A refused registration is not an exception: the seam returns False
# and names the reason on stderr, and this module then simply never
# answers, which is the shipping state and not a crash in discovery.
ui_dispatch.register_answerer(
    wire.TRADE_INVITE_VITAL_ID, answer_trade_invite
)
