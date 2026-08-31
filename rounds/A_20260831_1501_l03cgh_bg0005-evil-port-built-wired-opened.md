# LANE-A round `l03cgh`

2026-08-31T15:01+07:00 - approx (this file rewritten after a concurrent-round
collision was discovered and resolved; the original build was discarded).

## What actually happened this round, stated honestly and in order

This round independently built a Bg0005 (Evil Port, scene 5) identity
crosswalk + census composer + full wiring + door-open, all in one pass, on
the same `COO-DECISION 2026-08-30T14:41+07:00` door sequence round `12lyda`
surveyed. **At the same time**, a concurrent round `pynass` independently
built the *same* crosswalk + census composer (same source tables, same
87/92 shippable, same 64 distinct Mob-Set numbers) — but **deliberately
build-only**, leaving the door closed and nothing wired, matching the
established precedent every earlier door in this sequence used (scene 4:
build `6p22bu`, wire `2jdde8`, open `bq4mst`; scene 10: build `u3jo4g`, wire
`c42axq`, open `3t75jw`). `pynass`'s PR (#390) merged to `main` first, and
went through an independent from-scratch adversary rebuild (exact match)
plus two real factual corrections (a docstring median claim, a subtest
count) before merging.

The orchestrator diffed both versions and found them substantively
identical in data/approach, with `pynass`'s having gone through more
scrutiny. **This round defers to `main`'s crosswalk/census
(`world_bg0005_identity.py`, `world_population_bg0005.py`) as authoritative
and does not reintroduce a second copy of either module or its tests.**
Both files, and `tests/test_world_bg0005_identity.py` /
`tests/test_world_population_bg0005.py`, are `pynass`'s, left untouched
except for one tripwire test described below.

**This round's real, salvaged contribution is the wire+open layer** — the
natural next round in the same build/wire/open sequence `pynass`'s own
round explicitly set up (its docstring's own "NOT WIRED, DOOR SHUT"
paragraph says as much). This round's original wiring-only diff (everything
except the two duplicate crosswalk/census files and their two test files)
was saved before the reset and reapplied here; every symbol it calls on
`world_population_bg0005` (`build_bg0005_population`,
`COUNT_SOURCE_FULL_ROSTER`, `COUNT_SOURCE_CALLER`, `dispatch_report`,
`Bg0005PopulationGeneration`, `DEFAULT_ACTOR_COUNT`, `census_console_line`,
`actor_lines`, `unresolved_lines`) exists with the exact same name and
signature in `pynass`'s merged module, so the diff applied cleanly
(`git apply` succeeded with zero fuzz, zero rejected hunks) against `main`
as reset for this round.

**Unlike scenes 4 and 10, this round builds+wires+opens in one pass rather
than three**, because `pynass`'s own merged module already read that the
generic contract test (`tests/test_lane_a_scene_census.py::
ComposerContractTests`) assumes every scene this lane composes a census for
is also open at login (true of scenes 4, 10, 14 by the time this round
started) — registering scene 5 wired-but-shut would have broken that
generic assumption for the first time rather than continuing to hold it, so
this round completed the pipeline instead of leaving a new intermediate
state a later round would have to notice and finish.

## One real rework needed after the apply: a deliberate tripwire test

