# Coverage test-strength audit — round 4 (session lifecycle)

Date: 2026-08-17
Milestone: M14
Scope: the two `session_lifecycle` rows that still named
`tests/test_connection_lifecycle.py` among their primary watchers.

Round 1 (M10) flagged that one 512-line module about lease and socket teardown
was cited by seven rows across four domains, and treated that as the strongest
remaining "borrowed test" indicator. Rounds 2 and 3 spent that indicator on
`character_management` and `movement`. This round spends the rest of it.

Method is unchanged: read the row's own claim sentence, read every test method
it cites, decide whether any of them would fail if the claimed behaviour were
removed, then prove the decision with mutations rather than assert it.

## Verdicts

| Row | Status | Verdict |
|---|---|---|
| `session_lifecycle/character_select_to_scene_entry` | `runtime_pass` | 🟢 **watched — nothing added** |
| `session_lifecycle/abrupt_loss_recovery` | `runtime_pass` | 🔴 **half the claim was unwatched → new module** |

No status, no `required` flag, and no `evidence_refs` entry moved in this round.
The only graded change is one added `test_refs` path, which is why
`GRADE_SUBSET_SHA256` in `tests/test_foundation_legacy_seam.py` moved from
`264A0D44…` to `E2154CE6…`.

## `character_select_to_scene_entry` — watched, nothing added

The claim is "one single-client session reaching Port Royal with the persisted
name projected, then exiting cleanly". Three cited modules, and the citation of
`test_connection_lifecycle.py` here turns out to be the weakest of the three
rather than the load-bearing one — which is exactly the shape M10 predicted, but
in this row it does not matter, because the other two are strong:

- `test_foundation.py::test_create_list_select_start_same_identity` follows one
  identity through create → list → select → start and asserts byte-level facts
  at each hop: the identity tag appears exactly twice in the actor wire, three
  times in the start payload, the avatar wire is embedded verbatim, and the
  name tag appears exactly once. A projection that dropped or duplicated the
  persisted character would fail on a count, not on a vibe.
- `test_foundation.py::test_character_lifecycle_golden_hashes` pins sha256 of
  the create/list/start payloads against a golden fixture.
- `test_foundation.py::test_exit_restart_load_position` closes a session, opens
  a **new store over the same file**, and requires the reopened select/start to
  reproduce the same identity, the same opaque actor wire, and the saved
  position — including the float tags inside the payload.
- `test_session_row_persistence.py` (added in M10) owns the row-shape half.

Adding a fourth module here would have raised a number without watching anything
new. Decision recorded rather than left silent, per the M10 rule.

## `abrupt_loss_recovery` — the restart half had no watcher

The row title carries two claims joined by "and":

1. **abrupt client loss** — a client process dies, the server closes exactly
   that connection-local lease and keeps serving.
2. **abrupt server restart** — the server process dies, and a replacement
   process brings the database back to a usable state.

Claim 1 is watched. `test_connection_lifecycle.py` drives the adapted listener
with a body that raises, asserts the accepted socket closed, asserts the lease
row got a `closed_at`, and pins the event order so the lease close happens after
the heartbeat join. `test_server_shutdown.py` covers the frozen-recv variants.

Claim 2 is what FND-009 actually recorded as its primary sentence:

> A fresh server process using the same isolated SQLite database **closed the
> stale open lease before the new client login**

The entire server-side implementation of that sentence is one line:

```python
# app.py, in the read/write startup branch
# A previous process cannot own a live lease after this process starts.
store.expire_open_sessions()
```

Before this round nothing in the suite observed it. The single other mention of
`expire_open_sessions` anywhere in `tests/` is inside
`test_session_row_persistence.py`, where the test calls the store method itself
— which proves the method works, not that starting a server calls it. And no
test ran `app.main()` far enough to look at the sessions table afterwards: the
four modules that spawn `python -m pirateforce_foundation.app` do so to check
console behaviour, capture roots and the second-password CLI, and none of them
reads a session row.

### The trap: an obvious test here passes for the wrong reason

The natural way to write this test is: leave a session row open, start a server,
log the account back in, assert the old row closed. That test passes even with
the recovery deleted, because `open_session` already closes prior open rows
**for the account that logs in**:

```sql
UPDATE sessions SET closed_at=? WHERE account_id=? AND closed_at IS NULL
```

Every runtime pass so far has been single-client, so that self-healing has
masked the startup call in every observation to date. The masking disappears the
moment the dead process held leases for more than one account: the account that
never returns keeps a live row, and its session id still authorises
`save_position`. Reproduced directly against the store:

```
before                                   alpha: open   bravo: open
after alpha re-login, no startup recovery alpha: closed bravo: open
stale bravo session id writing a position -> accepted
```

So the module tests the account that **does not** come back, and carries
`test_a_relogin_alone_would_leave_the_other_lease_open` as an explicit vacuity
guard: it asserts that the re-login path alone leaves the other lease open, so
the recovery assertions cannot silently start passing for free.

