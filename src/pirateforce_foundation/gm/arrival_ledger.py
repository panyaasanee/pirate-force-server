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
arrived.  It is also produced by: this account's line budget below being
spent (look for the ``GM_VITAL_LEDGER_FULL`` line, written once per
budget precisely so this case is visible); any OSError on the write
(swallowed on purpose -- see ``record_arrival``); a ledger root that is
not writable; a server process whose working directory is not the one the
reader is looking under (which is why the first line of every process is
``GM_VITAL_LEDGER_OPENED``, carrying the ABSOLUTE path and the pid, and
why that same line is printed to the console once); and a process that
died between the arrival and the write.  Absence is evidence for worlds
1-3 TOGETHER, never for any one of them alone, and never against world 4
on its own.  Presence is the strong direction: a line means the frame
reached this lane, and its ``outcome=`` field says what this lane then did
with it.

AND ``id=``/``name=`` ARE THIS SERVER'S ROUTING, NOT A WIRE MEASUREMENT
(pf-adversary, round `5rxy86`, D9).  Each entry point hands this module
the id it is the handler for, so a line says "the frame that reached the
0x51E9 handler", never "the opcode on the wire was 0x51E9".  The wire
question -- which opcode a given GMUI button emits -- is answered by the
client-side hexdump in the attended ticket, not by this file.

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
    as text.  A truncated field ends in ``~`` so a reader never mistakes a
    cut token for a whole one.
  * THE LINE BUDGET IS PER ACCOUNT, NOT PER PROCESS AND NOT PER
    AUTHORIZATION STATE (pf-adversary, round `5rxy86`, D1 -- this file's
    first shape got this wrong in the one way that mattered).  A budget
    split by "authorized vs not" does NOT protect the attended tester,
    because the tester's own frames are exactly the ones this file exists
    for and they are refused, i.e. UNauthorized: one ordinary logged-in
    player sending 64 frames could spend the whole unauthorized budget and
    the tester's line would be the one that does not fit -- denial of
    evidence by an unprivileged peer, reproducing the very failure this
    module was written to end.  Keyed per account, a flooding peer can
    only spend its own ``MAX_LINES_PER_ACCOUNT``.

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

# Grep anchors, same discipline as `command_capture._UNLINK_STUCK_CONSOLE_TOKEN`
# and `allowlist_probe.GM_ALLOWLIST_CONSOLE_TOKEN`: fixed ASCII tokens at the
# start of the line so an attended tester can grep the file without knowing
# this module's shape.  All three are pinned by tests and named in
# docs/GM_LANE.md.
LEDGER_LINE_TOKEN = "GM_VITAL_ARRIVED"
LEDGER_FULL_TOKEN = "GM_VITAL_LEDGER_FULL"
LEDGER_OPENED_TOKEN = "GM_VITAL_LEDGER_OPENED"

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

# Budgets, per process, keyed on the SANITIZED account name (see the
# docstring's third bullet for why the key is the account and not the
# authorization state).  A restart is what clears them, exactly like the
# rate limiter's history in gm/dispatch.py.
#
# Sized for the job and for the worst case together: an attended boot
# presses a handful of buttons, so 24 lines is far past "every command one
# tester issues before reading the file"; 32 tracked accounts is far past
# "how many accounts are connected to a test server"; and past that, every
# further account shares ONE overflow bucket, which is what keeps a peer
# that invents a new name per frame from turning this file into a disk
# filler.  Worst case on disk for one process is therefore
# (32*24 + 32 + 34) * (MAX_LINE_LENGTH + 1) -- about 220 KB, once, ever.
MAX_LINES_PER_ACCOUNT = 24
MAX_TRACKED_ACCOUNTS = 32
MAX_OVERFLOW_LINES = 32
OVERFLOW_BUCKET_KEY = "\x00overflow"  # not a value _sanitize_field can return

# Field caps.  The per-field caps are the real bound; MAX_LINE_LENGTH is a
# backstop truncation that no legitimate value reaches.  It exists so that
# a field cap someone widens later cannot silently turn one arrival into a
# multi-kilobyte line, which is what makes the budgets a byte bound too.
MAX_ACCOUNT_LENGTH = 40
MAX_OUTCOME_LENGTH = 48
MAX_LINE_LENGTH = 256
TRUNCATION_MARK = "~"

_UNNAMED_ACCOUNT = "unnamed"
_UNNAMED_OUTCOME = "unstated"

_lock = threading.Lock()
_lines_by_account: dict[str, int] = {}
_full_announced: set[str] = set()
_opened_announced = False


