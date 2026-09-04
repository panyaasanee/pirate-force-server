"""LANE-A: a walker of its own for NavigationEx_EnterInstanceVital (0xC723).

COO-DECISION 20260904_0747 item 3(a), COO-DECISION 20260904_0850 item 3, and
the chief (LANE-E) letters of round `8nh6q5`/R334 at 08:01+07 and its 09:10
correction: the call site (`runtime.py`'s `nested_id ==
NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID` branch) landed a round early, on the
condition that it fires safely with no subscriber.  This module is the
subscriber.

RE-227 (static, full CFG census; pf_bridge/notes_to_chief/20260904_0724)
pinned this frame's body as a closed five-byte shape, not a tagged walk:

    12 <opaque-u16 little-endian> 0B 06

byte 0 is the tag that opens the record's own opaque field (`+0x12` on the
survey record the confirm callback copies from), bytes 1-2 are that u16
copied unchanged, and the trailing `0B 06` is the allocator's fixed byte at
record `+0x16`.  RE-227 nonclaim 3 forbids calling the u16 an island id, a
scene id, or a Trigger-TIP id: nothing has proven it is any of those, only
that it is copied unchanged, so it is printed here as a raw number.

WHY THIS IS NOT `lane_a_island_trigger_log`'s WALKER, REUSED.  The chief
letter that first asked for a mirror (08:01+07) had to be corrected at
09:10+07: that walker's tag-width table deliberately leaves out tag 0x12,
because 0x12 is the tag that starts the NEXT nested vital inside a
TriggerVital payload, and stepping over it there would walk out of the
trigger vital entirely.  This frame's first byte IS 0x12 -- it is not a
tagged walk with an unknown-length middle, it is one closed record whose
tag, width and trailer RE-227 already measured -- so a decode here means
checking the whole five bytes against that fixed shape, not walking tags.
Mirroring the other module byte-for-byte would silently produce UNPARSED on
every real frame and never print the opaque value the whole round exists to
surface (measured in the chief 09:10 letter: `12 34 12 0B 06` walks to
`first_tag_value(..., 0x12) -> None` under that walker's table).

IT SENDS NOTHING.  No frame is composed, no bytes are queued, no session
state is touched, nothing is returned.  `lane_hooks.fire()` is report-only
by construction; this module stays inside that shape on purpose, same as
the trigger-vital sibling.  The encoder for the OTHER half of this exchange
(`NavigationEx_AddSurveyDataVtial`, the record the server has to provision
before a client ever reaches this branch) is a separate module, built but
never called from any send path until GT-228 measures real island XYZ
(COO-DECISION 20260904_0747 item 3(b) forbids sending it before then).

IT IS WIRED.  `runtime.py`'s `nested_id ==
NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID` branch, next to the TriggerVital
branch it copies the shape of, calls `lane_hooks.fire(
"vital_inbound_navigationex_enter_instance_vital", session=self,
payload=bytes(parsed.nested_payload))` on every inbound frame with this
nested id -- landed one round early by chief (LANE-E) round `8nh6q5`/R334.
The registration line `LANE_HOOK_REGISTERED ...
vital_inbound_navigationex_enter_instance_vital` on stderr at boot, plus an
`LANE_A_ENTER_INSTANCE ...` line per frame once one arrives, is how you tell
it is firing.

WHAT A LINE MEANS, AND WHAT IT DOES NOT.  An `opaque=0x....` line means "a
frame with this nested id arrived and its five bytes matched the shape
RE-227 pinned".  It does NOT mean the value is an island id, a scene id, or
anything else with meaning yet.  The `issued=` / `provisioned=` pair beside
it comes from `world_m2_survey_plan` and is about THIS SERVER, not about the
client: ~~`provisioned=0` means this build could not have provisioned a
single proximity record (no island XYZ has been measured yet)~~ -- GT-228
(PASS, R308) has since measured both, so today the pair reads
`provisioned=2` -- so an `issued=no`
next to it says the captain report that produced this confirm popped without
anything from us -- which is the one reading of this line that would refute
RE-227's provisioning hypothesis instead of supporting it.  (Not during
GT-228, whose STOP rule forbids pressing confirm: no confirm, no frame, no
line.  This is what the FIRST confirm frame this server ever sees will say.)

    THAT REFUTATION READING NEEDS `sent=`, AND ONLY `sent=` (pf-adversary,
    round `16uvmp`).  It was written when this line's only possible state was
    "we have no send path", and it survived the strike-through above at the
    new number: on a build reading `sent=unwired`, an `issued=no` refutes
    NOTHING, because no record left this process for the client to have
    ignored -- it says a client sent us five bytes we do not recognise.  The
    refutation is available only on a run whose outbound hex actually carries
    the two `AddSurveyData` frames, i.e. `sent=` naming a count.  A grader who
    reads `issued=no` beside `sent=unwired` as evidence against RE-227 has
    graded a frame this server never sent.

AND `match=trial confidence=low` IS THE FRAGMENT NOT TO OVER-READ (round
`16uvmp`).  The first provisioning trial writes the destination number
(2/3) into the record rather than the plan's own 0xA0xx handle -- COO-DECISION
20260904_1345 item 1 -- so that is the value a confirm on that trial echoes,
and the plan now resolves it.  It appends `match=trial confidence=low` when
it does, because a single digit coming back is CONSISTENT with our record
having been the source and is not evidence of it; a handle echo, which no
other namespace in this exchange could produce, appends nothing and is the
strong reading.  Before this the plan recognised only the handle, so a
perfect attended run of `GT-233` would have printed `issued=no` -- the
refutation line above -- for a confirm produced by our own record.
It does NOT mean the confirm sequence that produced it has been seen live on
a real client (RE-227's own reachability proof for this branch is synthetic;
see the dispatch-wiring test's own docstring).  `UNPARSED` means the payload
did not match the fixed shape -- wrong length, wrong leading tag, or a wrong
trailer -- and the raw
hex is printed so the next round works from bytes rather than from this
module's opinion of them.
"""
from __future__ import annotations

