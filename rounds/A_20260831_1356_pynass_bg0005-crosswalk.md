# LANE-A round pynass

2026-08-31T13:33+07:00 - 2026-08-31T13:56+07:00 (approx).

## Step A / B (mandatory, start of round)

Orchestrator pre-verified and reported directly rather than re-derived by this round:
previous LANE-A PRs (round `h1utu5`) merged=true on both repos (server #383, bridge #597),
nothing to recover; no unconsumed mail addressed to LANE-A (`FROM_CHIEF_R256_TO_LANE-A`
already consumed, both COO-DECISIONs in the box already consumed); heartbeat ~13 minutes
stale, under the 60-minute threshold, no action; no unconsumed `CLAIM-LANE-A-*` under 90
minutes old; no open `[LANE-A]` PR on either repo. Independently re-checked before
starting work: `git log origin/main` on both repos showed no commits landed after the
orchestrator's check (server still at `7e2cbfde`, bridge at `3bf4b12` - the newest bridge
commit, `[LANE-GM] round x9wq3r`, is an unrelated GM-lane verify-only round). No scene-5
work found in either repo's recent history or mailbox (`grep -rl "bg0005\|Evil Port"
notes_to_chief/*.md` found only unrelated hits: a scene-id-reader status letter, an R236
gate-priority letter, and scene 10's own landing-geometry ask - none claim scene 5).

## What this round found and built

Continued the multi-round door sequence `COO-DECISION 2026-08-30T14:41+07:00` approved
(round `12lyda`'s own placement-count table, ten still-shut doors surveyed, no per-door
re-approval needed absent an irreversible fork). Scene 4 (116 placements) and scene 10
(100 placements) are both open at login as of round `h1utu5`'s merge (`7e2cbfde`) - checked
`scenarios/world_scene_registry_001.json` directly rather than assumed: `n_id 4` and
`n_id 10` both carry `login_entry_allowed: true`; the other eight rows in the same ten
(`3, 5, 6, 7, 8, 9, 11, 130`) all still carry `false`, and no `world_bg000N_identity.py` /
`world_population_bg000N.py` pair exists yet for any of the eight (checked: `ls
src/pirateforce_foundation | grep -E 'world_bg000|world_population_bg000'` returns only
`bg0004`, `bg0010`, `bg0015`, `bg0002`). This round starts the third door: scene 5, Bg0005
("Evil Port"), the next-highest native placement count (92) in round `12lyda`'s table,
same build-only granularity round `6p22bu`/`u3jo4g` used for scenes 4's and 10's first
rounds.

Read the join by script (not by hand - the tables are large enough that hand
transcription would itself be an error source, so a throwaway script did the extraction
and its own output is what appears in the module, unedited except formatting) directly
off the bridge clone's own committed tables: `CONSTDATA_TH__SCENE_NAME.tsv` (scene 5 ->
`n_CLINE_TYPE=5`, `n_SCENE_LV=60`), `CONSTDATA_TH__CLINE.tsv` (type 5's 64 rows, its
ENTIRE key range: 1-59, 101-105), `CONSTDATA_TH__MOBS.tsv`, `TEXTDATA_TH__MOBS_TIP.tsv`,
`CONSTDATA_TH__STANDARD_MOB.tsv`, and `gamedata/scene/bg0005/bg0005.placements.tsv` (92
rows). Digests re-derived and matched what `world_bg0004_identity.py` and
`world_bg0010_identity.py` already pin for the four shared tables; the scene's own
placements TSV got its own fresh digest (`b69ee8f1...8c0c5`).

Measured: 64 distinct Mob-Set numbers used across all 92 placements - CLINE type 5's
ENTIRE key range, unlike bg0004 (61 of 62 keys) and bg0010 (40 of 41 keys): this scene's
placement file touches every key its own CLINE type owns. 59 of the 64 resolve to a real
body; 5 do not, in TWO different failure shapes: set 1 -> leader 104, where CLINE carries
a real non-zero leader but `CONSTDATA MOBS` has NO ROW for it at all (a new failure mode
neither bg0004 nor bg0010 needed - both of their unresolved sets had a MOBS row with an
empty `s_OUTFIT`); sets 101-104 -> leaders 10020-10023, the familiar "pathfinding helper,
no `s_OUTFIT`" shape both sibling scenes' 101+ blocks carry (this scene has only 4 of
these, not 5 - its own set 105 is never used by the placements file, so it was never
examined). 87 of the 92 placements ship; 5 are dropped, one each.

**Control 2 gap, measured and stated rather than silently repeated.**
`world_bg0015_identity.SCENE_LEVEL_CONTROL['BG0005']` cites `(5, 60, 68.0, 35.0)` from an
earlier round's survey. Re-measuring BOTH medians this round over the 87 shippable
placements gives **70**, not 68 (CLINE-reading median), and **31**, not 35 (set-number
median, checked three independent ways - all agree at 31). This is the weak, non-blocking
control every sibling module's own docstring already discounts (monotone-in-level, so any
permutation reproduces a similar number) - recorded because the earlier citation's own
number does not reproduce independently, not because it changes anything this round ships.
Opened to lane C (see below) rather than investigated further this round.

Ten sets carry a `;`-separated multi-variant outfit; shipped first-variant only, same
[LANE-A ASSUMPTION] carried over from all three sibling crosswalks. Unlike bg0010's
roughly-even spread, this scene's distribution is lopsided: one set (44, leader 147) alone
accounts for 9 of the 87 shippable placements; the ten sets together cover 38 of 87
(measured, not estimated - first draft of this round's test wrongly assumed "one each",
caught by the test itself failing 38 != 10, fixed before this round closed).

No name-vs-template disagreement anywhere in the 92 rows (`MOBSET_NN` free text agrees
with the numeric `template_ids` column for every row, checked), no extra spawn triple, no
multi-template row, and no extraction-unresolved sentinel (`UNRESOLVED` literal) anywhere
in this scene's placements file - the cleanest of the three scenes built so far on every
axis this project checks. No INVISIBLE-marker/empty-name placement family either (all 59
resolved leaders carry a real `MOBS_TIP.s_NAME`). 0 of CLINE type 5's 64 rows carry any
`n_CREW` value, same as bg0010.

## What shipped in `src/`

- `src/pirateforce_foundation/world_bg0005_identity.py` (new) - the crosswalk table:
  `SceneIdentity`, `Bg0005Placement`, `IDENTITIES`/`UNRESOLVED`, `MULTI_VARIANT_OUTFITS`,
  `shippable_placements()`, `unshippable_placements()`, `_self_check()`.
  `production_allowed = True` (convention marker, matching the sibling modules' own
  value).
- `src/pirateforce_foundation/world_population_bg0005.py` (new) - the census composer,
  reusing the exact frozen encoder every sibling composer already uses; wire header
  constants and `INITIAL_REAPPLY_MS` imported from `world_population`, not redefined.
  Verified end to end against the real frozen `v141` encoder this round: builds an
  87-actor collection at the scene's own registry spawn (13025.0, 23379.0, -740.0),
  nearest-first order puts Columbus (placement 1) first, wire count agrees with the
  header, all 87 bodies byte-intact, every console line cp874-encodable.
- `tests/test_world_bg0005_identity.py` (new, 14 tests) and
  `tests/test_world_population_bg0005.py` (new, 14 tests) - table-shape controls,
  ASCII/cp874 checks, GT-078-regression check on the actual wire bytes, refusal tests,
  console-line shortfall tests, and a "nothing under `src/` imports this module yet"
  AST-walk pin (this round's build-only state, same as `6p22bu`'s and `u3jo4g`'s
  equivalent tests before their scenes were wired).

**One test-design fix this round found and applied.** The GT-078 wire-regression test
(`test_every_entry_carries_a_real_mobs_n_id_ON_THE_WIRE`) originally searched a small
byte pattern against the WHOLE concatenated `generation.pc` blob, the same shape the
sibling scenes' own tests use. This scene has a genuine, measured coincidence those two
did not: Mob-Set 105's own number (105) is numerically equal to Columbus's REAL
`MOBS.n_ID` (also 105, a different placement entirely). A whole-blob search false-failed
on Columbus's own correct bytes. Fixed by checking each entry's own bytes individually
(`census._entry(...)` called per placement) instead of the whole frame - same regression
coverage, no false collision. Documented in the test's own docstring so a future round
does not "fix" it back to the fragile shape.

Not registered anywhere a player can reach: `world_scene_travel.CENSUS_SOURCES`,
`world_population_handoff.ROSTER_COMPOSERS` and `lane_hooks/lane_a_scene_census.py`'s
console-reader table are all untouched this round, and scene 5's `login_entry_allowed`
stays `false`.

**Landing-geometry note, read and recorded, not acted on.**
`scenarios/world_scene_registry_001.json`'s own
`table_row_differences.marker_geometry_measured_not_enforced` for this scene records the
marker point 564.3 units from the nearest of this scene's 92 native placements, outside
the placement extents - the ordinary "recorded, not enforced" shape 6 of the 10 doors
carry (NOT scene 10's elevated `the_two_interiors` flag). Recorded in both new modules'
docstrings so a future door-opening round reads it before flipping
`login_entry_allowed`, not touched by this round.

## Fallout from adding a new actor-entry-building module (fixed this round)

Adding `world_population_bg0005.py` moved the same three numbers scenes 4's and 10's
build rounds moved: `tools/pf_runtimeres_actor_entry_static.py`'s
`SRC_ACTOR_ENTRY_SITES` 19->20, `SRC_ACTOR_STREAM_SITES` 28->29,
`SRC_MODULES_WITH_ACTOR_ENTRY` 18->19 (new name inserted alphabetically between
`world_population_bg0004.py` and `world_population_bg0010.py`). Re-pinned in the same
commit: `tools/pf_runtimeres_actor_entry_static.py` (guard + name tuple),
`tests/test_runtimeres_actor_entry_static.py` (the bridge-only test module's own copy),
and `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (the `RUNTIMERES_COUNTS`
JSON block re-pinned). `tests/test_static_verifier_pins_cloud.py` (the test that
re-derives these numbers from `src/` and catches a lane that skips this step) failed
before this fix (11 sub-failures) and passes clean after.

## Manual adversary pass (no subagent tool available in this environment, same limit
## every LANE-A round since `i95a1z` has reported)

1. Removed the `scene_id` refusal guard from `build_bg0005_population` in a working copy
   (backed up first) - a call with `scene_id=999` built a collection instead of raising,
   confirming the guard is what refuses wrong scenes rather than something incidental.
   Restored from backup; `diff` confirmed byte-identical restoration, and the full
   targeted test suite (28 tests) passed clean afterward.
2. Changed resolved row 1's `mobs_n_id` from 105 to 2 (its own Mob-Set number) in a
   scratch copy of the identity table - import-time `_self_check()` raised
   `Bg0005IdentityError("a row ships its own Mob-Set number as an identity")` before any
   test even ran, the exact GT-078-class regression this control exists to catch.
   Reverted in-process; `_self_check()` confirmed clean afterward.
3. Ran the FULL suite before and after, not just the two new test files - specifically
   because scenes 4's and 10's own build rounds each found re-pin fallout the targeted run
   alone would have missed. This round found the same class of fallout
   (`test_static_verifier_pins_cloud.py`) the same way, and additionally found (via the
   targeted run alone, before the fallout fix) the multi-variant-count assumption error
   (10 assumed, 38 real) and the whole-blob byte-search false collision described above -
   three independent things this pass caught before the round closed, not zero.

## Player-visible claim

**None.** Scene 5's door (`login_entry_allowed`) is unchanged (`false`), no scene reaches
a player differently than yesterday, and no other scene's behavior changed. This round is
identity-table + census-composer construction and test coverage only.

## What's blocked / waiting

- The pairing (which Mob-Set number is which leader) is table inference only - no human
  has stood in this scene (registry `status: never_sent_to_any_client_by_this_project`).
  No ticket number opened for it this round since nothing is wired to a login path yet.
- Whether any of this scene's monster-shaped placements (sets 35-47, rank-1,
  ai-combat-nonzero) should be hostile is a LANE-B decision, explicitly not made here.
- Wiring (`CENSUS_SOURCES` / `ROSTER_COMPOSERS` / `lane_hooks` console reader) - next
  round of this same multi-round order, same shape as scene 4's `2jdde8` and scene 10's
  `c42axq`.
- The landing-geometry note above - a future door-opening round's job, not this one's.
- The Control-2 median gap (68->70, 35->31 measured vs. cited) - opened to lane C rather
  than chased down this round; see ticket below.

## Numbers measured this round

Placements: 92 total, 87 shippable, 5 unshippable (1 no-MOBS-row + 4 empty-outfit sets).
Mob-Set numbers: 64 distinct used (CLINE type 5's entire key range), 59 resolved, 5
unresolved. Multi-variant outfits: 10 sets, 38 of 87 shippable placements affected.
Targeted regression (2 new test files): 28 passed, 362 subtests. Full test suite (this
repo, `python3 -m pytest -q`): **5676 passed, 383 skipped, 10592 subtests passed, 0
failed** (~116s) - up from this round's own directly-measured baseline (stashed this
round's changes and re-ran clean: 5648 passed / 383 skipped / 10228 subtests). Delta: +28
tests, +364 subtests (28 from the two new files standalone; the remaining 2 are
additional subtests inside the shared verifier tests whose tuples grew by one entry).
`python3 tools/verify_hypothesis_ledger.py`: `PASS entries=47` (unchanged).
`python3 tools/verify_functional_coverage.py`: `OPEN DOMAINS: 8` (unchanged).
`git diff --stat` on `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`: empty
(none touched, none needed).

## CORE-REQUEST

None this round. Same finding round `u3jo4g` already established: the registry-generic
census-selection modules (`world_faction_admission`, `lane_hooks/lane_a_scene_census.py`,
the scene-admission gate) will need no `runtime.py`/`app.py` change to wire scene 5 in a
future round either.

## ASK-COO

None this round. Continuing the already-approved door sequence (`COO-DECISION
2026-08-30T14:41+07:00`'s own instruction: "no need to ask again per door absent an
irreversible fork").

## Tickets opened for lane C (RE re-derivation), see handback letter for the numbers

- Control-2 median re-derivation for BG0005: does `world_bg0015_identity.
  SCENE_LEVEL_CONTROL['BG0005']`'s cited `(68.0, 35.0)` reproduce under a DIFFERENT
  counting convention than this round used (per-placement over 87 shippable rows), or is
  it simply wrong and due a correction in that module's own table? This round's own
  measurement (70, 31) is believed correct for the counting convention stated in this
  round's docstring, but the earlier citation's own convention was not independently
  re-derived, only compared against.
