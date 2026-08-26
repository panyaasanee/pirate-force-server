"""Raw capture sink for GM_RunGMCommandVital (client->server, vital id 0x51E9).

This module does not parse or interpret the message -- it only guarantees a
lossless copy of every raw send lands on disk.  A structural candidate
layout for 0x51E9 IS now proven at the byte level (added to
pf_bridge/external/PF_SERIALIZER_FIELDS.tsv by commit 5ab34dc, 2026-08-26
02:50 UTC / 09:50 +07:00 -- see docs/GM_LANE.md for the field list and its
span_sha256 pins), so this is deliberately NOT the blind "we know nothing"
tool an earlier version of this docstring claimed; see the correction note
in docs/GM_LANE.md for how that stale claim happened. What is still
unresolved is (a) which of the two runtime-selected sub-paths a real client
actually takes when it sends this message, and (b) what each field means --
both are RE-request territory, not something this lane should decode and
label on its own. Until that lands, this sink stays a raw hex-dump so a
later structural/semantic pass has real bytes -- from a GM-flagged
account, in whatever raw/prefixed/@/# chat forms an attended tester tries
-- to check a decoder against instead of guessing.

Wiring the actual dispatch call (chief's runtime.py, wherever
GM_RunGMCommandVital 0x51E9 lands after being read off the wire) is out of
this lane's write zone; see notes_to_chief CORE-REQUEST letter series.
This module only provides the sink function that wiring should call.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9

DEFAULT_CAPTURE_ROOT = "capture/gm_command_capture"

# Forensic filenames stay plain ASCII on purpose (never mangle a Thai
# account name mid-grapheme by half-sanitizing it) and bounded (a very long
# account_name must not be able to blow a filesystem's NAME_MAX and turn a
# capture sink into a crash point for its own caller).
_MAX_SAFE_ACCOUNT_LEN = 40


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


def capture_raw_gm_command(
    raw: bytes,
    account_name: str,
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    now_ts: float | None = None,
) -> Path:
    """Write one raw GM_RunGMCommandVital capture: a timestamped file with a
    hex dump header followed by the untouched raw bytes.

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
    header_account = account_name.encode("unicode_escape").decode("ascii")
    header = (
        f"# GM_RunGMCommandVital raw capture (0x{GM_RUN_GM_COMMAND_VITAL_ID:04X})\n"
        f"# account={header_account} captured_at={ts_label} length={len(raw)}\n"
        f"# structural candidate layout proven, field semantics NOT proven --\n"
        f"# see docs/GM_LANE.md GM-002 / RE request queue\n\n"
    )
    body = (header + _hex_dump(bytes(raw)) + "\n").encode("utf-8")

    suffix = 0
    while True:
        candidate_name = base_name if suffix == 0 else f"{base_name}_{suffix}"
        out_path = root / f"{candidate_name}.txt"
        try:
            fd = os.open(out_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            suffix += 1
            continue
        try:
            os.write(fd, body)
        finally:
            os.close(fd)
        return out_path
