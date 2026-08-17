# DELETE-SOFT-001 — Soft delete + slot reuse, headless wire/DB pass (HYP-PF-015)

Date: 2026-08-18 · Chief scheduled round 51 · Owner decision: Lane 1 Option B
(2026-08-18 00:52, recorded in `pf_bridge/CHIEF_CONTINUATION.md` head block)

## Primary claim (grade B, wire/DB layer only)

Behind the explicit opt-in scenario
`scenarios/delete_actor_hypothesis_soft_delete.json` (`production_allowed`
false), a real server process over a scratch migrated DB completed the
owner-mandated cycle **create → soft delete → recreate into the same slot**
end to end over real TCP:

1. the designed `DeleteActorVital` op-1 request (34-byte PC in the designed
   one-vital `GSCN_LoginProtocol` envelope) was answered by **exactly one**
   non-heartbeat frame, byte-equal to the pinned designed echo ack
   (44-byte frame, sha
   `4132E4014572E829C6A9F258B22BB3C76B48C76CFA18CC6EB0B379D24E22DECA`);
2. the character row had `deleted_at` set, the active list projected empty,
   and the child position/backpack rows survived unchanged as history;
3. an op-2 request produced **no reply and no write** (fail closed);
4. a second connection recreated with the byte-identical captured V25 create
   PC **into the freed slot**: new active row with the same selector (0),
   the same `identity_lo`/`identity_hi`, and the same `create_fingerprint`
   as the soft-deleted row, which itself survives (`total_rows=2`,
   `active=1`).

Slot reuse is enabled by migration
`migrations/004_character_soft_delete_reuse.sql`: the two table-level UNIQUE
constraints and the fingerprint unique index are replaced by **partial unique
indexes** (`WHERE deleted_at IS NULL`). The migration was proven on a copy of
the canonical DB before being committed (row-identical copy, clean
`PRAGMA foreign_key_check`, guard-checked rebuild; the canonical DB applies
it on the next server start).

## Provenance and design boundary

- Nested record, id 0x36DB, version 1, and both producer op values:
  DELETE-003 grade-A static decode
  (`reports/PF_DELETE003_PRODUCER_OUTER_FRAMING_NEGATIVE_20260816.md`).
- **No natural 0x36DB wire exists in any corpus** (DELETE-003 bounded
  negative still true). Both the accepted request envelope
  (`GSCN_LoginProtocol` one-vital, the shape every captured
  character-select-stage request uses) and the echo-ack response
  (`GSCN_RunTimeProtocolRes` v4 single-vital, the envelope every accepted
  character-select-stage response uses) are **designed hypotheses** under
  HYP-PF-015, fail-closed everywhere else.
- The DELETE-003 stop rule ("do not add a dispatcher branch / deleted_at
  mutation before a natural capture") is superseded by the owner's explicit
  Lane-1 Option-B decision of 2026-08-18 00:52 and the standing pre-approval
  of 2026-08-17 18:2x; its nonclaims (no semantic names for op values, no
  claim about the original server) are kept.

## Evidence

- `reports/delete_soft001_smoke/DELETE_SOFT001_sandbox_smoke_20260818_010214_probe.json`
  — verdict JSON, all checks true, exit 0.
- `reports/delete_soft001_smoke/DELETE_SOFT001_sandbox_smoke_20260818_010214_transcript.txt`
  — probe stdout.
- Probe: `pf_bridge/replay/pf_hyp015_delete_probe.py` (sockets + scratch DB
  only; never touches the canonical DB or GameClient).
- Offline: `tests/test_delete_actor_hypothesis.py` (9 tests) proves the
  commit-before-ack ordering, the pinned probe forms, the exact scenario
  allowlist, the classifier fail-closed set, the store guards (stale
  session, unknown selector, double delete, selected-by-open-session), and
  the reuse cycle through the real dispatch path.

## Nonclaims / evidence gap

- No claim about the original server's request envelope, response bytes, or
  refresh behavior. Op values 1 and 2 keep no semantic names; op 2 stays
  fail-closed.
- Client-observable layer is **unmeasured**: whether the real client's
  delete button emits this envelope, accepts the echo ack, refreshes the
  list, and shows the freed slot is exactly the attended big-round claim
  (queued in `pf_bridge/GAME_TEST_QUEUE.md`). The first natural 0x36DB
  capture falsifies or confirms the designed envelope.
- No production exposure: default-mode dispatch is unchanged (frame counted,
  no reply, no write — offline-tested).
