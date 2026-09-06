"""LANE-GM hook: inbound Activity_CheatCodeVital (0x6CEC) dispatch.

Same shape as ``lane_gm_run_command.py`` next to it, and deliberately so:
this house's convention -- stated in ``runtime.py``'s own TRIGGER_VITAL
comment -- is that THE REQUESTER WRITES THE HOOK and the requester's
letter asks chief for the one call site only chief may add.  Round
`eu2g1d`'s first draft of CORE-REQUEST-GM-062 asked chief for an inline
``elif`` calling ``gm.dispatch.handle_activity_cheat_code_vital``
directly, while citing ``tests/test_gm_run_command_dispatch_wiring.py`` as
the test shape.  Those two do not fit together: 0x51E9's ``elif`` does not
call dispatch at all, it fires ``vital_inbound_gm_run_command``, and that
wiring test asserts on the ``session.events`` entries THIS kind of module
appends.  A direct inline call emits no event, so the cited test would
have been unreachable unless chief put lane logic back inside
``runtime.py`` -- exactly what ``lane_hooks`` exists to prevent
(pf-adversary, round `eu2g1d`, D12).  This module is what makes GM-062 the
one-line ask it claims to be.

WHAT FIRING THIS COSTS A NON-GM PLAYER: nothing.  The handler it calls
runs the account-authorization gate first, writes no file for an
unauthorized sender, and sends no reply frame either way -- the six
fields' semantics are unproven, so nothing here decodes a meaning or acts
on one.  A capture file appears only for an account already on the
``gm_accounts`` allowlist.

NOT CLAIMED: that any client has ever sent 0x6CEC (both rows in
``PF_FIELD_VALIDATION.tsv`` read ``NOT_OBSERVED``), nor that any GMUI
button sends it.  This hook is what makes that question ANSWERABLE from an
attended round instead of guessed at -- if the folder stays empty after
every button is clicked, that is now a measurement rather than a gap.
"""
from __future__ import annotations

from . import hook
from ..gm.dispatch import handle_activity_cheat_code_vital

# Same convention every other shippable lane module uses: True means "no
# scenario flag needed, safe to run for every connection."  A module that
# omits this is withdrawn from _HOOKS right after import (see
# lane_hooks/__init__.py's _discover()) and never fires.
production_allowed = True

# NOT FIRED YET, DECLARED RATHER THAN LEFT FOR THE AUDIT TO FIND.
# `gm/lane_gate_name_audit.py`'s dead-hook-point scan reds on a registered
# point no `fire()` names -- correctly: a hook nothing calls is a promise
# nobody keeps.  The call site is CORE-REQUEST-GM-062, chief's one edit.
# THE COMMIT THAT ADDS THAT `fire()` MUST DELETE THIS DECLARATION IN THE
# SAME COMMIT -- the same scan reds the other way (a stale declaration over
# a point that IS fired is a silencer over a question nobody is asking any
# more).  Exactly the shape LANE-UI's `lane_ui_tracepath_wire_log.py`
# carried while its own CORE-REQUEST was pending, and removed the day chief
# granted it.
registered_but_not_fired = ("vital_inbound_activity_cheat_code",)


@hook("vital_inbound_activity_cheat_code")
def _on_activity_cheat_code(session: object, payload: bytes) -> None:
    outcome = handle_activity_cheat_code_vital(session.token, payload)  # type: ignore[attr-defined]
    if outcome.captured_path is not None:
        session.events.append("activity_cheat_code_authorized_capture")  # type: ignore[attr-defined]
    else:
        session.events.append(  # type: ignore[attr-defined]
            f"activity_cheat_code_refused_{outcome.refusal_reason}"
        )
