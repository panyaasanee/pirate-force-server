"""LANE-UI: the third button on this seam the server answers.

WHAT A PLAYER CAN DO THAT THEY COULD NOT BEFORE THIS MODULE.  Press a
party COMMAND in the shipped client UI -- the buttons beside the invite
that operate on a party that already exists -- and have the server
answer the frame instead of dropping it.  ``PartyInviteVital``
(``0x37B1``) and ``TradeInviteVital`` (``0x3700``) were answered in the
two rounds before this one; the remaining six of the eight
``_FRIEND_MAIL_PARTY_TRADE_DISPATCH`` vitals still came back with an
empty list.  This module takes the third, ``PartyCmdVital``
(``0x2466``).

WHICH BUTTON, SAID AS PRECISELY AS THE EVIDENCE ALLOWS.  Not "the party
command", because nobody has traced which client control sends this and
with what field values: ``ui_party_wire``'s header records
``CALL_UNCLASSIFIED`` for both party classes and names its fields
positionally for that reason.  What IS proven is where the frame goes:
``RE-312`` RESULT-1 (pf_bridge
``notes_to_chief/20260908_1038_RE-312-RESULT-*``) lists
``0x2466 PartyCmdVital INBOUND_YES handler=0x0062EA70`` -- the SAME
handler VA as ``PartyInviteVital``, inside ``"PartyModule_Client"``
(``0x00F0DA14``) -- and RESULT-2 pins the caller at ``0x005F38B2``
inside the batch dispatch loop, so the vtable slot is reached by the
ordinary receive path.  Answering with this id is therefore an answer,
not a guess: the same two letters the two answerers beside this one
rest on, for a class those letters cover in the same row.

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_party_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be:
letter ``20260904_1120`` nonclaim (2) stands, ``proven_semantics`` is
UNKNOWN for both party classes, and this module does not treat a party
command as a party invite -- it only observes that this class's own
decode/encode pair round-trips it.

THIS PAYLOAD IS FIXED WIDTH, WHICH THE OTHER TWO ARE NOT, and that is
the one real difference in this file.  ``PartyCmdFields`` is
``u8 + u64`` with no string, so every payload this lane can emit is
exactly ``_PARTY_CMD_PAYLOAD_BYTES`` bytes -- measured, in this
module's own test file, over 4,000 random field pairs including both
ends of each field's range.  The reviewed outbound shape in
``ui_dispatch`` therefore pins the EXACT width instead of leaving the
512-byte headroom the two wstring classes need, and a payload of any
other length cannot leave under this label at all.  A class whose
width cannot vary does not need room to spare, and headroom nobody
needs is reach nobody reviewed.

ONE BYTE THAT LEAVES IS NOT THE PLAYER'S, exactly as the two answerers
beside this one record (pf-adversary round xqxadg, D3).  The reply is
``make_runtime_vitals([(vital_id, version, payload)])``; only
``payload`` is the client's.  ``version`` is the module constant
``ui_party_wire.PARTY_CMD_VITAL_VERSION``, whose own header calls it an
UNPROVEN DEFAULT, and the inbound version byte the client sent is
parsed by ``runtime.py`` and NOT handed to ``ui_dispatch.answer()`` --
so if a client ever sends anything but zero, the server answers with
zero anyway.  ``RE-312`` RESULT-2 reads ``0x005F3EF4`` comparing that
u8 against ``[obj+0x10]`` and logging ``0xE0000031`` on a mismatch, and
nobody has read ``[obj+0x10]`` for this class either.  So the version
byte is a REVIEWED guess pinned by the outbound registry, not a derived
value, and closing it needs the inbound version passed to ``answer()``
-- a ``runtime.py`` change, filed by the round before this one, not
taken here.

WHO CAN PRESS IT AND HOW OFTEN: NOT THIS MODULE'S QUESTION ANY MORE.
``ui_dispatch.answer()`` refuses before any answerer runs unless the
session holds a selected character (pf-adversary D7, round 1gc6hl), and
it holds the allowance itself, keyed by (session, vital id)
(pf-adversary D-B/D1, round vy1m79).  This file therefore keeps no
counter and reads nothing from the session -- and because the allowance
is per VITAL, a storm on this new button cannot silence the invite
button of the same session.  That property is pinned by test here, not
asserted: it is the exact property the registry was once wrongly
claimed to provide.

WHAT THE PLAYER SEES IS STILL A QUESTION FOR A SCREEN.  Static evidence
says a live inbound handler exists and the receive path reaches it.
Whether the client draws anything is a question about pixels, and this
project answers those with an attended ticket -- ``observed_frames = 0``
for this class as for the other seven.
"""
from __future__ import annotations

