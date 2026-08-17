# GT-006 — typing in the chat box emits one unknown 34-byte vital per send, and nothing answers

Date: 2026-08-17
Scope: one attended observation run through the real `GameClient.local.bin`,
executed 14:37–14:38 inside the same session as the GT-001 smoke
(capture root `GameClient\capture_gt001_20260817_143122`, HEAD `abf3696`).
Observation only: no code changed, no semantic name is assigned to any raw
value, and no protocol hypothesis is opened by this report.

## Result

**Grade B controlled capture** for one claim:

> Typing an ASCII message into the client's chat box and pressing Enter emits
> exactly one 34-byte payload vital with id `0xAC52` — an id unknown to the
> server's registry — carried inside the standard `GSCN_RunTimeProtocolReq`
> envelope. The server dispatches nothing for it and answers nothing, and the
> client renders no echo of the message.

This is the first wire evidence ever collected for the `chat/client_chat_input`
matrix row, which until this run was `not_started` because nobody had tried.

## Measurements

### UI layer (directly observed)

- Click chat box → type `PFCHATPROBE1` (confirmed by zoom: text in the box with
  caret) → Enter → the input clears, **no message of any kind appears in the
  chat window** — no client echo, no error line, only the pre-existing
  `[ระบบ]` line. `PFCHATPROBE2` repeated with the same pre-send check at 14:38
  → identical outcome.
- Timing note with evidentiary value: the *first* attempt at PROBE2 (typed
  immediately after the first Enter without re-clicking the chat box) produced
  **no wire event at all** — consistent with focus leaving the chat box after a
  send, keystrokes presumably landing as hotkeys. The wire therefore carries 2
  events, not 3. Operational lesson: re-click the chat box before every typed
  probe.

### Wire layer (raw facts, byte-counting only — no decode)

`capture_v141\GAME_EVENTS_LIVE.txt` seq 2 and 3, each timed exactly at an Enter
press, both `id 0xAC52` (`name=UNKNOWN_0xAC52`, i.e. unknown to the server
registry), `version=0`, `vital_count=1`, `payload_bytes=34`:

```
14:37:53.848  frame=56  48000000004818000000500046004300480041005400500052004F00420045003100
14:38:33.926  frame=87  48000000004818000000500046004300480041005400500052004F00420045003200
```

- `GAME_LIVE.txt` shows both frames arriving as
  `RECV ... ids=[(0, 28271, 'GSCN_RunTimeProtocolReq'), (15, 44114, '0xAC52')]`
  with `pc_len=54`, surrounded by ordinary 12-byte
  `GSCN_RunTimeProtocolReq` heartbeats — the unknown vital rides the normal
  runtime envelope (44114 decimal = 0xAC52).
- Byte observations countable from the hex table (not a decode): the trailing
  24 bytes are the typed characters' codes interleaved with `0x00` one byte at
  a time (`P=50, F=46, C=43, …`), the two frames differing only in the final
  character (`31`/`32`); the leading 10 bytes are identical in both frames:
  `48 00 00 00 00 48 18 00 00 00`.
- **The server sent no frame in response to either event**, consistent with the
  absence of any UI echo: in `GAME_LIVE.txt` no `SENT` line follows frame 56 or
  frame 87 before the next heartbeat.
- Why a text scan finds nothing: job 061's grep for `PFCHATPROBE` over every
  capture file returned 0 because the on-wire message bytes are interleaved
  with `0x00` and are not contiguous ASCII. **A zero from that scan must never
  be read as "no frame was sent."**

## Non-claims

Not proven or named here: what `0xAC52` means, what the prefix bytes encode,
any channel/whisper/broadcast semantics, any length limit, what the original
server would answer, or whether the client-side rendering path would display a
server response. No semantic name is assigned to any raw value, per the
standing rule.

## Matrix consequence

`chat/client_chat_input` moves `not_started` → `in_progress` on this evidence
in the same commit (the row's first evidence ever). The row cannot go higher:
the request is captured but not decoded, not dispatched, and nothing answers.

## Evidence

Hash-pinned in `PF_GT006_CHAT_INPUT_UNKNOWN_FRAME_WIRE_CAPTURE_20260817.manifest`:
`GAME_EVENTS_LIVE.txt` (seq 2–3), the full raw GAME log
`GAME_20260817_143546_708289_57440.txt` (frames 56 and 87), `GAME_LIVE.txt`,
the server console `server_console_live.out.txt`, and the teardown job log
`pf_bridge\outbox\061_gt001_teardown.utf8.txt` (which records the zero-hit
ASCII scan and the clean post-run database state).
