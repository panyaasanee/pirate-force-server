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
anything else with meaning yet, and it does NOT mean the confirm sequence
that produced it has been seen live on a real client (RE-227's own
reachability proof for this branch is synthetic; see the dispatch-wiring
test's own docstring).  `UNPARSED` means the payload did not match the fixed
shape -- wrong length, wrong leading tag, or a wrong trailer -- and the raw
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
    # scene, or Trigger-TIP id; chief 09:10 restates the same limit.
    return f"{TOKEN} opaque=0x{opaque:04x} no_responder bytes_out=0"


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