import sys

from . import console_safe
from .. import ui_dispatch
from .. import ui_party_wire as wire

production_allowed = True

LABEL = "UI_PARTY_CMD_ANSWERED"

# THE WIDTH, DERIVED ONCE FROM THE ENCODER, NOT TYPED IN.  A literal
# here would be a second copy of a number ``ui_party_wire`` already
# owns, free to drift the moment that file gains a field; deriving it
# from the encoder itself means this module and the wire module cannot
# disagree.  ``ui_dispatch``'s reviewed shape keeps its own literal on
# purpose -- that one is the REVIEW, and a review that reads the value
# it is reviewing pins nothing -- and the test file compares the two.
_PARTY_CMD_PAYLOAD_BYTES = len(
    wire.encode_party_cmd_payload(wire.PartyCmdFields(field1_u8=0, field2_u64=0))
)


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


def answer_party_cmd(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``PartyCmdVital`` with the bytes it arrived as.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.PARTY_CMD_VITAL_ID:
        _say("UI_PARTY_CMD_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_PARTY_CMD_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_party_cmd_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_PARTY_CMD_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed -- the same argument, in the same words, as the two
    # answerers beside this one.  ``decode_*`` returns fields for the
    # bytes it consumed; re-encoding and comparing is what turns "these
    # bytes parsed" into "these are exactly the bytes that parsed".
    reencoded = wire.encode_party_cmd_payload(fields)
    # AND IT IS DEAD CODE TODAY, SAID OUT LOUD (pf-adversary D5, round
    # 1gc6hl).  ``decode_party_cmd_payload`` calls ``require_exhausted``
    # and the encoder is its exact inverse for every payload it accepts:
    # measured over 4,000 structurally valid payloads in this module's
    # own test file, every one that decoded re-encoded byte for byte, so
    # the refusal below has never fired through the real decoder.  It
    # stays because it is the guard for the decoder this project will
    # have LATER, and the test file reaches it by making the encoder
    # disagree -- so the comparison cannot be deleted or inverted under
    # a green suite.
    if reencoded != payload:
        _say(
            "UI_PARTY_CMD_REFUSED reason=not_byte_exact in=%d out=%d"
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
            "UI_PARTY_CMD_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    # FIXED WIDTH IS CHECKED AS FIXED WIDTH, NOT AS A CEILING.  For the
    # two wstring classes ``len(reencoded) > budget`` is the whole
    # question, because their payload grows with a name.  This class
    # cannot vary: anything the encoder emits is exactly
    # ``_PARTY_CMD_PAYLOAD_BYTES``, so a length that merely fits under a
    # ceiling would be evidence of nothing.  Requiring EQUALITY is what
    # makes the check able to fail: it fires if the wire module ever
    # gains a field without this lane's review, and it fires if the
    # reviewed shape and the encoder ever disagree, which a ``>`` test
    # would pass in silence.
    if len(reencoded) != shape.max_payload_bytes:
        _say(
            "UI_PARTY_CMD_REFUSED reason=not_the_reviewed_fixed_width"
            " len=%d reviewed=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    # NO COUNTER HERE (pf-adversary D-B, round vy1m79).  The seam charges
    # the SESSION, per vital, at its send point, so this module neither
    # counts nor knows who is asking.
    _say("UI_PARTY_CMD_ANSWER len=%d" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.PARTY_CMD_VITAL_ID,
            version=wire.PARTY_CMD_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape, and the same note, as the two answerers beside it.  A
# refused registration is not an exception: the seam returns False and
# names the reason on stderr, and this module then simply never answers,
# which is the shipping state and not a crash in discovery.
ui_dispatch.register_answerer(wire.PARTY_CMD_VITAL_ID, answer_party_cmd)
