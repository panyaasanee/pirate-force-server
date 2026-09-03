"""LANE-A: make the 0x1FB2 frames that vanish silently today visible.

WHAT THIS IS FOR (COO-DECISION 20260904_0343 item 4, narrowed by
PANYA-INFO 20260904_0409 item 1)

R307 measured five `TriggerVital` (0x1FB2) frames arriving from a real client
sailing the ocean scene, and zero answers: nothing in this server branches on
that nested id, so each frame is dispatched, matched by nothing, and dropped
without a word on the console.  M2 is blocked on a question those frames may
already answer -- the owner says docking on the real server is "sail the ship
into the island and the captain report window pops by itself" (her words,
PANYA-INFO 0409), and `world_island_dock_table` shows the client's own tables
give every island a trigger id in one no-click-verb block (153 = Prison Exile
Island, 154 = Spice Paradise Island).

So this hook prints what arrived.  That is its whole job.

IT SENDS NOTHING.  No frame is composed, no bytes are queued, no session
state is touched, nothing is returned.  `lane_hooks.fire()` is report-only by
construction (its own docstring), and this module stays inside that shape on
purpose: the point of the round is to learn whether the island ids ever
appear on the wire, and answering a frame we have not yet decoded would be
guessing an opcode -- which this lane is forbidden to do and which
COO-DECISION 0343 item 4 explicitly excluded.  The day a capture shows the
ids, the responder is a separate PR with its own evidence.

IT IS NOT WIRED YET.  There is no `lane_hooks.fire("vital_inbound_trigger_
vital", ...)` call site in `runtime.py` today; adding an insertion point is a
chief-owned edit (lane_hooks/__init__.py's `hook()` docstring says so in as
many words).  The one-line CORE-REQUEST rides in this round's PR body.  Until
chief lands it this module registers and never fires -- the same harmless
state `lane_gm_chat_command` is already in -- and the registration line
`LANE_HOOK_REGISTERED ... vital_inbound_trigger_vital` on stderr at boot is
how you tell it is loaded.  Registering ahead of the call site is deliberate:
it means the attended capture round can happen the moment the one line lands,
without a second lane round in between.

WHAT A LINE MEANS, AND WHAT IT DOES NOT
An `ISLAND` line means "the client fired trigger id N, and the client's own
tables call N a named travel destination".  It does NOT mean the frame is the
docking frame, that the server understood it, or that anything was sent back;
every line says `no_responder bytes_out=0` for exactly that reason.  A
`PROP` line is the R307 case (Seafood Cargo and friends).  `UNPARSED` means
the payload did not walk cleanly as tags -- the hex is printed so the next
round works from bytes rather than from this module's opinion of them.
"""
from __future__ import annotations

import sys

from . import hook
from .. import world_island_dock_table as islands


production_allowed = True

POINT = "vital_inbound_trigger_vital"
TOKEN = "LANE_A_TRIGGER_VITAL"

# gm/lane_gate_name_audit.py's dead-hook-point half: this module registers a
# point nothing fires yet, ON PURPOSE (see the paragraph above), and this is
# the house declaration that says so out loud instead of leaving the audit to
# report a defect.  It is a declaration, not a mute button: the audit's
# inverse guard goes RED the moment something DOES fire this point, so the
# chief PR that adds the `lane_hooks.fire("vital_inbound_trigger_vital", ...)`
# call site must delete this line in the same commit.
registered_but_not_fired = ("vital_inbound_trigger_vital",)

# The trigger id rides in a tag 0x0F (u16 LE) field, per the R307 capture
# shape `12 B2 1F 0B 01 0F <u16 trigger> 00 0B 04 2A x 2A y 2A z` (letter
# notes_to_chief/20260903_1901, five frames, 69 bytes each).
TRIGGER_ID_TAG = 0x0F

