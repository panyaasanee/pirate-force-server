"""LANE-UI: report-only subscriber for ``CTracePathReqVital`` (``0x4391``)
-- see ``lane_ui_party_wire_log.py``'s module docstring for the shared
shape, limits, and the CORE-REQUEST/letter chain this belongs to.

WIRED into ``runtime.py``. The point name below
(``vital_inbound_trace_path_req_vital``) is REGISTERED (this module's
import prints ``LANE_HOOK_REGISTERED`` for it, same as every other
``lane_hooks`` module) and, since chief (LANE-E) round 5e00uw, is also
FIRED: ``lane_hooks.fire(...)`` sits inside ``trace_path.py``'s existing
dispatch branch (``nested_id == trace_path.TRACE_PATH_REQ_VITAL_ID``, grep
that rather than trusting a line number). That call was CORE-REQUEST'd to
chief in
``notes_to_chief/20260905_0347_LANE-UI-CORE-REQUEST-fire-trace-path-req-observer.md``,
the same round this file was written, and granted the round after. It is
log-only: ``fire()`` returns no value and touches no control flow, so the
empty-vector reply CORE-REQUEST-025 installed in that branch is unchanged,
and this module still decides nothing about the request's own fields
(``RE-236`` item (b) stays open). Before that call landed, this module
changed zero behavior on ``main`` -- it existed so the call, once added,
had something ready to fire into, the same reasoning
``logout_dialog_open_hypothesis.py``'s own docstring gives for its own
inert-until-wired module.

WHY THIS IS WORTH BUILDING BEFORE THE WIRING LANDS. The next attended round
that answers ``RE-236`` item (b) (``CLIENT_RE_QUEUE.md``: click two targets
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

# This point IS fired now.  ``runtime.py``'s ``CTracePathReqVital`` dispatch
# branch calls ``lane_hooks.fire("vital_inbound_trace_path_req_vital", ...)``
# as of chief (LANE-E) round 5e00uw, granting LANE-UI's CORE-REQUEST of
# 20260905_0347.  The ``registered_but_not_fired`` declaration that stood
# here is therefore removed in the same commit that added that call, exactly
# as the comment it replaces (and the CORE-REQUEST itself) required:
# ``gm/lane_gate_name_audit.py``'s dead-hook-point scan reds if a real
# ``fire()`` lands while the declaration is still present.

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
