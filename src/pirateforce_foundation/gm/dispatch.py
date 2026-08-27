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

import bisect
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from . import accounts as gm_accounts
from .command_capture import DEFAULT_CAPTURE_ROOT, capture_raw_gm_command

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9

# pf-adversary (round 50x5xt, "What is intentionally NOT built yet" in
# docs/GM_LANE.md): nothing stopped one authorized GM connection from
# sending 0x51E9 frames back-to-back with no cooldown -- each authorized
# call does a synchronous os.mkdir/os.open/os.write, so a scripted GM
# client could still fill disk even after that round's OSError guard made
# a single write failure survivable. Deferred to its own round because a
# rate limiter needs state SHARED across calls, unlike every other guard
# in this module (which is a pure function of its own arguments) -- that
# raises real thread-safety (this dict is read/written from whichever
# connection-handling thread each call lands on) and test-isolation
# (a naive module-level dict leaks call history across every test in the
# same process unless something resets it) questions this round answers:
#
# * A lock around every read+write of the shared dict, not just the write
#   (a check-then-append with no lock is a classic TOCTOU race between two
#   threads for the SAME account, undercounting or overcounting the window).
# * The default window/limit are generous enough that no existing test in
#   this package's suite (repeated same-second calls for one account name
#   across a handful of test methods) trips it -- this is a flood guard,
#   not a per-command throttle; a real GM issuing several commands within
#   one second is normal and must not be refused.
# * ``reset_rate_limit_state_for_tests()`` lets a test that specifically
#   exercises this guard start from a known-empty state regardless of what
#   ran before it in the same process, without having to reach into a
#   private module attribute.
RATE_LIMIT_WINDOW_SECONDS = 5.0
RATE_LIMIT_MAX_CALLS_PER_WINDOW = 20

_rate_limit_lock = threading.Lock()
_rate_limit_call_history: dict[str, list[float]] = {}


def reset_rate_limit_state_for_tests() -> None:
    """Test-only: clear every account's recorded call history.

    Production code never calls this -- the history is meant to persist for
    the life of the process. Exists so a test that deliberately fills the
    window (or a test that runs after one) does not have to guess what
    history earlier tests in the same process left behind.
    """
    with _rate_limit_lock:
        _rate_limit_call_history.clear()


def _rate_limit_allows(account_name: str, now_ts: float | None) -> bool:
    """True and records this call, or False and records nothing.

    One lock scope covers reading the clock (when ``now_ts`` is not
    supplied), pruning the account's history, the length check, and (only
    when allowed) recording the new call -- a caller never observes or
    acts on a length, or a clock reading, that a second thread already
    invalidated.

    pf-adversary (this round, verify pass): an earlier version of this
    function read ``time.time()`` in the caller, *before* the lock, then
    passed the value in. Two threads for the SAME account could read the
    clock at T_early and T_late (T_early < T_late) but race the lock so
    T_late's ``append`` landed first -- reproduced live with real threads,
    no clock mocking. The prune loop below (``while history and
    history[0] <= cutoff: history.pop(0)``) assumes ascending order; a
    plain ``append`` after that race put a newer timestamp in front of an
    older one, so the older, individually-expired entry could sit unpruned
    behind it until the newer one also aged out -- self-healing, never a
    bypass (the account was held at its cap *longer* than the window, not
    let through early), but still a real deviation from the documented
    window. Reading the clock inside this same lock removes the race for
    every production caller (none passes ``now_ts`` explicitly -- see
    ``handle_gm_run_command_vital``): whoever enters the critical section
    first now also reads the earlier timestamp, by construction, not by
    convention. ``bisect.insort`` (instead of ``append``) closes the
    remaining gap for a caller that DOES pass an explicit, intentionally
    out-of-order ``now_ts`` (a test, or a future caller) and for a wall
    clock that steps backward (NTP correction, VM pause/resume): the
    history list stays sorted regardless of insertion order, so the
    front-pop prune loop's ascending-order assumption holds by
    construction instead of by caller discipline.
    """
    with _rate_limit_lock:
        ts = now_ts if now_ts is not None else time.time()
        cutoff = ts - RATE_LIMIT_WINDOW_SECONDS
        history = _rate_limit_call_history.setdefault(account_name, [])
        while history and history[0] <= cutoff:
            history.pop(0)
        if len(history) >= RATE_LIMIT_MAX_CALLS_PER_WINDOW:
            return False
        bisect.insort(history, ts)
        return True

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

