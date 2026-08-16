# Coverage test-strength audit — 2026-08-17

## Question

`docs/COVERAGE_TEST_AUDIT_20260817.md` (M9) closed the *mechanical* gap: every
graded row in `docs/FUNCTIONAL_COVERAGE.json` now names at least one test, and
`tests/test_functional_coverage.py` ratchets that shut.

This audit asks the harder question that the ratchet cannot ask:

> **Does the cited test actually watch the claim the row makes?**

A citation that points at a real, passing test module still watches nothing if
that module tests a different behavior. The count looks healthy either way, so
the only way to find out is to read every cited module against the row's own
`notes` text.

## Method

For all **36 graded rows** (18 `runtime_pass`, 15 `in_progress`, 3 `blocked`;
the 15 `not_started` rows carry nothing by ratchet) the cited modules were
enumerated by test-method name and read against the row's claim. Each row was
sorted into one of three verdicts:

- **watched** — at least one cited test fails if the claim stops being true
- **bookkeeping gap** — a test that watches the claim already exists in the
  repository but the row does not cite it
- **unwatched** — nothing in the repository watches the claim

## Result

| verdict | rows |
|---|---|
| watched (before this audit) | 32 |
| bookkeeping gap | 3 |
| unwatched | 1 |
| **rows repaired this round** | **4** |

The smell that led to the finding: **`tests/test_connection_lifecycle.py` was
cited by 7 rows spread across 4 different domains** — inventory, session
lifecycle, movement and character management. A single 512-line module about
lease and socket teardown cannot be the thing that watches four domains. Two of
those seven rows cited it *and nothing else*.

## Repaired rows

### 1. `session_lifecycle/session_row_persistence` — was **unwatched**

Claim: *"Read-only post-state oracle confirms one session row with both
timestamps, integrity ok and an empty foreign-key check."*

Sole citation was `tests/test_connection_lifecycle.py`. That module does query
`sessions.closed_at`, twice — but only as a side observation while asserting
that a *lease* was closed on an error path. Nothing in the repository watched
the row shape, the `lease_generation` sequence, the accumulated session
history, the idempotence of `close_session`, or the `integrity_check` /
`foreign_key_check` pair that the runtime report actually leans on.

**Fix: new module `tests/test_session_row_persistence.py` (13 tests).** It
drives the real `SQLiteStore` and `CharacterLifecycle` against a temporary file
database and reproduces the runtime oracle offline, reading through
`connect_read_only()` — the same read-only path the runtime post-state check
used.

It deliberately does **not** drive `FoundationSession.select_and_start`,
because that method carries the opt-in gate that is under active revision as
M3 work in progress; this claim belongs to the store, not to that gate.

Nonclaims, kept identical to the runtime report: no concurrent multi-client
session, no account isolation as a security property, no credential policy,
nothing about what the client observed.

### 2. `session_lifecycle/character_select_to_scene_entry` — bookkeeping gap

Claim: *"One single-client session reaching Port Royal with the persisted name
projected, then exiting cleanly."*

`tests/test_foundation.py::test_create_list_select_start_same_identity` asserts
the select-then-start projection carries the persisted name exactly once and
that the built `ActorAttr` matches, and `test_exit_restart_load_position`
covers the exit-and-reload half. Both already existed; neither was cited.
Added, together with the new session-row module, which watches the
select-binds-then-exit-closes half at the store.

### 3. `character_management/character_list_projection` — bookkeeping gap

Claim: *"One persisted character was listed and selected through the real
client."* `test_create_list_select_start_same_identity` asserts the character's
`actor_wire` appears inside the list frame, and
`test_retry_multi_character_and_account_isolation` covers the multi-character
listing path. `tests/test_foundation.py` added.

### 4. `combat/hostile_relation_and_target_selection` — bookkeeping gap

Claim: *"One faction value made a scene actor selectable as hostile ... Tab
selection alone produced TargetVital without any action, per the V132
negative."*

Both cited modules (`test_relation_probe.py`, `test_relation_matrix_probe.py`)
guard the *probe instrumentation* — binary hashes, relocation bounds, event
schema strictness. They are the right tests for the provenance of the evidence,
but they never exercise the server-side seam. Two modules that do already
existed:

- `tests/test_arena.py::test_arena_v2_packet_diff_is_only_mask_and_tagged_faction`
  pins the tagged faction value byte-for-byte against a golden, so the value
  that makes the actor selectable cannot drift silently.
- `tests/test_action_ack.py::test_hostile_kind1_end_to_end_gate_does_not_weaken_kind2`
  proves kind-1 hostile target capture is distinct from kind 2 and that the
  gate does not leak.

Both added.

## Considered and declined

Adding a citation that does not watch the claim is worse than leaving the row
thin, because it hides the gap behind a number. The following were read and
**not** added:

- **`combat/knockdown_and_reaction_states`, `combat/skill_use`,
  `combat/behavior_range_gating`** — cited only by probe-tooling tests, the
  same shape as the row repaired above. But unlike that row, their claims are
  explicitly *"statically characterized"* or *"traced at runtime"*, and nothing
  server-side implements them. The probe tests are the correct and only
  watchable surface. Nothing added.
- **`movement/scene_entry_placement`** — looked thin, is not.
  `tests/test_scene_load.py` already asserts the exact action sequence
  `FOUNDATION_SELECTED_START_GAME` then
  `V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE`, which is precisely the
  "sent exactly once" half of the claim.
- **`npc_interaction`, 5 rows on one module** — `test_npc_interaction_wire.py`
  is 20 tests written in M9 specifically for those five rows. Concentration
  here is by design, not by borrowing.
- **`inventory/move_negative_paths`** — keeps its `test_connection_lifecycle.py`
  citation; `test_idempotence_selected_position_and_cross_account_isolation`
  genuinely watches the cross-account half the row names.

## Mutation checks

A test that has never been shown to fail is a test of unknown value. Every
behavioral assertion in the new module was checked by mutating a throwaway copy
of `src/pirateforce_foundation/store.py` outside the repository and confirming
the intended test failed.

| # | mutation | test that failed |
|---|---|---|
| M1 | `open_session` stops closing the previous open row | second-login generation |
| M2 | `close_session` drops `AND closed_at IS NULL` | close idempotence |
| M3 | `close_session` deletes the row instead of stamping it | history accumulation |
| M4 | `connect()` sets `PRAGMA foreign_keys=OFF` | orphan row refused |
| M5 | `select_character` drops `s.closed_at IS NULL` | closed session cannot select |
| M6 | `save_position` drops `closed_at IS NULL` | closed session cannot write |
| M7 | select no longer binds `selected_character_id` | select binds then exit closes |
| M8 | `lease_generation` never advances | second-login generation |
| M9 | `expire_open_sessions` restamps already-closed rows | expire leaves closed alone |
| M10 | login closes every account's open rows, not its own | other-account isolation |
| M11 | `opened_at` written empty | open row column shape |

All eleven bit. Two of the module's own tests are themselves mutation checks
kept in the suite (`..._would_notice_a_session_left_open`,
`..._would_notice_a_foreign_key_violation`), so the oracle can never quietly
become vacuous.

## New ratchet

`tests/test_functional_coverage.py` gains
`test_every_cited_test_path_is_a_module_that_defines_tests`.

The verifier proves a cited path exists inside the repository. That is not
enough — a golden fixture, a package marker or a helper module would all
satisfy it. The ratchet requires every citation to be a `tests/` module that
defines at least one test method. Mutation-checked against four bad citations
(a golden JSON fixture, a path outside `tests/`, a `tools/` module with no test
method, a missing file); all four were rejected.

This is a *mechanical* floor and it is honest about being one. Whether a test
watches the right thing stays a reading job — which is why this document
exists rather than a rule.

## What this audit does not do

- No row changed `status`, `required`, `evidence_refs` or `notes`. Only
  `test_refs` moved, on four rows, and the change was asserted field-by-field.
- No domain was opened or closed. The matrix still reads 0/51 complete.
- Nothing in `src/` was touched, and `docs/HYPOTHESIS_LEDGER.json` was not
  opened.
- Test coverage is not evidence. A row still needs a runtime pass to move, and
  a stronger test never promotes a row on its own.
