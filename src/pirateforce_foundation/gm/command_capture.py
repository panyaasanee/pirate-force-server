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
inbound 0x51E9 and the account_id it arrived on, it checks that account_id
against the gm_accounts allowlist ITSELF (accounts.is_gm) and, only if it is
a member, appends one JSON record (hex + length, nothing decoded) to a
capture file.  GM-002's attended step (queued in pf_bridge/GAME_TEST_QUEUE.md)
is a human typing several chat forms while in GM state and reading this file
back to recover the real layout from real bytes.

WHY THE ALLOWLIST IS PASSED IN, NOT A PRE-COMPUTED BOOL (pf-adversary review,
LANE-GM round 1): an earlier version took ``is_gm: bool`` from the caller and
trusted it.  That shape lets a future wiring bug -- an ``is_gm`` cached once
per connection and never rechecked after a mid-session revoke, or a leftover
dev-stub ``is_gm=True`` -- turn this gate into a silent no-op with no test in
this module able to catch it, since the tests would only ever exercise the
boolean directly.  Taking the allowlist and recomputing the membership check
on every call means there is exactly one place this can be wrong:
accounts.is_gm itself, which is already covered by its own tests.
"""
import json
from pathlib import Path

from . import accounts

GM_RUN_COMMAND_VITAL_ID = 0x51E9


def capture_raw_command(
    payload: bytes, *, account_id: int, gm_accounts: frozenset[int], out_path,
) -> dict | None:
    """Append one raw-capture record; return it, or None if account is not GM.

    ``gm_accounts`` is the allowlist itself (e.g. from
    ``accounts.load_gm_accounts``) -- this function decides membership by
    calling ``accounts.is_gm``, it never accepts that decision pre-made.

    ``out_path`` is opened in append mode and is the caller's concern to
    create/rotate; this function never overwrites or truncates it.
    """
    if not accounts.is_gm(account_id, gm_accounts):
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
