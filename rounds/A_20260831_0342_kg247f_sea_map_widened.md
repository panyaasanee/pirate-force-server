# LANE-A round kg247f

2026-08-31T03:42+07:00 (TZ=Asia/Bangkok date).

## Mailbox check first

Read `notes_to_chief/` (pf_bridge) for any file addressed to LANE-A without a
`.CONSUMED.txt` stub. Found none: every unstamped file is this lane's own
outbound ASK-COO/STATUS letters, or addressed to chief/COO/another lane for
their own consumption. Also checked for a `CLAIM-LANE-A-...` reservation
file on the sea-map/ship topic (PROCESS_GATES.md section 12): none exists,
so this topic was not claimed by anyone else.

## Where this round starts: last round said the M2 report family had no next
step

Round `1sejs4` (previous LANE-A round, empty `src/` diff) grepped every
`WORLD_M2_*`/`M2_*` report and concluded the whole M2 family -- no-vehicle
notice, stowaway report, return-leg report, return-population report,
crossing-handoff report, sea-destination report -- was fully wired onto the
flagless default path, with nothing left to build that did not depend on
identity RE (Columbus's own identity confirmation, still pending) or
attended capture (`RE-155`, `RE-077`). This round re-derived that
conclusion from scratch rather than trusting the letter, and it still holds
for the *destination* question (scene 17's own arrival point). But the
brief for this round asked specifically for the *sea map / ship* concept --
"map the sea across the whole travel model, not identity-dependent" -- and
that turned out to be a different, narrower, still-open question:
`world_m2_sea_destination.COLUMBUS_ROUTES` has held all eight islands'
Columbus routes since round `drrnpu` (2026-08-29), but every registry-facing
function in that module (`_target`, `arrival_position`, `destination_state`,
`console_line`) was hardcoded to scene 17 only. The other seven islands'
registry readiness had never been asked about, by anyone, on any path.

One fact checked directly against gamedata before building on it (never
just quoted from a docstring): `n_SCENE_TYPE` is 4 for the seven
Bg1001..Bg1007 scenes AND for hundreds of other scenes in
`CONSTDATA_TH__SCENE_NAME.tsv` -- it does not discriminate "is a ship scene"
at all, contrary to what the module's own prose implied. That path was
abandoned before any code was written on it. The path that IS real,
re-verified from the same table: all eight `COLUMBUS_ROUTES` target scenes
(17, 18, 19, 20, 21, 39, 40, 41) carry `n_MARKER == 0` -- the same "no
authored arrival point keyed by scene" finding this module already reported
for scene 17 alone, now confirmed across every reachable Columbus
destination rather than assumed to extend past the one door this project
has actually walked.

## What was built

Reused the existing scene-17-only encoder, generalized to take a scene id,
rather than writing a second one (`_target_for`, `arrival_position_for`,
`arrival_is_decreed_for`, `destination_state_for` in
`world_m2_sea_destination.py`; the original scene-17-only names are now
one-line calls onto these, so every existing caller and test keeps working
unchanged).

1. `COLUMBUS_ROUTE_SCENE_MODEL_ID` / `COLUMBUS_ROUTE_SCENE_NAME_MARKER`:
   measured, not derived by the `Bg100<n>` arithmetic that happens to hold
   for six of the eight islands and breaks for two (scenes 39/40/41 are
   `Bg1023`/`Bg1024`/`Bg1025`, not `Bg1006`/`Bg1007`/`Bg1008`).
2. `sea_map_lines(registry)` / `sea_map_console_line(registry)` /
   `sea_map_console_line_safe(registry)`: the same two-function
   (raising / never-raising) shape every other report in this M2 family
   already uses. Reports, for all eight islands, whether the registry
   currently holds a landing point and whether it is still the owner's
   decree or something firmer -- explicitly NOT a claim that a player can
   reach any of the other seven doors today (only row 3021 dispatches).
3. `columbus_quest_dispatch.dispatch_columbus_quest3021` appends this as a
   SIXTH report, last, after the sea-destination report -- same
   append-only discipline every earlier addition to this function followed,
   because the decision line and the reports ahead of it are pinned by
   position in `tests/test_columbus_quest_dispatch.py`.
4. Added a `_self_check()` guard so the two new tables cannot silently drift
   from `COLUMBUS_ROUTES` (wrong key set) or from each other (a nonzero
   marker suddenly appearing would mean the "no arrival point" finding no
   longer holds for all eight and the report's assumptions need
   re-checking).

Live boot output (registry loaded from `scenarios/world_scene_registry_001.json`,
unchanged this round):

```
M2_SEA_DESTINATION offer=3021 target_scene=17 model=Bg1001 advertises_ocean=126 (Atlantic_Ocean_Rising_Sun_Sea) var2_reading=CONTESTED state=READY_DECREED arrival=0.000,0.000,0.000 evidence=GT-106 reason=none
WORLD_M2_SEA_MAP islands=8 ready_decreed=1 ready_not_decreed=0 refused=7 detail=17:READY_DECREED,18:REFUSED,19:REFUSED,20:REFUSED,21:REFUSED,39:REFUSED,40:REFUSED,41:REFUSED evidence=GT-106 reason=none
```

## Tests

New/updated: `sea_map_lines`/`sea_map_console_line`/`sea_map_console_line_safe`
consistency, generalized-helper-agrees-with-original tests, "unmeasured
registry" and "malformed registry" refusal tests, and a
reused-registry-not-a-second-copy control (adds a synthetic scene-18
destination cloned from scene 17's row and checks only that island's word
changes) in `tests/test_world_m2_sea_destination.py`; the dispatch-level
pinned-order test and a new `SeaMapReportTests` class in
`tests/test_columbus_quest_dispatch.py`; the two pinned-index assertions in
`tests/test_world_m2_crossing_handoff.py` that assumed the sea-destination
line was last are corrected to `lines[-3]` with the new class comment
explaining why (house rule: strike/correct, do not silently renumber
without saying so).

Manual adversary pass (no subagent tool available in this environment, same
as round `i95a1z` reported -- mutation testing by hand instead):

1. Swapped the order of the two emit calls in
   `dispatch_columbus_quest3021` (sea-map before sea-destination) -->
   caught by the pinned-position tests in both
   `test_columbus_quest_dispatch.py` and `test_world_m2_crossing_handoff.py`.
   Reverted.
2. Removed one key (`41`) from `COLUMBUS_ROUTE_SCENE_MODEL_ID` -->
   `_self_check()` raises `SeaDestinationError` on import, before any test
   even runs. Reverted.
3. Changed `ready_decreed` to count `STATE_REFUSED` instead of
   `STATE_READY_DECREED` --> caught by three separate tests (the counting
   test in each of the two test files, plus the reused-registry control).
   Reverted.

All three mutations were caught; none needed a code fix (the tests already
covered them), confirming the coverage rather than finding a defect.

## Numbers

- `python3 -m pytest tests -q`: **5639 passed, 327 skipped, 9733 subtests
  passed, 0 failed** (round `1sejs4`'s letter, the last time the full suite
  was run and reported, measured 5608 passed / 323 skipped -- the skip-count
  delta tracks environment-linked markers such as
  `@BRIDGE_GAMEDATA.skip_unless_present()`, the same drift `1sejs4` itself
  flagged as not a regression and not pursued that round either; this
  round's own diff adds 13 new test methods across the two test files,
  net +31 passed which is consistent with 13 new tests plus subtests).
- `tools/verify_hypothesis_ledger.py`: `PASS entries=47` (unchanged).
- `tools/verify_functional_coverage.py`: `OPEN DOMAINS: 8` (unchanged).
- `git diff --stat` on `src/ tests/`: 5 files, 443 insertions, 49 deletions.
- `git diff --stat` on `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`:
  empty (none touched).
- `tests/test_tree_is_cp874_safe.py`: 5 passed, 407 subtests passed (this
  round's new prose/strings scanned clean).

## What a player sees

Nothing on screen this round -- same as every other report-only addition to
this M2 family (`WORLD_M2_RETURN_LEG`, `WORLD_M2_CROSSING_HANDOFF`,
`M2_SEA_DESTINATION` before it). What changed is what the console says every
time a player takes the one crossing that exists today: it now also states,
truthfully, that seven of the eight ship doors this project has measured
have no landing point pinned yet -- information a later round wiring any of
those seven can use instead of re-discovering the same registry gap scene
17 already closed.

## Not proven by this round

No human has watched any of the other seven Columbus routes fire -- this
round did not claim, and the code does not claim, that those seven islands'
Columbus NPCs are even placed on a default boot. That is a separate,
unmeasured question this round explicitly declined to guess at.

## CORE-REQUEST

None. All edits are inside `columbus_quest_dispatch.py`/
`world_m2_sea_destination.py`, both already in this lane's write scope, and
the call site was already reading `registry` before this round (no new
plumbing needed from `runtime.py`).

## Tickets opened for lane C

None. This round answered a question from source data it could re-derive
directly (`CONSTDATA_TH__SCENE_NAME.tsv`); it did not open a new RE.