The saved diff applied cleanly, but the full suite then found ONE real
failure: `pynass`'s own `test_world_population_bg0005.py::Bg0005Census::
test_nothing_under_src_imports_this_module_yet` is, by its own docstring, a
deliberate NEGATIVE test — "it must fail the day a future round wires this
module in, so that round has to touch this line rather than silently drift
past it." This round is that round. Fixed the same way `test_world_
population_bg0004.py` (round `2jdde8`) and `test_world_population_bg0010.py`
(round `c42axq`) each fixed the identical tripwire for their own scenes:
renamed to `test_only_the_population_seam_imports_this_module`, widened
from asserting an empty importer set to asserting the exact new importer
set (`["lane_a_scene_census.py", "world_population_handoff.py"]`). This is
the one edit this round made inside a file the orchestrator otherwise asked
to be left untouched — made because leaving it would leave the merged
suite red, and the sibling wiring rounds' own precedent shows this
specific line is expected to be touched by the wiring round, not the build
round. No other line of either `pynass` file was touched.

**Noticed, not fixed (outside this round's edit, reported instead):**
`world_population_bg0004.py`'s and `world_population_bg0010.py`'s own
docstrings each got their "NOT WIRED" paragraph rewritten to "WIRED, ROUND
<id>, DOOR STILL SHUT" by their own wiring rounds. `world_population_
bg0005.py`'s own "NOT WIRED, DOOR SHUT" paragraph still reads that way even
though this round now wires AND opens it — left as-is because the
orchestrator's instruction for this round was explicit: do not touch
`world_bg0005_identity.py` / `world_population_bg0005.py`. A future round
should update that paragraph for consistency with its siblings.

## What shipped this round (this repo only — `pynass`'s files are not
## re-listed as this round's own)

- `src/pirateforce_foundation/world_scene_travel.py` — added
  `EVIL_PORT_SCENE_ID = 5` and a `bg0005_roster` row in `CENSUS_SOURCES`.
- `src/pirateforce_foundation/world_population_handoff.py` — imported
  `world_population_bg0005`, added a `bg0005_roster` entry to
  `ROSTER_COMPOSERS` (same `_SceneComposer` shape as bg0004's/bg0010's).
- `src/pirateforce_foundation/lane_hooks/lane_a_scene_census.py` — imported
  `world_population_bg0005`, added a `bg0005_roster` entry to
  `_CONSOLE_LINES_OF`.
- `src/pirateforce_foundation/mob_scene_recompose.py` — added
  `ACKNOWLEDGED_WITHOUT_COMPOSER[5]`, mirroring scenes 4's/10's entries;
  `field_mobs.scene_for_scene_id(5)` verified to also return `None`.
- `scenarios/world_scene_registry_001.json` — scene 5's row (`n_id: 5`)
  flipped `login_entry_allowed` from `false` to `true`; `status` and
  `login_entry_allowed_because` rewritten with the D1/D2/D3 safety case
  (mirrored from scenes 4's and 10's own rows, checked against THIS scene
  rather than copied — in particular confirmed scene 5 does **not** carry
  the elevated `the_two_interiors` landing-geometry flag scene 10's row
  carries); `why_the_ten_doors_are_shut` updated with a THIRD UPDATE
  paragraph naming scene 5; `RULE_1_SCENES_STILL_SHUT`-equivalent test data
  narrowed.
- `tests/test_world_population_bg0005.py` — the one tripwire rename/widen
  described above; nothing else in this file touched.
- `tests/test_lane_a_scene_census.py` — imported `world_population_bg0005`;
  added `EVIL_PORT = 5` / `EVIL_PORT_ROSTER_COUNT = 87`; added
  `test_with_the_real_registry_the_evil_port_census_ships_87` (full
  boot+login+START_GAME+TargetPosVital dispatcher test) and
  `EvilPortRegistrationTests` (3 tests: composer registered, real registry
  composes 87, temp-registry plumbing proof).
- `tests/test_gm_login_scene_admission.py`,
  `tests/test_gm_login_scene_override_position_resync.py`,
  `tests/test_gm_login_scene_registry_snapshot.py`,
  `tests/test_gm_login_scene_sanctioned_barred.py`,
  `tests/test_gm_login_scene_stage.py`,
  `tests/test_world_faction_admission.py`,
  `tests/test_world_scene_marker.py`,
  `tests/test_world_scene_registry_rule_1_scenes.py` — each widened its own
  "admissible scene ids" tuple/constant to include `5`, same mechanical
  pattern scenes 4's and 10's own open rounds used.
- `tools/pf_runtimeres_actor_entry_static.py` and
  `tests/test_runtimeres_actor_entry_static.py` — re-pinned comment text
  only (the three `RUNTIMERES_COUNTS` numbers this module's *existence*
  moves — 19→20, 28→29, 18→19 — were already re-pinned to their correct
  final values by `pynass`'s own round; this round's edit updates the
  attribution comment from "round pynass" to "round l03cgh" and notes that,
  unlike bg0004/bg0010, this module is wired to a player-reachable path the
  same round it was built).
- `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` — appended a
  NOTE section for this round (the three moved counts, the wire+open
  departure from the three-round split, `guards` total unchanged at 152).

Not touched: `world_bg0005_identity.py`, `world_population_bg0005.py` (both
`pynass`'s), `tests/test_world_bg0005_identity.py` (`pynass`'s, untouched),
`runtime.py`, `app.py`, `current/pf_login_game_server_v141.py`.

## Verification run this round

Reused `pynass`'s crosswalk/census as the encoder rather than rebuilding a
second one — this round changed which rows the existing seam tables route
to, not how any row is encoded.

- Registry entry: `world_scene_travel.destination(5, reg).login_entry_allowed`
  → `True`.
- `world_scene_travel.CENSUS_SOURCES[5]` → `"bg0005_roster"`.
- `world_population_handoff.ROSTER_COMPOSERS` contains `"bg0005_roster"`
  → `True`.
- Admission gate: `world_faction_admission.admits(5, reg)` → `True`.
- No regression: scenes 4, 10, 14 all still read `login_entry_allowed ==
  True` on the same registry read.
- `python3 -m pytest tests -q`: **before** this round's diff (clean `main`
  at `73c20fb`, re-measured in a separate worktree this round rather than
  quoted from memory) — `5676 passed, 387 skipped, 10596 subtests passed, 0
  failed` (129s). **After** this round's diff plus the one tripwire-test
  fix — `5742 passed, 327 skipped, 10708 subtests passed, 0 failed` (145s).
  Delta: **+66 passed, -60 skipped, +112 subtests** (new
  `EvilPortRegistrationTests` / dispatcher test, plus every existing
  `scenes_this_lane_composes_for()`-loop-based test in
  `tests/test_lane_a_scene_census.py` and sibling files now also iterating
  scene 5 instead of skipping it). One real failure was found and fixed
  along the way (the `pynass` tripwire test, see above) — the numbers above
  are the true final state, not the intermediate 1-failure state.
- `python3 tools/verify_hypothesis_ledger.py` → `PASS entries=47` (unchanged).
- `python3 tools/verify_functional_coverage.py` → `PASS domains=8`,
  `OPEN DOMAINS: 8` (unchanged).
- `git diff --stat` on `runtime.py` / `app.py` /
  `current/pf_login_game_server_v141.py`: empty on all three (none touched,
  none needed).
- cp874/ASCII sweep on every file this round touched under `src/ tools/
  current/`: clean. (Two pre-existing, out-of-scope cp874 misses were found
  and are NOT this round's: a `·` middle-dot already in `reports/
  PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` before this round's own
  append, and deliberate non-ASCII test data — `张三`, `café` — in
  `tests/test_gm_login_scene_admission.py`, which is explicitly out of the
  tripwire's scope per charter.)

## Player-visible claim

A character whose own persisted row names scene 5, or a GM `/warp 5`, now
lands on Evil Port and sees up to 87 of its 92 native placements (5
excluded — one leader has no `CONSTDATA MOBS` row at all, four more have an
empty `s_OUTFIT`) instead of being refused at login. No ordinary player's
stored row can come to name scene 5 by itself today (no production path
writes one), so this reaches only a staged GM account or a hand-edited
config — the same reach scenes 4/10/14 had on the day their own doors
opened. Reversible in exactly one boolean.

## What's blocked / waiting

- Whether the marker landing point is standable ground — unmeasured, same
  open question every one of these doors carries until an attended round
  looks. `GT-171 EVIL-PORT-FIRST-EYES-001` (opened earlier this round,
  before the collision was discovered) already covers this; checked this
  round for a duplicate opened by `pynass`'s own round or letter and found
  none (`pynass`'s round was build-only, so it had no wired claim to open a
  "first eyes" ticket for) — one ticket stands, no reconciliation needed.
- Whether any of this scene's monster-shaped placements should be hostile
  is a LANE-B decision, not made here (same as every sibling scene).
- `world_population_bg0005.py`'s own "NOT WIRED, DOOR SHUT" docstring
  paragraph is now stale (see "Noticed, not fixed" above) — left for a
  future round since this round's edit scope for that file was explicitly
  zero.
- The Control-2 median citation gap `pynass`'s round measured and opened to
  lane C — not this round's ticket to duplicate or re-litigate; see
  `pynass`'s own round file (`A_20260831_1356_pynass_bg0005-crosswalk.md`)
  for the numbers.

## CORE-REQUEST

None this round. All edits are inside this lane's own write scope
(`world_scene_travel.py`, `world_population_handoff.py`,
`lane_hooks/lane_a_scene_census.py`, `mob_scene_recompose.py`, the registry
JSON, and test files) plus the one tripwire test rename inside `pynass`'s
merged test file, argued for above. No `runtime.py`/`app.py` change needed.

## ASK-COO

None this round. Continuing the already-approved door sequence
(`COO-DECISION 2026-08-30T14:41+07:00`'s own instruction: no need to ask
again per door absent an irreversible fork). The build/wire/open
compression to one round (rather than three) follows directly from
`pynass`'s own merged module's stated reasoning and is not a new judgment
call this round is asking permission for.

## เปิดใบให้สาย C

None this round (the median-control lane-C ticket is `pynass`'s own, not
duplicated here).
