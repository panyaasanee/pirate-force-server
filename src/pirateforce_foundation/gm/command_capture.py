"""Capture sink for the inbound GM-surface vitals this lane authorizes.

TWO OPCODES SINCE ROUND `eu2g1d`, not one: GM_RunGMCommandVital (0x51E9)
and Activity_CheatCodeVital (0x6CEC).  Everything the rest of this
docstring says about the 0x51E9 sink holds for both -- they share one
`_capture_raw` and differ only in the opcode in the filename, the header
line, the pin block and which decoder writes the `# decode:` section.
The original text, written when there was one:

This module guarantees a lossless copy of every raw send lands on disk --
that guarantee does not change below.  RE-088 (STRUCTURAL-LAYOUT-PINNED,
pf_bridge/notes_to_chief/20260826_1811_RE-088-RESULT-GM-COMMAND-WIRE-PINNED.md)
closed the structural question this docstring used to call open: there is
exactly one nested body, gated by a presence flag, not "two runtime-selected
sub-paths" as an earlier round's correction note had it (see docs/GM_LANE.md
for that history). This sink now attempts a schema-aware decode
(gm/command_wire.py) alongside the hex dump on every capture -- what is
still unresolved is what each field MEANS: the two wide strings are not
confirmed to be a command name and its argument text, and the live
chat-input trigger condition is RE-091, still open. Both are RE-request
territory, not something this lane decides on its own. A decode failure
(bytes that do not match the RE-088 pin) is recorded as a failure line, not
silently dropped and not a reason to skip writing the raw bytes -- a real
client sending something that does not match the pin is exactly the kind of
fact GM-002 exists to catch.

Wiring the actual dispatch call (chief's runtime.py, wherever
GM_RunGMCommandVital 0x51E9 lands after being read off the wire) is out of
this lane's write zone; see notes_to_chief CORE-REQUEST letter series. This
module only provides the sink function that wiring should call, and that
future wiring MUST hand this sink the same slice command_wire.py expects:
the vital's PAYLOAD bytes only (after vital id and version in the
runtime-vital envelope), not the whole frame. Nothing in this codebase
exercises that boundary yet -- no wiring exists to call this sink with a
real frame, so the decode section below has only ever run against payloads
built to that same assumption. A caller that instead hands in the full
frame will not crash, but every decode section will read "FAILED" forever;
the raw hex dump stays correct either way since it never depends on framing.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from .activity_cheat_code_wire import (
    ACTIVITY_CHEAT_CODE_VITAL_ID,
    GmActivityCheatCodeWireError,
    decode_activity_cheat_code_vital,
)
from .command_wire import GmCommandWireError, decode_gm_run_command_vital
from .login_scene_override import console_safe

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9

DEFAULT_CAPTURE_ROOT = "capture/gm_command_capture"

# Forensic filenames stay plain ASCII on purpose (never mangle a Thai
# account name mid-grapheme by half-sanitizing it) and bounded (a very long
# account_name must not be able to blow a filesystem's NAME_MAX and turn a
# capture sink into a crash point for its own caller).
_MAX_SAFE_ACCOUNT_LEN = 40

# pf-adversary (round 50x5xt, verify-pass addendum, docs/GM_LANE.md): the
# collision-suffix loop below used to be `while True`, unbounded on both the
# suffix value and the iteration count. Not an uncaught-exception risk on
# its own -- gm/dispatch.py already wraps this whole function in
# `except OSError` -- but under a capture root with many pre-existing or
# colliding filenames for the same account+second, one authorized call
# could spin through repeated os.open attempts before finding a free
# suffix, or never find one at all. Bounded here instead: past this many
# collisions for the same base_name, give up and raise (dispatch.py's
# existing OSError guard turns that into REFUSAL_CAPTURE_WRITE_FAILED_PREFIX
# the same way any other capture write failure already does) rather than
# spin unboundedly. Far larger than any realistic same-second collision
# count for one account (this project's own rate limiter, gm/dispatch.py's
# RATE_LIMIT_MAX_CALLS_PER_WINDOW, now also bounds how often this loop can
# even be entered).
_MAX_FILENAME_COLLISION_ATTEMPTS = 1000

# COO-DECISION 2026-09-06T20:47+07:00 (pf_bridge letter
# `20260906_2047_COO-DECISION-gm1940-unlink-bounded-retry-3-plus-doc-line-LANE-GM.md`,
# answering this lane's own `1940` question): the cleanup unlink below gets a
# BOUNDED retry and nothing more -- no background janitor, no quota refund
# after the fact. The failure it exists for is Windows-only and transient by
# nature: another process (an antivirus scanner, an indexer, a backup agent)
# holding a handle open on the file we just closed makes DeleteFile fail with
# a sharing violation for as long as it holds it, and it usually lets go in
# milliseconds. Retrying costs nothing on the path where unlink succeeds --
# and POSIX never enters the retry path at all for this reason (a handle held
# elsewhere does not block unlink there), which is why the "succeeds first
# try = no sleep at all" test below pins that the Linux path is unchanged.
# Two constants, one place, so the total time this can add to a failing
# capture call stays readable: 3 attempts, 2 gaps, 0.1 s of sleeping at the
# very worst -- well under COO's ~300 ms ceiling.
_UNLINK_ATTEMPTS = 3
_UNLINK_RETRY_DELAY_SECONDS = 0.05

# pf-adversary (round `0op9bt`, D7): `_best_effort_unlink` below has a
# comment calling its final loop iteration "unreachable" -- true only
# because this holds. At 0, the loop body never runs at all and the
# function would report "could not remove" without ever calling
# `os.unlink`, silently. Raised rather than asserted (pf-adversary round
# `smztdu`, finding 2): ``python -O`` strips a bare ``assert`` entirely --
# verified (``python3 -O`` makes this line a no-op) -- and this project has
# already hit that exact mistake once and fixed it the same way
# (``world_port_royal_identity.py``'s own comment on its module-level
# ``raise ValueError`` says so in nearly these words): a consistency guard
# that must always hold is not a development aid to compile away.
if _UNLINK_ATTEMPTS < 1:
    raise ValueError("_UNLINK_ATTEMPTS must allow at least one try")

# One line, on stderr, naming the file that stayed on disk. Same channel and
# shape as this lane's other console tokens (`gm/chat_command_action.py`'s
# CONSOLE_TOKEN / LV_CONSOLE_TOKEN), plain ASCII for the cp874 bridge console.
_UNLINK_STUCK_CONSOLE_TOKEN = "GM_CAPTURE_UNLINK_STUCK"


class CaptureFileNotVerifiedRemoved(OSError):
    """A capture write failed and the partial file could not be confirmed removed.

    pf-adversary (round `40bjg7`, follow-up round `gn7gk5`): before this
    class existed, ``_capture_raw``'s write failure path (``os.write``
    raising after ``os.open(..., O_CREAT | O_EXCL, ...)`` had already
    created the file on disk) left that file behind with no cleanup
    attempt, then raised the plain ``OSError`` that carried it. Every
    caller of this module -- ``gm/dispatch.py``'s ``_authorize_and_capture``
    -- reads a plain ``OSError`` from this function as "nothing was
    written", refunds the quota it had already charged for the call, and
    moves on: reproduced live (mocking only ``os.write``, letting the real
    ``os.open`` run) as a leftover zero-length file on disk with the
    account's tracked quota usage reading exactly what it read before the
    call -- the same "quota tracks less than real disk usage" failure
    round `40bjg7`'s own D9 fix exists to close, just relocated to this
    path instead of fixed.

    ``_capture_raw`` now attempts a best-effort ``os.unlink`` of the
    partial file whenever ``os.write`` fails, and raises the ORIGINAL
    ``OSError`` (unchanged) only when that cleanup succeeds -- a caller
    reading a plain ``OSError`` from this function can now trust "zero
    bytes remain on disk for this call" the same way it always assumed.
    When the cleanup ITSELF fails (the partial file could not be removed,
    so real bytes may still be sitting on disk from a call nothing ever
    charged for), this class is raised instead, chained from the original
    write error, so a caller can tell the two cases apart and refuse to
    refund a charge it cannot prove was never spent.

    EXPANDED (round `gn7gk5`, follow-up `79ahzl`): the same treatment now
    also covers ``os.close(fd)`` failing, in both places it can --
    immediately after a failed ``os.write`` (a close-time error was
    previously raised BEFORE the unlink/classify logic above ever ran,
    skipping this whole contract), and after a SUCCESSFUL ``os.write``
    (POSIX ``close()`` can report a write's real outcome only at close
    time -- documented for NFS, not exclusive to it -- so a write that
    looked successful can still turn out not to have landed). The second
    case is the more severe one: nothing before round `79ahzl` caught it
    at all, so a fully-written, non-empty real capture could be left on
    disk with its quota charge refunded as if the call had written
    nothing.
    """


def _best_effort_unlink(
    path: Path,
    *,
    retry: bool = True,
    account_name: str = "",
    attempted_bytes: int = 0,
) -> bool:
    """Try to remove ``path``; return whether it is now confirmed absent.

    Called only after a capture write has already failed, to answer the
    one question ``_capture_raw``'s caller needs: is it now safe to treat
    this call as having left zero bytes on disk? ``FileNotFoundError``
    counts as success -- the property this returns is "does not exist
    now", not "this specific call is what deleted it" (a second failure
    racing the first, or an external cleanup, could have removed it
    first, and the file being gone either way is exactly what matters to
    the caller).

    BOUNDED RETRY (round `0op9bt`, COO-DECISION `2047`): a failing unlink is
    retried up to ``_UNLINK_ATTEMPTS`` times with ``_UNLINK_RETRY_DELAY_SECONDS``
    between attempts, because the failure this function is most likely to
    meet in production is a Windows sharing violation from another process
    holding a transient handle, which typically clears in milliseconds. An
    unlink that succeeds on the first attempt sleeps ZERO times -- the
    success path is byte-for-byte the same work it was before.

    ``retry=False`` (pf-adversary round `0op9bt` ADDENDUM, D1): the ONE
    caller of this function that runs from ``_capture_raw``'s
    ``except BaseException`` branch passes this. That branch's whole job is
    re-raising an in-flight ``KeyboardInterrupt``/``SystemExit``/etc.
    UNCHANGED; ``time.sleep`` between retries opens a window, during
    interpreter shutdown, where a second signal can arrive mid-sleep and
    replace the exception Python actually delivers to the caller with
    whatever the sleep itself raises. ``retry=False`` makes exactly one
    unlink attempt -- zero sleeps -- so the shutdown path's timing is
    whatever it already was without this cleanup call, while the two
    ordinary failure paths (write failed, close failed) keep the full
    bounded retry.

    WHEN THE RETRIES RUN OUT the answer is still ``False``: the caller
    raises ``CaptureFileNotVerifiedRemoved`` and the quota charged for that
    call is NOT refunded, exactly as before. There is no janitor, nothing
    sweeps the file up later, and nothing re-credits that quota during the
    life of the process -- **a capture quota left stuck this way is cleared
    by RESTARTING THE PROCESS, and by nothing else** (COO ruled the janitor
    out until the failure is measured on a real Windows machine). One
    stderr line names the file, the account, and the bytes this call
    attempted so the operator can see which one it was and how much is
    stuck; see docs/GM_LANE.md.
    """
    attempts = _UNLINK_ATTEMPTS if retry else 1
    for attempt in range(1, attempts + 1):
        try:
            os.unlink(path)
        except FileNotFoundError:
            return True
        except OSError:
            if attempt >= attempts:
                try:
                    stream = sys.stderr
                    # pf-adversary (round `0op9bt` ADDENDUM, D4): both
                    # operator-controlled fields go through `console_safe`,
                    # not just the account name -- `path` is built from
                    # `capture_root` (a config value, not this project's own
                    # `TemporaryDirectory`-only test fixtures) and a console
                    # forced to `cp874:strict` raises on the first character
                    # it cannot encode, which used to fall straight into
                    # this guard and drop the whole line silently.
                    #
                    # `_escape_for_header` FIRST, `console_safe` second (pf-
                    # adversary round `smztdu`, finding 1): `console_safe`
                    # only folds characters the STREAM cannot encode -- a
                    # literal newline is representable in every encoding
                    # this project uses, so it passes straight through
                    # unchanged and this "one line" (docs/GM_LANE.md's own
                    # words) becomes two, the second one carrying
                    # attacker-chosen `path=`/`attempted_bytes=`/
                    # `attempts=` text a grep-this-token tool cannot tell
                    # from the real line. `account_name` is the account
                    # login name (`gm/accounts.py`'s `gm_accounts` entries
                    # match it verbatim; nothing in this codebase restricts
                    # its characters), and this file already treats it as
                    # needing exactly this defense for the on-disk header
                    # (`header_account = _escape_for_header(account_name)`
                    # above, "an account_name containing a newline must not
                    # be able to forge extra header lines") -- this stderr
                    # line is the other place a newline in the same field
                    # can forge a fake line, so it gets the same escape.
                    safe_account = console_safe(
                        _escape_for_header(account_name) or "(unknown)", stream,
                    )
                    safe_path = console_safe(str(path), stream)
                    print(
                        f"{_UNLINK_STUCK_CONSOLE_TOKEN} path={safe_path} "
                        f"account={safe_account} attempted_bytes={attempted_bytes} "
                        f"attempts={attempts} -- file stayed on disk and its "
                        f"capture quota stays charged; restart the process to "
                        f"clear that quota",
                        file=stream,
                    )
                except BaseException:
                    # This function is called from `_capture_raw`'s
                    # `except BaseException` cleanup path too, which runs at
                    # interpreter shutdown (KeyboardInterrupt/SystemExit) --
                    # where `sys.stderr` can already be closed and a bare
                    # `print` then raises. Widened to `BaseException`
                    # (pf-adversary round `0op9bt` ADDENDUM, D2): a plain
                    # `except Exception` here does NOT cover
                    # `KeyboardInterrupt`/`SystemExit`, the exact two named
                    # one paragraph above as the reason this guard exists at
                    # all -- so a `print` that raised one of them used to
                    # escape uncaught. The ANSWER this function returns is
                    # what the caller's quota decision depends on; a failed
                    # log line must never replace the exception that cleanup
                    # path is in the middle of re-raising.
                    pass
                return False
            time.sleep(_UNLINK_RETRY_DELAY_SECONDS)
        else:
            return True
    # Unreachable: the final iteration always returns on both branches.
    return False


def _hex_dump(raw: bytes) -> str:
    lines = []
    for offset in range(0, len(raw), 16):
        chunk = raw[offset : offset + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_part:<47}  {ascii_part}")
    return "\n".join(lines)


def _sanitize_account(account_name: str) -> str:
    # Drop (rather than replace-with-underscore) any character outside
    # plain ASCII alnum/-/_ so a non-Latin account name doesn't turn into
    # unreadable underscore soup; an account name with nothing left after
    # that falls back to a fixed label instead of an empty path segment.
    safe = "".join(
        c for c in account_name
        if ("a" <= c <= "z" or "A" <= c <= "Z" or "0" <= c <= "9" or c in "-_")
    )
    safe = safe[:_MAX_SAFE_ACCOUNT_LEN]
    return safe or "unnamed"


def _escape_for_header(text: str) -> str:
    # Same reasoning as the account_name escape below: a decoded string comes
    # straight from client-controlled bytes, so it must not be able to forge
    # a newline and inject a fake header/comment line into the capture file.
    return text.encode("unicode_escape").decode("ascii")


def _decode_section(raw: bytes) -> str:
    try:
        body = decode_gm_run_command_vital(raw)
    except GmCommandWireError as exc:
        return f"# decode: FAILED against RE-088 pin -- {exc}\n"
    if body is None:
        return "# decode: presence=0 (no nested body; structurally valid, empty)\n"
    return (
        f"# decode: presence={body.presence} (nonzero -- RE-088 pin; field"
        " names are positional, not semantic)\n"
        f"# decode: field_0x10={body.field_0x10} field_0x14={body.field_0x14}"
        f" field_0x18={body.field_0x18}\n"
        f"# decode: string_0x1c=\"{_escape_for_header(body.string_0x1c)}\"\n"
        f"# decode: string_0x38=\"{_escape_for_header(body.string_0x38)}\"\n"
    )


def _activity_cheat_code_decode_section(raw: bytes) -> str:
    """The `# decode:` block for one Activity_CheatCodeVital payload.

    Same posture as `_decode_section` above and for the same reason: the
    field names it prints are POSITIONAL, never semantic -- see
    `gm/activity_cheat_code_wire.py`'s own docstring, which refuses to
    rename them to `code_id`/`arg1`.. without an RE answer.  A decode that
    fails prints the failure and the hex dump underneath still carries the
    exact bytes, so a capture is never lost to a decoder disagreeing with
    what the client sent.
    """
    try:
        body = decode_activity_cheat_code_vital(raw)
    except GmActivityCheatCodeWireError as exc:
        return (
            "# decode: FAILED against PF_SERIALIZER_FIELDS.tsv rows 4345-4356"
            f" pin -- {exc}\n"
        )
    return (
        "# decode: structurally valid (field names are positional, not"
        " semantic)\n"
        f"# decode: field_0x14={body.field_0x14}\n"
        f"# decode: text_0x18=\"{_escape_for_header(body.text_0x18)}\"\n"
        f"# decode: text_0x34=\"{_escape_for_header(body.text_0x34)}\"\n"
        f"# decode: text_0x50=\"{_escape_for_header(body.text_0x50)}\"\n"
        f"# decode: text_0x6c=\"{_escape_for_header(body.text_0x6c)}\"\n"
        f"# decode: text_0x88=\"{_escape_for_header(body.text_0x88)}\"\n"
    )


#: The two provenance lines each capture header carries under its own
#: `account=` line.  They name the pin the decode section was written
#: against, so a capture file read a month from now says what "structurally
#: valid" was measured against rather than leaving a reader to guess.
_GM_RUN_COMMAND_PIN_LINES = (
    "# RE-088: structural layout PINNED, field semantics NOT proven --\n"
    "# see docs/GM_LANE.md GM-002 / RE request queue\n"
)
_ACTIVITY_CHEAT_CODE_PIN_LINES = (
    "# PF_SERIALIZER_FIELDS.tsv rows 4345-4356 sha256 ba19699b0ff750e75abd\n"
    "# 226eb3ae25e356f487e4fc325ec6512335dfbf7d3205, tags corrected by\n"
    "# PF_A2_STRING_WIRE_TAG_DELTA.tsv base_rows 4347-4356 (that file's own\n"
    "# base_row_number column, NOT its line numbers -- it is 409 lines long)\n"
    "# sha256 e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2:\n"
    "# structural layout PINNED, field semantics NOT proven --\n"
    "# see gm/activity_cheat_code_wire.py\n"
)


def _capture_raw(
    raw: bytes,
    account_name: str,
    *,
    capture_root: str | Path,
    now_ts: float | None,
    vital_id: int,
    vital_name: str,
    decode_section,
    pin_lines: str,
    caller_name: str,
) -> Path:
    """The capture sink both public entry points below are.

    EXTRACTED, NOT REWRITTEN (round `eu2g1d`).  Every guarantee documented
    on `capture_raw_gm_command` -- the 0o700 directory re-chmod on every
    call, the 0o600 `O_EXCL` create, the collision suffix, the header
    escaping -- lives here now and is shared, so a second inbound GM vital
    cannot get a weaker version of any of them by being captured through a
    copy of this code that drifts.  The 0x51E9 filename, header line and
    decode block are byte-identical to what this function wrote before the
    extraction; `tests/test_gm_command_capture.py` is what says so.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    root = Path(capture_root)
    # mode=0o700 on the leaf directory only -- Path.mkdir(parents=True)
    # creates any missing *parents* at the platform default mode, ignoring
    # `mode` (a Python stdlib behavior, not something this call can override).
    # Without this, a permissive host umask (e.g. 0o000) leaves this
    # directory world-writable, which lets another local user delete or
    # rename the 0o600 capture files inside even though they can't read
    # their contents -- a partial defeat of this function's own "nothing
    # captured is ever lost" guarantee. Same regardless-of-umask reasoning
    # as the file mode below: 0o700 has no group/other bits for any umask to
    # add back.
    #
    # pf-adversary (verification pass, same round): `mkdir(..., exist_ok=True)`
    # is a silent no-op on a directory that already exists -- it never
    # chmods it. `DEFAULT_CAPTURE_ROOT` and `gm/commands.py`'s
    # `DEFAULT_LOG_PATH` share the literal parent `capture/`, which
    # `.gitignore` documents as never cleaned up: whichever of the two
    # functions runs first on a real host creates that shared parent at
    # whatever mode a stale/permissive umask left it at on that one call,
    # and every later call -- under this project's own real default umask
    # included -- would otherwise leave it stuck there forever. The explicit
    # `os.chmod` below re-asserts 0o700 on every call, not just first
    # creation, so the directory cannot stay wide open from one unlucky
    # umask at creation time.
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    ts = now_ts if now_ts is not None else time.time()
    ts_label = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(ts))
    safe_account = _sanitize_account(account_name)
    base_name = f"{ts_label}_{safe_account}_0x{vital_id:04X}"
    # The header is plain-text metadata a human or a future tool might grep
    # for an "account=" line -- an account_name containing a newline must
    # not be able to forge extra header lines (e.g. a second, fake
    # "account=" or "#" line). Escape control characters instead of writing
    # account_name verbatim; the exact bytes are always recoverable from the
    # hex dump below regardless.
    header_account = _escape_for_header(account_name)
    header = (
        f"# {vital_name} raw capture (0x{vital_id:04X})\n"
        f"# account={header_account} captured_at={ts_label} length={len(raw)}\n"
        f"{pin_lines}"
        f"{decode_section(bytes(raw))}\n"
    )
    file_body = (header + _hex_dump(bytes(raw)) + "\n").encode("utf-8")

    suffix = 0
    while suffix <= _MAX_FILENAME_COLLISION_ATTEMPTS:
        candidate_name = base_name if suffix == 0 else f"{base_name}_{suffix}"
        out_path = root / f"{candidate_name}.txt"
        try:
            # Explicit mode=0o600 (owner read/write only, no execute bit for
            # anyone). `os.open` without a `mode` argument defaults to 0o777
            # (masked by umask) -- unlike the builtin `open()` used elsewhere
            # in this lane (`commands.py`'s `log_gm_command`, default 0o666,
            # no execute bit ever), so this one call site was silently
            # writing forensic captures -- real client-controlled bytes,
            # account names, and free-text a GM typed, per this module's own
            # docstring -- as world-readable and, under a permissive umask,
            # world-writable and executable by every OS user on the host.
            # Reproduced live under this project's own default umask
            # (0o022): the old call produced mode 0o755 (rwxr-xr-x); this
            # explicit mode produces 0o600 regardless of umask, since 0o600
            # has no group/other bits for umask to need to clear -- ON
            # POSIX. This project's real deployment target is Windows (the
            # gate this repo trusts runs on windows-latest on purpose, see
            # .github/workflows/gate-windows.yml), and NTFS has no POSIX
            # permission bits: CPython's os.open() on Windows only reads
            # this argument for a single bit (writable vs read-only) and
            # otherwise ignores it, so the owner-only enforcement this call
            # provides is POSIX-only -- confirmed by this project's own
            # Windows gate reporting mode 0o666 for this exact call (round
            # vb3ktn, run 33132956815). On the real Windows bridge, access
            # to this capture directory is governed by its NTFS ACL, not by
            # this argument; this lane's write zone has no ACL API
            # available to close that gap from here. See
            # `tests/test_gm_command_capture.py`'s
            # `test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask`
            # and the round `vb3ktn` follow-up letter to COO.
            # os.O_BINARY (Windows only; getattr default 0 makes this a
            # no-op on POSIX, where the flag does not exist) -- pf-adversary
            # D6, round `lkwmkp`: without it, CPython's os.open() on Windows
            # opens the descriptor in the C-runtime's default text mode, and
            # the raw os.write() calls below are then subject to that
            # runtime's own \n -> \r\n translation. file_body is UTF-8 bytes
            # containing a hex dump and a decode section that can hold
            # literal \n bytes not meant as line separators, so a silent
            # CRLF rewrite would both corrupt the "lossless copy" this
            # module's docstring promises and desync the short-write retry
            # loop below, which assumes every byte handed to os.write()
            # either lands on disk unchanged or is reported back as not
            # written -- not silently expanded in place.
            fd = os.open(
                out_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
                0o600,
            )
        except FileExistsError:
            suffix += 1
            continue
        try:
            # pf-adversary (round `79ahzl`, follow-up `w87k4s`): this used
            # to be a bare `os.write(fd, file_body)` whose return value was
            # discarded. write(2) is not required to write every requested
            # byte in one call, and a filesystem that fills up mid-write is
            # the classic case where it writes fewer WITHOUT raising -- the
            # exact same bug this package already found and fixed twice
            # (`gm/commands.py`'s `_append_audit_record`, round `hs9m2r`,
            # and `gm/login_scene_stage.py`'s copy of it) without ever
            # porting the fix to this sibling call site, despite three
            # consecutive rounds re-auditing this exact function's write
            # path (`40bjg7`/`gn7gk5`/`79ahzl`) and this file's own
            # `os.open` mode fix (round `vb3ktn`) being the precedent
            # `commands.py`'s fix explicitly cites in the other direction.
            # A short write here used to fall straight through to
            # `return out_path` reporting ordinary full success -- no
            # exception, no refusal_reason, quota charged as normal -- for
            # a truncated capture file this module's own docstring promises
            # never happens ("a lossless copy of every raw send lands on
            # disk"). Looping until every byte lands (or raising if a call
            # makes zero forward progress) means a short write now flows
            # into the SAME `except OSError` below as any other write
            # failure, inheriting the whole cleanup-then-classify contract
            # rounds `gn7gk5`/`79ahzl` already built, with no new branch
            # shape needed.
            written = 0
            while written < len(file_body):
                count = os.write(fd, file_body[written:])
                if count <= 0:
                    raise OSError(
                        f"short write to {out_path}: "
                        f"{written}/{len(file_body)} bytes"
                    )
                written += count
        except OSError as write_error:
            # pf-adversary (round `gn7gk5`, follow-up `79ahzl`): this
            # `os.close` used to be unguarded -- a close() failure here
            # (real filesystems, not only NFS, can defer a write's own
            # error to close time, so this is not a hypothetical second
            # failure) raised BEFORE `_best_effort_unlink` ever ran,
            # skipping the whole cleanup-then-classify contract this round
            # exists to hold. It is swallowed here on purpose: the write
            # already failed, `write_error` is the fact this call cares
            # about, and the file's on-disk state is exactly what the
            # unlink below verifies regardless of whether closing the fd
            # itself succeeded.
            try:
                os.close(fd)
            except OSError:
                pass
            # The file already exists on disk at this point (`os.open` with
            # `O_CREAT` above already created it, empty or partially
            # written) -- best-effort remove it so this failed call really
            # does leave zero bytes behind, then tell the caller whether
            # that promise held. See `CaptureFileNotVerifiedRemoved`'s own
            # docstring for the failure this closes.
            if _best_effort_unlink(
                out_path, account_name=account_name, attempted_bytes=len(file_body)
            ):
                raise
            raise CaptureFileNotVerifiedRemoved(
                f"{caller_name}: write to {out_path} failed ({write_error!r}) "
                f"and the partial file could not be removed -- bytes may "
                f"still be on disk for a call nothing charged for"
            ) from write_error
        except BaseException:
            # pf-adversary (round `lkwmkp`, D5): rounds `gn7gk5`/`79ahzl`
            # replaced this function's original `try: os.write(...) finally:
            # os.close(fd)` with an `except OSError` branch, and quietly
            # traded away the guarantee the `finally` gave for free -- any
            # NON-OSError escaping the write loop (`KeyboardInterrupt` or
            # `SystemExit` at shutdown, `MemoryError` on the
            # `file_body[written:]` slice) left the descriptor open AND the
            # `O_CREAT|O_EXCL` file on disk, in a function whose whole
            # subject is "a failed call really does leave zero bytes
            # behind". On Windows that leaked handle also locks the file for
            # the life of the process, so nothing can clean it up later.
            # This branch restores the old guarantee without touching the
            # OSError classification above: close, remove, re-raise the
            # original exception unchanged (no `CaptureFileNotVerifiedRemoved`
            # translation -- an interpreter shutdown is not a quota event).
            try:
                os.close(fd)
            except OSError:
                pass
            # `retry=False` (pf-adversary round `0op9bt` ADDENDUM, D1): this
            # is the shutdown re-raise path -- see `_best_effort_unlink`'s
            # own docstring for why it must not sleep here.
            _best_effort_unlink(
                out_path,
                retry=False,
                account_name=account_name,
                attempted_bytes=len(file_body),
            )
            raise
        try:
            os.close(fd)
        except OSError as close_error:
            # pf-adversary (round `gn7gk5`, follow-up `79ahzl`): the more
            # severe half of the same finding -- `os.write` above can
            # SUCCEED (every byte accepted into the kernel's write buffer)
            # and the write's real outcome only surface here, at close()
            # (deferred write-back error; documented for NFS, not
            # exclusive to it). Before this branch existed, nothing caught
            # this at all: the plain OSError propagated straight past this
            # function untouched, dispatch.py's ordinary OSError handler
            # refunded the quota, and a COMPLETE real capture -- not an
            # empty or partial one -- was left on disk with nothing
            # accounting for it. `fd` is already consumed by this failed
            # close (POSIX: never retry `close()` on the same descriptor),
            # so there is nothing left to close here -- only to classify,
            # the same way a failed write is classified above.
            if _best_effort_unlink(
                out_path, account_name=account_name, attempted_bytes=len(file_body)
            ):
                raise
            raise CaptureFileNotVerifiedRemoved(
                f"{caller_name}: close for {out_path} failed ({close_error!r}) "
                f"after a successful write -- the write's real outcome was "
                f"never confirmed, and the file could not be removed to "
                f"prove zero bytes remain"
            ) from close_error
        return out_path
    raise OSError(
        f"{caller_name}: exceeded {_MAX_FILENAME_COLLISION_ATTEMPTS} "
        f"filename collision retries for base name {base_name!r} under {root}"
    )


