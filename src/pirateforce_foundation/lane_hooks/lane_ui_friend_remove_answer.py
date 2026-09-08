"""LANE-UI: the fourth button on the production path the server answers.

WHAT A PLAYER CAN DO THAT THEY COULD NOT BEFORE THIS MODULE.  Press
"remove friend" in the shipped client UI and have the server answer the
frame instead of dropping it.  ``Community_RemoveFriendVital``
(``0x98A1``) is one of the eight ids ``runtime.py`` already routes into
``ui_dispatch``; until this module it was one of the ids with no owner,
so every press produced an empty action list and zero bytes back.

WHY THIS ONE NEEDED NO NEW REVERSING.  ``RE-312`` RESULT-1 (pf_bridge
``notes_to_chief/20260908_1038_RE-312-RESULT-*``) measured all eight ids
``INBOUND_YES``: ``0x98A1`` carries a live inbound handler at vtable slot
``+0x1C`` (``handler=0x00645BF0``, ``next=0x0063F9B0``), and RESULT-2
pinned the caller at ``0x005F38B2`` inside the batch dispatch loop, so
the slot is reached by the ordinary receive path.  Answering with the
same id is therefore an answer, not a guess.  The wire shape is not new
either: ``ui_friend_wire.RemoveFriendFields`` (``u64, u64, u8``) is
copied field-for-field from ``pf_bridge/external/PF_SERIALIZER_FIELDS
.tsv`` and has shipped, tested, in this repository since before this
module existed.

!! WHAT RE-312 DID NOT SETTLE, AND THIS MODULE DOES NOT PRETEND IT DID.
BUILD_IMPACT 3 of that letter says the five ``Community_`` ids share one
vtable entry and split INSIDE ``0x0063F9B0`` rather than at the table,
so "this id has a handler" is measured while "the split inside that
function reaches a body for THIS id" is not.  Nobody has read that
function.  The consequence is bounded and is the same one the friend
REQUEST answerer beside this file carries: if the split refuses
``0x98A1``, the client ignores a frame it asked for, which is the state
the player is already in today.  It is not a reason to send different
bytes, and it IS a reason this module echoes rather than composes.

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_friend_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be:
letter ``20260904_1120`` nonclaim (2) and ``RE-312`` nonclaim 5 both
stand and ``proven_semantics`` is UNKNOWN.  "field2_u64 is the friend
being removed" is the obvious reading and it is NOT written into this
file, because nothing has measured it.

!! ONE BYTE THAT LEAVES IS NOT THE PLAYER'S, the same one the party and
trade answerers name: ``version`` is the module constant
``ui_friend_wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION``, whose own
header calls it an UNPROVEN DEFAULT, and the inbound version the client
sent is parsed by ``runtime.py`` and NOT handed to
``ui_dispatch.answer()``.  So a client that sends anything but zero is
answered with zero anyway.  Closing that needs the inbound version
passed through the seam -- a ``runtime.py`` change, filed by the party
answerer, not taken here.

THIS PAYLOAD HAS NO STRING, SO IT HAS NO HEADROOM.  ``u64 + u64 + u8``
under this lane's tag encoding is exactly 20 bytes for every field
triple the type can hold -- measured over 4,000 random triples in
``tests/test_lane_ui_friend_remove_answer.py``, including both u64
extremes.  The reviewed row in ``ui_dispatch`` therefore states 20 and
this module requires EQUALITY against it, the same choice
``lane_ui_party_cmd_answer`` made for its fixed-width class: headroom
nobody needs is reach nobody reviewed.

WHO CAN PRESS THIS BUTTON: SOMEBODY WHO LOGGED IN.  ``ui_dispatch
.answer()`` refuses before any answerer runs unless the session holds a
selected character, and the answer allowance is the seam's, keyed by
(session, vital id).  This module keeps no counter of its own and reads
nothing from the session snapshot it is handed.
"""
from __future__ import annotations

import sys

from . import console_safe
from .. import ui_dispatch
from .. import ui_friend_wire as wire

production_allowed = True

LABEL = "UI_FRIEND_REMOVE_ANSWERED"


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


def answer_remove_friend(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``Community_RemoveFriendVital`` with its own bytes.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID:
        _say("UI_FRIEND_REMOVE_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_FRIEND_REMOVE_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_remove_friend_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_FRIEND_REMOVE_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed.  ``decode_*`` returns fields for the bytes it consumed;
    # re-encoding and comparing is what turns "these bytes parsed" into
    # "these are exactly the bytes that parsed".
    reencoded = wire.encode_remove_friend_payload(fields)
    # AND IT IS DEAD CODE TODAY, SAID OUT LOUD, the same way the trade
    # answerer says it: the decoder calls ``require_exhausted`` and the
    # encoder is its exact inverse for every payload the decoder
    # accepts, so this refusal has never fired through the real decoder.
    # It stays because it guards the decoder this project will have
    # LATER, and the test file reaches it by making the encoder
    # disagree, so it cannot be deleted or inverted under a green suite.
    if reencoded != payload:
        _say(
            "UI_FRIEND_REMOVE_REFUSED reason=not_byte_exact in=%d out=%d"
            " bytes_out=0" % (len(payload), len(reencoded))
        )
        return []
    shape = ui_dispatch.outbound_shape(LABEL)
    # A MISSING ROW IS A REFUSAL, NOT A CHECK THAT DID NOT APPLY: the
    # registry is the authority on whether this label may leave at all,
    # so no row means no answer, said in its own token.
    if shape is None:
        _say(
            "UI_FRIEND_REMOVE_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    # EQUALITY, NOT A CEILING -- see the header: every payload this class
    # can produce is the same width, so anything else is not this class.
    if len(reencoded) != shape.max_payload_bytes:
        _say(
            "UI_FRIEND_REMOVE_REFUSED reason=not_the_fixed_payload_width"
            " len=%d width=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    _say("UI_FRIEND_REMOVE_ANSWER len=%d" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
            version=wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape as the three answerers beside it.  A refused
# registration is not an exception: the seam returns False and names the
# reason on stderr, and this module then simply never answers, which is
# the shipping state and not a crash in discovery.
ui_dispatch.register_answerer(
    wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID, answer_remove_friend
)
