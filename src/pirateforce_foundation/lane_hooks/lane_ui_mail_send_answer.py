"""LANE-UI: the sixth button on this seam the server answers.

WHAT A PLAYER CAN DO THAT THEY COULD NOT BEFORE THIS MODULE.  Press
"send mail" in the shipped client UI and have the server answer the
frame instead of dropping it.  Before this round five of the eight
``_FRIEND_MAIL_PARTY_TRADE_DISPATCH`` vitals answered (party invite
``0x37B1``, trade invite ``0x3700``, party command ``0x2466``, friend
request ``0xB9E9``, friend removal ``0x98A1``); this module takes the
sixth, ``Community_SendMailVital`` (``0x6E12``), and the remaining TWO
(``0xAF60`` get-mail-content, ``0x8183`` delete-mail) still come back
with an empty list.

RESIDUAL, NOT A NEW DESIGN (COO-DECISION ``20260909_1312_COO-DECISION-
ui2132-*``, answering this lane's own ``20260908_2132_LANE-UI-ASK-COO-
the-answerer-public-api-*``): "keep adding buttons, do not stop; the
one write point for ``_ANSWERERS`` closes ONCE at the seam, in chief's
``_discover()``/``adopt_answerer`` work, not in this lane."  This
module is in that residual window exactly like the five before it, and
carries the same one-line marker its round file also carries.

WHY ANSWERING WITH THIS ID IS AN ANSWER, NOT A GUESS.  ``RE-312``
RESULT-1 (pf_bridge ``notes_to_chief/20260908_1038_RE-312-RESULT-*``)
measured all eight ids ``INBOUND_YES``, ``0x6E12`` included: a live
inbound handler at vtable slot ``+0x1C``, and RESULT-2 pins the caller
at ``0x005F38B2`` inside the batch dispatch loop -- the same ordinary
receive path the other five answered ids share.  The wire shape is not
new reversing either: ``ui_mail_wire.SendMailFields`` (``u64, wstring,
u64, wstring, wstring, wstring, wstring, wstring, u8``) is copied
field-for-field from ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``
and has shipped, tested, in this repository since before this module
existed (``ui_mail_wire.py``'s own header, round ``rqwwp8``).

THIS CLASS IS ALREADY WATCHED, AND THAT DOES NOT CHANGE.
``lane_ui_mail_wire_log.py`` has been decoding this exact class on the
production path since before this module existed, printing a
report-only line with ``bytes_out=0``.  ``runtime.py`` fires that hook
and THEN calls ``ui_dispatch.answer()``, so both run: the log still
prints what arrived, and this module is the first thing to put a byte
back.  The log hook is not a prerequisite and is not consulted -- two
modules reading the same frame for two different purposes, the same
split ``lane_ui_friend_request_answer.py`` records for ``0xB9E9``.

WHAT IT SENDS: THE PLAYER'S OWN BYTES.  ``ui_mail_wire`` decodes the
payload, this module RE-ENCODES it, and refuses unless the result is
byte-identical to what arrived.  No field is named and none can be:
``ui_mail_wire.py``'s own header records ``CALL_UNCLASSIFIED`` for
this class -- it has FIVE wstring fields in a row, and it would be
easy to guess "recipient/subject/body/..." but nothing in the registry
or any capture proves which is which, so none of that guessing happens
here.  This module does not create, store, or deliver a message:
nothing in this file touches a row, and ``proven_semantics`` is
UNKNOWN for this class.  It observes only that this class's own
decode/encode pair round-trips the bytes the player sent.

THE ROUND TRIP IS THE SAME GUARD, ON THE SAME PRIMITIVE, MEASURED
ONCE ALREADY.  Every one of this class's six wstring fields decodes
through ``ui_social_wire.read_wstring_tag``, which wraps the same
``read_untagged_wstring`` that ``lane_ui_friend_request_answer.py``'s
test file scanned exhaustively (every two-byte code unit, plus 200,000
random four-byte names) and found injective: strict UTF-16LE decode
with the two failure shapes -- odd byte length, unpaired surrogate --
refused before or during the codec, never silently repaired.  That
scan is not re-run field-by-field here (six independent instances of
the same already-proven primitive is not six new facts); what this
module's own test file measures instead is round-trip identity through
its OWN nine-field encoder/decoder pair, over random well-formed
values including multiple wstring fields at once, which is the
composition the single-field scan does not exercise.

FIXED WIDTH IS NOT AVAILABLE TO THIS CLASS, AND THE ROW SAYS SO.  Six
wstring fields make this payload grow far more than the one-string
classes beside it, so the reviewed row in ``ui_dispatch`` uses a wider
ceiling than the 512 bytes those classes carry (see the row's own
comment for the number and why), and this module compares with ``>``
rather than ``!=`` -- the equality check the fixed-width buttons use
would turn every combination of six field lengths but one into a dead
button.

ONE FIELD THIS MODULE CHOOSES IS NOT THE PLAYER'S, exactly as every
answerer beside this one records.  The reply is
``make_runtime_vitals([(vital_id, version, payload)])``; of those
three, only ``payload`` is the client's.  ``version`` is the module
constant ``ui_mail_wire.COMMUNITY_SEND_MAIL_VITAL_VERSION``, whose own
header calls it an UNPROVEN DEFAULT, and the inbound version byte the
client sent is parsed by ``runtime.py`` and NOT handed to
``ui_dispatch.answer()`` -- so if a client ever sends anything but
zero, the server answers with zero anyway.  Closing that needs the
inbound version passed to ``answer()``, a ``runtime.py`` change
already filed by the party answerer's letter, not taken here.

WHO CAN PRESS IT AND HOW OFTEN: NOT THIS MODULE'S QUESTION.
``ui_dispatch.answer()`` refuses before any answerer runs unless the
session holds a selected character, and it holds the allowance itself,
keyed by (session, vital id).  This file therefore keeps no counter and
reads nothing from the session -- and because the allowance is per
VITAL, a storm on this button cannot silence the other five answered
buttons of the same session.

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
from .. import ui_mail_wire as wire

production_allowed = True

LABEL = "UI_SEND_MAIL_ANSWERED"


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


def answer_send_mail(session=None, vital_id=0, payload=b"", **_ignored):
    """Answer one ``Community_SendMailVital`` with its own bytes.

    ``session`` is ``ui_dispatch``'s snapshot, not the runtime, and this
    module reads nothing from it -- it is accepted only because the seam
    passes it by keyword.  Returns ``[]`` on every refusal, each one
    named on stderr so an attended round can line the console up against
    what the screen did.
    """
    if vital_id != wire.COMMUNITY_SEND_MAIL_VITAL_ID:
        _say("UI_SEND_MAIL_REFUSED reason=wrong_id bytes_out=0")
        return []
    if type(payload) is not bytes:
        _say("UI_SEND_MAIL_REFUSED reason=payload_not_bytes bytes_out=0")
        return []
    fields = wire.decode_send_mail_payload(payload)
    if fields is None:
        # The report-only hook beside this one prints the hex; this line
        # only has to say why nothing went back.
        _say(
            "UI_SEND_MAIL_REFUSED reason=undecodable len=%d bytes_out=0"
            % (len(payload),)
        )
        return []
    # THE ROUND TRIP IS THE WHOLE SAFETY ARGUMENT, so it is checked, not
    # assumed -- the same argument, in the same words, as every answerer
    # beside this one.  ``decode_*`` returns fields for the bytes it
    # consumed; re-encoding and comparing is what turns "these bytes
    # parsed" into "these are exactly the bytes that parsed".
    reencoded = wire.encode_send_mail_payload(fields)
    if reencoded != payload:
        _say(
            "UI_SEND_MAIL_REFUSED reason=not_byte_exact in=%d out=%d"
            " bytes_out=0" % (len(payload), len(reencoded))
        )
        return []
    # THE SEAM'S OWN BUDGET, READ BEFORE SPENDING OURS.  ``ui_dispatch``
    # refuses a payload past the reviewed budget for this label, and
    # that refusal lands after the answerer has run.  The registry is
    # the authority on that number; this module asks it instead of
    # keeping a second copy that can drift.
    shape = ui_dispatch.outbound_shape(LABEL)
    # A MISSING ROW IS A REFUSAL, NOT A CHECK THAT DID NOT APPLY.  No row
    # means no answer, said in its own token, rather than a silent skip
    # that dies inside ``ui_dispatch._compose`` instead.
    if shape is None:
        _say(
            "UI_SEND_MAIL_REFUSED reason=no_reviewed_outbound_shape"
            " label=%.64s bytes_out=0" % (LABEL,)
        )
        return []
    # A CEILING, NOT AN EQUALITY -- this payload carries six strings, so
    # its width is the player's to move across all six at once.  The
    # equality check the fixed-width buttons use would turn every
    # combination of lengths but one into a dead button.
    if len(reencoded) > shape.max_payload_bytes:
        _say(
            "UI_SEND_MAIL_REFUSED reason=over_reviewed_budget len=%d"
            " budget=%d bytes_out=0"
            % (len(reencoded), shape.max_payload_bytes)
        )
        return []
    # NO COUNTER HERE.  The seam charges the SESSION, per vital, at its
    # send point, so this module neither counts nor knows who is asking.
    #
    # ACCEPTED, NOT ANSWERED (pf-adversary round ncejt8, F8, paid once on
    # the friend-removal answerer and applied here from the start rather
    # than repeated): this line is printed BEFORE ``ui_dispatch``'s own
    # ``_compose`` / ``_actions_are_well_formed`` /
    # ``_outbound_shapes_are_registered`` / budget charge / ``sendall``
    # all run, so it can only say what THIS module decided, not that a
    # byte has left the process.
    _say("UI_SEND_MAIL_ACCEPTED len=%d bytes_out=pending" % (len(reencoded),))
    return [
        ui_dispatch.VitalReply(
            label=LABEL,
            vital_id=wire.COMMUNITY_SEND_MAIL_VITAL_ID,
            version=wire.COMMUNITY_SEND_MAIL_VITAL_VERSION,
            payload=reencoded,
            delay=0.0,
        )
    ]


# THE TWO NAMES THE ARMING RUNNER ASKS FOR, DECLARED AHEAD OF THE
# RUNNER -- the same shape as every answerer beside this one.  The
# runner reads the reviewed owner table, imports the lane that owns the
# id, and asks the lane for its own token and its own sample frame; no
# edit to the runner and no spelling of this class's name outside this
# file.
ARMING_TOKEN = "UI_SEND_MAIL_ANSWER_ARMED"


def arming_sample():
    """``(vital_id, version, payload)`` for a well-formed frame of this class.

    Called only by the arming runner.  It is a FUNCTION, not a module
    constant, so no boot pays for building a sample frame it will never
    send.  The name is ASCII on purpose: the bridge console is cp874 and
    the runner prints what it measured.
    """
    return (
        wire.COMMUNITY_SEND_MAIL_VITAL_ID,
        wire.COMMUNITY_SEND_MAIL_VITAL_VERSION,
        wire.encode_send_mail_payload(
            wire.SendMailFields(
                field1_u64=1,
                field2_wstring="Ann",
                field3_u64=2,
                field4_wstring="Ahoy",
                field5_wstring="Meet at the dock",
                field6_wstring="",
                field7_wstring="",
                field8_wstring="",
                field9_u8=1,
            )
        ),
    )


# THE ADOPT-SIDE CONTRACT, DECLARED TOO -- the replacement for a lane
# calling ``register_answerer()`` itself once ``lane_hooks._discover()``
# adopts through ``ui_dispatch.adopt_answerer()`` (COO ``20260908_1642``
# item 2, restating ``1441``; PR ``#1167``, not yet on main).  Declaring
# these two names now is the whole cost of the conversion round having
# six files to flip instead of a seventh.
ANSWERS_VITAL_ID = wire.COMMUNITY_SEND_MAIL_VITAL_ID
ANSWERS_WITH = answer_send_mail

# REGISTERED AT IMPORT, WHICH IS WHEN ``lane_hooks._discover()`` RUNS --
# the same shape as the five answerers beside it.  A refused
# registration is not an exception: the seam returns False and names the
# reason on stderr, and this module then simply never answers, which is
# the shipping state and not a crash in discovery.
#
# RESIDUAL D2, STILL OPEN (COO-DECISION ``20260909_1312_COO-DECISION-
# ui2132-*``): this call is the half of the seam's write-ownership fix
# that is NOT paid by adding a sixth button.  It stays until
# ``_discover()`` calls ``adopt_answerer()`` in chief's own commit, which
# converts every answerer named above in one atomic round rather than a
# seventh conversion done alone.
ui_dispatch.register_answerer(
    wire.COMMUNITY_SEND_MAIL_VITAL_ID, answer_send_mail
)