# pf-adversary (gm/ package sweep): MAX_RAW_PAYLOAD_LENGTH bounds one call,
# RATE_LIMIT_MAX_CALLS_PER_WINDOW/RATE_LIMIT_WINDOW_SECONDS bound burst rate
# -- neither bounds SUSTAINED total volume. An already-listed GM account
# scripted to send max-size payloads at the sustained-legal rate (this
# window's own cap, never tripping REFUSAL_RATE_LIMITED) writes roughly
# 4 files/second, each several hundred KB once command_capture.py's hex
# dump expands the raw bytes -- unbounded over time, in one flat directory,
# forever, entirely inside the range of traffic the rate limiter was
# deliberately built generous enough to never refuse (docs/GM_LANE.md,
# round `kzwdle`: "a flood guard, not a per-command throttle"). This is a
# distinct failure mode from the two guards above: it lives inside their
# accepted operating range, not outside it.
#
# Charged per account, in-process, for the life of the process -- same
# accepted scoping as RATE_LIMIT_* above (a restart resets the counter even
# though prior capture files remain on disk; closing that would need a
# directory-size scan on every call, trading a cheap O(1) check for an
# O(n)-in-file-count one for a guard whose job is bounding a *scripted*
# sender, not certifying exact disk usage). The charge is an estimate of
# the actual capture file size (see _estimate_capture_file_bytes), not the
# raw payload length, so the accounting reflects what command_capture.py
# actually writes, not what it receives.
MAX_CAPTURED_BYTES_PER_ACCOUNT = 50 * 1024 * 1024  # 50 MiB

# command_capture._hex_dump renders 16 raw bytes as one line: an 8-hex-digit
# offset + 2 spaces (10), up to 47 columns of hex pairs, 2 spaces, up to 16
# ASCII columns, and a newline -- 76 output bytes per 16 input bytes in the
# worst case, a ~4.75x expansion. The multiplier below is deliberately
# rounder and larger (5x) plus a flat 1 KiB for the header lines
# (account/timestamp/length/decode-section text), so this estimate always
# meets or exceeds what capture_raw_gm_command actually writes -- charging
# the quota too much fails closed slightly earlier than the real disk
# usage would; charging it too little would let real usage exceed the
# stated cap, which this guard exists to prevent.
def _estimate_capture_file_bytes(raw_payload_length: int) -> int:
    return raw_payload_length * 5 + 1024


_capture_quota_lock = threading.Lock()
_capture_quota_bytes_by_account: dict[str, int] = {}


def reset_capture_quota_state_for_tests() -> None:
    """Test-only: clear every account's recorded capture-quota usage.

    Production code never calls this -- the usage total is meant to persist
    for the life of the process, same as ``reset_rate_limit_state_for_tests``
    above. Exists so a test that deliberately fills the quota (or a test
    that runs after one) does not have to guess what usage earlier tests in
    the same process left behind.
    """
    with _capture_quota_lock:
        _capture_quota_bytes_by_account.clear()


def _capture_quota_allows(account_name: str, raw_payload_length: int) -> bool:
    """True and charges the estimate, or False and charges nothing.

    One lock scope covers the read-then-compare-then-write of this
    account's running total, the same reason ``_rate_limit_allows`` above
    takes its own lock for the whole check: two threads for the same
    account must not both read a total that is under the cap, then both
    add their own charge past it.
    """
    estimate = _estimate_capture_file_bytes(raw_payload_length)
    with _capture_quota_lock:
        used = _capture_quota_bytes_by_account.get(account_name, 0)
        if used + estimate > MAX_CAPTURED_BYTES_PER_ACCOUNT:
            return False
        _capture_quota_bytes_by_account[account_name] = used + estimate
        return True


