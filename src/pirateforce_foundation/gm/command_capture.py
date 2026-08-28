"""Capture sink for GM_RunGMCommandVital (client->server, vital id 0x51E9).

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
import time
from pathlib import Path

from .command_wire import GmCommandWireError, decode_gm_run_command_vital

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
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    root = Path(capture_root)
    root.mkdir(parents=True, exist_ok=True)
    ts = now_ts if now_ts is not None else time.time()
    ts_label = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(ts))
    safe_account = _sanitize_account(account_name)
    base_name = f"{ts_label}_{safe_account}_0x51E9"
    # The header is plain-text metadata a human or a future tool might grep
    # for an "account=" line -- an account_name containing a newline must
    # not be able to forge extra header lines (e.g. a second, fake
    # "account=" or "#" line). Escape control characters instead of writing
    # account_name verbatim; the exact bytes are always recoverable from the
    # hex dump below regardless.
    header_account = _escape_for_header(account_name)
    header = (
        f"# GM_RunGMCommandVital raw capture (0x{GM_RUN_GM_COMMAND_VITAL_ID:04X})\n"
        f"# account={header_account} captured_at={ts_label} length={len(raw)}\n"
        f"# RE-088: structural layout PINNED, field semantics NOT proven --\n"
        f"# see docs/GM_LANE.md GM-002 / RE request queue\n"
        f"{_decode_section(bytes(raw))}\n"
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
            fd = os.open(out_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            suffix += 1
            continue
        try:
            os.write(fd, file_body)
        finally:
            os.close(fd)
        return out_path
    raise OSError(
        f"capture_raw_gm_command: exceeded {_MAX_FILENAME_COLLISION_ATTEMPTS} "
        f"filename collision retries for base name {base_name!r} under {root}"
    )
