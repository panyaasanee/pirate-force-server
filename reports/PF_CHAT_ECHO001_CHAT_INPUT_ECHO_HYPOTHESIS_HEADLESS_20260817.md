# PF CHAT-ECHO-001 — HYP-PF-014 designed chat input echo, headless wire proof (2026-08-17)

One claim (Grade B, wire layer only): behind the
`scenarios/chat_input_hypothesis_echo.json` opt-in
(`response_policy: echo_exact_request_vital_no_write_no_close`,
`production_allowed: false`), the Foundation server acknowledges the exact
captured chat input frame shape — the vital id `0xAC52` (44114,
`UNKNOWN_0xAC52`, unknown to the server registry and named here only by the
UI action GT-006 proved emits it — with a **designed byte-exact echo**: the
34-byte request payload wrapped in the accepted `GSCN_RunTimeProtocolRes` v4
single-vital envelope (56-byte PC / 66-byte frame, both captured probes
hash-pinned end to end). The lane writes nothing to the database (chat has
no table and no repository call exists on the path), never touches the
socket, echoes **every** accepted frame on a session (deliberately not
one-shot), and fails closed on everything else. **No client-observable claim
is made**: whether the real client renders the echoed message in its chat
window — instead of the GT-006 silent-window baseline — is exactly the
attended big-round check queued for this shape.

## Why this shape (design lineage)

- GT-006 (grade B wire capture,
  `reports/PF_GT006_CHAT_INPUT_UNKNOWN_FRAME_WIRE_CAPTURE_20260817.md`):
  typing an ASCII message in the chat box and pressing Enter emits exactly
  one 34-byte payload vital id `0xAC52` inside the standard
  `GSCN_RunTimeProtocolReq` envelope (pc_len 54); the server dispatches
  nothing and answers nothing, and the client renders no echo. Two probes
  captured, differing only in the final typed character.
- No `0xAC52` response frame exists anywhere in the corpus — no golden. The
  echo response shape is therefore a designed hypothesis, not a
  reproduction. It reuses the same accepted RuntimeRes envelope lever whose
  deliverability GT-007 confirmed on the real client for HYP-PF-012.
- Byte index 6 of the payload (0x18 = 24) is a *candidate* length field that
  two equal-length samples cannot prove: the 10-byte prefix is pinned as one
  opaque blob and nothing decodes it.

## Implementation (opt-in, fail closed, no write, no close)

- `scenarios/chat_input_hypothesis_echo.json` — exact-allowlist scenario, id
  `chat_input_hypothesis_echo_ascii12`, hypothesis `HYP-PF-014`; pins the
  request shape (payload 34B, prefix `48 00 00 00 00 48 18 00 00 00`, 12
  printable-ASCII (low, 0x00) pairs), both request probes (payload + 54B pc
  sha256), and both composed echoes (56B pc / 66B frame sha256).
- `src/pirateforce_foundation/chat_input_hypothesis.py` — shape
  classification (fail closed: wrong length, wrong prefix, non-zero high
  byte, non-printable low byte, wrong envelope) and the drift-checked echo
  composer (`make_chat_input_echo_response`: structural pins for every
  accepted payload, full hash pins for the two captured probes).
- `src/pirateforce_foundation/runtime.py` — dispatch owns `0xAC52` only
  while the scenario is active: classification → selected-character check →
  runtime-ready sequence check → composed echo, event
  `chat_input_hypothesis_echo_ack_ascii12`, action
  `HYP_PF_014_CHAT_INPUT_ECHO_ASCII12`. No store call, no socket action,
  no one-shot latch; every rejection appends a
  `chat_input_hypothesis_*_no_reply` event and returns nothing.
- `src/pirateforce_foundation/app.py` — `--chat-input-hypothesis-scenario`
  (mutually exclusive with every other scenario mode, requires an explicit
  existing `--db`).

## Loopback unit layer (sandbox, this round)

`tests/test_chat_input_echo.py` — 15 tests: both captured probes echo
byte-exactly through the real dispatch path (action + pc/frame sizes 56/66 +
pinned hashes + payload at the fixed envelope offset); three consecutive
sends (probe1, probe2, probe1) are each echoed (not one-shot, count 3);
database file bytes identical before/after the chat dispatches and the
session lease stays open; wrong lengths (32/36), wrong prefix (one flipped
byte), non-zero high byte, non-printable 0x1F/0x7F low bytes, wrong
envelopes (nested version, outer version, outer id) and wrong sequences
(not runtime-ready, no selected character) all fail closed with the named
`_no_reply` events; without the scenario the frame stays counted-and-ignored
exactly as GT-006 observed; the scenario allowlist rejects tampered JSON
(production flag, id, extra/missing field, payload_size, response hash); the
response maker rejects non-conforming payloads and accepts any 12-pair
printable payload structurally; request fixtures re-verified against the
GT-006 capture pins; chat+logout scenarios are mutually exclusive.
`tests/test_presentation_ownership.py` — the GT-006 ownership negative ("no
Foundation module mentions the unknown chat vital") demanded, in its own
docstring, to be revisited in the same change that starts handling the
vital: the pin moved from the empty list to the exact HYP-PF-014 lane files
(`chat_input_hypothesis.py`, `runtime.py`), so any module beyond the lane
mentioning `0xAC52` still fails loudly.
Full sandbox suite: 439 passed (424 baseline + 15 new) + 1 pre-existing
py3.10-only failure (`test_server_shutdown` reads `__notes__`, a 3.11+
feature; unrelated files) — same single known failure as rounds 42–43, no
new failures.

## Headless runtime layer (sandbox, real server process, real TCP)

Sandbox loopback smoke, 2026-08-17 16:39 UTC (run dir
`run_20260817_163935`): server booted as a real process
(`python3 -m pirateforce_foundation.app`) on a fresh copy of the canonical
DB (canonical sha verified `FA794D0B..4400` before and after — untouched)
with `--chat-input-hypothesis-scenario scenarios/chat_input_hypothesis_echo.json`.
Probe `pf_bridge/replay/pf_hyp014_chat_probe.py` (sockets only; never
touches GameClient.exe) drove the proven R17/R19 world-entry replay (10
frames from the canonical demo capture, 0.34/1.75 cadence, 11 frames
received, no EOF), then sent the **byte-exact captured client chat frames**
(extracted from the GT-001 capture where GT-006 recorded them) as probe1,
probe2, probe1-again on one connection:

- **send 1 (probe1)**: exactly one non-heartbeat frame in the window — 66B,
  sha `06C23375..2323` (pinned) — at **+9.5 ms**; no EOF.
- **send 2 (probe2)**: echo byte-exact, 66B, sha `E97A1225..EA10` (pinned),
  at **+1.7 ms**; no EOF.
- **send 3 (probe1 repeated)**: echoed **again** byte-exactly (+1.5 ms) —
  the lane is not one-shot; no EOF.
- No other dispatch frame in any window; the frozen v141 clock heartbeat
  kept its ~2 s cadence through every window and the 4.5 s tail
  (3 heartbeats, 0 dispatch frames).
- **DB unchanged across the chat window**: run-DB file sha256
  `F39324B8..8578` immediately before send 1 == immediately after the last
  echo (`db_unchanged_across_chat: true`). The only later write is the
  teardown lease close: after SIGINT shutdown the run DB (read-only open)
  shows sessions 6/6 closed, open 0, integrity ok.
- Probe exit 0, `ok: true`. Evidence:
  `reports/chat_echo001_smoke/CHAT_ECHO001_sandbox_smoke_20260817_163935_transcript.txt`
  (full driver transcript: canonical shas, boot, probe say-lines, teardown)
  and `..._probe.json` (machine-readable summary), both hash-pinned in the
  manifest. Server process ended cleanly on SIGINT; nothing left running.

The Windows-side bridge re-run of the same probe (same pins, plus
`--db-file` on the run copy) is available to the chief as the usual gate
step; the probe script is bridge-compatible by construction (stdlib +
capture parsing only).

## Nonclaims

1. No client-observable claim (does the real client render the echoed
   message, and how — the attended big round owns this; the GT-006 baseline
   is a silent chat window).
2. No semantic claim: `0xAC52` keeps the name `UNKNOWN_0xAC52` / "chat
   input frame" (the proven UI action), the prefix bytes stay undecoded,
   and the 0x18 byte stays a candidate, not a length field.
3. No original-server response-policy claim (no golden exists).
4. No channel, whisper, broadcast, delivery-to-others, or persistence
   claim; no message lengths other than 12 characters; no non-ASCII/Thai
   text (all fail closed by the shape pin).
5. No production or default-mode behavior; the scenario is opt-in and
   `production_allowed` stays false; without the flag the frame remains
   counted-and-ignored exactly as GT-006 observed.
