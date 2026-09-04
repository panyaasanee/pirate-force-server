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

IT IS WIRED.  `runtime.py`'s TriggerVital dispatch branch (`nested_id ==
legacy.TRIGGER_VITAL`, next to the GM_RUN_GM_COMMAND_VITAL_ID branch it
copies the shape of) calls `lane_hooks.fire("vital_inbound_trigger_vital",
session=self, payload=bytes(parsed.nested_payload))` on every inbound
TriggerVital frame -- CORE-REQUEST of `pf_bridge/notes_to_chief/
20260904_0434` and `20260904_0437` (LANE-A), landed by LANE-E round zsctq7.
The registration line `LANE_HOOK_REGISTERED ... vital_inbound_trigger_vital`
on stderr at boot, plus a `LANE_A_TRIGGER_VITAL ...` line per frame once one
arrives, is how you tell it is firing.

WHAT A LINE MEANS, AND WHAT IT DOES NOT
An `ISLAND` line means "the client fired trigger id N, and the client's own
tables call N a named travel destination".  It does NOT mean the frame is the
docking frame, that the server understood it, or that anything was sent back;
every line says `no_responder bytes_out=0` for exactly that reason.  A
`PROP` line is the R307 case (Seafood Cargo and friends).  `UNPARSED` means
the payload did not walk cleanly as tags -- the hex is printed so the next
round works from bytes rather than from this module's opinion of them.

GT-228 OBSERVED OVERRIDE (COO-DECISION 20260904_1345 item 3(a))
-----------------------------------------------------------------
R308 (PASS, OBSERVER_CONFIRMED 2026-09-04T13:22+07:00,
`pf_bridge/notes_to_chief/20260904_1331_KA1A-R308-RESULTS-*`) measured the
REAL wire ids at island contact: id **2** at Prison Exile Island (3/3
contacts) and id **3** at Spice Paradise Island (2/2 contacts) -- NOT 153 or
154, which is what `world_island_dock_table`'s own dock rows use and what
this hook used to key off of.  No 0x1FB2 frame carrying 153 or 154 has ever
been captured; the two id spaces (dock-table `trigger_id` vs this frame's
0x0F tag) may simply not be the same namespace at all (nonclaim ①/② of the
R308 letter -- this is not proven, only accepted as the PRIMARY hypothesis
per COO-DECISION item 1).

So `M2_OBSERVED_ISLAND_TRIGGER_IDS` below overrides the general dock-table
classification for exactly ids 2 and 3, printing ISLAND with the matching
dock row's name (153 Prison Exile / 154 Spice Paradise) while keeping the
WIRE id in the `id=` field, so a reader can always tell "what arrived" from
"what we think it means".  KNOWN, ACCEPTED FALSE-POSITIVE RISK: `Trigger_TIP`
itself names ids 2/3 "Edmund Hidden Treasure"/"Seafood Cargo", ordinary sea
props, and R307 (round `ufcemz`, before GT-228 existed) captured a REAL id=3
frame during ordinary sailing (frame #217 in this hook's own test fixture)
that this override now ALSO reports as ISLAND.  That collision is exactly
what the narrow RE ticket opened alongside this decision (COO 1345 item
3(d): what the client does with 0x1FB2's response, and how many paths open
the captain-report page) exists to resolve -- this override is a deliberate,
documented hypothesis, not a claim that ids 2/3 mean ISLAND unconditionally.
"""
from __future__ import annotations

import sys

from . import hook
from .. import world_island_dock_table as islands


production_allowed = True

POINT = "vital_inbound_trigger_vital"
TOKEN = "LANE_A_TRIGGER_VITAL"

# The trigger id rides in a tag 0x0F (u16 LE) field.  PROVEN STATICALLY, not
# inferred from the capture: pf_bridge/external/PF_SERIALIZER_FIELDS.tsv gives
# the TriggerVital serializer at 0x006007C0 (span sha256 2f30bd87...791a12) as
# six fields, W and R alike -- order 1 tag 0x0F +0x14 2 bytes ALWAYS, order 2
# tag 0x0B, order 3 a subcall, orders 4/5/6 tag 0x2A -- so the trigger id is
# the FIRST field, the tag set is closed at three tags for this message, and
# no 0x12 can appear inside it.  Those are exactly the three things the walker
# below relies on.  The R307 capture shape
# `12 B2 1F 0B 01 0F <u16 trigger> 00 0B 04 2A x 2A y 2A z`
# (notes_to_chief/20260903_1901, five frames, 69 bytes each) AGREES with that
# row; it is the corroboration, not the source.  (pf-adversary D8: the first
# draft cited only the capture, which is a client-observable correlation
# standing in for grade A evidence that already existed.)
TRIGGER_ID_TAG = 0x0F

# Fixed-width tag sizes taken from the frozen encoders in
# current/pf_login_game_server_v141.py (u8tag/u16tag/u32tag/qwordtag/f32tag).
# Deliberately a closed set: an unknown tag stops the walk and the line says
# UNPARSED, rather than the walker guessing a width and reading a trigger id
# out of the middle of some other field.
#
# 0x12 is DELIBERATELY ABSENT even though `parse_outer` reads it as a u16
# (outer id, vital count, nested id).  0x12 is the tag that starts another
# VITAL, and a payload for one vital can be followed by a second one -- R307's
# own frames are `vital_count = 2`, a TriggerVital then a position vital.
# Teaching this walker to step over a 0x12 would let it walk out of the
# trigger vital and find a 0x0F belonging to the NEXT vital, and report that
# u16 as a trigger id.  A wrong island name on the console is worse than no
# name: `UNPARSED` prints the hex and the next round works from bytes.  The
# known shape puts the trigger id before any 0x12, so this costs nothing
# today and refuses rather than guesses if the shape ever changes.
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

# Wire trigger id (as observed on 0x1FB2, R308) -> dock table trigger_id
# (world_island_dock_table.DESTINATION_ROWS) whose name/scene this hook
# reports.  See the module docstring's "GT-228 OBSERVED OVERRIDE" section
# for what this does and does not claim.
M2_OBSERVED_ISLAND_TRIGGER_IDS: dict[int, int] = {
    2: 153,  # Prison Exile Island -- GT-228 R308, id=2 on 3/3 contacts
    3: 154,  # Spice Paradise Island -- GT-228 R308, id=3 on 2/2 contacts
}


def _m2_observed_override_line(wire_trigger_id: int, dock_trigger_id: int) -> str:
    """The console body for a wire id in ``M2_OBSERVED_ISLAND_TRIGGER_IDS``.

    Keeps the WIRE id in ``id=`` (what actually arrived) and the dock row's
    own name/scene from ``dock_trigger_id`` (what we now believe it means),
    tagged ``wire=OBSERVED_GT228_R308`` so this is never confused with
    ``world_island_dock_table``'s own ``wire_scene_id_status`` grading, which
    this override does not carry (no 0x1FB2 frame with 153/154 has ever been
    seen, so that field would have nothing to grade).
    """
    row = islands.destination_for_trigger_id(dock_trigger_id)
    name = islands.console_safe(row.name) if row is not None else "?"
    scene = row.scene_name_tip_id if row is not None else "?"
    return (
        f"id={wire_trigger_id} name={name} {islands.CLASS_ISLAND}"
        f" scene={scene} wire=OBSERVED_GT228_R308"
    )


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
    dock_trigger_id = M2_OBSERVED_ISLAND_TRIGGER_IDS.get(trigger_id)
    if dock_trigger_id is not None:
        body = _m2_observed_override_line(trigger_id, dock_trigger_id)
    else:
        body = islands.describe_trigger_id(trigger_id)
    return f"{TOKEN} {body} no_responder bytes_out=0"


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
