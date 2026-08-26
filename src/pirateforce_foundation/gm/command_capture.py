"""GM-002: raw capture of GM_RunGMCommandVital (0x51E9), unclassified.

PROVENANCE.  pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv names 0x51E9 as
GM_RunGMCommandVital, client->server, default handler 0x00A106C0 (no
client-side handler).  pf_bridge/external/PF_SERIALIZER_FIELDS.tsv carries a
structural field layout for it (a mode byte, two u32s, a byte and two
length-prefixed wstrings behind a nested pointer) -- but which field carries
the command text, a target name, or a numeric argument has NOT been RE'd.
Guessing that mapping here would be exactly the kind of invented meaning
G1-G8 forbids, so this module does not attempt it.

WHAT THIS MODULE DOES.  Nothing but log.  Given the raw payload bytes of an
inbound 0x51E9 from an account already confirmed to be a GM (accounts.is_gm),
it appends one JSON record (hex + length, nothing decoded) to a capture file.
GM-002's attended step (queued in pf_bridge/GAME_TEST_QUEUE.md) is a human
typing several chat forms while in GM state and reading this file back to
recover the real layout from real bytes.

Non-GM accounts are refused outright: this module never captures or looks at
traffic from an account that isn't already on the gm_accounts allowlist.
"""
import json
from pathlib import Path

GM_RUN_COMMAND_VITAL_ID = 0x51E9


def capture_raw_command(
    payload: bytes, *, account_id: int, is_gm: bool, out_path,
) -> dict | None:
    """Append one raw-capture record; return it, or None if account is not GM.

    ``out_path`` is opened in append mode and is the caller's concern to
    create/rotate; this function never overwrites or truncates it.
    """
    if not is_gm:
        return None
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    record = {
        "vital_id": hex(GM_RUN_COMMAND_VITAL_ID),
        "account_id": account_id,
        "length": len(payload),
        "hex": bytes(payload).hex(),
    }
    with Path(out_path).open("a", encoding="ascii") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record