This is also the reason `test_foundation.py::test_new_session_revokes_stale_position_writer`
is not a duplicate of the new module. That test watches the masking mechanism
(same account, second session revokes the first). The new module watches the
startup recovery that the masking hides.

### Differential proof that the gap was real

Same tree, same interpreter, one mutation: delete `store.expire_open_sessions()`
from the read/write startup branch of `app.py`.

| Run | Failing tests |
|---|---|
| pre-existing suite, pristine | 322 tests, 25 environment-only errors |
| pre-existing suite, recovery deleted | 322 tests, **the identical 25** |
| with the new module, recovery deleted | the same 25 **+ 8 new failures** |

(Run in the Linux pre-check sandbox, where a fixed set of modules cannot import
`capstone`/`pefile`. The absolute count is an artefact of that environment; the
comparison between the two rows is not, because the tree, interpreter and
selection are identical across them. Windows remains the real gate.)

The pre-existing suite is not merely thin on this behaviour; it is exactly as
green with the recovery removed as with it present.

## `tests/test_startup_stale_lease_recovery.py` — 15 tests, three groups

**Group 1 — behaviour through the real entry point.** One dead process is
simulated by seeding two accounts, two characters, one cleanly closed lease and
two leases left open with characters selected, then running the actual module
entry point through `--self-test-only`, the one documented path that opens no
listener. The assertions read the durable state afterwards:

- every open lease is closed, including the account that never logs back in;
- the stale session id can no longer `save_position` (PermissionError) or
  `select_character` (KeyError);
- closing is not deleting: ids, `opened_at`, `lease_generation` and
  `selected_character_id` are all unchanged, so lease history survives recovery;
- a lease that had already closed cleanly keeps a byte-identical stamp;
- every `characters` and `character_positions` row is byte-identical after the
  start — this is FND-006/FND-009's "the checkpoint survived" half;
- the recovered database is usable: the next login opens exactly one live lease,
  gets generation 2, and can select the same character.

**Group 2 — the creation path.** A start against a database that does not exist
yet must create, migrate and recover in that order; recovering first would raise
on a database with no `sessions` table, so a zero exit pins the order.

**Group 3 — wiring, read structurally from `app.py` with `ast`.** Exactly two
recovery calls exist, each preceded by a migration in its own block, and both
before any `CharacterLifecycle`/`make_state_class` construction. The scene-load
branch is pinned as the one deliberate exception, together with the reason that
makes the exception coherent: `ReadOnlyFoundationSession` contains no
`open_session`, so that mode can leave no lease behind.

## Mutation check — 14 must bite, 2 controls must pass, 1 differential

Run on throwaway copies under `/tmp`. The repository was never mutated.

| # | Mutation | Result |
|---|---|---|
| M01 | default startup branch never recovers | bit |
| M02 | item-move startup branch never recovers | bit |
| M03 | recovery moved after the lifecycle is built | bit |
| M04 | recovery closes one account only | bit |
| M05 | recovery deletes rows instead of stamping them | bit |
| M06 | recovery restamps rows that had already closed | bit |
| M07 | recovery also clears the selected-character binding | bit |
| M08 | recovery also resets stored positions | bit |
| M09 | `save_position` stops requiring an open lease | bit |
| M10 | `select_character` stops requiring an open lease | bit |
| M11 | recovery runs before the migration | bit |
| M12 | a third recovery call appears | bit |
| M13 | `ReadOnlyFoundationSession` starts opening leases | bit |
| M14 | `open_session` stops closing the prior lease | bit |
| C15 | control: the comment above the call is reworded | passed |
| C16 | control: equivalent SQL spelling (`ISNULL`) | passed |
| — | *differential:* M01 against the suite **without** this module | **did not bite — this is the gap** |

C16 matters as much as the bites: it proves the module pins the *behaviour* of
recovery rather than the text of one SQL statement, so a rewrite that preserves
meaning stays cheap.

## Nonclaims

- No live process holds a stale session id after an abrupt loss, so a lease left
  open is an invariant and oracle defect rather than a reachable write path
  today. The module states this in its docstring and does not claim otherwise.
- Nothing here proves host power loss, torn writes, or fsync behaviour. That
  boundary was already in the row's notes and has not moved.
- `--self-test-only` opens no listener, so this module proves nothing about
  socket binding, listener count, or client-visible behaviour.
- The seeded wire bytes are deterministic filler. This module makes no claim
  about wire semantics; those live in the byte-exact modules of M9–M13.
- Concurrent multi-account runtime is still unproven (`concurrent_multi_client`
  remains `not_started`, queued as `GT-003`). The masking analysis above is an
  offline store-level observation, not a runtime multi-client result.

## Observation recorded, not acted on

The scene-load-only startup branch skips both `migrate()` and
`expire_open_sessions()`, so the four other modes and the default path recover
leases while scene-load does not. This is coherent today because that mode
installs `ReadOnlyFoundationSession`, which never opens a lease, and the module
pins both halves of that reasoning so the skip cannot become incoherent quietly.
It is recorded here rather than changed, because changing it would be a scope
decision rather than an audit result.
