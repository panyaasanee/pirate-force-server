# Coverage test-strength audit, round 3 — the `movement` domain

Date: 2026-08-17
Scope: the five graded rows of `movement` in `docs/FUNCTIONAL_COVERAGE.json`.
Rounds 1 and 2 (`COVERAGE_TEST_STRENGTH_AUDIT_20260817.md`,
`..._ROUND2_20260817.md`) read all 36 graded rows for bookkeeping gaps and then
drilled the three thinnest `inventory` / `character_management` rows. `movement`
had never been read row by row; only `scene_entry_placement` was spot-checked.

One claim turned out to be unwatched, and reading it exposed a second issue that
is not about tests at all.

## Verdicts

| row | status | verdict |
|---|---|---|
| `scene_entry_placement` | `runtime_pass` | watched — `test_scene_load.py` pins the exact action order `FOUNDATION_SELECTED_START_GAME` then `V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE`. No change (confirms round 1). |
| `local_player_position_checkpoint` | `in_progress` | watched — `test_foundation.py` carries `test_exit_restart_load_position`, `test_position_rejects_nonfinite` and `test_new_session_revokes_stale_position_writer`, which is exactly what the row's notes claim. No change. |
| `scene_actor_population_streaming` | `runtime_pass` | watched — three modules pin byte-exact nearest-20 generation, membership strictness and frozen-source drift. No change. |
| `teleport_transport` | `runtime_pass` | watched at the wire — `test_teleport_transport_wire.py` (round M9) decodes the payload by hand. No change, but see the provenance section below. |
| **`npc_locomotion_presentation`** | `runtime_pass` | 🔴 **unwatched** — the cited test never touches the field the claim rests on. Fixed this round. |

## The unwatched claim

The row claimed:

> Gait selection is accounted for by the decoded MOBS walk-speed value carried
> in BasicAttr bit `0x0040`.

Its only cited test was `tests/test_population.py`, which pins nearest-20
membership and byte-exact frames and never mentions speed. Searching the whole
tree, **no test referenced `movement_speed`, `0x0040`, walk or gait at all** —
so the single byte-level fact the row exists to record had nothing watching it.

Reading the cited evidence made the gap sharper. `PF_RE_V67_to_V87_Walk_Gait_20260813.md`
does not merely report that the field exists; it reports a **runtime negative**:

- V67–V69 sent `150.0` for P5 in every generated state, and P5 walked.
- V75 and descendants pinned speed in the baseline snapshot only. V85 therefore
  omitted it from every movement snapshot, and the same model visibly **ran**.

So the accepted rule is stronger than "the bit exists": the value must be
serialized in **every** generation. That rule was written in a report and
implemented in the frozen scenario runner, but nothing would have noticed if a
later edit reintroduced the exact V85 regression.

## The second finding — the Foundation server does not do this at all

`src/pirateforce_foundation/population.py` calls `legacy.make_npc_attr(...)`
in both the initial and transition builders **without `movement_speed`**. The
serializer only sets bit `0x0040` when the argument is not `None`, so every
NPCAttr the Foundation server emits has the walk-speed field absent — which is
precisely the V85 shape that produced a run gait.

Nothing here is broken code: the Foundation population capability was scoped to
membership, not gait. But the coverage row was graded `runtime_pass` and read as
though the running server had the behavior. It does not. That is recorded in the
row's `notes` this round and pinned by tests, and the status is left alone
because changing a grade is a decision, not an audit finding.

## What was added

`tests/test_npc_gait_wire.py`, 14 tests in three groups.

1. **The seam, byte-exactly.** The expected NPCAttr wire is rebuilt by hand with
   `struct` rather than by calling the legacy tag helpers back through the same
   path, so a mutation inside those helpers cannot cancel itself out of the
   assertion. Tests pin that the request sets exactly bit `0x0040` and nothing
   else in the mask, that the float lands immediately after the HP pair, that
   adding it inserts exactly five bytes and leaves every other byte identical,
   that it is float32 and not float64, and that `0.0` is still serialized
   because only `None` means absent.
2. **The provenance and the every-generation rule.** `V73_WALK_SPEED`,
   `V89_WALK_SPEED`, `V73_MOVERS` and `V89_TEST_INDICES` are pinned to the
   reported values, and every one of the twenty V89 movement generations plus
   the baseline generation must carry the speed for all three walkers. This is
   the assertion that the V85 regression fails.
3. **The Foundation negative, fail-closed.** Both Foundation population builders
   must emit twenty NPCAttrs with the bit clear and none with it set, and no
   module under `src/` may mention `movement_speed`. If someone wires gait into
   the Foundation server, these fail in the same change that adds it, forcing
   the matrix row to be revisited rather than silently drifting.