# Fixed-width tag sizes taken from the frozen encoders in
# current/pf_login_game_server_v141.py (u8tag/u16tag/u32tag/qwordtag/f32tag).
# Deliberately a closed set: an unknown tag stops the walk and the line says
# UNPARSED, rather than the walker guessing a width and reading a trigger id
# out of the middle of some other field.
_TAG_WIDTHS = {
    0x05: 1,
    0x08: 1,
    0x0B: 1,
    0x0F: 2,
    0x14: 4,
    0x2A: 4,
    0x32: 8,
}
# Length-prefixed tags: tag, then u32 byte count, then that many bytes.
_TAG_LENGTH_PREFIXED = (0x44, 0x48)

# A capture-sized ceiling on the hex a single line may print.  The R307
# frames are 69 bytes whole; a malformed or hostile payload is not a reason
# to write a megabyte into the console a grader reads.
_MAX_HEX_BYTES = 96


def first_tag_value(payload: bytes, tag: int) -> int | None:
    """The first ``tag`` value in ``payload``, walking tags in order.

    Returns None when the payload does not walk cleanly all the way to a
    match: an unknown tag byte, a truncated field, or a length prefix that
    runs past the end.  Never raises, never scans for a loose byte pattern --
    a 0x0F that happens to sit inside a float is not a trigger id.
    """
    i = 0
    end = len(payload)
    while i < end:
        code = payload[i]
        i += 1
        if code == tag:
            width = _TAG_WIDTHS.get(code)
            if width is None or i + width > end:
                return None
            return int.from_bytes(payload[i:i + width], "little")
        width = _TAG_WIDTHS.get(code)
        if width is not None:
            if i + width > end:
                return None
            i += width
            continue
        if code in _TAG_LENGTH_PREFIXED:
            if i + 4 > end:
                return None
            size = int.from_bytes(payload[i:i + 4], "little")
            i += 4
            if size > end - i:
                return None
            i += size
            continue
        return None
    return None


def console_line(payload: bytes) -> str:
    """The exact ASCII line this hook prints for ``payload``.  Never raises.

    Split out from the hook so a test can assert the line for the five R307
    frames without standing up a session or capturing stderr.
    """
    trigger_id = first_tag_value(payload, TRIGGER_ID_TAG)
    if trigger_id is None:
        shown = payload[:_MAX_HEX_BYTES]
        truncated = "+" if len(payload) > len(shown) else ""
        return (
            f"{TOKEN} UNPARSED len={len(payload)} hex={shown.hex()}{truncated}"
            " no_responder bytes_out=0"
        )
    return (
        f"{TOKEN} {islands.describe_trigger_id(trigger_id)}"
        " no_responder bytes_out=0"
    )


# The point name is spelled as a STRING LITERAL here, not as ``POINT``.
# gm/lane_gate_name_audit.py reads @hook() arguments from source: a Name node
# makes "no fire() call names this point" unanswerable for the WHOLE tree, and
# the audit correctly refuses to grade any hook point in the repository while
# one dynamic name is in play.  Measured -- the first draft of this file used
# ``@hook(POINT)`` and turned that audit red for every lane.
@hook("vital_inbound_trigger_vital")
def _on_trigger_vital(session: object = None, payload: object = b"", **_ignored) -> None:
    # `session` is accepted and unused: the call site chief will write passes
    # it the way every other vital_inbound_* point does, and taking it here
    # keeps that call site identical to the one it copies from.  **_ignored
    # absorbs any further kwarg that call site grows later -- a TypeError
    # here would be caught by fire() and would print nothing at all, which is
    # the one outcome this hook exists to prevent.
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raw = bytes(payload)
    else:
        # Untrusted-input coercion, same posture as the census call site:
        # a non-bytes payload is a call-site bug, and the line that says so
        # is worth more than an exception fire() would swallow into one
        # LANE_HOOK ... ERR line with no id in it.
        print(
            f"{TOKEN} UNPARSED len=0 hex= no_responder bytes_out=0"
            f" bad_payload_type={type(payload).__name__}",
            file=sys.stderr,
        )
        return
    print(console_line(raw), file=sys.stderr)
