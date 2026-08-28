"""LANE-GM hook: GM commands typed into the ordinary chat box (0xAC52).

Second LANE-GM hook.  It landed one round BEFORE the point it registers
for existed, which is the whole reason this file could ship on its own:
`lane_hooks`' contract is that a point name is agreed out of band between
the call site and the hook module (see the `hook` decorator's docstring),
so the lane can land, test and review its half first.  For that one round
the registration was inert -- `_HOOKS` gained an entry, `fire()` was never
called for it, and `LANE_HOOK_REGISTERED` printed at import exactly as for
the live hook next to it.

CORE-REQUEST-GM-028 (pf_bridge/notes_to_chief) asked chief for the other
half and chief wired it in round `lo7e03` (R214): a
`lane_hooks.fire("vital_inbound_chat_local_talk", session=..., payload=...)`
at the 0xAC52 branch of the nested-vital router, shaped like the 0x51E9 one
in the same method, but with no `return` and no `rx_frames` bump so the
frame's own path stays byte-identical.  This hook now runs on every chat
line of every flagless boot; what it DOES for a player who is not on the
gm_accounts allowlist is still nothing at all.

WHY CHAT AND NOT THE GM BUTTON: see `gm/chat_command.py`'s module
docstring.  Short version: GT-101-R3 and GT-103 both measured `BT_GM`
clicks as completely silent (0 x 0x51E9 across a whole boot, four UI
states), while the chat box has been proven three times to put every typed
line on the wire.

FAIL-CLOSED: every decision this hook makes is `handle_local_talk_chat`'s,
which refuses on identity before it decodes anything.  This module adds no
authorization logic of its own -- if it did, there would be two places to
get GM permission wrong instead of one.
"""
from __future__ import annotations

from . import hook
from ..gm.chat_command import handle_local_talk_chat

# Same convention every other shippable lane module uses: True means "no
# scenario flag needed, safe to run for every connection". Required by the
# lane_hooks approval (PANYA-ORDER 20260827_1230, COO-DECISION
# 20260827_1241); a module that omits it has its hooks withdrawn right
# after import and never fires.
#
# Safe for every connection because "runs for everyone" and "does something
# for everyone" are different things: this hook runs on every chat line any
# player sends and refuses on the very first check for every account that
# is not in gm_accounts.json -- which, by default, is every account there
# is. The always-on requirement (no production_allowed=false gate) is rule
# 1 of this lane's founding order; the allowlist is what keeps it invisible
# to ordinary players.
production_allowed = True


@hook("vital_inbound_chat_local_talk")
def _on_chat_local_talk(session: object, payload: bytes) -> None:
    # Argument order matters and is asserted by
    # tests/test_gm_chat_command.py::HookBehaviourTests: the FIRST argument
    # is the authenticated login name off the session, the SECOND is the
    # client-supplied bytes. Passing the payload as the identity would hand
    # `is_gm_account` something a client controls.
    outcome = handle_local_talk_chat(session.token, payload)  # type: ignore[attr-defined]
    if outcome.command is not None:
        session.events.append(  # type: ignore[attr-defined]
            f"gm_chat_command_accepted_{outcome.command.name}"
        )
        return
    # Every other path is a refusal, including the ordinary-chat one. The
    # event names stay coarse on purpose: `not_gm_account` is by far the
    # most common outcome on a real server (every non-GM player's every
    # chat line), and the refusal reasons never carry the typed text, so a
    # console full of these leaks nothing about what players said.
    session.events.append(  # type: ignore[attr-defined]
        f"gm_chat_command_refused_{outcome.refusal_reason}"
    )
