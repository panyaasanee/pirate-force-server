# รอบใหญ่ #2 — attended UI test results, processed (GT-008 / GT-009 / GT-010 / GT-001)

Date: 2026-08-18 · Attended by the main session (ผู้เทส) 01:33–02:15 · Processed
by chief scheduled round 52. Raw result blocks with full timing live in
`pf_bridge/GAME_TEST_QUEUE.md` (archived blocks:
`pf_bridge/archive/GAME_TEST_QUEUE_ARCHIVE_20260818.md`); this report is the
repo-side record backing the ledger and coverage-matrix movements.

## One claim per test, client-observable layer only

Wire/DB layers were all headless-proven before the round and are cited, not
re-claimed.

### GT-008 — HYP-PF-013 ack+socket-close: ❌ FAIL, shape falsified (both subcodes)

After the pinned PF-012 echo ack the server cleanly shut down the accepted
socket at ack+250 ms (wire layer re-confirmed by teardown job 088 ×2). The
client **never noticed at all** on either subcode: no transition, no error
dialog, no disconnect handling for 40+ s, UI fully responsive, world running
(subcode 03 pressed 01:39:42; subcode 01 pressed 01:47:20 on a second boot).
A ~20 s white-flash after the socket died was a render stutter that recovered
by itself, not a freeze. **Conclusion for design: the client's screen
transitions are not driven by the TCP layer; they need a protocol response
frame the client recognizes. Follow-up = 0x3D4B-first fallback (ledger
PF-013 design note), to be opened as a new entry when implemented.**

### GT-009 — HYP-PF-014 chat echo: ✅ PASS — first chat message ever rendered in the project

`PFCHATPROBE1/2/9` each rendered in the chat window as `[ทั่วไป] : PFCHATPROBEn`
(white text, channel tag, **no speaker name**, input box cleared after send).
Echo is not one-shot and the general 12-ASCII shape works, not just the two
hash-pinned probes. UI-side fail-closed confirmed: a 5-char message got
silence, no error. HYP-PF-014 passes client acceptance. Follow-up research on
the speaker-name field and channel tag:
`reports/PF_CHAT_ECHO002_SPEAKER_FIELD_RESEARCH_20260818.md` (0xAC52 is
`Channel_LocalTalkMessageVital`; the payload reads as two wstrings with an
empty speaker slot; `[ทั่วไป] ` and `: ` are client text resources id 540/451).

### GT-010 — HYP-PF-015 delete character: ❌⭐ FAIL as specified, but both envelope answers were captured

Real delete flow (never seen before): leftmost button on char select →
plain yes/no dialog (no name-typing, unlike the DELETE-003 guess) → a
second-step password pad with a randomized on-screen keyboard (`test` typed) →
client error dialog `GSCN_RunTimeProtocolRes ErrorData=28317`, character
still listed. Wire/DB: the server parsed the **first natural 0x36DB of the
project** and committed `deleted_at` 39 ms before the ack on the test copy —
request envelope **confirmed**; response envelope **falsified** (client
over-read: the v1 ack lacked the RuntimeRes trailing derived-class mask
`0B 00`; 28317 = 0x6E9D = the RuntimeRes class id). Decode:
`reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md`. Fix +
headless GREEN same round:
`reports/PF_DELETE_SOFT003_RUNTIMERES_TAIL_FIX_HEADLESS_20260818.md`.
Attended re-test queued as GT-011.

### GT-001 — smoke full-loop at `005b3d4`: ✅ PASS (3rd attended pass)

Full loop, sessions 5→6, lease 5→6, backpack `[1@0,2@1,4@3]` and position
X:-8,094 Y:-3,207 persisted unchanged, integrity ok. `TeleportVital` observed
exactly once in GAME_LIVE (per the TELEPORT_AUDIT001 watch); no stray gift UI
in any of the night's four tests. Canonical sha after this boot =
`B5557E9F3874BFA452B14A01495C4F7E0EA8176AF9C14BE09CF66865A597C9ED` (the boot
created a new session row; migration 004 had already been applied at 01:22 —
see the incident note below).

## Incident processed with this round

During the round-51 Windows gate (job 096) at 01:22:31, migration 004 was
applied to the **canonical** DB by pytest itself:
`test_runtime_console.py::test_self_test_only_is_the_console_exception`
booted the app without `--db`, which resolves to the canonical path and runs
`store.migrate()` + `expire_open_sessions()` on it. Latent since the test
existed (migrations 001–003 were already applied → no-op → invisible); data
verified intact by the attended session. Root-cause fix in this commit (the
test now passes an explicit scratch `--db`) plus a systemic guard (the gate
job now snapshots the canonical sha before/after pytest and goes RED on any
movement). Details: `pf_bridge/FINDINGS_R41_PYTEST_TOUCHED_CANONICAL_DB.md`.

## Evidence (attended layer — outside-repo paths, hashed in the manifest)

GT-008: `GameClient/capture_gt008_20260818_013613/` + `_014313/` + teardown
logs `pf_bridge/outbox/088_*`; DB copies
`state/pirateforce_gt008_20260818_013613/_014313.sqlite3`.
GT-009: `GameClient/capture_gt009_20260818_015036/` + `091_*` + DB copy.
GT-010: `GameClient/capture_gt010_20260818_015927/` + `098_*` + DB copy.
GT-001: `GameClient/capture_gt001_20260818_020703/` + `073_*` (canonical DB
itself, not manifested — it legitimately moves with every session).

## Nonclaims

Per-test nonclaims live in the queue blocks and are all kept (no multi-cycle
logout, no non-ASCII/Thai chat, no channel/whisper semantics, no UI-layer
slot-reuse proof, no golden-server response claims anywhere). The white-flash
cause is unexplained observation only.
