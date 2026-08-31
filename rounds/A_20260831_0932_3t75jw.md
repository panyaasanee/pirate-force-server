# LANE-A round `3t75jw`

2026-08-31T09:32+07:00 - 2026-08-31T09:5x+07:00 (approx).

## Step A / B (mandatory, start of round)

GitHub API reachable this round via the proxy-injected token. Checked both
repos' latest `[LANE-A]` PR: `pirate-force-server#371` (round `c42axq`) and
`pf_bridge#579` (round `c42axq`) both `merged=true`, no `[LANE-A]` PR open
before this round started. Both working trees were fast-forward clean at
`origin/main` before branching.

Mailbox: `grep -rl "ADDRESSEE: LANE-A" pf_bridge/notes_to_chief/*.md`,
diffed against `.CONSUMED.txt` stubs. Three hits with no stub
(`gt151-holes...`, `crossing-handoff-dispatch...`, `bg0010-deep-sea-temple-
crosswalk-built-not-wired.md`) are all this lane's own outbound STATUS
letters (each quotes this exact grep command in its own Step B section, not
a real inbound header) -- same false-positive shape every round since
`u3jo4g` has found. Nothing owed to this lane this round; no `CLAIM-LANE-A-*`
file found either.

## What this round found and built

Continued the multi-round door sequence `COO-DECISION 2026-08-30T14:41+07:00`
approved. Scene 10 (Deep Sea Temple floor 1, Bg0010) was built (`u3jo4g`) and
wired (`c42axq`) in the previous two rounds, deliberately left shut. This
round is the judgment-call round scene 4 had at `bq4mst`: check the same
three defects against THIS scene rather than assume scene 4's answer, and
flip `login_entry_allowed` if they close.

D1 (frozen v141:4292 legacy branch) and D2 (stale position row) are closed
GENERICALLY, not per-scene, same as scene 4 and scene 14 -- verified against
source, not quoted. D3 (faction-1 byte) does not apply: this composer ships
no faction bit either, same as scene 4, confirmed by grep (only one comment
line mentions "faction" in `world_population_bg0010.py`, no wiring code).

ONE THING SCENE 4 DID NOT HAVE, read and acted on rather than skipped:
`scenarios/world_scene_registry_001.json`'s own
`table_row_differences.the_two_interiors` (pf-adversary, round `ga91m5`)
names scene 10 (with scene 11) as the pair an attended round should check
FIRST if a landing goes wrong -- marker point 5174.7 units outside this
scene's placement extents (vs. scene 4's 777.5), placement z floor -4532.9
against marker z 465, a no-glide no-height-limit interior. Rule 3
("authored and no more than authored") already treats this measurement as
recorded-not-enforced for every one of the ten scenes it applies to, four of
which are still shut for the same outside-bounds reason -- so this round
applied the same rule rather than inventing a stricter one for this row,
opened the door, tagged the call `[LANE-A ASSUMPTION - AWAITING COO
CONFIRMATION]` on the registry row itself, sent
`pf_bridge/notes_to_chief/20260831_0932_LANE-A-ASK-COO-scene10-landing-
geometry-elevated-risk.md` without blocking, and opened `GT-166` (attended,
two independent objectives: are there actors, is the floor standable) in the
same round rather than deferring the landing question to later.

## What shipped in `src/`, `tests/` and `scenarios/`