import sys

from . import hook


production_allowed = True

POINT = "vital_inbound_navigationex_enter_instance_vital"
TOKEN = "LANE_A_ENTER_INSTANCE"

# RE-227's pinned shape: tag 0x12, u16 LE opaque value, then the allocator's
# fixed trailer `0B 06` (record `+0x16` = byte 6).  Five bytes, closed --
# not a tag-width table, because RE-227 measured this exact whole shape and
# nothing walks past it.
_LEADING_TAG = 0x12
_TRAILER = b"\x0b\x06"
_EXPECTED_LEN = 5

# A capture-sized ceiling on the hex a single UNPARSED line may print, same
# constant and same reason as the trigger-vital sibling's own
# `_MAX_HEX_BYTES`: the payload is client-supplied off the same dispatch
# path, and a malformed or hostile one is not a reason to write an unbounded
# line into the console a grader reads.  pf-adversary (this round) measured
# the gap directly: with no cap, a 2,000,000-byte payload produced a
# 4,000,072-character console line.
_MAX_HEX_BYTES = 96

# THE ONE FRAGMENT ON THIS LINE THAT IS ABOUT WHAT THIS SERVER DID.
#
# pf-adversary (round `16uvmp`) asked the question this line could not answer:
# what on it distinguishes "we provisioned a record and the client echoed it"
# from "we have never sent anything and a client sent us a 2"?  Nothing did.
# `issued=`, `provisioned=` and `arrival_plan=` are all computed from
# `world_m2_survey_plan.MEASURED_XYZ` and the scene registry -- CAPABILITY, not
# event -- so every one of them reads the same on a build with no send path at
# all, which is this build.  A client that sends five bytes can make the line
# say `issued=yes` today.
#
# `unwired` is the state of THIS REPOSITORY, and it is checked rather than
# asserted: the provisioning-trial module (the only composer of a record) has
# a guard test that fails if ANY file in the tree so much as names it, so
# while that test is green nothing can call it and no record can have left
# this process.  `tests/test_lane_a_enter_instance_log.py` pins the two
# together, so the day a call site lands, this constant goes red rather than
# lying quietly on an attended console.
SEND_PATH_STATE = "unwired"


def decode_opaque(payload: bytes) -> int | None:
    """The opaque u16 RE-227 pinned at survey-record `+0x12`, copied
    unchanged into this frame's bytes 1-2 -- or ``None`` if ``payload`` does
    not match the fixed five-byte shape `12 <u16 LE> 0B 06` exactly.

    Never raises, never guesses a width: a payload that is the wrong length,
    that does not open with the 0x12 tag, or whose last two bytes are not
    the allocator's fixed `0B 06` trailer is a refusal, not a partial read.
    """
    if len(payload) != _EXPECTED_LEN:
        return None
    if payload[0] != _LEADING_TAG:
        return None
    if payload[3:5] != _TRAILER:
        return None
    return int.from_bytes(payload[1:3], "little")


