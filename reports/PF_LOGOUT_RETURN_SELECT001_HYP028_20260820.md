# LOGOUT-RETURN-SELECT-001 (HYP-PF-028) - the return-select-server logout response

Round 101 - 2026-08-20 - chief, under the owner's standing pre-approval of
2026-08-19 for newly found gameplay functions under the standard pattern
(opt-in, production_allowed false, fail closed, ledger/verifier/matrix, headless
proof).  This is the server half of GT-033 variant B.

## Why this lane exists

GT-026 (round 100, attended) drove the real in-game logout button for the first
time on a corrected PLAYBOOK.  The client sent `LogoutVital` (0x1B40, subcode
03 = return to character select, subcode 01 = exit game) and then WAITED: it
did not freeze, but it did not transition either, because the default server
does not answer.  Round-100 static RE (agent D) then explained the mechanism
and named the candidate:

- **An echo can never transition the client.**  Every vital echoed inside the
  `GSCN_RunTimeProtocolRes` envelope is consumed by the inbound actor-vital
  RECONCILE pass at 0x446F30, which only adds / updates / removes actor-attached
  vitals and contains no branch that switches scene, state, or connection.  This
  is why HYP-PF-012 (echo) left the client parked (GT-007) - now with a
  mechanism, not just an observation.
- **The transition is driven by a session/connection orchestrator** (vtable
  0xf45030; methods 0x719c30 / 0x719ab0 / 0x719b90) that reads a mode field
  (+0x28 in {1,4}) and a timer (+0x24) and then CLOSES its game connection(s)
  via the virtual [vtable+0xf4].  The client's shape is "set a mode, wait for a
  server-side connection close / redirect, then switch to `cStateSelectServer`
  or quit."
- **`ReturnSelectServerVital` (0x709E) is the strongest NAMED candidate** for
  the char-select direction, but agent D found NO client code path that consumes
  0x709E to drive the transition (its id-getter 0x5e6960 has zero callers; no
  inbound handler keys on 0x709E).  Whether sending it transitions the client is
  therefore UNDECIDABLE from the client binary and is exactly the queued
  attended A/B (GT-033).

This lane builds the server so an attended run can answer that A/B.  Variant A
(close the connection) already exists as HYP-PF-013 (`logout_hypothesis_ack_
close.json`).  Variant B is this lane: answer `LogoutVital` with a well-formed
`ReturnSelectServerVital` 0x709E, then the pinned ack, then the proven clean
close.

## Static provenance of the 0x709E body (round-101 pass)

The `ReturnSelectServerVital` wire serializer was decoded from
`GameClient.local.bin` (sha256
`9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623`, image base
0x400000) the same way agent D decoded LogoutVital's 0x5e6820.  Key addresses:

- Descriptor method table (stride 0x24) at **0xf304ec**; slot0 id-getter
  **0x5e6960** (`mov ax,[0x1082080]; ret`), where [0x1082080] holds 0x709E
  (verified name-hash `sum((i+1)*ord(c))&0xFFFF` of "ReturnSelectServerVital" =
  0x709E).
- **slot2 serializer = 0x5e69f0** (symmetric read/write, `cmp byte[esp+8],0`).
  Its write path emits exactly three fields, in order:

  | # | object off | wire tag | C type | wire |
  |---|-----------|----------|--------|------|
  | 1 | +0x14 | 0x08 | u8 | `08 <v>` |
  | 2 | +0x18 | 0x32 | 8-byte scalar | `32 <8 bytes>` |
  | 3 | +0x20 | 0x44 | `std::string` (u32 length + data) | `44 <u32 len><data>` |

  Field 3 is a `std::basic_string<char>` (the primitive 0x89a6d0 calls
  `basic_string::length()` [0xc3b470] and `c_str()` [0xc3b494]).  The scalar
  write primitive is 0x89a600; the tag-writer gate is 0x89a4d0.