def reset_for_tests() -> None:
    """Test-only: forget every budget, announcement, and the opened header.

    Production never calls this; the budgets are meant to last the life of
    the process.  Exists for the same reason
    ``gm/dispatch.reset_rate_limit_state_for_tests`` does: a test that
    deliberately fills a budget must not depend on what ran before it in
    the same process.
    """
    global _opened_announced
    with _lock:
        _lines_by_account.clear()
        _full_announced.clear()
        _opened_announced = False


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
    """ASCII alnum/-/_ only, length-capped, never empty, cut marked.

    Same drop-don't-replace rule as ``command_capture._sanitize_account``
    (a Thai account name must not become underscore soup), applied here to
    every free-text field rather than only to a filename, because THIS
    file's whole contract is that one arrival is one line: a value
    carrying a newline, a NUL, or 4 KB of text would break the shape the
    tester greps.  A non-``str`` value is not coerced with ``str()`` --
    that would let ``__str__`` put anything at all in the file -- it falls
    back to the fixed label instead.

    A value that had to be CUT ends in ``~`` (pf-adversary, round
    `5rxy86`, D12): ``refused_capture_write_failed_CaptureFileNotVerified``
    read as a whole token would send a reader grepping for an exception
    name that is not there, and two exception types sharing a prefix would
    become one token with no sign that anything was lost.
    """
    if type(value) is not str:
        return fallback
    safe = "".join(
        c for c in value
        if ("a" <= c <= "z" or "A" <= c <= "Z" or "0" <= c <= "9" or c in "-_")
    )
    if len(safe) > limit:
        return safe[:limit - len(TRUNCATION_MARK)] + TRUNCATION_MARK
    return safe or fallback


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


def _render_authorized(authorized: bool | None) -> str:
    """yes / no / unknown.

    ``unknown`` is not decoration (pf-adversary, round `5rxy86`, D4).  When
    the gate chain RAISES, this module is told an arrival happened but not
    whether the account is in the allowlist -- the exception may have come
    from the allowlist read itself.  Printing ``no`` there would answer the
    one question an operator uses this field for ("does the server know my
    account yet?") with a confident wrong answer, and send them editing
    ``gm_accounts.json`` for a problem that is not there.
    """
    if authorized is None:
        return "unknown"
    return "yes" if authorized else "no"


def format_arrival_line(
    vital_id: object,
    account_name: object,
    payload_length: object,
    outcome: object,
    *,
    authorized: bool | None,
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
    if type(vital_id) is int and 0 <= vital_id <= 0xFFFF:
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
        f"authorized={_render_authorized(authorized)} "
        f"outcome={_sanitize_field(outcome, MAX_OUTCOME_LENGTH, _UNNAMED_OUTCOME)}"
    )
    return line[:MAX_LINE_LENGTH]