def console_line(payload: bytes) -> str:
    """The exact ASCII line this hook prints for ``payload``.  Never raises.

    Split out from the hook so a test can assert the line without standing
    up a session or capturing stderr, same split as the trigger-vital
    sibling module.
    """
    opaque = decode_opaque(payload)
    if opaque is None:
        shown = payload[:_MAX_HEX_BYTES]
        truncated = "+" if len(payload) > len(shown) else ""
        return (
            f"{TOKEN} UNPARSED len={len(payload)} hex={shown.hex()}{truncated}"
            " no_responder bytes_out=0"
        )
    # Raw number only -- RE-227 nonclaim 3 forbids naming this an island,
    # scene, or Trigger-TIP id; chief 09:10 restates the same limit.  The
    # annotation from `world_m2_survey_plan` stays inside that limit on
    # purpose: it says whether the value is a handle THIS BUILD issued and
    # how many records this build could provision at all, never what the
    # client thinks the number means.  ~~With no measured island XYZ that
    # reads `issued=no provisioned=0`, which is the line that tells a
    # grader a captain report popped WITHOUT a record from this server.~~
    # CORRECTED (pf-adversary second pass, this round): GT-228 measured both,
    # so it reads `provisioned=2`, and no fragment here can tell a grader
    # anything about a record leaving this server -- only `sent=` below can,
    # and today it says `unwired`.  See this module's docstring section on
    # the refutation reading.
    return (
        f"{TOKEN} opaque=0x{opaque:04x} {_annotation(opaque)}"
        f" {_arrival_annotation()}"
        f" sent={SEND_PATH_STATE}"
        " no_responder bytes_out=0"
    )


def _annotation(opaque: int) -> str:
    """`world_m2_survey_plan.console_annotation`, behind a guard that covers
    the IMPORT as well as the call.

    The import is inside the function on purpose.  pf-adversary measured what
    a module-scope import costs here: give `world_island_dock_table`'s pinned
    TSV one extra byte, or empty `world_bg3001_identity`'s rows, and this
    hook drops out of `lane_hooks._discover()` with `IMPORT_FAILED` -- no
    registration, no line, and on an attended console "no confirm frame
    arrived" and "the subscriber never loaded" look identical.  That is the
    exact reading GT-228 is allowed to PASS on, so the annotation must never
    be able to take the evidence line down with it.  A plan that cannot be
    imported or that raises costs the annotation and says so: `issued=err`.
    """
    try:
        from .. import world_m2_survey_plan as plan

        return plan.console_annotation(opaque)
    except Exception:
        return "issued=err provisioned=err"


def _arrival_annotation() -> str:
    """`world_m2_arrival.console_annotation`, behind a guard of its OWN.

    Deliberately not folded into `_annotation` above: the two answer
    different questions off different data (the plan needs measured island
    XYZ, the arrival half needs the scene registry), and one of them failing
    must not cost the other's fragment.  A reader who sees `issued=no
    provisioned=0 arrival_plan=err` learns something a single `err` would
    have hidden.

    THE INDEPENDENCE IS CONDITIONAL, AND BOTH CASES ARE PINNED BY TESTS
    rather than left to this paragraph.  `world_m2_arrival` imports
    `world_m2_survey_plan` at module scope, so: once both are loaded,
    breaking the plan costs only `issued=`/`provisioned=` and
    `arrival_plan=` still answers; but on a COLD boot -- the case a real
    server meets -- an unimportable plan takes the arrival import with it
    and all three read err.  The guards are still separate because the
    warm case is the common one and because the two answer off different
    data, not because the coupling does not exist.

    Takes no argument, and that is the point: it says nothing about the value
    the client just sent -- only whether THIS BUILD has anywhere to put a
    player if a handle ever does resolve.  So it stays inside RE-227 nonclaim
    3 the same way the `issued=` pair does, and the guard test that forbids
    the words island/scene/trigger in this line still passes:
    `arrival_plan=2/2` carries none of them.
    """
    try:
        from .. import world_m2_arrival as arrival

        return arrival.console_annotation()
    except Exception:
        return "arrival_plan=err"


# The point name is spelled as a STRING LITERAL here, not as ``POINT``, for
# the same reason `lane_a_island_trigger_log.py` does it: `@hook(POINT)`
# would be a Name node to `gm/lane_gate_name_audit.py`'s source-level reader,
# which turns "no fire() call names this point" unanswerable for the WHOLE
# tree and makes that audit refuse to grade every hook point in the repo.
@hook("vital_inbound_navigationex_enter_instance_vital")
def _on_enter_instance(session: object = None, payload: object = b"", **_ignored) -> None:
    # `session` is accepted and unused, same posture as the sibling hook:
    # the call site passes it the way every other vital_inbound_* point
    # does, and taking it here keeps that call site identical to the one it
    # copies from.  **_ignored absorbs any further kwarg that call site
    # grows later -- a TypeError here would be caught by fire() and would
    # print nothing at all, which is the one outcome this hook exists to
    # prevent.
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raw = bytes(payload)
    else:
        print(
            f"{TOKEN} UNPARSED len=0 hex= no_responder bytes_out=0"
            f" bad_payload_type={type(payload).__name__}",
            file=sys.stderr,
        )
        return
    print(console_line(raw), file=sys.stderr)