def capture_raw_gm_command(
    raw: bytes,
    account_name: str,
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> Path:
    """Write one raw GM_RunGMCommandVital capture: a timestamped file with a
    hex dump header followed by the untouched raw bytes.

    ``raw`` should be the vital's payload bytes only (after vital id and
    version in the runtime-vital envelope) -- the same slice
    ``command_wire.decode_gm_run_command_vital`` expects.  This is not
    enforced (there is no envelope-stripping logic in this lane to enforce
    it with; wiring is chief's territory), so a caller that hands in the
    whole frame gets a wrong-but-not-crashing decode section (see module
    docstring) while the raw hex dump underneath stays correct regardless.

    Returns the path written.  Never raises on the content of ``raw`` --
    this is a capture sink, not a validator; anything the client sends,
    however malformed, is exactly what GM-002 needs on disk.

    Filenames are guaranteed unique even when two captures share the same
    account and the same (second-resolution) timestamp: a colliding name
    gets a numeric suffix instead of silently overwriting the earlier
    capture.  Losing a capture silently would defeat the point of this
    module -- it exists so nothing a tester sends while probing 0x51E9 gets
    thrown away.
    """
    return _capture_raw(
        raw,
        account_name,
        capture_root=capture_root,
        now_ts=now_ts,
        vital_id=GM_RUN_GM_COMMAND_VITAL_ID,
        vital_name="GM_RunGMCommandVital",
        decode_section=_decode_section,
        pin_lines=_GM_RUN_COMMAND_PIN_LINES,
        caller_name="capture_raw_gm_command",
    )


def capture_raw_activity_cheat_code(
    raw: bytes,
    account_name: str,
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> Path:
    """Write one raw Activity_CheatCodeVital (0x6CEC) capture.

    WHY A SECOND INBOUND VITAL LANDS IN THE SAME FOLDER.  The capture bus
    exists to answer one question a GMUI button press asks -- "what did the
    client just send?" -- and it can only answer it for opcodes it is
    called for.  A button that sends 0x6CEC rather than 0x51E9 leaves the
    folder empty, which reads on a test result sheet exactly like "those
    buttons send nothing" -- and the two answers are opposite.  So the file
    name carries the opcode (`..._0x6CEC.txt`) and both opcodes share one
    folder rather than one opcode owning it.

    WHAT THIS DOES NOT YET DO, said here because the first draft of this
    docstring said the opposite (pf-adversary, round `eu2g1d`, D3): NOTHING
    CALLS IT ON A REAL FRAME.  `gm.dispatch.handle_activity_cheat_code_
    vital` is its only caller and that handler has no `runtime.py` call
    site, so today this function runs in tests and nowhere else.  The
    ambiguity above is closed when chief wires CORE-REQUEST-GM-062, not
    when this function merges.

    Same contract as ``capture_raw_gm_command`` in every other respect:
    ``raw`` is the payload slice after the runtime-vital envelope, the
    return value is the path written, and no content of ``raw`` can make
    this raise -- a payload the decoder rejects still gets its exact bytes
    on disk with the failure named in the header.

    NOT CLAIMED, and this is the whole of what this lane knows: that any
    client has ever sent this frame to this server.  Both
    Activity_CheatCodeVital rows in PF_FIELD_VALIDATION.tsv (W and R) read
    ``observed_frames=0 ... status=NOT_OBSERVED``, so the decode section
    prints POSITIONAL field names only -- see
    ``gm/activity_cheat_code_wire.py``'s docstring for why they must not be
    renamed to semantic ones without an RE answer.
    """
    return _capture_raw(
        raw,
        account_name,
        capture_root=capture_root,
        now_ts=now_ts,
        vital_id=ACTIVITY_CHEAT_CODE_VITAL_ID,
        vital_name="Activity_CheatCodeVital",
        decode_section=_activity_cheat_code_decode_section,
        pin_lines=_ACTIVITY_CHEAT_CODE_PIN_LINES,
        caller_name="capture_raw_activity_cheat_code",
    )
