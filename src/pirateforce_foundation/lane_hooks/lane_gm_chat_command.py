"""LANE-GM hook: GM commands typed into the ordinary chat box (0xAC52).

Second LANE-GM hook, and the first one registered for a point runtime.py
does NOT fire yet.  That is deliberate and is the whole reason this file
exists in this PR: `lane_hooks`' contract is that a point name is agreed
out of band between the call site and the hook module (see the `hook`
decorator's docstring), so the lane can land, test and review its half
before chief's three-line half exists.  Registering onto a point nothing
fires is inert -- `_HOOKS` gains an entry, `fire()` is never called for it,
and `LANE_HOOK_REGISTERED` prints at import exactly as for the live hook
next to it.

CORE-REQUEST-GM-002 (pf_bridge/notes_to_chief) asks chief for the missing
half: a `lane_hooks.fire("vital_inbound_chat_local_talk", ...)` at the
0xAC52 branch of the nested-vital router, shaped exactly like the 0x51E9
one already at runtime.py:4824.  Until that lands this module changes
nothing about how the server behaves for anybody, GM or not.

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
