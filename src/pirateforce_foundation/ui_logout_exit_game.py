"""LANE-UI: UI-B real logout -- "exit game" (LogoutVital 0x1B40 subcode 1).

Scope, evidence, and non-claims
--------------------------------
PANYA-ORDER `20260905_1911` / COO-DECISION `20260905_1948`: LANE-UI's
first real, player-visible job is UI-B ("exit game") closing the session
for real, proven HEADLESS (server-side test only, no live client boot
required for this ticket): the socket closes, the session/position row
is not left stale, and a fresh login can select the same character
again. Per that same order, a button that "works" means the player sees
what the button promises; today a real Exit Game click
in production gets nothing but LANE-A's refusal notice
(`world_logout_button_notice`) -- no ack, no close, no cleanup. This
module is the real behavior.

UI-A ("return to character select", subcode 3) is explicitly OUT of
scope for this module. It needs a NEW screen the client renders after
close; that half stays BLOCKED-ON-RE (COO-DECISION `20260905_1352`:
narrow RE on the `0x709E` handler / whether the client blocks waiting
for a `WorldInfo` reply after a logout ack). Exit Game needs no new
client screen -- the client is quitting on its own -- so it carries none
of that blocker. A frame classified as subcode 3 is left completely
untouched by this module (`handled=False`, reason `not_exit_game_*`) so
LANE-A's existing refusal notice keeps firing for it exactly as before.

This module invents NO new wire bytes and NO new teardown path. It is a
thin, pure orchestration of two building blocks that are ALREADY proven
correct in isolation and are NOT part of the logout-hypothesis apparatus
(that apparatus is hard-gated `production_allowed: False` everywhere --
see `logout_hypothesis.load_logout_hypothesis_scenario` -- specifically
because it must never run for a real player; this module is the
non-hypothesis, real-player replacement queue item 1 of `docs/UI_LANE.md`
calls for):

  * `logout_hypothesis.make_logout_ack_response` -- the HYP-PF-012 echo
    ack composer. Hash-pinned against `LOGOUT_ACK_PC_SHA256` /
    `LOGOUT_ACK_FRAME_SHA256`; unchanged, called verbatim.
  * `session.close_connection()` -- the teardown EVERY ordinary socket
    drop already reaches in production (see that method's own docstring,
    CORE-REQUEST-007): it commits the session lease's `closed_at`,
    releases any held mob-pickup bag cell, and is not gated by any
    hypothesis scenario or `production_allowed` flag. This module does
    not reimplement teardown; it just calls the one that already exists.
  * `session.transport_socket_closer` / the caller's `close_timer_factory`
    -- the SAME delayed clean-shutdown-then-close lever HYP-PF-013 (report
    `PF_LOGOUT_CLOSE001`) already measured headless-correct (ack bytes hit
    the wire strictly before the FIN). Same default delay, same ordering.

Non-claims:
  * Does not decide what happens on screen. It proves the SERVER half of
    "exit game works": ack composed, lease closed in the DB, socket
    scheduled to close, relogin unblocked. Whether/how the real client
    renders anything after its own voluntary exit is not this ticket's
    question -- Exit Game's promise is "the session ends cleanly and you
    can log back in", not a client-visible transition.
  * Does not touch `logout_hypothesis.py`, `runtime.py`, `app.py`, or any
    frozen wire composer. The one hookup point -- calling this function
    from the `LOGOUT_VITAL_ID` dispatch branch only when
    `logout_hypothesis_scenario is None` (a real player, not an attended
    hypothesis boot) -- is a CORE-REQUEST to chief; `runtime.py` is
    outside this lane's write zone.
  * Does not change behavior for any hypothesis-scenario boot: this
    function is never called from that path (the hookup letter asks for
    it only in the `is None` branch), so every existing
    `test_logout_*` scenario test is untouched by this module's
    existence.
  * Does not re-validate `parsed`'s envelope shape beyond what
    `logout_hypothesis.classify_logout_attempt` already checks (outer id,
    version, mask, nested id/version, payload). A malformed frame that
    fails that classifier is reported as `not_exit_game_wrong_envelope` /
    `not_exit_game_wrong_payload` and produces no write, no reply --
    fail-closed, matching every other lane in this dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import logout_hypothesis

# Same pinned delay HYP-PF-013 measured headless-safe
# (`logout_hypothesis.LOGOUT_CLOSE_DELAY_MS`, report PF_LOGOUT_CLOSE001):
# long enough that the frozen listener's send of the ack frame is strictly
# on the wire before the scheduled FIN, short enough the player does not
# notice a stall before the process/socket actually goes away.
DEFAULT_CLOSE_DELAY_MS = logout_hypothesis.LOGOUT_CLOSE_DELAY_MS

_EXIT_GAME_SUBCODE = 1  # UI-B ("exit game"); UI-A (subcode 3) is not handled here


@dataclass(frozen=True)
class ExitGameLogoutOutcome:
    """Result of one dispatch attempt.

    `handled=False` means: this module did nothing (no write, no reply,
    no session mutation) and the caller's existing behavior (today:
    LANE-A's refusal notice) is unaffected. `reason` is always one ASCII
    token, suitable for `session.events` / a wiring test's assertion.
    """

    handled: bool
    reason: str
    actions: tuple = ()


def dispatch_real_exit_game_logout(
    session: Any,
    legacy: Any,
    parsed: Any,
    *,
    close_timer_factory: Callable[[float, Callable[[], None]], Any],
    close_delay_ms: int = DEFAULT_CLOSE_DELAY_MS,
) -> ExitGameLogoutOutcome:
    """Real UI-B teardown for one already-routed LogoutVital frame.

    Caller contract (the CORE-REQUEST hookup installs this): call only
    when `logout_hypothesis_scenario is None` (this is a real player, not
    an attended hypothesis boot) and `parsed.nested_id == LOGOUT_VITAL_ID`.
    Every precondition below is re-checked here regardless -- this
    function never trusts its caller and never assumes control flow
    upstream validated anything; every branch fails CLOSED (no write, no
    ack) rather than guessing.

    ``session`` must expose the same attributes every
    ``PersistentGameSessionState`` instance already carries
    unconditionally (not just under a hypothesis scenario):
    ``foundation`` (with ``.selected`` and ``.close_connection()``),
    ``teleport_sent``, ``runtime_ack_sent``, ``logout_acknowledged``,
    ``logout_ack_count``, ``logout_close_scheduled``, and
    ``transport_socket_closer``.
    """
    classification = logout_hypothesis.classify_logout_attempt(legacy, parsed)
    if classification != f"exact_{_EXIT_GAME_SUBCODE:02d}":
        return ExitGameLogoutOutcome(False, f"not_exit_game_{classification}")
    if session.foundation.selected is None:
        return ExitGameLogoutOutcome(False, "no_selected_character")
    if session.logout_acknowledged:
        return ExitGameLogoutOutcome(False, "already_acknowledged")
    if not session.teleport_sent or not session.runtime_ack_sent:
        return ExitGameLogoutOutcome(False, "wrong_sequence")
    closer = session.transport_socket_closer
    if closer is None:
        return ExitGameLogoutOutcome(False, "no_transport_closer")

    # Composed and pinned before the lease is touched, same discipline as
    # every other lane in this dispatch: nothing is queued unless the
    # close below actually commits.
    pc, frame = logout_hypothesis.make_logout_ack_response(
        legacy, _EXIT_GAME_SUBCODE,
    )
    try:
        closed = session.close_connection()
    except Exception as exc:  # noqa: BLE001 - a courtesy fail-closed path
        # must never take the listener thread down for the player whose
        # click it was, same discipline as `_dispatch_logout_hypothesis`.
        return ExitGameLogoutOutcome(
            False, f"repository_failure_{type(exc).__name__}",
        )
    if not closed:
        return ExitGameLogoutOutcome(False, "already_closed")

    session.logout_acknowledged = True
    session.logout_ack_count += 1
    session.logout_close_scheduled = True
    close_timer_factory(close_delay_ms / 1000.0, closer)

    return ExitGameLogoutOutcome(
        True,
        "ack_then_server_socket_close",
        actions=(
            (
                "UI_LOGOUT_EXIT_GAME_ACK_THEN_SERVER_SOCKET_CLOSE",
                pc, frame, 0.0,
            ),
        ),
    )
