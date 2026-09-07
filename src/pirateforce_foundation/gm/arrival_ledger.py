"""One bounded on-disk line per inbound GM-surface vital that reached dispatch.

WHY THIS EXISTS, IN ONE SENTENCE THAT NAMES A REAL FAILURE.  The attended
boot R322B (pf_bridge
`notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-*`) pressed the real
client's GM EXECUTE button, put three real 0x51E9 frames on the wire, and
afterwards `capture/gm_command_capture/` was EMPTY -- and an empty capture
folder is the SAME observation for four different worlds:

  1. the client never sent anything for that button,
  2. the client sent something with a DIFFERENT vital id (0x162E CheatVital
     has no sink at all, so it also produces an empty folder),
  3. the frame never reached ``gm/dispatch.py`` (no runtime.py dispatch
     branch took it, or ``lane_hooks.fire()`` never reached the hook), or
  4. the frame DID reach ``gm/dispatch.py`` and this lane refused it there
     -- overwhelmingly likely ``REFUSAL_NOT_GM``, because the attended
     account is not in ``gm_accounts.json``.

GT-279's own FAIL branch reads "the folder is empty" as world 1 ("those
buttons do not send 0x51E9").  That is a false negative worth an attended
booking, and it is unrecoverable after the boot ends: the console line
``gm/allowlist_probe.py`` prints scrolls away, prints only ONCE per
process, and covers only world 4's ``REFUSAL_NOT_GM`` branch.

This module splits world 4 off from worlds 1-3 in a form that is still
there the next morning: one fixed-shape ASCII line, appended to
``arrival_ledger.txt``, for every inbound GM-surface vital that reached
``gm/dispatch.py``, WHATEVER the outcome -- captured, refused, or raised.

WHAT ABSENCE OF A LINE DOES *NOT* PROVE (read this before grading a
ticket with this file).  A missing line is NOT proof the frame never
arrived.  It is also produced by: the per-process budgets below being
spent (look for the ``GM_VITAL_LEDGER_FULL`` line, which is written once
per budget precisely so this case is visible); any OSError on the write
(swallowed on purpose -- see ``record_arrival``); a ledger root that is
not writable; and a process that died between the arrival and the write.
Absence is evidence for worlds 1-3 TOGETHER, never for any one of them
alone, and never against world 4 on its own.  Presence is the strong
direction: a line means the frame reached this lane, and its ``outcome=``
field says what this lane then did with it.

WHY THIS IS NOT WRITTEN INTO THE CAPTURE ROOT.  ``gm/dispatch.py`` exists
to hold one property: "nothing captured or written for a non-GM
connection."  The capture root keeps that property literally -- payload
bytes, GM accounts only.  This ledger deliberately DOES write for a non-GM
connection (that is the whole point: world 4 must be visible), so it lives
in its own sibling directory, ``gm_arrival_ledger`` next to
``gm_command_capture``, and pays for that with three bounds the capture
sink does not need:

  * NO PAYLOAD BYTES EVER.  Only ``len=``, an integer.  Nothing an
    unauthenticated peer sends can appear in this file as bytes.
  * EVERY FIELD IS SANITIZED AND LENGTH-CAPPED, so one line is one line:
    the account name goes through the same ASCII-alnum filter
    ``command_capture`` uses for filenames, the outcome token through a
    tighter one, and the vital id is rendered from an int, never echoed
    as text.  A line has a hard maximum length (``MAX_LINE_LENGTH``),
    which is what makes the line budgets below a byte bound too.
  * TWO SEPARATE PER-PROCESS LINE BUDGETS, one for arrivals this lane
    authorized and one for arrivals it did not.  A flood from
    unauthenticated peers can spend only the unauthorized budget, so it
    can never make a real GM's line be the one that does not fit --
    denial of evidence by flooding is the exact attack this file would
    otherwise invite, since its whole value is that a line is there.

NOT A QUOTA CLIENT.  This does not touch ``gm/dispatch.py``'s per-account
capture quota.  That quota is byte-based, refundable, and exists to bound
attacker-chosen bytes on disk; this file writes no attacker bytes and is
bounded by line count instead.  Charging the two together would let a
ledger line push a real capture over the quota, which would turn a
forensic aid into a cause of lost evidence.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from .command_capture import DEFAULT_CAPTURE_ROOT

# Grep anchor, same discipline as `command_capture._UNLINK_STUCK_CONSOLE_TOKEN`
# and `allowlist_probe.GM_ALLOWLIST_CONSOLE_TOKEN`: one fixed ASCII token at
# the start of the line so an attended tester can grep the file without
# knowing this module's shape.
LEDGER_LINE_TOKEN = "GM_VITAL_ARRIVED"
LEDGER_FULL_TOKEN = "GM_VITAL_LEDGER_FULL"

LEDGER_DIR_NAME = "gm_arrival_ledger"
LEDGER_FILENAME = "arrival_ledger.txt"

# The two ids this lane has a dispatch entry point for.  An id outside this
# map is still recorded (the point of the file is arrivals, not a
# whitelist), but its NAME is rendered as `unlisted` rather than echoed
# from anywhere: no caller-supplied text ever reaches this file.
KNOWN_VITAL_NAMES = {
    0x51E9: "GM_RunGMCommandVital",
    0x6CEC: "Activity_CheatCodeVital",
}
UNLISTED_VITAL_NAME = "unlisted"

# Budgets are per process, not per account and not per file: a restart is
# what clears them, exactly like the rate limiter's history in
# gm/dispatch.py.  Sized for the job -- an attended boot presses a handful
# of buttons, so 192 authorized lines is far past "every command a tester
# issues in one session", while 64 unauthorized lines is enough to show a
# refusal pattern and small enough that a flood is cheap to survive.
MAX_AUTHORIZED_LINES = 192
MAX_UNAUTHORIZED_LINES = 64

# Field caps.  The per-field caps are the real bound; MAX_LINE_LENGTH is a
# backstop truncation that no legitimate value reaches (the longest line
# the caps below can produce is 227 characters: 16 token + 23 ts + 11 id +
# 28 name + 48 account + 24 len + 14 authorized + 56 outcome + 7 spaces).
# It exists so that a field cap someone widens later cannot silently turn
# one arrival into a multi-kilobyte line, which is what makes the line
# budgets a byte bound as well (see the module docstring).
MAX_ACCOUNT_LENGTH = 40
MAX_OUTCOME_LENGTH = 48
MAX_LINE_LENGTH = 256

_UNNAMED_ACCOUNT = "unnamed"
_UNNAMED_OUTCOME = "unstated"

_lock = threading.Lock()
_authorized_lines_written = 0
_unauthorized_lines_written = 0
_authorized_full_announced = False
_unauthorized_full_announced = False


def reset_for_tests() -> None:
    """Test-only: forget both budgets and both full-announcements.

    Production never calls this; the budgets are meant to last the life of
    the process.  Exists for the same reason
    ``gm/dispatch.reset_rate_limit_state_for_tests`` does: a test that
    deliberately fills a budget must not depend on what ran before it in
    the same process.
    """
    global _authorized_lines_written, _unauthorized_lines_written
    global _authorized_full_announced, _unauthorized_full_announced
    with _lock:
        _authorized_lines_written = 0
        _unauthorized_lines_written = 0
        _authorized_full_announced = False
        _unauthorized_full_announced = False


def ledger_root_for_capture_root(capture_root: str | os.PathLike) -> Path:
    """The ledger directory that belongs beside ``capture_root``.

    DERIVED, NOT CONFIGURED, on purpose.  Every caller in this package
    already threads a ``capture_root`` through (tests point it at a
    temporary directory; production leaves it at
    ``DEFAULT_CAPTURE_ROOT``).  A second independent setting would be one
    forgotten argument away from a test writing its ledger into the real
    repository tree -- so the ledger root is always the sibling directory
    ``gm_arrival_ledger`` of whatever capture root the call already has.
    """
    return Path(capture_root).parent / LEDGER_DIR_NAME


def _sanitize_field(value: object, limit: int, fallback: str) -> str:
    """ASCII alnum/-/_ only, length-capped, never empty.

    Same drop-don't-replace rule as ``command_capture._sanitize_account``
    (a Thai account name must not become underscore soup), applied here to
    every free-text field rather than only to a filename, because THIS
    file's whole contract is that one arrival is one line: a value
    carrying a newline, a NUL, or 4 KB of text would break the shape the
    tester greps.  A non-``str`` value is not coerced with ``str()`` --
    that would let ``__str__`` put anything at all in the file -- it falls
    back to the fixed label instead.
    """
    if type(value) is not str:
        return fallback
    safe = "".join(
        c for c in value
        if ("a" <= c <= "z" or "A" <= c <= "Z" or "0" <= c <= "9" or c in "-_")
    )
    return safe[:limit] or fallback


def _format_timestamp(now_ts: float | None) -> str:
    if now_ts is None:
        now_ts = time.time()
    try:
        stamp = time.gmtime(float(now_ts))
    except (TypeError, ValueError, OSError, OverflowError):
        # A clock this module cannot read must not lose the arrival: the
        # line is worth more than its timestamp.
        return "unreadable_clock"
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", stamp)


def format_arrival_line(
    vital_id: object,
    account_name: object,
    payload_length: object,
    outcome: object,
    *,
    authorized: bool,
    now_ts: float | None = None,
) -> str:
    """The exact line ``record_arrival`` would append, without writing it.

    Split out so the shape can be tested without a filesystem, and so a
    caller that wants the line for a console can have the same text.
    """
    # `type(x) is int`, not `isinstance`: an int subclass (or a bool, which
    # IS an int subclass) must not decide which name this line carries --
    # the same reason gm/dispatch.py checks `type(account_name) is not str`
    # before the allowlist test.
    is_plain_int = type(vital_id) is int
    if is_plain_int and 0 <= vital_id <= 0xFFFF:
        rendered_id = f"0x{vital_id:04X}"
        name = KNOWN_VITAL_NAMES.get(vital_id, UNLISTED_VITAL_NAME)
    else:
        rendered_id = "unlisted"
        name = UNLISTED_VITAL_NAME
    if type(payload_length) is int and payload_length >= 0:
        # Capped so a bogus length cannot lengthen the line: any real
        # payload is already bounded by MAX_RAW_PAYLOAD_LENGTH one level up.
        rendered_length = str(payload_length)[:20]
    else:
        rendered_length = "-1"
    line = (
        f"{LEDGER_LINE_TOKEN} "
        f"ts={_format_timestamp(now_ts)} "
        f"id={rendered_id} "
        f"name={name} "
        f"account={_sanitize_field(account_name, MAX_ACCOUNT_LENGTH, _UNNAMED_ACCOUNT)} "
        f"len={rendered_length} "
        f"authorized={'yes' if authorized else 'no'} "
        f"outcome={_sanitize_field(outcome, MAX_OUTCOME_LENGTH, _UNNAMED_OUTCOME)}"
    )
    return line[:MAX_LINE_LENGTH]


def _append_line(ledger_root: Path, line: str) -> bool:
    """Append one line.  True if it reached the file, False on any OSError.

    ONE ``os.write`` OF ONE COMPLETE LINE, to a descriptor opened
    ``O_APPEND``: that is what keeps two connection threads from
    interleaving half-lines.  ``O_APPEND`` makes the seek-and-write one
    operation in the kernel, and a write this short is not split in
    practice -- but the module lock in ``record_arrival`` is what this file
    actually relies on for ordering and for the budget counters; the flag
    is the belt to that lock's braces, for the case where some other
    process has the same file open.
    """
    payload = (line + "\n").encode("ascii", "replace")
    try:
        os.makedirs(ledger_root, mode=0o700, exist_ok=True)
        fd = os.open(
            os.path.join(ledger_root, LEDGER_FILENAME),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
    except OSError:
        return False
    try:
        os.write(fd, payload)
    except OSError:
        return False
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return True


def record_arrival(
    vital_id: object,
    account_name: object,
    payload_length: object,
    outcome: object,
    *,
    authorized: bool,
    capture_root: str | os.PathLike = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> str | None:
    """Record one arrival.  Returns the line written, or None if none was.

    NEVER RAISES FOR A DISK PROBLEM.  This function is called from
    ``gm/dispatch.py``'s gate chain, which is called from a lane hook, which
    is called from the game listener thread: a full disk, a read-only
    volume, or a permissions change must cost the arrival's LINE, never the
    player's connection.  Every OSError is swallowed and reported as
    ``None``.

    NOTHING ELSE IS SWALLOWED.  Argument types are not validated and not
    coerced either -- every field goes through the sanitizers above, which
    already refuse to put a non-``str`` (or an unrenderable int) in the
    file.  A programmer error here shows up as ``account=unnamed`` in the
    file, not as a crashed connection and not as a silent skip.
    """
    global _authorized_lines_written, _unauthorized_lines_written
    global _authorized_full_announced, _unauthorized_full_announced
    ledger_root = ledger_root_for_capture_root(capture_root)
    with _lock:
        if authorized:
            spent, budget = _authorized_lines_written, MAX_AUTHORIZED_LINES
        else:
            spent, budget = _unauthorized_lines_written, MAX_UNAUTHORIZED_LINES
        if spent >= budget:
            # Announce exhaustion exactly once per budget, so a reader can
            # tell "no line for this arrival because the budget is spent"
            # from "no line because nothing arrived" -- the same
            # distinction this whole module exists to make, one level up.
            already = (
                _authorized_full_announced if authorized
                else _unauthorized_full_announced
            )
            if already:
                return None
            if authorized:
                _authorized_full_announced = True
            else:
                _unauthorized_full_announced = True
            full_line = (
                f"{LEDGER_FULL_TOKEN} "
                f"ts={_format_timestamp(now_ts)} "
                f"authorized={'yes' if authorized else 'no'} "
                f"budget={budget} "
                f"further_arrivals_of_this_kind_are_not_recorded"
            )
            return full_line if _append_line(ledger_root, full_line) else None
        line = format_arrival_line(
            vital_id,
            account_name,
            payload_length,
            outcome,
            authorized=authorized,
            now_ts=now_ts,
        )
        if not _append_line(ledger_root, line):
            # A failed write spends no budget: the next arrival (after the
            # disk recovers) still gets its line.
            return None
        if authorized:
            _authorized_lines_written += 1
        else:
            _unauthorized_lines_written += 1
        return line