Two tests are kept in the suite purely so the absence assertions cannot go
vacuous: one builds a generation that *does* carry speed and requires the
detector to flag it, and one runs the source scanner over a throwaway directory
and requires it to flag a planted module while ignoring `no_movement_speeds`.

### Counting the speed by raw bytes would have been wrong

The first detector counted occurrences of `f32tag(150.0)` in the frame. That
overcounts: `V89_STEP` is also `150.0`, so a movement target coordinate produces
the identical five bytes, and one tick reported four speed values instead of
three. The shipped detector matches the twelve-byte NPCAttr prefix
`tag0B count, tag32 identity, tag12 mask` for a specific actor identity instead,
which cannot collide with a coordinate.

## Mutation check — 16 mutations, 16 killed

Run against copies of `current/pf_login_game_server_v141.py` and
`src/pirateforce_foundation/population.py` under `/tmp`. **The repository was
never modified**; the test module resolves its inputs through the overridable
`LEGACY_PATH` and `SRC_ROOT` constants, so the harness redirects them without
relocating the file (relocating would break `ROOT`).

| # | mutation | killed by |
|---|---|---|
| M01 | drop `basic_mask \|= 0x0040` | mask, insertion, every V89 generation |
| M02 | use bit `0x0080` instead of `0x0040` | mask, every V89 generation |
| M03 | `if movement_speed:` instead of `is not None` | zero-speed test |
| M04 | write the float before the HP pair | hand-built wire, insertion, float32 |
| M05 | drop the float from the body but keep the mask bit | hand-built wire, insertion |
| M06 | serialize as float64 | hand-built wire, insertion, float32 |
| M07 | tag byte `0x2B` instead of `0x2A` | hand-built wire, insertion |
| M08 | always emit a speed, defaulting to `0.0` | insertion, zero-speed |
| M09 | `V73_WALK_SPEED = 100.0` | frozen constants |
| M10 | `V89_WALK_SPEED = 100.0` | frozen constants |
| M11 | `V89_TEST_INDICES` drift | mover sets, both V89 generation tests |
| M12 | `V73_MOVERS` drift | mover sets |
| M13 | **the V85 regression**: speed in the baseline only | 20 movement generations |
| M14 | the inverse: speed in movement generations only | baseline generation |
| M15 | Foundation initial builder starts requesting speed | initial-population absence, source scanner |
| M16 | Foundation transition builder starts requesting speed | transition absence, source scanner |

The unmutated suite passes, so none of the kills come from a broken harness.

## A new audit axis — whose runtime produced the evidence

Reading this row surfaced a question no previous audit asked: a row graded
`runtime_pass` does not say **which server** produced the pass. The project has
two, and they are not interchangeable — the frozen legacy V1xx scenario scripts,
and the Foundation server that is the actual deliverable.

For `movement`, classifying each row's cited reports:

| row | evidence provenance |
|---|---|
| `scene_entry_placement` | Foundation |
| `local_player_position_checkpoint` | Foundation |
| `scene_actor_population_streaming` | mixed — one Foundation report plus legacy lineage |
| `npc_locomotion_presentation` | **legacy scenario runner only** |
| `teleport_transport` | **legacy scenario runner only** |

Two of five graded `movement` rows rest entirely on legacy-runner runtime. For
`npc_locomotion_presentation` this round proved the Foundation server cannot
reproduce the behavior. For `teleport_transport` the same question is open and
**not answered here**: the Foundation runtime does send a scene-entry teleport
via `make_login_teleport`, but whether that is the same capability as the
standalone V137 `TeleportVital` transport to a decoded MARKER row has not been
read, and no claim is made either way.

This is a matrix-semantics question, not a bug, so it is written up for the
owner rather than acted on. See §6.2 of `pf_bridge/CHIEF_CONTINUATION.md`.

## Nonclaims

- No claim that a Foundation client walks, or that gait would work if the field
  were added. Adding it is untested and out of scope for this round.
- No claim that `150.0` is correct for any template other than the reported
  P5 / P144 / P50 and the V73 mover set.
- No claim that bit `0x0040` is sufficient for locomotion; MovementAttr `+0x38`,
  ActionVital and the unknown fields remain unclaimed exactly as the V67–V87
  report left them.
- No status, `required` flag, `evidence_refs` entry, or any other row in the
  matrix was changed. The only edits are one `test_refs` addition and one
  `notes` rewrite on `movement/npc_locomotion_presentation`, asserted
  field by field against a deep copy before the file was written.
