# DELETE-SOFT-002 — RuntimeRes trailing-mask fix for the delete ack, headless wire/DB pass (HYP-PF-015 v2)

Date: 2026-08-18 · Chief scheduled round 52 · Trigger: attended GT-010
falsification of the v1 ack (2026-08-18 01:59–02:06, รอบใหญ่ #2), processed
under the owner's standing pre-approval of 2026-08-17 18:2x.

## Primary claim (grade B, wire/DB layer only)

The designed delete ack is now the exact request vital echoed inside the
accepted `GSCN_RunTimeProtocolRes` v4 single-vital **collection** envelope
**with the trailing derived-class change mask `0B 00`**
(`make_runtime_vitals`), replacing the tail-less v1 composition
(`make_runtime_vital`) that attended GT-010 falsified live. With only this
change (one call-site swap plus the moved ack pins; the request side,
guards, commit-before-ack ordering, scenario, and migration are untouched),
a real server process over a scratch DB (copy of the GT-010 test copy, which
already carries migration 004) completed the full owner-mandated cycle
**create → soft delete → recreate into the same slot** end to end over real
TCP: exactly one non-heartbeat delete reply, byte-equal to the new pin
(46-byte frame, sha `055ACBB0…223E`); `deleted_at` committed before the ack;
children survive as history; op-2 silent with no write; recreate reuses
selector/identity/fingerprint while the history row survives
(`total_rows_after_cycle=3` on the GT-010-copy scratch which already held
one deleted row from the attended run).

## Why the v1 ack failed (decode summary)

Full decode: `reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md`.

- Attended GT-010 produced the project's **first natural 0x36DB wire**. The
  request confirmed the designed envelope byte-compatible (outer 0x453A v0
  mask 0x02 count 1, nested 0x36DB v1, op 1, selector 0, zero u32); the only
  free field is the opaque UI wstring, which carried a 32-char ASCII-hex
  token (still opaque; DELETE-003 nonclaim kept). The server parsed it and
  committed the soft delete on the test copy (`deleted_at` 39 ms before the
  ack).
- The client then rejected our v1 ack with
  `GSCN_RunTimeProtocolRes ErrorData=28317`. 28317 = 0x6E9D = the protocol
  class id of `GSCN_RUNTIME_PROTOCOL_RES` itself: a "RuntimeRes stream did
  not read out cleanly" error, not an unknown-vital error. RuntimeRes v4
  carries a second (derived-class) change mask after the inherited VitalData
  collection; every RuntimeRes collection response the client accepted live
  in the same session (character_list, create_success) ends with `0B 00`,
  and `make_runtime_vitals` documents this exact over-read failure mode.
  Our v1 delete ack was the only RuntimeRes ever sent without it.
- Net effect observed live: **state divergence** — server-side delete
  committed, client-side delete rejected. On a real DB the player would see
  a character disappear at next login without UI confirmation. This is why
  the fix must land before GT-011 re-arms the attended claim.

## Evidence

- `reports/delete_soft003_smoke/DELETE_SOFT003_sandbox_smoke_20260818_024727_probe.json`
  — verdict JSON, all checks true, exit 0 (probe run in the chief sandbox,
  server + real TCP + scratch DB `/tmp/hyp015_v2_scratch.sqlite3`, a copy of
  `state/pirateforce_gt010_20260818_015927.sqlite3`).
- `reports/delete_soft003_smoke/DELETE_SOFT003_sandbox_smoke_20260818_024727_transcript.txt`
  — probe stdout.
- (`…024701_transcript.txt` in the same directory is a superseded stub from
  an aborted invocation refused by the probe's repo-write guard; no server
  ran, no DB was touched. Kept only because the sandbox mount cannot unlink.)
- Probe: `pf_bridge/replay/pf_hyp015_delete_probe.py`, unchanged — it reads
  the ack pins from the module, so the same probe that proved v1 GREEN now
  proves v2 GREEN against the moved pins.
- New pins (module constants in
  `src/pirateforce_foundation/delete_actor_hypothesis.py`): ack PCs 36/52
  bytes, ack frames 46/62 bytes (+2 bytes each over v1); request pins
  unchanged.

## Nonclaims

- No claim that the real client *accepts* the v2 ack or refreshes its list —
  that is exactly the re-queued attended claim (GT-011).
- No claim about the original server's delete response (no golden trace).
- Op-2 semantics, the opaque wstring token, restore/undelete, second-password
  server-side verification, and retention policy remain out of scope.
- The GT-010 password pad and its `test` entry are not claimed to be
  server-verified (the server's second-password bypass was active).