**No producer sets these fields to non-zero content** - the id-getter has zero
callers, no inbound handler keys on 0x709E, and only the reflection/registry
framework references the descriptor singleton (0x1030fb8).  So the field VALUES
have no client-side source, and the honest minimal well-formed body is all-zero:

```
08 00  32 00 00 00 00 00 00 00 00  44 00 00 00 00        (16 bytes)
```

Every tag byte (0x08, 0x32, 0x44) is read from the client's own serializer;
nothing structural is invented.  The two scalar values default to 0 and the
string is empty - an explicit nonclaim, the same honest default agent D applied
to LogoutVital's unknown fields.

## What the server composes

`make_return_select_server_response(legacy)` wraps the 16-byte body in the
accepted `GSCN_RunTimeProtocolRes` v4 envelope (`make_runtime_vitals`, one vital,
nested id 0x709E version 0), giving a deterministic frame:

- response PC 38 bytes, sha256 `A4C8DF4299EA7C3A5EE5554D1D29D7F8C1A2B51031CA210CBEB9AF2AD9D4CA9E`
- response frame 48 bytes, sha256 `08C2A925BD67CD3D0AFA7992F98D472ED8FD22787756521A5DF8CBF174E5CB8E`

PC layout: `12 9D6E | 14 00000000 | 08 04 | 0B 02 | 12 0100 | 12 9E70 | 0B 00 |
08 00 32 00..00 44 00000000 | 0B 00` (the trailing derived-class change mask
`0B 00` is the DELETE-SOFT-002 lesson).

On a captured `LogoutVital` from a runtime-ready session the dispatcher queues,
in strict order on the one TCP stream: the 0x709E response FIRST, the
byte-identical hash-pinned PF-012 ack SECOND, then the PF-013 clean socket close
at 250 ms.  The session lease `closed_at` is committed before any response byte
is queued.  Wrong payloads, wrong sequences, replays after the ack, a missing
close lever, and every frame without the opt-in scenario fail closed with no
reply and no write.  The three pre-existing logout scenarios (echo, ack+close,
worldinfo-first) stay byte-identical, and `production_allowed` is false
everywhere.

## Proof (headless; no client, no socket, no server process)

- `tools/verify_logout_return_select_encoder.py` - 34 guards, RESULT PASS.
  Re-derives the 16-byte body by an independent hand-walker (tag 0x08 u8, 0x32
  8-byte, 0x44 empty string), re-pins the composed response, confirms the
  PF-012/013 pins are unchanged, and drives every scenario-allowlist tamper to a
  named refusal.
- `tools/pf_logout_return_select_headless_replay.py` - 45 guards, RESULT PASS.
  Drives the REAL `make_state_class` dispatcher on a throwaway COPY of the
  database for subcodes 03 and 01: exactly two queued actions (0x709E response
  then PF-012 ack), `closed_at` committed before either byte, PF-013 close
  scheduled, only the `sessions` table changes, the source database is untouched
  end to end, and an independent walker reads the dispatched 0x709E frame back
  from byte zero (all body fields zero, empty string).
- `tests/test_logout_return_select_hypothesis.py` - 13 tests: profile fields,
  body provenance, pinned composition, both-subcode ordering, fail-closed
  guards, isolation of the other logout scenarios, and the exact-allowlist
  tamper traps.

## Nonclaims

- The response is OUR design, NOT the original server's return-select response,
  which is unknown and unrecoverable (the original server is closed, unpublished
  and unrecoverable).
- The 0x709E field values and the string are the honest zero default; no client
  producer exists to say what they should be.
- NO CLAIM that the client consumes 0x709E or transitions to character select.
  Agent D proved that is undecidable from the binary; a negative attended result
  (client does not transition on 0x709E) is itself a real result and would
  strengthen the reading that the operative lever is a connection teardown
  (variant A), not a response vital.
- NO CLIENT HAS EVER BEEN SHOWN ONE BYTE OF THIS PROFILE.  GT-033 is queued,
  not run; no coverage row grade moves until a human watches the screen.
