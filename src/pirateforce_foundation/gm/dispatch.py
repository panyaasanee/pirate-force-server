"""Inbound dispatch entry point for GM_RunGMCommandVital (0x51E9, client->server).

Every other module in this package -- ``command_wire`` (structural decode),
``command_capture`` (forensic sink), ``commands`` (text grammar/log) -- is a
pure function reachable by any caller; none of them checks who is allowed to
send 0x51E9 before doing its own work.  RE-091 (PASS/DONE) already
established that the *real* client's gate on sending 0x51E9 is a UI widget
(a dedicated GM editor box), not a wire-level check -- so nothing on the
wire stops a non-GM connection from sending this vital, and nothing in this
package before this module refused one.  A naive wiring that called
``command_capture.capture_raw_gm_command`` for every inbound 0x51E9
regardless of sender would let any connected account make this lane write a
file to disk on demand, GM or not -- that is the authorization gap the
previous round (``rounds/GM_20260827_0438_...md``) flagged as needing its
own round rather than a rushed one-line CORE-REQUEST.

This module is that round's answer: the single function this lane asks
``CORE-REQUEST-GM-010`` to wire into ``runtime.py``'s inbound vital dispatch
for id 0x51E9.  It enforces the account-authorization gate FIRST, before any
capture, decode, or log side effect -- reusing ``gm/accounts.py``'s existing
allowlist and the exact "refuse by name, not by crash" pattern
``runtime.py``'s own login-time GM check already uses for a malformed
``gm_accounts.json`` (see ``runtime.py`` ~line 4403-4421, CORE-REQUEST-006):
a config typo must refuse this one command, not take the whole
game-listener thread down for every player's next command.

What this module does NOT do, on purpose:

* It does not decode the two wide strings (``string_0x1c``/``string_0x38``)
  into a ``gm/commands.py`` ``GmCommand`` and does not call
  ``log_gm_command``.  Which field (if either) is a command name versus raw
  argument text is still NOT proven (RE-088's own nonclaim) -- inventing
  that mapping here would be exactly the guess this lane's rules forbid.
  ``gm/commands.py`` already takes plain ``str`` independent of 0x51E9 as
  its own stated policy choice; bridging wire bytes into that grammar stays
  open until RE or an attended capture matrix resolves the mapping.
* It does not execute anything and does not send
  ``GM_RunGMCommandResultVital`` (0x8C77) back -- the result byte's meaning
  is not proven either (RE-088 declines to call it success/error), and this
  lane has no send path outside a ``CORE-REQUEST`` wiring point regardless.

So the visible effect of wiring this in is exactly GM-002's stated goal:
"real bytes captured for every command a GM account actually sends, nothing
captured or written for a non-GM connection." No command yet takes effect
in the game world.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import accounts as gm_accounts
from .command_capture import DEFAULT_CAPTURE_ROOT, capture_raw_gm_command

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9

# pf-adversary (this round): command_capture.py's hex-dump sink is an
# unbounded pure-Python loop with no size cap of its own -- its own
# docstring's promise is "never lose a real capture," which is right for a
# forensic sink, but this module is what makes that sink reachable from a
# live 0x51E9 for the first time. A single authorized-but-hostile or
# scripted GM client sending a many-megabyte payload would block the
# handling thread for tens of seconds and could fill disk per call, once
# CORE-REQUEST-GM-010 wires this into a real socket. No known real
# GM_RunGMCommandVital frame is anywhere near this size (RE-088's proven
# shape is two short wide strings plus three scalars), so refusing an
# oversized payload here costs nothing against any real command and closes
# the gap pf-adversary found rather than leaving it as a silent limitation.
MAX_RAW_PAYLOAD_LENGTH = 65536

# Refusal reasons are stable strings a caller (or a test) can match on --
# same "name a config error, don't just say False" discipline
# ``runtime.py``'s own ``gm_account_lookup_failed_<ExceptionType>`` event
# already uses for CORE-REQUEST-006.
REFUSAL_NOT_GM = "not_gm_account"
REFUSAL_LOOKUP_FAILED_PREFIX = "gm_account_lookup_failed_"
REFUSAL_PAYLOAD_TOO_LARGE = "payload_too_large"


@dataclass(frozen=True)
class GmDispatchOutcome:
    """Result of one ``handle_gm_run_command_vital`` call.

    ``authorized`` is False for both an account simply not on the allowlist
    and a malformed allowlist config -- ``refusal_reason`` tells the two
    apart (``REFUSAL_NOT_GM`` vs a ``gm_account_lookup_failed_*`` string) for
    a caller that wants to log which one happened, without ever raising out
    of this function for either case.

    ``authorized`` can also be True with ``captured_path`` still None: an
    account that IS on the allowlist but sent a payload larger than
    ``MAX_RAW_PAYLOAD_LENGTH`` is a real GM account (so ``authorized`` says
    so truthfully), but nothing is written to disk for that one call
    (``refusal_reason`` is ``REFUSAL_PAYLOAD_TOO_LARGE``) -- see
    ``MAX_RAW_PAYLOAD_LENGTH``'s own comment for why.

    ``captured_path`` is otherwise set whenever, and only whenever,
    ``command_capture.capture_raw_gm_command`` actually wrote the raw bytes
    and structural decode to disk. It is None for every refusal, including
    the oversized-payload case above -- an unauthorized or oversized send
    leaves no capture file, by design (see module docstring).
    """

    authorized: bool
    captured_path: Path | None
    refusal_reason: str | None


def handle_gm_run_command_vital(
    account_name: str,
    raw_payload: bytes,
    *,
    config_path: str | None = None,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> GmDispatchOutcome:
    """Authorize, then (only if authorized) capture one inbound 0x51E9.

    ``account_name`` must be the authenticated login name for the
    connection this payload arrived on -- the same value ``runtime.py``'s
    own GM-state login check already uses (``self.token``), never anything
    read out of ``raw_payload`` itself: the client has no message that
    grants or claims GM status for itself (see ``gm/accounts.py``), so this
    function must not be handed anything the client could have supplied as
    the identity to check.

    ``raw_payload`` must be the vital's payload bytes only (after vital id
    and version in the runtime-vital envelope), the same slice
    ``command_wire``/``command_capture`` already expect -- this function
    does not strip an envelope itself, matching the rest of this package.
    """
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    if not isinstance(raw_payload, (bytes, bytearray)):
        raise TypeError("raw_payload must be bytes")

    try:
        is_gm = gm_accounts.is_gm_account(account_name, config_path)
    except (ValueError, OSError) as error:
        return GmDispatchOutcome(
            authorized=False,
            captured_path=None,
            refusal_reason=f"{REFUSAL_LOOKUP_FAILED_PREFIX}{type(error).__name__}",
        )

    if not is_gm:
        return GmDispatchOutcome(
            authorized=False, captured_path=None, refusal_reason=REFUSAL_NOT_GM,
        )

    if len(raw_payload) > MAX_RAW_PAYLOAD_LENGTH:
        return GmDispatchOutcome(
            authorized=True,
            captured_path=None,
            refusal_reason=REFUSAL_PAYLOAD_TOO_LARGE,
        )

    captured_path = capture_raw_gm_command(
        raw_payload, account_name, capture_root=capture_root, now_ts=now_ts,
    )
    return GmDispatchOutcome(
        authorized=True, captured_path=captured_path, refusal_reason=None,
    )
