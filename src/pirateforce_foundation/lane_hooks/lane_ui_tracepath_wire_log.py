"""LANE-UI: report-only subscriber for ``CTracePathReqVital`` (``0x4391``)
-- see ``lane_ui_party_wire_log.py``'s module docstring for the shared
shape, limits, and the CORE-REQUEST/letter chain this belongs to.

NOT wired into ``runtime.py`` yet. The point name below
(``vital_inbound_trace_path_req_vital``) is REGISTERED (this module's
import prints ``LANE_HOOK_REGISTERED`` for it, same as every other
``lane_hooks`` module) but never FIRED until a ``lane_hooks.fire(...)`` call
lands inside ``trace_path.py``'s existing dispatch branch
(``runtime.py:7487``, ``nested_id == trace_path.TRACE_PATH_REQ_VITAL_ID``)
-- see ``lane_hooks/__init__.py``'s own module docstring, "ROUND apk7ue,
ACCURACY NOTE", for the precedent this module follows exactly
(``vital_inbound_chat_local_talk`` is the same shape: registered, never
fired, until its own owning lane's dispatch branch adds one line). That one
line is CORE-REQUEST'd to chief in
``notes_to_chief/20260905_0347_LANE-UI-CORE-REQUEST-fire-trace-path-req-observer.md``,
same round this file was written. Until that lands, this module changes
zero behavior on ``main`` -- it exists so the call, once added, has
something ready to fire into, the same reasoning
``logout_dialog_open_hypothesis.py``'s own docstring gives for its own
inert-until-wired module.

WHY THIS IS WORTH BUILDING BEFORE THE WIRING LANDS. The next attended round
that answers ``RE-236`` item (ข) (``CLIENT_RE_QUEUE.md``: click two targets
whose ``QUEST.n_ID``/``MOBS.n_ID`` do not collide, GO! each, compare
``u16@+0x14`` across the two outbound frames) currently has to capture raw
hex and decode it by hand afterward, the way this project's own static
bonus this round did for ``GT-246``'s frame. Once the one dispatch-table
line lands, that same click prints every field of this class -- including
field 1, the discriminator the ticket is testing -- directly to the
server's own console in real time, the same live-decode convenience this
project's other eight ``CORE-REQUEST 1120`` classes already have. This
module is the half of that convenience LANE-UI can build without chief
today; the CORE-REQUEST above is the other half.

Field shape decoded here comes from ``ui_tracepath_wire.py``, already
proven and on ``main`` as of this round.

``consumed=<c>/<n>`` on the decoded line -- see
``lane_ui_party_wire_log.py``'s module docstring for why (pf-adversary,
that round: a decode success with unconsumed trailing bytes must never
read identically to a fully-matched frame).
"""
from __future__ import annotations

import sys

from . import console_safe, hook
from .. import ui_tracepath_wire as wire

production_allowed = True

# The registration below is DELIBERATELY never fired yet -- see this
# module's own docstring, "NOT wired into runtime.py yet", for why and for
# the CORE-REQUEST that is the one thing that changes this. Declaring it
# here (same mechanism ``lane_gm_chat_command.py`` uses for
# ``vital_inbound_chat_local_talk``) makes that a machine-checked fact
# instead of a docstring claim nothing re-verifies:
# ``gm/lane_gate_name_audit.py``'s dead-hook-point scan reds if EITHER side
# of the premise stops holding -- a real ``fire()`` for this point landing
# in ``runtime.py`` without this line being removed in the same PR, or this
# module ceasing to register the point while the line is still here.
registered_but_not_fired = ("vital_inbound_trace_path_req_vital",)

_TOKEN = "LANE_UI_TRACE_PATH_REQ"

_MAX_HEX_BYTES = 96


def _hex_line(payload: bytes) -> str:
    shown = payload[:_MAX_HEX_BYTES]
    truncated = "+" if len(payload) > len(shown) else ""
    return f"{_TOKEN} UNPARSED len={len(payload)} hex={shown.hex()}{truncated} bytes_out=0"


@hook("vital_inbound_trace_path_req_vital")
def _on_trace_path_req(session: object = None, payload: object = b"", **_ignored) -> None:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raw = bytes(payload)
    else:
        print(
            console_safe(
                f"{_TOKEN} UNPARSED len=0 hex= bytes_out=0"
                f" bad_payload_type={type(payload).__name__}"
            ),
            file=sys.stderr,
        )
        return
    fields = wire.decode_trace_path_req_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_trace_path_req_payload(fields))
    print(
        console_safe(
            f"{_TOKEN} decoded consumed={consumed}/{len(raw)}"
            f" field1_u16={fields.field1_u16}"
            f" field2_u16={fields.field2_u16}"
            f" field3_u32={fields.field3_u32}"
            f" field4_u16={fields.field4_u16}"
            f" field5_u16={fields.field5_u16}"
            f" field6_u16={fields.field6_u16}"
            f" field7_u16={fields.field7_u16}"
            f" field8_u8={fields.field8_u8} bytes_out=0"
        ),
        file=sys.stderr,
    )
