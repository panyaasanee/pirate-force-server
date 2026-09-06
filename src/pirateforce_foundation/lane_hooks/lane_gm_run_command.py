"""LANE-GM hook: inbound GM_RunGMCommandVital (0x51E9) dispatch.

Relocated out of runtime.py's inline dispatch block as the FIRST lane_hooks
move-out demo (v6.3 architecture; see the package docstring in
``lane_hooks/__init__.py`` for why this package exists).  This is
deliberately the smallest CORE-REQUEST-010 (LANE-GM) wired: one inbound
vital id, one downstream call, two possible events, no reply frame, no
data threaded back into the composed response.  Every other lane_hooks
candidate this round (CORE-REQUEST-006's GM-state-after-login frame,
CORE-REQUEST-014's Columbus quest dispatch) writes into the composed
START_GAME_RES/actions list further down the same handler -- lifting those
into the fire-and-forget shape ``lane_hooks.fire()`` offers is next round's
work, not this one's (see AGENTS.md, "lane_hooks first PR = skeleton + ONE
smallest move, never the whole board").

Behavior is byte-for-byte unchanged from the block this replaces:
``tests/test_gm_run_command_dispatch_wiring.py`` drives the real dispatcher
end to end and asserts on ``self.events``/absence of a reply frame, not on
runtime.py's internal shape -- it is the regression proof for this move,
not a new test written for it.
"""
from __future__ import annotations

from . import hook
from ..gm.allowlist_probe import announce_not_gm_once
from ..gm.dispatch import REFUSAL_NOT_GM, handle_gm_run_command_vital

# Same convention every other shippable lane module in this project already
# uses (field_mobs.py, columbus_quest_dispatch.py, ...): True means "no
# scenario flag needed, safe to run for every connection." Required
# explicitly by the lane_hooks approval (PANYA-ORDER 20260827_1230,
# COO-DECISION 20260827_1241) as the same gate, not a new one -- a module
# that omits this is withdrawn from _HOOKS right after import (see
# lane_hooks/__init__.py's _discover()) and never fires.
production_allowed = True


@hook("vital_inbound_gm_run_command")
def _on_gm_run_command(session: object, payload: bytes) -> None:
    outcome = handle_gm_run_command_vital(session.token, payload)  # type: ignore[attr-defined]
    if outcome.captured_path is not None:
        session.events.append("gm_run_command_authorized_capture")  # type: ignore[attr-defined]
        return
    session.events.append(  # type: ignore[attr-defined]
        f"gm_run_command_refused_{outcome.refusal_reason}"
    )
    if outcome.refusal_reason == REFUSAL_NOT_GM:
        # The attended boot R322B (pf_bridge
        # `notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-*`) pressed the
        # real client's EXECUTE button, put three real 0x51E9 frames on the
        # wire, and could not tell from outside whether they were refused
        # here, never reached this hook, or hit a capture bug -- because all
        # three look the same from a game client: an empty reply and an
        # empty disk.  The event line above is the answer, and it goes into
        # a structure nobody reads at the keyboard.  One console line, once
        # per process, closes that gap; see `gm/allowlist_probe.py` for why
        # it prints only a count of the allowlist and never its contents,
        # and why nothing about it reaches the client.
        announce_not_gm_once(session.token)  # type: ignore[attr-defined]