- `scenarios/world_scene_registry_001.json` -- scene 10's `login_entry_
  allowed` flipped `false -> true`. `status` field struck (not deleted).
  `table_row_differences.login_entry_allowed_because` added, mirroring
  scene 4's field in shape and naming the elevated-risk difference
  explicitly rather than hiding it inside the same three-defect prose.
  `arrival_point_rule.why_the_ten_doors_are_shut`'s closing sentence
  appended with a second UPDATE.
- `src/pirateforce_foundation/world_population_bg0010.py` -- docstring's
  "WIRED, DOOR STILL SHUT" bullet split into "WIRED" and a new "DOOR OPENED,
  ROUND 3t75jw" bullet naming the landing-geometry caveat and GT-166.
- `tests/test_lane_a_scene_census.py` -- `DeepSeaTempleRegistrationTests`'
  `test_the_real_registry_still_shuts_this_door` replaced with
  `test_the_real_registry_now_composes_and_that_is_the_round` (mirrors
  `SlaveMarketRegistrationTests`' own inversion, old assertion struck as a
  comment rather than silently dropped). New end-to-end production test
  added to `OnTheRealDispatcherTests`:
  `test_with_the_real_registry_the_deep_sea_temple_census_ships_94` -- full
  dispatcher boot, login, `START_GAME`, a `TargetPosVital` at scene 10's
  spawn, asserts `WORLD_CENSUS_LANE_SCENE10_INITIAL_94`/`_REAPPLY_94`,
  the byte-count event, and `WORLD_POP_HANDOFF scene=10 kind=census` /
  `WORLD_CENSUS_BG0010 assembled=94/100` printed -- same shape as scene 4's
  own headline test, driven against the real registry file.
- `tests/test_world_scene_registry_rule_1_scenes.py` -- `RULE_1_SCENES_
  STILL_SHUT` now excludes both 4 and 10; added
  `test_the_second_scene_that_opened_is_no_longer_in_this_set` mirroring
  the scene-4 method exactly.
- `tests/test_world_scene_marker.py` -- `test_the_other_ten_marker_doors_
  did_not_open_with_it`'s loop narrowed from nine scenes to eight (10
  removed); added `test_scene_10_opened_separately_and_that_is_a_different_
  round` asserting the opposite.
- `tests/test_world_faction_admission.py` -- added `DEEP_SEA_TEMPLE = 10`
  constant; widened the admitted-set assertion, the per-scene admits loop,
  and the moving-registry console-line assertion to include it (the last
  one changed because the BASE registry this test opens a second door on
  top of now already admits scene 10).
- `tests/test_gm_login_scene_admission.py`,
  `tests/test_gm_login_scene_stage.py`,
  `tests/test_gm_login_scene_sanctioned_barred.py`,
  `tests/test_gm_login_scene_registry_snapshot.py`,
  `tests/test_gm_login_scene_override_position_resync.py` -- five literal
  admissible/stageable-set assertions (added when scenes 14 and 4 opened)
  widened to include scene 10, found by running the full suite rather than
  only targeted files (same discovery method round `bq4mst` used).

## Player-visible claim

A character whose own persisted row names scene 10, a staged GM account
(`config/gm_login_scene.json` scene_id=10), or a GM `/warp 10` now enters
Deep Sea Temple floor 1 and sees up to 94 of its 100 native placements
instead of `WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]`.
Reversible in exactly one boolean. UNVERIFIED ON A SCREEN: whether the
landing point is standable ground -- that is what `GT-166` exists to find
out, and a "yes there are actors, no the floor is bad" result from that
ticket is data for the registry, not a regression of this round's own
claim.

## Manual adversary pass (no subagent tool available this round, same limit
## every LANE-A round has reported since `i95a1z`)

1. Flipped scene 10's `login_entry_allowed` back to `false` in the live
   registry file (backed up first), ran the nine touched/new test files:
   17 tests failed exactly as expected across all nine files (the mirror of
   every assertion this round added or widened). Restored from backup,
   `diff` confirmed byte-identical.
2. Confirmed the no-faction-bit claim is not merely asserted but true by
   absence: `grep -n faction src/pirateforce_foundation/
   world_population_bg0010.py` returns exactly the one comment line that
   states it, no wiring code.

## Gate, measured

| check | result |
|---|---|
| full suite before this round's edits | 5695 passed, 327 skipped, 10236 subtests, 0 failed |
| full suite after edits (door open) | 5702 passed, 323 skipped, 10238 subtests, 0 failed (127s) |
| full suite after mutation pass + revert (re-run) | 5702 passed, 323 skipped, 10238 subtests, 0 failed (identical, confirming the revert left no trace) |
| `python3 tools/verify_hypothesis_ledger.py` | `PASS entries=47` (unchanged) |
| `python3 tools/verify_functional_coverage.py` | `PASS domains=8`, `OPEN DOMAINS: 8` (unchanged) |
| `git diff --stat` on `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py` | empty (none touched, none needed) |

The skipped count moved 327 -> 323 across this round's run; not traced to
any file this round touched (no skip conditions exist in the touched
files) -- noted as measured rather than silently ignored, consistent with
this project's own past rounds' skip-count drift between edits.

## What's blocked / waiting

- `GT-166` (attended): does the census actually render, and is the landing
  point standable ground. Nobody has stood in this scene yet.
- Whether any of this scene's monster-shaped placements should be hostile is
  still a LANE-B decision, not made here (same as scene 4).
- The remaining eight doors in the queue (3, 5, 6, 7, 8, 9, 11, 130) are
  unchanged.

## CORE-REQUEST

None this round. The registry flip and every test change are inside this
lane's own write scope; no `runtime.py`/`app.py` change was needed (the
admission gate and faction-admission derivation already read the registry
generically, confirmed by the full suite passing with zero diff to either
file).

## ASK-COO

`pf_bridge/notes_to_chief/20260831_0932_LANE-A-ASK-COO-scene10-landing-
geometry-elevated-risk.md` -- not blocking; this round proceeded on its own
best judgment (rule 3 applies uniformly across the ten scenes) and tagged
the registry row `[LANE-A ASSUMPTION - AWAITING COO CONFIRMATION]`. Revert
is one boolean if the COO rules the other way.
