# Coverage test-reference audit — 2026-08-17

**Scope:** the eight capability rows that carried evidence and no test reference.
**Result:** every row in the matrix that is not `not_started` now names at least one test.
**Not in scope:** no capability status, required flag, evidence ref, note, domain
flag or source file changed. The hypothesis ledger is not touched.

## 1. Why this was worth doing

`ROADMAP_TO_PLAYABLE.md` recorded that eight rows carried evidence with no test
guarding them, five of them in `npc_interaction`. A row in that state is a claim
nobody watches: the report that justified it is frozen in `reports/`, but nothing
fails if the behavior it describes is later broken, re-scoped, or quietly
implemented somewhere else.

The verifier only demands a test reference for `complete` rows. Since no row is
`complete`, the demand had never applied to anything.

## 2. What was already there but uncited

Six test files were cited by no row at all. Only one of them is a capability test:

| test file | verdict |
|---|---|
| `tests/test_equip_state_static.py` | **bookkeeping defect** — it is precisely the static equipped/collection boundary in `PF_EQUIP_STATE001`, cited by no row |
| `tests/test_functional_coverage.py` | meta-test of the matrix itself; correctly uncited |
| `tests/test_hypothesis_ledger.py` | meta-test of the ledger; correctly uncited |
| `tests/test_item_move_consumer_static.py` | static consumer decode, already represented by the cited move tests |
| `tests/test_scene_db_guard.py` | tooling guard for evidence databases, not a capability |
| `tests/test_wait_for_pf_stage.py` | tooling guard for the stage waiter, not a capability |

Only `test_equip_state_static.py` was added as a reference. Citing the others
would inflate the count without adding a watcher.

## 3. Tests written for the remaining seven rows

Three new files, 40 tests. Each one exercises real behavior — builder output,
dispatch sequencing, or a fail-closed guard — rather than pointing at an
unrelated file to satisfy the matrix.

### `tests/test_system_message_wire.py` → `chat/server_system_message`

The row's own note said the vital "has no offline test, so it is one observation
rather than an owned feature". That is now half-false in the useful direction:
the observation stands, but it is watched.

- payload is exactly one wide-string tag decoded by hand (0x48, u32 length,
  UTF-16LE body) and nothing else, under the RuntimeRes v4 trailing change mask
- empty text raises, because the client handler drops it
- through the real dispatch path: the first `RuntimeReq` emits exactly one
  message equal to the builder output, after the runtime ack, and three repeat
  requests emit nothing
- a connection that never sends `RuntimeReq` never receives the message
- **fail-closed guard:** no module under `src/pirateforce_foundation/` may
  reference the vital. If a Foundation module takes ownership, the note is stale
  and the row has to be re-graded.

### `tests/test_teleport_transport_wire.py` → `movement/teleport_transport`

- MARKER1 constants are the decoded row (scene 1, seq 0, −10322/−755/671)
- the probe body differs from the proven bootstrap teleport by exactly the three
  floats, and from its login carrier by exactly the trailing change mask — so no
  other field was quietly repurposed into a transport parameter
- one exact confirm produces exactly one probe; replays produce none
- **every single-bit mutation** of the confirm packet is refused
- a confirm without the prompt is refused, and a plain scene-1 echo is captured
  without transporting — which is the row's "no server-validated transport"
  sentence, expressed as a test

### `tests/test_npc_interaction_wire.py` → the five `npc_interaction` rows

- `npc_conversation_handshake`: the TargetVital + embedded ChooseNPC composition
  yields exactly one identity; TargetVital alone yields none; a foreign vital
  stops the walk instead of byte-scanning; the empty and q3020 conversations are
  byte-exact; any actor other than P0 raises
- `conversation_operation_sequence`: operation 1 before the conversation is
  refused, operation 2 before the accept UI is refused, the ordered pair answers
  action 6 then action 1 once each, replays answer nothing, and a different
  quest id or vital version is not the exact request
- `quest_accept_and_progress` and `shop_buy_sell`: **fail-closed guards** on the
  claim that nothing is persisted or implemented server-side — the migrated
  schema must contain exactly the seven known tables, and no Foundation module
  may contain the whole words quest, shop, store5, price, reward or trade
- `interaction_negative_paths`: the V140 P86 position is asserted to be the
  explicit MARKER1 + (100, 50, 0) harness offset, to differ from P86's decoded
  placement, to match no other actor's decoded placement, and to appear nowhere
  in the plain V138 snapshot — the harness stays visibly a test device

Each guard was mutation-checked before commit: a simulated quest table, a
Foundation module referencing the message vital, and a Foundation module
containing shop/price words each made the corresponding test fail.

## 4. Ratchet

`tests/test_functional_coverage.py` gains two invariants:

1. every row whose status is not `not_started` must name at least one test
2. every `not_started` row must stay empty on both evidence and tests

The first pins the repaired state. Adding evidence for a new behavior now costs
a test in the same change, so this class of gap cannot silently reopen.

## 5. What this does not claim

No behavior became more proven today. `runtime_pass` rows are still one
observation each, `in_progress` rows are still bounded by their recorded
negatives, and the matrix still reports **0 of 51 required capabilities
complete** across 7 open domains. The only thing that changed is that breaking
one of these claims now breaks a test.
