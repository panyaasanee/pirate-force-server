"""Raw capture sink for GM_RunGMCommandVital (client->server, vital id 0x51E9).

This module does not parse or interpret the message.  Its layout is not
proven yet (notes_to_chief 20260826_1630: serializer 0x00729E10 has no row in
pf_bridge/external/PF_SERIALIZER_FIELDS.tsv), so GM-002's job is to record
exactly what the client sends -- when a GM-flagged account types in chat, in
whatever raw/prefixed/@/# forms the attended tester tries -- so a later RE
pass, or an attended-capture diff, can read the layout off real bytes instead
of guessing it.

Wiring the actual dispatch call (chief's runtime.py, wherever
GM_RunGMCommandVital 0x51E9 lands after being read off the wire) is out of
this lane's write zone; see notes_to_chief CORE-REQUEST-GM-001 letter series.
This module only provides the sink function that wiring should call.
"""
from __future__ import annotations

import time
from pathlib import Path

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9

DEFAULT_CAPTURE_ROOT = "capture/gm_command_capture"


def _hex_dump(raw: bytes) -> str:
    lines = []
    for offset in range(0, len(raw), 16):
        chunk = raw[offset : offset + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_part:<47}  {ascii_part}")
    return "\n".join(lines)


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
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    if not isinstance(account_name, str) or not account_name:
        raise ValueError("account_name must be a non-empty str")
    root = Path(capture_root)
    root.mkdir(parents=True, exist_ok=True)
    ts = now_ts if now_ts is not None else time.time()
    ts_label = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(ts))
    safe_account = "".join(c if c.isalnum() or c in "-_" else "_" for c in account_name)
    out_path = root / f"{ts_label}_{safe_account}_0x51E9.txt"
    header = (
        f"# GM_RunGMCommandVital raw capture (0x{GM_RUN_GM_COMMAND_VITAL_ID:04X})\n"
        f"# account={account_name} captured_at={ts_label} length={len(raw)}\n"
        f"# layout NOT proven -- see docs/GM_LANE.md GM-002 / RE request queue\n\n"
    )
    out_path.write_text(header + _hex_dump(bytes(raw)) + "\n", encoding="utf-8")
    return out_path
