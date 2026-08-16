# Pirate Force Lean Evidence Workflow

This file is the canonical execution workflow. `AGENTS.md` defines safety and
project boundaries; this file defines how work is selected, allocated, reviewed,
verified, and handed off. If older handoff prose conflicts with this file, follow
this file.

## 1. Outcome and work-in-progress limit

- The outcome remains a function-by-function playable local server driven by the
  unmodified game client, with persistence and reconnect proof wherever stateful.
- Keep exactly one active milestone. A milestone has one primary claim, explicit
  nonclaims, an acceptance oracle, and a stop rule written before implementation.
- Do not start an adjacent investigation merely because it is interesting. It must
  unblock the current claim or be the next dependency in the roadmap.
- Finish, retire, or record a bounded negative before moving to another milestone.

## 2. Milestone intake

Before work begins, record the following in the task plan or concise commentary:

1. User-visible or architectural outcome.
2. Evidence already accepted and the remaining gap.
3. Smallest implementation or observation that can close the gap.
4. Required evidence grade and exact pass/fail oracle.
5. Explicit nonclaims and stop rule.
6. Cloud/local allocation and the reason for any duplicated execution.
7. Risk tier and therefore the required review/test gates.

If the work cannot state these seven items, it is exploration. Time-box it and do
not let it silently become an implementation milestone.

## 3. Cloud/local allocation

- Cloud is the default for sanitized source changes, portable unit tests, static
  analysis, documentation consistency checks, and independent code review.
- Local Windows is reserved for GameClient, proprietary binaries/data, raw
  captures, Frida/instrumentation, Windows launchers, SQLite integration tied to
  local evidence, visual checks, and final runtime acceptance.
- Sanitize a seam instead of moving proprietary evidence to Cloud. If sanitizing
  would remove the fact being tested, keep that bounded lane local and say why.
- Never run the same test suite in Cloud and locally without a named purpose. Valid
  purposes are portability comparison, Windows-only integration, or the final
  authoritative local release gate. Otherwise reuse the first valid result.
- The authoritative local repository remains without a remote. Cloud work uses the
  explicitly sanitized code-only repository/environment described in the handoff.
- If no callable Cloud execution surface is available in the current task, do not
  simulate Cloud locally and call it Cloud. Continue only the necessary local lane
  and record the allocation limitation.

## 4. Execution loop and local resource budget

1. Inspect only current status, the relevant ledger entries, and directly needed
   source/evidence. Do not reload the full historical narrative.
2. During code work, close GameClient, Computer Use, recorders, and idle terminals.
3. During runtime work, keep only one server, one GameClient, one lightweight
   recorder, and the current command task.
4. Use one implementer. Add one reviewer only when the risk tier requires it; do
   not leave idle agents or duplicate audits running.
5. Prefer one stable diff over a chain of micro-corrections. Freeze the diff before
   requesting review.
6. Report only outcomes, blockers, user decisions, or a short update before three
   minutes of an active operation. Do not stream unchanged logs or reviewer chatter.

## 5. Test tiers

- **T0 — static hygiene:** compile/import check, schema/config validation,
  `git diff --check`, and direct invariants.
- **T1 — focused:** the changed module and its malformed, replay, ordering,
  rollback, and no-mode regressions. Use this inner loop while editing.
- **T2 — domain integration:** only the neighboring lifecycle, repository, wire,
  or platform boundary affected by the change.
- **T3 — full acceptance:** `tools\verify_foundation.ps1`, deterministic release,
  and V141 immutability. Run once after the diff is frozen and before accepting an
  implementation checkpoint. Rerun only after a material corrective changes code,
  tests, migrations, release membership, or verifier behavior.
- Docs-only wording or manifest corrections use T0 plus exact artifact rehash. They
  do not require T3 unless they change a verifier, canonical ledger, release input,
  or executable contract.
- Runtime is not a substitute for offline feedback-loop tests. Packet features must
  first prove bounded state, duplicate/replay behavior, timing/rate limits, and a
  circuit-breaker/stop condition where applicable.

## 6. Risk-based independent audit

- **High risk — mandatory one independent audit:** protocol emission or parser
  acceptance, migrations/transactions, persistence ownership, native hooks or
  instrumentation, security/authentication, destructive operations, release gates,
  or promotion of runtime evidence.
- **Medium risk — one targeted review when useful:** cross-module state changes,
  platform/process lifecycle, complex serialization, or evidence reports with a
  new factual ceiling.
- **Low risk — self-review:** wording, pointers, formatting, test refactors,
  mechanical integration, and docs-only corrections with no claim change.
- Review begins only after the producer declares a frozen diff and supplies focused
  results. The reviewer audits the claim boundary and highest-risk failure paths,
  not the entire project history.
- Permit one corrective re-review for actual blocker/medium findings. Additional
  review cycles require a material new defect, not wording preference or repeated
  reassurance.
- A reviewer PASS does not broaden the evidence grade. Runtime claims still require
  their own oracle.

## 7. Reverse engineering and hypothesis stop rules

- Static work must target a named producer, consumer, field binding, or observation
  seam. Stop after the bounded search is exhausted; record the negative and return
  to the roadmap instead of expanding into adjacent class/name mining.
- A class name, table string, UI label, or regression fixture is not field semantics.
- Never implement an unresolved value merely to keep activity moving. If a
  hypothesis is justified, register it in the canonical hypothesis ledger with
  strict scope, falsification artifact, expiry, and `production_allowed=false`.
- Do not build a second probe when the existing safe observation seam can answer the
  question. Do not rerun a stopped runtime lane without new evidence or a corrected
  failure mechanism.

## 8. Runtime acceptance

- Pin the exact client/server/config/database/capture roots and expected mutation
  allowlist before input.
- Identify the exact UI screen/control before clicking. Perform one bounded action,
  inspect the result, and never repeat an ambiguous or destructive action blindly.
- Preserve raw transport and authoritative DB/process oracles. Operator visual
  observations are labelled as such and never substituted for missing wire data.
- Stop on unexpected packet loops, client/server errors, ambiguous PID/process
  identity, out-of-scope DB mutation, or loss of the exact acceptance oracle.
- Stateful features require persistence/reconnect evidence before completion.

## 9. Documentation and evidence economy

- `STATUS.md` answers what is accepted now and what the next gap is.
- `docs/EXPERIMENT_LEDGER.md` records the milestone result and evidence ceiling.
- `docs/COMMAND_HANDOFF.md` records only durable operating context and the current
  next action. Do not repeat the full report in all three files.
- Write a long report and hash manifest only for a major runtime pass/negative,
  provenance-sensitive static checkpoint, or evidence promotion. Use the smallest
  artifact set that directly supports cited claims.
- Do not create a report for ordinary implementation iterations, review chatter, or
  wording-only corrections. Tests and commit history are the implementation record.
- Batch artifact cleanup only with explicit approval and recoverable-path checks.

## 10. Acceptance and handoff gates

A milestone may be accepted only when:

- its primary claim and nonclaims still match the implemented delta;
- required T0–T3 tests for its risk tier pass;
- required independent audit is complete after the final material diff;
- runtime/visual evidence exists when the claim is client-visible;
- persistence/reconnect exists when the claim is stateful;
- proprietary artifacts remain untracked and unpublished;
- status/ledger/handoff receive one concise final update; and
- the next action is either a single named dependency or an explicit stop.

Commits should normally be one implementation checkpoint, one corrective commit
only when needed, and one runtime evidence/docs checkpoint. Do not manufacture a
corrective commit or audit cycle when no correction exists.
