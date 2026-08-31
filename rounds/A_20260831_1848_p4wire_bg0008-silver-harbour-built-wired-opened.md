# LANE-A round `p4wire`

2026-08-31T18:31+07:00 - 2026-08-31T18:48+07:00 (approx).

## Step A / B (mandatory, start of round)

Checked both repos' most recent `[LANE-A]` PR: `pirate-force-server#403` and
`pf_bridge#620`, both `merged=true` at HEAD (`4b5765b1` server, `5ffb8c9`
bridge) - work landed, no recovery needed. Mailbox: no unconsumed
`ADDRESSEE: LANE-A` letter found (grep across `notes_to_chief/*.md` for the
marker, all matches already have a `.CONSUMED.txt` stub); heartbeat
(`_BRIDGE_HEARTBEAT.txt`) 24 minutes stale, under the 60-minute threshold.
No open `[LANE-A]` PR on either repo at round start (only a `[LANE-GM]` WIP
round-claim PR open on each, not this lane's lock). Placed a claim
(`notes_to_chief/20260831_1831_CLAIM-LANE-A-round-p4wire-bg0008-silver-harbour.md`)
before starting, per `COO-DECISION 2026-08-31T13:45+07:00` (claim-before-work
extended to scene selection) - re-checked `origin/main` on both repos
immediately after placing it, unchanged from the pre-claim check on
`pirate-force-server` and one unrelated `[LANE-GM]` merge on `pf_bridge`
(`CLIENT_RE_QUEUE.md` only, no collision).

## Prompt hygiene note (not actioned as work, reported per this lane's own
## prior finding)

This round's prompt still carries the stale `BUILD-001`/`BUILD-002` blocks
(115 bg0001 actors / scene_id default) that `notes_to_chief/consumed/
20260831_1658_KA1A-FINDING-lane-A-stall-is-the-pf-builder-role-file-not-
todays-prompt-work-plus-stale-BUILD-001-002.md` already reported dead - both
shipped to `main` rounds ago and the lane is now five doors into the
`COO-DECISION 2026-08-30T14:41+07:00` scene-opening sequence. This round did
not stop to re-litigate that finding (already filed, chief/COO already have
it); it read the mailbox for "who does what next" per that same letter's own
recommendation and continued the door queue rather than re-running BUILD-001/
002 verification for the sixth time. The prompt's own commit/push/PR
authority question is also moot at HEAD: `.claude/agents/pf-builder.md`
already reads "you claim your own round lock... `git commit`... `git push`...
open... take it out of draft yourself", confirmed identical in both repos'
copies (`de0fa5c`/`ff4282c`/`1abab8f` on server; matching commits on bridge) -
no conflict to escalate this round.

## What this round found and built

Continued the multi-round door sequence `COO-DECISION 2026-08-30T14:41+07:00`
approved (round `12lyda`'s own placement-count table). Scenes 4, 5, 10, 14
and 6 are open at login as of round `fx0007`'s merge. The next-highest native
placement count among the six still-shut doors (3, 7, 8, 9, 11, 130): scene 8,
Bg0008 ("Silver Harbour"), 76 native placements - the highest of the six
still shut when this round started.

Read the join by script (not by hand), directly off the bridge clone's own
committed tables: `CONSTDATA_TH__SCENE_NAME.tsv` (scene 8 -> `n_CLINE_TYPE=8`,
`n_SCENE_LV=86`), `CONSTDATA_TH__CLINE.tsv` (type 8's 48 rows, its entire key
range: 1-42, 101-106), `CONSTDATA_TH__MOBS.tsv`, `TEXTDATA_TH__MOBS_TIP.tsv`,
`CONSTDATA_TH__STANDARD_MOB.tsv`, and `gamedata/scene/Bg0008/Bg0008.placements.tsv`
(76 rows). The five scene-independent tables' digests match every sibling
crosswalk's own citation (same committed files); the placements file got its
own fresh digest (`7143642442ab...d1e42fdb86`).

Measured: 48 distinct Mob-Set numbers used across all 76 placements - CLINE
type 8's ENTIRE key range, the same "placement file touches every key its own
CLINE type owns" shape scenes 5's and 6's own crosswalks carry (unlike
bg0004's 61-of-62 and bg0010's 40-of-41). NOTE: the registry's own
`native_definition_count` for this scene reads 49; this round's own count
(CLINE rows grouped by `n_CREATURE_TYPE`, checked for duplicates - none) is
48, agreeing with the placement-file's own 48 distinct Mob-Set numbers.
Recorded as a discrepancy in `world_bg0008_identity.py`'s own docstring
rather than silently reconciled - this round did not re-derive whatever the
registry's own count measured.

41 of the 48 resolve to a real, shippable body; 7 do not, in two familiar
failure shapes, no third one this time:

* 2 sets (1, 106) -> leaders [249, 0]. Set 1: CLINE carries a real non-zero
  leader but `CONSTDATA MOBS` has no row for it (the same "no row" family
  bg0005's set 1 and bg0006's sets 1/114 needed). Set 106: CLINE's own
  `n_LEADER_BK1` is literally 0, which resolves to no leader at all - a
  leader-less variant of the same family, distinguished in the test rather
  than folded into the same assertion as set 1's.
* 5 sets (101-105) -> leaders [10043..10047]. Every one HAS a real
  `CONSTDATA MOBS` row but `s_OUTFIT` is empty - the familiar "pathfinding
  helper, no avatar" shape every sibling's own 101+ block carries.
* NO CJK/non-cp874 name family this scene needed (unlike bg0006's three
  teleporter drops) - every one of this scene's 41 resolved `MOBS_TIP` rows
  is plain ASCII, checked directly rather than assumed.

## What shipped in `src/`

- `src/pirateforce_foundation/world_bg0008_identity.py` (new) - the
  crosswalk table: `SceneIdentity`, `Bg0008Placement`, `IDENTITIES`/
  `UNRESOLVED`, `MULTI_VARIANT_OUTFITS`, `shippable_placements()`,
  `unshippable_placements()`, `_self_check()`. 41 resolved, 7 unresolved, 76
  placements total, 69 shippable, 7 unshippable.
- `src/pirateforce_foundation/world_population_bg0008.py` (new) - the
  census composer, reusing the exact frozen encoder every sibling composer
  already uses (`legacy.make_npc_attr` / `make_remote_movement_attr` /
  `make_remote_actor_entry` / `make_runtime_remote_actors`); wire header
  constants and `INITIAL_REAPPLY_MS` imported from `world_population`, not
  redefined. Verified end to end against the real frozen `v141` encoder:
  builds a 69-actor collection at the scene's own registry spawn (19440.0,
  23997.0, 560.0), nearest-first order puts placement index 2 ("Chamber
  sailor") first - NOT placement index 0, which is 8.8 units from the spawn
  but resolves to Mob-Set 1, one of the 7 unresolved sets - wire count
  agrees with the header, all 69 bodies byte-intact, every console line
  cp874-encodable.
- `tests/test_world_bg0008_identity.py` (new, 15 tests, 99 subtests) and
  `tests/test_world_population_bg0008.py` (new, 14 tests, 238 subtests) -
  table-shape controls, ASCII/cp874 checks, GT-078-regression check on the
  actual wire bytes, refusal tests, console-line shortfall tests, and a
  dedicated test for the "nearest placement is unresolved" ordering quirk
  this scene needed that no sibling did.

Following rounds `l03cgh`/`fx0007`'s compressed precedent for scenes 5 and 6
(the generic contract test `tests/test_lane_a_scene_census.py::
ComposerContractTests` already assumed every scene this lane composes for is
also open at login, since scenes 4/5/6/10/14 all were by the time this round
started), this round also wires and opens the door in the same pass:

- `src/pirateforce_foundation/world_scene_travel.py` - added
  `SILVER_HARBOUR_SCENE_ID = 8` and a `bg0008_roster` row in
  `CENSUS_SOURCES`.
- `src/pirateforce_foundation/world_population_handoff.py` - imported
  `world_population_bg0008`, added a `bg0008_roster` entry to
  `ROSTER_COMPOSERS` (same `_SceneComposer` shape as siblings').
- `src/pirateforce_foundation/lane_hooks/lane_a_scene_census.py` - imported
  `world_population_bg0008`, added a `bg0008_roster` entry to
  `_CONSOLE_LINES_OF`.
- `src/pirateforce_foundation/mob_scene_recompose.py` - added
  `ACKNOWLEDGED_WITHOUT_COMPOSER[8]`, mirroring the scene 5/6 entries;
  `field_mobs.scene_for_scene_id(8)` verified to also return `None`.
- `scenarios/world_scene_registry_001.json` - scene 8's row (`n_id: 8`)
  flipped `login_entry_allowed` from `false` to `true`; `status` and
  `login_entry_allowed_because` rewritten with the D1/D2/D3 safety case
  (checked against THIS scene, confirmed it does **not** carry the
  elevated `the_two_interiors` flag); `why_the_ten_doors_are_shut` updated
  with a FIFTH UPDATE paragraph naming scene 8.
- `tests/test_lane_a_scene_census.py` - imported `world_population_bg0008`;
  added `SILVER_HARBOUR = 8` / `SILVER_HARBOUR_ROSTER_COUNT = 69`; added
  `SilverHarbourRegistrationTests` (3 tests, mirroring
  `OceanWalledCityRegistrationTests`).
- Eight admissible-scene-ids test files widened mechanically to include 8
  (same pattern rounds `l03cgh`/`fx0007` used): `tests/test_gm_login_scene_admission.py`,
  `tests/test_gm_login_scene_override_position_resync.py`,
  `tests/test_gm_login_scene_registry_snapshot.py`,
  `tests/test_gm_login_scene_sanctioned_barred.py`,
  `tests/test_gm_login_scene_stage.py`, `tests/test_world_faction_admission.py`
  (also added `SILVER_HARBOUR` constant and updated the derived-set
  assertions), `tests/test_world_scene_marker.py` (moved 8 out of the
  still-shut loop, added `test_scene_8_opened_separately_...`),
  `tests/test_world_scene_registry_rule_1_scenes.py` (narrowed
  `RULE_1_SCENES_STILL_SHUT`, added `test_the_fifth_scene_that_opened_...`).

## Fallout from adding a new actor-entry-building module (fixed this round)

Adding `world_population_bg0008.py` moved the same three numbers every
earlier sibling's own build round moved: `tools/pf_runtimeres_actor_entry_static.py`'s
`SRC_ACTOR_ENTRY_SITES` 21->22, `SRC_ACTOR_STREAM_SITES` 30->31,
`SRC_MODULES_WITH_ACTOR_ENTRY` 20->21 (new name inserted alphabetically
between `world_population_bg0006.py` and `world_population_bg0010.py`).
Re-pinned in the same commit: `tools/pf_runtimeres_actor_entry_static.py`
(guard + name tuple), `tests/test_runtimeres_actor_entry_static.py` (the
bridge-only test module's own copy), and
`reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (the
`RUNTIMERES_COUNTS` JSON block re-pinned, plus a new NOTE section). This
round's environment has no `GameClient.local.bin` to run the tool itself
against (the same limit every LANE-A round in this environment has had), so
the three-count fallout was applied mechanically per the established +1/+1/+1
pattern rather than re-verified against the binary; `tests/
test_static_verifier_pins_cloud.py` (which recomputes from `src/` directly,
no binary needed) passed clean after the edit.

## Manual adversary pass (no subagent tool available in this environment,
## same limit every LANE-A round since `i95a1z` has reported)

1. Simulated a table drift where a resolved row ships its own Mob-Set
   number as its identity (the exact GT-078-class regression) - `_self_check()`
   raised `Bg0008IdentityError("a row ships its own Mob-Set number as an
   identity")` before any test ran. Restored; re-ran `_self_check()` clean.
2. Called `build_bg0008_population` with `scene_id=999` directly (bypassing
   the normal call site) - raised `Bg0008CensusError` naming the refusal,
   confirming the guard is what refuses wrong scenes.
3. Ran the FULL suite after the change (5878 passed, 323 skipped, 11573
   subtests, 0 failed) - this found the same class of fallout
   `test_static_verifier_pins_cloud.py` caught for every sibling scene's own
   build round, and confirmed nothing else regressed.

## Player-visible claim

A character whose own persisted row names scene 8, or a GM `/warp 8`, now
lands on Silver Harbour and sees up to 69 of its 76 native placements (7
excluded: 2 leaders have no `CONSTDATA MOBS` row at all, 5 more have an
empty `s_OUTFIT`) instead of being refused at login. No ordinary player's
stored row can come to name scene 8 by itself (no production path writes
one), so this reaches only a staged GM account or a hand-edited config - the
same reach scenes 4/5/6/10/14 had on the day their own doors opened.
Reversible in exactly one boolean.

## What's blocked / waiting

- Whether the marker landing point (8.8 units from the nearest native
  placement, inside the placement extents - the tightest gap of any door
  opened so far) is standable ground - unmeasured, same open question every
  door carries until an attended round looks. `GT-174
  SILVER-HARBOUR-FIRST-EYES-001` opened this round in
  `pf_bridge/GAME_TEST_QUEUE.md` (checked for a duplicate against `GT-173`/
  `GT-171`/`GT-165`, none found).
- Whether any of this scene's monster-shaped placements (sets 22-35 of the
  41 resolved, rank-1, ai-combat-nonzero) should be hostile is a LANE-B
  decision, not made here.
- The registry's own `native_definition_count` (49) disagreeing with this
  round's measured 48 - recorded in the module docstring, not resolved.

## Numbers measured this round

Placements: 76 total, 69 shippable, 7 unshippable (2 no-MOBS-row + 5
empty-outfit). Mob-Set numbers: 48 distinct used (CLINE type 8's entire key
range), 41 resolved, 7 unresolved. Multi-variant outfits: 10 sets, 36 of 69
shippable placements affected. Targeted regression (4 new/widened test
files' own new classes): 29 new/changed tests, 337 new subtests. Full test
suite (this repo, `python3 -m pytest tests -q`): **5878 passed, 323 skipped,
11573 subtests passed, 0 failed** (142s).
`python3 tools/verify_hypothesis_ledger.py`: `PASS entries=47` (unchanged).
`python3 tools/verify_functional_coverage.py`: `PASS domains=8`, `OPEN
DOMAINS: 8` (unchanged).
`git diff --stat` on `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`:
empty (none touched, none needed).

## CORE-REQUEST

None this round. Same finding every earlier door-opening round already
established: the registry-generic census-selection modules
(`world_faction_admission`, `lane_hooks/lane_a_scene_census.py`, the
scene-admission gate) needed no `runtime.py`/`app.py` change to wire scene 8
either.

## ASK-COO

None this round. Continuing the already-approved door sequence
(`COO-DECISION 2026-08-30T14:41+07:00`'s own instruction: "no need to ask
again per door absent an irreversible fork").

## Tickets opened for lane C

None this round - unlike scene 6, this scene needed no third unresolved-
identity family that would call for a lane-C fact-check (no CJK name, no
translation-alternate question).

## Tickets opened for attended testing

- `GT-174` (`pf_bridge/GAME_TEST_QUEUE.md`): SILVER-HARBOUR-FIRST-EYES-001,
  same shape as `GT-173`/`GT-171`/`GT-165`.