# Refusal reasons are stable strings a caller (or a test) can match on --
# same "name a config error, don't just say False" discipline
# ``runtime.py``'s own ``gm_account_lookup_failed_<ExceptionType>`` event
# already uses for CORE-REQUEST-006.
REFUSAL_NOT_GM = "not_gm_account"
REFUSAL_LOOKUP_FAILED_PREFIX = "gm_account_lookup_failed_"
REFUSAL_PAYLOAD_TOO_LARGE = "payload_too_large"
# pf-adversary (this round): this module's own docstring claims it reuses
# the "refuse by name, not by crash" pattern -- but until this round that
# was only true for the account-lookup call above, not for the disk write
# below. capture_raw_gm_command() does a real os.mkdir/os.open/os.write
# (gm/command_capture.py); ENOSPC, EACCES, a read-only filesystem, or a
# same-second filename collision that also fails O_CREAT|O_EXCL all raise
# OSError subclasses straight out of this function. Since runtime.py wires
# this in with no flag and no surrounding try/except of its own
# (CORE-REQUEST-GM-010, "always on"), an unhandled OSError here would
# propagate out of the inbound-vital handler for one authorized GM command
# and could take the connection-handling thread down for every player --
# exactly the failure mode the module docstring says this lane closed.
REFUSAL_CAPTURE_WRITE_FAILED_PREFIX = "capture_write_failed_"
# See the RATE_LIMIT_* constants above for why this exists and how it is
# scoped. Same shape as every other refusal in this module: authorized
# stays True (the account really is GM), only captured_path/refusal_reason
# say nothing was written this call.
REFUSAL_RATE_LIMITED = "rate_limited"
# See MAX_CAPTURED_BYTES_PER_ACCOUNT's own comment for why this exists and
# how it is scoped/estimated. Same shape as every other refusal in this
# module: authorized stays True (the account really is GM), only
# captured_path/refusal_reason say nothing was written this call.
REFUSAL_CAPTURE_QUOTA_EXCEEDED = "capture_quota_exceeded"


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
    ``MAX_RAW_PAYLOAD_LENGTH``'s own comment for why. The same shape applies
    when the account has made ``RATE_LIMIT_MAX_CALLS_PER_WINDOW`` or more
    calls in the last ``RATE_LIMIT_WINDOW_SECONDS`` (``refusal_reason`` is
    ``REFUSAL_RATE_LIMITED``) -- see the ``RATE_LIMIT_*`` constants' own
    comment for why. The same shape applies once the account's estimated
    total captured bytes for the life of this process would exceed
    ``MAX_CAPTURED_BYTES_PER_ACCOUNT`` (``refusal_reason`` is
    ``REFUSAL_CAPTURE_QUOTA_EXCEEDED``) -- see that constant's own comment
    for why this is a distinct guard from the payload-size and rate-limit
    ones above.

    ``captured_path`` is otherwise set whenever, and only whenever,
    ``command_capture.capture_raw_gm_command`` actually wrote the raw bytes
    and structural decode to disk. It is None for every refusal, including
    the oversized-payload case above and an OS-level write failure
    (``refusal_reason`` a ``REFUSAL_CAPTURE_WRITE_FAILED_PREFIX`` string) --
    an unauthorized, oversized, or unwritable send leaves no capture file,
    by design (see module docstring). ``authorized`` stays True for a write
    failure, same reasoning as the oversized-payload case: the account really
    is GM, the disk just refused this one write.
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
    # pf-adversary (gm/ package sweep): ``type(account_name) is not str``,
    # not ``isinstance`` -- this value flows straight into
    # ``gm_accounts.is_gm_account``'s allowlist test, so a ``str`` subclass
    # lying through ``__eq__``/``__hash__`` here is the same bypass closed
    # in ``accounts.is_gm_account`` itself; this entry point must not
    # reopen it by accepting a subclass one call earlier.
    if type(account_name) is not str or not account_name:
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

    if not _rate_limit_allows(account_name, now_ts):
        return GmDispatchOutcome(
            authorized=True,
            captured_path=None,
            refusal_reason=REFUSAL_RATE_LIMITED,
        )

    if len(raw_payload) > MAX_RAW_PAYLOAD_LENGTH:
        return GmDispatchOutcome(
            authorized=True,
            captured_path=None,
            refusal_reason=REFUSAL_PAYLOAD_TOO_LARGE,
        )

    if not _capture_quota_allows(account_name, len(raw_payload)):
        return GmDispatchOutcome(
            authorized=True,
            captured_path=None,
            refusal_reason=REFUSAL_CAPTURE_QUOTA_EXCEEDED,
        )

    try:
        captured_path = capture_raw_gm_command(
            raw_payload, account_name, capture_root=capture_root, now_ts=now_ts,
        )
    except OSError as error:
        return GmDispatchOutcome(
            authorized=True,
            captured_path=None,
            refusal_reason=f"{REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}{type(error).__name__}",
        )
    return GmDispatchOutcome(
        authorized=True, captured_path=captured_path, refusal_reason=None,
    )
