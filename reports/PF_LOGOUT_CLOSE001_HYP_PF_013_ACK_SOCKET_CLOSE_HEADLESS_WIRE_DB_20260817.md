# PF LOGOUT-CLOSE-001 — HYP-PF-013 ack + server-initiated socket close, headless wire/DB proof (2026-08-17)

One claim (Grade B, wire/DB layer only): behind the separate
`scenarios/logout_hypothesis_ack_close.json` opt-in
(`post_ack_action: close_socket`, `close_delay_ms: 250`,
`production_allowed: false`), the Foundation server acknowledges both captured
`LogoutVital` (0x1B40) request forms with the **byte-identical hash-pinned
HYP-PF-012 echo composition** and then performs exactly one additional
server-owned action: a clean `shutdown(2)+close` of that connection's accepted
GAME socket, observed on the wire as EOF ~250 ms after the ack, strictly after
the ack bytes. The session lease (`sessions.closed_at`) commits before the ack
is queued, exactly as under PF-012. Everything else fails closed with no reply
and no write, including the ack_close scenario itself when no transport close
lever is attached. **No client-observable claim is made**: whether the real
client treats the close as a logout transition (01: window/process close,
03: leaves the map) is exactly GT-008, queued for the attended big round.

## Why this shape (design lineage, round 42–43)

- GT-007 (attended negative,
  `reports/PF_GT007_LOGOUT_ECHO_ACK_CLIENT_TRANSITION_NEGATIVE_20260817.md`):
  the echo-only PF-012 shape was falsified at the client-observable layer —
  the real client neither returned to character select (03) nor exited (01).
- New fact from the GT-007 `GAME_LIVE` timeline: after the ack the client
  stayed parked on the never-closed socket, sending `GSCN_RunTimeProtocolReq`
  keepalives every ~2 s (19:33:57 → 19:40:14, until teardown), with no
  reconnect and no timeout.
- R40 corpus re-sweep: **no 0x1B40 response frame exists anywhere in the
  evidence** (the only grep hits were hexdump offset columns) — no golden.
- Therefore the minimal next falsifiable shape is the one lever the server
  owns without inventing a single payload byte: delayed clean TCP close.
  The full `0x3D4B` GetWorldInfoVital-first shape (R40 decode: 248B skeleton,
  4 float32 slots) is recorded in the ledger as the designed fallback and is
  not part of this claim.

## Implementation (opt-in, fail closed, no byte invented)

- `scenarios/logout_hypothesis_ack_close.json` — new exact-allowlist scenario,
  id `logout_hypothesis_ack_close_subcode01_03`, hypothesis `HYP-PF-013`;
  the request/ack pins are the unchanged PF-012 values.
- `src/pirateforce_foundation/logout_hypothesis.py` — the allowlist now accepts
  exactly two frozen profiles (echo / ack_close); any other content, including
  a changed `close_delay_ms`, is rejected.
- `src/pirateforce_foundation/runtime.py` — the PF-012 lane gains one guarded
  branch: with `post_ack_action=close_socket`, after `closed_at` commits and
  the ack is queued, a 250 ms timer pulls the attached transport close lever;
  without an attached lever the lane fails closed **before** the lease is
  touched (event `logout_hypothesis_close_unavailable_no_reply`). Without the
  flag the PF-012 behavior is byte-identical (proven by the unchanged PF-012
  test suite passing untouched).
- `src/pirateforce_foundation/connection.py` — `AcceptedGameSocket.bind` offers
  each state one closer over that connection's raw socket (`shutdown(2)` then
  `close()`, both idempotent, OSError-swallowed); only the ack_close scenario
  ever pulls it.

## Loopback unit layer (sandbox, this round)

`tests/test_logout_ack_close.py` — 10 tests: both subcodes return the
`HYP_PF_013_*_ACK_THEN_SERVER_SOCKET_CLOSE` action with the pinned PF-012 ack
bytes, commit `closed_at`, and schedule exactly one close at 0.250 s (recorded
timer factory; lever fires once); ack pins re-verified against
`LOGOUT_ACK_{PC,FRAME}_SHA256`; missing lever fails closed with no write; the
echo scenario never schedules a close; wrong payload/sequence fail closed with
no schedule; post-ack frames inside the close window stay counted-and-ignored;
tampered scenario JSON (production flag, delay, action, missing key) rejected;
`bind` attaches a shutdown-then-close lever (ordering asserted on a fake raw
socket, idempotent); duplicate/non-callable lever attach rejected.
Full sandbox suite: 424 passed + 1 pre-existing py3.10-only failure
(`test_server_shutdown` reads `__notes__`, a 3.11+ feature; unrelated files).

## Headless runtime layer (Windows, real server process, real TCP)

Job 084 (bridge, 20:22:07–20:22:49 ICT): server booted direct
(`py -3 -m pirateforce_foundation.app`, visible console) on a fresh copy of the
canonical DB (sha verified `FA794D0B..4400`, canonical untouched) with
`--second-password-mode bypass --logout-hypothesis-scenario
scenarios/logout_hypothesis_ack_close.json`. Probe
`pf_bridge/replay/pf_hyp013_probe.py` (sockets only; never touches
GameClient.exe) drove the proven R17/R19 world-entry replay, then per pass:

- **pass subcode 01**: ack byte-exact (single non-heartbeat frame, 46B,
  sha `9B417B5F..3D0A`), then **EOF at ack+253.5 ms** (window 100–2000 ms),
  no other dispatch frame; `GAME_LIVE` 20:22:25.881
  `SENT label=HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE`;
  lease 6 `closed_at` 2026-08-17T13:22:25.876Z = 20:22:25.876 ICT →
  **closed_at 5 ms before the ack SENT line**.
- **pass subcode 03**: ack byte-exact (46B, sha `AB172DFF..6696`), then
  **EOF at ack+254.1 ms**, no other dispatch frame; `GAME_LIVE` 20:22:41.671
  `SENT ...SUBCODE03...`; lease 7 `closed_at` 20:22:41.667 ICT →
  **closed_at 4 ms before the ack SENT line**.
- Run DB after (read-only copy): sessions total 7, **open 0**, integrity ok,
  backpack rows unchanged (GT-002 runtime-proven projection), no position
  rewrite. Run DB retained as evidence:
  `state/pirateforce_hyp013_20260817_202207.sqlite3`.
- Probe JSON: `pf_bridge/outbox/084_probe_20260817_202207.json` (`ok: true`,
  probe exit 0). Full job log:
  `pf_bridge/outbox/084_hyp013_headless.utf8.txt`.
- Sandbox loopback smoke earlier the same round reproduced identical numbers
  (EOF +250.4/250.5 ms), so the 250 ms schedule is platform-stable.

## Nonclaims

1. No client-observable claim (GT-008 owns: 01 window/process closes,
   03 leaves the map; a disconnect-error dialog would partially falsify this
   shape and route design to the recorded 0x3D4B-first fallback).
2. No original-server response-policy claim (no golden exists — R40).
3. No production or default-mode behavior; the scenario is opt-in and
   `production_allowed` stays false.
4. No lease-policy, reconnect, or store change (the close path writes nothing
   beyond the pre-existing `closed_at` commit).
5. No claim about subcodes other than 01/03 or requests outside the
   runtime-ready sequence (all fail closed, unchanged).