def _append_line(ledger_root: Path, line: str) -> bool:
    """Append one line.  True if the WHOLE line reached the file.

    ONE COMPLETE LINE PER CALL, to a descriptor opened ``O_APPEND``: that
    is what keeps two connection threads from interleaving half-lines.
    ``O_APPEND`` makes the seek-and-write one operation in the kernel, and
    the module lock in ``record_arrival`` is what this file actually relies
    on for ordering and for the budget counters; the flag is the belt to
    that lock's braces, for the case where some other process has the same
    file open.  NOT CLAIMED: that ``O_APPEND`` is atomic across processes
    on Windows, where CPython maps it to the CRT's seek-then-write
    (pf-adversary, round `5rxy86`, D10) -- within one process the lock is
    the guarantee, and two processes writing one ledger is a shape this
    module does not promise to survive.

    ``os.write`` IS LOOPED, NOT CALLED ONCE (pf-adversary, D2).  A short
    write is not an error and does not raise: on a volume with a few bytes
    left, one call can put half a line on disk and report success, after
    which the next line runs on from the middle of it and a grep sees one
    corrupt line instead of two good ones.  This lane has fixed exactly
    this bug three times before (``gm/commands._append_audit_record``,
    ``gm/login_scene_stage.py``, ``gm/command_capture._capture_raw``); it
    is not going to ship a fourth.  If the loop cannot finish, a bare
    newline is attempted so the partial line at least ends, and the caller
    is told False so the budget is not spent on it.
    """
    payload = (line + "\n").encode("ascii", "replace")
    try:
        os.makedirs(ledger_root, mode=0o700, exist_ok=True)
        # `makedirs(..., exist_ok=True)` is a silent no-op on a directory
        # that already exists -- it never chmods it (the same caveat
        # `command_capture` writes out at its own capture root, and the
        # reason it chmods every time).  An operator who created this
        # folder by hand because a ticket told them to look in it would
        # otherwise leave the evidence file world-writable.
        os.chmod(ledger_root, 0o700)
    except OSError:
        return False
    try:
        fd = os.open(
            os.path.join(ledger_root, LEDGER_FILENAME),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except OSError:
        return False
    written = 0
    try:
        while written < len(payload):
            count = os.write(fd, payload[written:])
            if count <= 0:
                break
            written += count
        if written < len(payload):
            try:
                os.write(fd, b"\n")
            except OSError:
                pass
            return False
    except OSError:
        if written:
            try:
                os.write(fd, b"\n")
            except OSError:
                pass
        return False
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return True


def _opened_header(ledger_root: Path, now_ts: float | None) -> str:
    """The first line of every process: where this file actually is.

    R322B reported "no capture folder ever appeared under the boot tree",
    and a working directory that is not the one the reader is looking under
    explains that observation just as well as "the frame never arrived"
    (pf-adversary, round `5rxy86`, D3/D7).  The capture roots in this
    package are RELATIVE paths resolved against the server process's cwd,
    so a reader holding a ticket at one in the morning cannot rule that
    out -- unless the file, and the console, say the absolute path once.
    The pid is here for the other half of the same problem: this file is
    append-only across runs, so without a per-process header a reader
    cannot tell this boot's lines from the previous boot's, or from a
    ``pytest`` run that used the same relative root.
    """
    try:
        resolved = str(Path(ledger_root).resolve())
    except OSError:
        resolved = str(ledger_root)
    return (
        f"{LEDGER_OPENED_TOKEN} "
        f"ts={_format_timestamp(now_ts)} "
        f"pid={os.getpid()} "
        f"path={resolved}"
    )


def _budget_key(sanitized_account: str) -> str | None:
    """Which bucket this account spends from, or None when all are spent."""
    if sanitized_account in _lines_by_account:
        return sanitized_account
    if len(_lines_by_account) < MAX_TRACKED_ACCOUNTS:
        return sanitized_account
    return OVERFLOW_BUCKET_KEY


def record_arrival(
    vital_id: object,
    account_name: object,
    payload_length: object,
    outcome: object,
    *,
    authorized: bool | None,
    capture_root: str | os.PathLike = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> str | None:
    """Record one arrival.  Returns the line written, or None if none was.

    NEVER RAISES.  This function is called from ``gm/dispatch.py``'s gate
    chain, which is called from a lane hook, which is called from the game
    listener thread: a full disk, a read-only volume, a permissions
    change -- or a ``capture_root`` this module cannot even turn into a
    path (pf-adversary, round `5rxy86`, D5: the non-GM branch of the gate
    chain never touched ``capture_root`` before this module existed, so a
    caller that passed a bad one used to get a clean refusal and would
    otherwise now get a ``TypeError`` out of the hook, losing the refusal
    event AND the console line at once) -- must cost the arrival's LINE and
    nothing else.  Every failure is reported as ``None``.

    Argument types are otherwise not validated and not coerced: every field
    goes through the sanitizers above, which already refuse to put a
    non-``str`` (or an unrenderable int) in the file.  A programmer error
    shows up as ``account=unnamed`` in the file, not as a crashed
    connection and not as a silent skip.
    """
    global _opened_announced
    try:
        ledger_root = ledger_root_for_capture_root(capture_root)
    except (TypeError, ValueError, AttributeError):
        return None
    safe_account = _sanitize_field(
        account_name, MAX_ACCOUNT_LENGTH, _UNNAMED_ACCOUNT,
    )
    try:
        with _lock:
            key = _budget_key(safe_account)
            spent = _lines_by_account.get(key, 0)
            budget = (
                MAX_OVERFLOW_LINES if key == OVERFLOW_BUCKET_KEY
                else MAX_LINES_PER_ACCOUNT
            )
            if spent >= budget:
                # Announce exhaustion exactly once per bucket, so a reader
                # can tell "no line for this arrival because the budget is
                # spent" from "no line because nothing arrived" -- the same
                # distinction this whole module exists to make, one level
                # up.
                if key in _full_announced:
                    return None
                _full_announced.add(key)
                full_line = (
                    f"{LEDGER_FULL_TOKEN} "
                    f"ts={_format_timestamp(now_ts)} "
                    f"account={safe_account if key != OVERFLOW_BUCKET_KEY else 'overflow'} "
                    f"budget={budget} "
                    f"further_arrivals_of_this_account_are_not_recorded"
                )
                return full_line if _append_line(ledger_root, full_line) else None
            if not _opened_announced:
                header = _opened_header(ledger_root, now_ts)
                if _append_line(ledger_root, header):
                    _opened_announced = True
                    # The console half of the same line: a tester at the
                    # keyboard must not have to read this module's source
                    # to learn which absolute path to open.  Once per
                    # process, like `allowlist_probe`'s own line.
                    print(header, flush=True)
            line = format_arrival_line(
                vital_id,
                account_name,
                payload_length,
                outcome,
                authorized=authorized,
                now_ts=now_ts,
            )
            if not _append_line(ledger_root, line):
                # A failed write spends no budget: the next arrival (after
                # the disk recovers) still gets its line.
                return None
            _lines_by_account[key] = spent + 1
            return line
    except OSError:
        return None
