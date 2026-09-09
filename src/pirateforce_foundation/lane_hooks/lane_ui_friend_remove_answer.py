"""LANE-UI: the fourth button on the production path the server answers.

WHAT CHANGES, STATED AT THE WIDTH THE EVIDENCE SUPPORTS.  A
``Community_RemoveFriendVital`` (``0x98A1``) frame arriving from a
logged-in session is answered instead of dropped: until this module it
was one of the ids ``runtime.py`` routes into ``ui_dispatch`` with no
owner, so it produced an empty action list and zero bytes back.

!! AND NOT "the remove-friend button in the shipped client sends this"
(pf-adversary round `ncejt8`, F9).  ``RE-312`` nonclaim 2 records
``observed_frames = 0`` for all eight classes in BOTH directions and
nonclaim 4 declines to claim packet direction, so nobody has watched a
client send ``0x98A1`` at all.  The button-to-id link is the reading
this lane is building on and it is NOT measured; the ticket that
measures it is the one this module's row in
``docs/FUNCTIONAL_COVERAGE.json`` is open on.

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
function.  The consequence is bounded: if the split refuses ``0x98A1``, the client
ignores a frame it asked for, which is the state the player is already
in today.  It is not a reason to send different bytes, and it IS a
reason this module echoes rather than composes.  (An earlier draft of
this paragraph said "the same one the friend REQUEST answerer beside
this file carries".  There is no such file in this repository --
pf-adversary round `ncejt8`, F6: it exists only on an unmerged branch,
and a reviewer cannot open the argument they are asked to lean on.)

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_friend_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be:
letter ``20260904_1120`` nonclaim (2) stands, and the ``RE-312``
nonclaim that covers THIS class is nonclaim **3** (nothing is claimed
about what separates the five ``Community_*`` classes), not nonclaim 5.
Nonclaim 5 is scoped to serializer ``0x00664550``, which RESULT-2 shows
is the one PartyInviteVital and TradeInviteVital share; this class
serialises at ``0x006E7B20``.  The party and trade answerers cite
nonclaim 5 correctly and this file copied the citation without
re-reading its scope (pf-adversary round `ncejt8`, F5).  The
conservative conclusion is unchanged -- ``proven_semantics`` is UNKNOWN
either way -- but the authority for it is now the right one.
"field2_u64 is the friend being removed" is the obvious reading and it
is NOT written into this file, because nothing has measured it.

!! ONE BYTE THAT LEAVES IS NOT THE PLAYER'S, the same one the party and
trade answerers name: ``version`` is the module constant
``ui_friend_wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION``, whose own
header calls it an UNPROVEN DEFAULT, and the inbound version the client
sent is parsed by ``runtime.py`` and NOT handed to
``ui_dispatch.answer()``.  So a client that sends anything but zero is
answered with zero anyway.
!! AND THAT BYTE IS COMPARED BY THE CLIENT, which this file must say
rather than leave to its neighbours (pf-adversary round `ncejt8`, F10):
``RE-312`` RESULT-2 reads ``0x005F3EF4`` comparing the u8 after the id
against ``[obj+0x10]`` and logging ``0xE0000031`` on a mismatch, and
nobody has read ``[obj+0x10]`` for this class.  RESULT-2's own verdict
is that the client LOGS and carries on -- a warning, not an error -- so
the guess is bounded, and carrying the conclusion rather than only the
evidence is what round m54yxh's D12 was about.  Closing it needs the
inbound version passed through the seam, a ``runtime.py`` change this
lane has not filed as its own letter (the party answerer's header calls
it filed; no letter in ``notes_to_chief/`` matches, so treat it as
UNFILED until one does).

THIS PAYLOAD HAS NO STRING, SO IT HAS NO HEADROOM.  ``u64 + u64 + u8``
under this lane's tag encoding is exactly 20 bytes for every INT triple,
and the reason is structural rather than statistical (pf-adversary round
`ncejt8`, F11: 4,000 random samples out of a 2**136 space is not "every"
-- the guarantee is that the encoder masks with ``& 0xFFFF...`` / ``&
0xFF`` and hands fixed-width ``struct.pack`` codes, so negative and
oversized ints normalise instead of widening).  ``RemoveFriendFields``
is an unvalidated dataclass, so a NON-int field raises inside the
encoder instead of producing 20 bytes; that raise is caught by
``ui_dispatch.answer()`` and costs the player nothing, and it is why
this paragraph says "int triple" and not "anything the type can hold".

BOTH NUMBERS, NOT ONE (round m54yxh, D7, and pf-adversary round
`ncejt8`, F4 for repeating it).  ``_REMOVE_FRIEND_PAYLOAD_BYTES`` below
is this module's own reviewed width and the ``ui_dispatch`` row is the
seam's; the guard requires the re-encoding to equal the first AND the
row to equal it too.  Comparing only against the registry would leave
this module's constant dead -- measured on the sibling class: setting it
to 999 left the button working.

AND WHAT ``!=`` COSTS, not only what it buys.  ``!=`` is NOT strictly
safer than ``>``: widening the reviewed row -- the one edit that is
harmless everywhere else in that registry -- makes this button answer
nothing at all rather than answer a wider frame.  That is the trade
taken here on purpose, for the same reason as the sibling: headroom
nobody needs is reach nobody reviewed.

AND THE GUARD IS DEAD CODE TODAY, said as plainly as the round-trip
guard below says it (pf-adversary round `ncejt8`, F3: this file declared
one of two identical facts and presented the other as an active
safeguard).  The decoder admits exactly one length -- 20 -- measured
exhaustively over lengths 0..39 plus fuzz, and the byte-exact check
above the width check has already required ``reencoded == payload``.  So
no input the seam can deliver reaches the width refusal through the real
decoder.  It stays for the decoder this project will have LATER.

WHICH HALF OF THE GUARD IS PINNED, MEASURED, not asserted.  The ROW
half is pinned in both directions: the test file moves the reviewed
number to 19 and to 512 and requires a refusal each time, so mutating
that clause's ``!=`` to ``>`` or to ``<`` turns the suite red (verified
by running both mutants).  The LENGTH half is NOT pinned and cannot be,
because it is unreachable: mutating ``len(reencoded) != ...`` to ``>``
survives a green suite, and it survives because no input the decoder
accepts has any other length.  Saying only the first half would be the
kind of half-true this file has already been caught making.

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

# THIS MODULE'S OWN REVIEWED WIDTH, kept beside the answerer and checked
# against the seam's row rather than read from it -- see the header's
# "BOTH NUMBERS, NOT ONE".
_REMOVE_FRIEND_PAYLOAD_BYTES = 20


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
    # EQUALITY AGAINST BOTH NUMBERS -- see the header.
    if (len(reencoded) != _REMOVE_FRIEND_PAYLOAD_BYTES
            or shape.max_payload_bytes != _REMOVE_FRIEND_PAYLOAD_BYTES):
        _say(
            "UI_FRIEND_REMOVE_REFUSED reason=not_the_fixed_payload_width"
            " len=%d width=%d row=%d bytes_out=0"
            % (len(reencoded), _REMOVE_FRIEND_PAYLOAD_BYTES,
               shape.max_payload_bytes)
        )
        return []
    # ACCEPTED, NOT ANSWERED (pf-adversary round `ncejt8`, F8).  This
    # line used to read `UI_FRIEND_REMOVE_ANSWER`, and it prints four
    # gates and one `sendall` before any byte can leave: `_compose`,
    # `_actions_are_well_formed`, `_outbound_shapes_are_registered` and
    # the budget charge all run after this module returns, and a caller
    # that reaches `answer()` without an envelope gets zero bytes out
    # under a console line that said ANSWER.  The seam renamed its own
    # token for exactly this reason; so does this one.  The attended
    # round reading this console is told what this module decided, not
    # what the wire did.
    _say("UI_FRIEND_REMOVE_ACCEPTED len=%d bytes_out=pending"
         % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
            version=wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


# THE TWO NAMES THE ARMING RUNNER ASKS FOR (recovered from PR #1167,
# `claude/festive-shannon-ly40b5`, round `ly40b5`: `EveryAnswered
# ButtonHasARunnerTests` in `tests/test_ui_dispatch.py` refuses to boot
# any process where a reviewed-owner id's lane is imported but does not
# declare both names -- this module shipped one round BEFORE that guard
# landed on this branch, and was the one gap the guard's own commit
# message describes finding).  Same shape and same reason as the three
# sibling answerers: the runner reads the reviewed owner table, imports
# the lane that owns the id, and asks the lane for its own token and
# sample frame -- no edit to the runner, no spelling of this class's name
# outside this file.
ARMING_TOKEN = "UI_FRIEND_REMOVE_ANSWER_ARMED"


def arming_sample():
    """``(vital_id, version, payload)`` for a well-formed frame of this class.

    Called only by the arming runner.  It is a FUNCTION, not a module
    constant, so no boot pays for building a sample frame it will never
    send.  The name is ASCII on purpose: the bridge console is cp874 and
    the runner prints what it measured.
    """
    return (
        wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
        wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION,
        wire.encode_remove_friend_payload(
            wire.RemoveFriendFields(
                field1_u64=0x1122334455667788,
                field2_u64=0x99AABBCCDDEEFF00,
                field3_u8=1,
            )
        ),
    )


# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape as the three answerers beside it.  A refused
# registration is not an exception: the seam returns False and names the
# reason on stderr, and this module then simply never answers, which is
# the shipping state and not a crash in discovery.
ui_dispatch.register_answerer(
    wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID, answer_remove_friend
)
