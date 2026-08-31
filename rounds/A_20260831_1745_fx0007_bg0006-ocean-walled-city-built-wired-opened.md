# LANE-A round `fx0007`

2026-08-31T17:29+07:00 - 2026-08-31T17:45+07:00 (approx).

## Step A / B (mandatory, start of round)

Checked both repos' most recent `[LANE-A]` PR: `pf_bridge#609` and
`pirate-force-server#394`, both `merged=true` at HEAD (`557573b` server,
`5905c43` bridge) - work landed, no recovery needed. Mailbox: no
unconsumed `ADDRESSEE: LANE-A` letter found (grep across
`notes_to_chief/*.md` for the marker, all matches already have a
`.CONSUMED.txt` stub); heartbeat (`_BRIDGE_HEARTBEAT.txt`) 5 minutes stale,
under the 60-minute threshold. No open `[LANE-A]` PR on either repo
(`pf_bridge#614` and `pirate-force-server#399` are both `[LANE-B]`, not
this lane's lock). Placed a claim
(`notes_to_chief/20260831_1729_CLAIM-LANE-A-round-fx0007-bg0006-ocean-walled-city.md`)
before starting, per the collision this same "pick the next scene" topic
had between rounds `pynass`/`l03cgh` two hours earlier - re-checked
`origin/main` immediately after placing it, unchanged from the pre-claim
check.

## What this round found and built

Continued the multi-round door sequence `COO-DECISION 2026-08-30T14:41+07:00`
approved (round `12lyda`'s own placement-count table). Scenes 4, 5, 10 and
14 are open at login as of round `l03cgh`'s merge. The next-highest native
placement count among the six still-shut doors (3, 7, 8, 9, 11, 130) minus
this round's own scene: scene 6, Bg0006 ("Ocean Walled City"), 80 native
placements - the highest of the seven still shut when this round started.

Read the join by script (not by hand), directly off the bridge clone's own
committed tables: `CONSTDATA_TH__SCENE_NAME.tsv` (scene 6 -> `n_CLINE_TYPE=6`,
`n_SCENE_LV=70`), `CONSTDATA_TH__CLINE.tsv` (type 6's 52 rows, its entire key
range: 1-38, 101-114), `CONSTDATA_TH__MOBS.tsv`, `TEXTDATA_TH__MOBS_TIP.tsv`,
`CONSTDATA_TH__STANDARD_MOB.tsv`, and `gamedata/scene/bg0006/bg0006.placements.tsv`
(80 rows). The four scene-independent tables' digests match every sibling
crosswalk's own citation (same committed files); the placements file got its
own fresh digest (`4493f6e0...3563ce`).

Measured: 52 distinct Mob-Set numbers used across all 80 placements - CLINE
type 6's ENTIRE key range, the same "placement file touches every key its
own CLINE type owns" shape scene 5's crosswalk carries. 38 of the 52 resolve
to a real, shippable body; 14 do not, in **three** different failure shapes -
one of them new to this project:

* 2 sets (1, 114) -> CLINE carries a real non-zero leader but `CONSTDATA
  MOBS` has no row for it at all (the same shape bg0005's set 1 needed, one
  occurrence there, two here).
* 9 sets (101-109) -> a real MOBS row exists but `s_OUTFIT` is empty (the
  familiar "pathfinding helper, no avatar" shape every sibling's own 101+
  block carries; this scene has the most of any scene built so far).
* 3 sets (111, 112, 113) -> **new failure mode, not needed by any sibling
  scene**: a real MOBS row AND a real, non-empty `s_OUTFIT` exist, but
  `MOBS_TIP.s_NAME` is CJK script (`海皇城寨傳送員`, a teleporter NPC going
  by the outfit) that `cp874` - the bridge console's own codepage, and the
  codepage CHARTER-02 says nothing under `src/` may carry a character it
  cannot map - cannot encode. Dropped rather than shipped mis-encoded or
  with an invented transliteration, the same fail-closed choice this
  project makes for an empty `s_OUTFIT`. Opened to lane C (`RE-171`) rather
  than guessed at.

## What shipped in `src/`

- `src/pirateforce_foundation/world_bg0006_identity.py` (new) - the
  crosswalk table: `SceneIdentity`, `Bg0006Placement`, `IDENTITIES`/
  `UNRESOLVED`, `MULTI_VARIANT_OUTFITS`, `shippable_placements()`,
  `unshippable_placements()`, `_self_check()`. 38 resolved, 14 unresolved,
  80 placements total, 66 shippable, 14 unshippable.
- `src/pirateforce_foundation/world_population_bg0006.py` (new) - the
  census composer, reusing the exact frozen encoder every sibling composer
  already uses (`legacy.make_npc_attr` / `make_remote_movement_attr` /
  `make_remote_actor_entry` / `make_runtime_remote_actors`); wire header
  constants and `INITIAL_REAPPLY_MS` imported from `world_population`, not
  redefined. Verified end to end against the real frozen `v141` encoder:
  builds a 66-actor collection at the scene's own registry spawn (-9848.0,
  24151.0, 375.0), nearest-first order puts Columbus (placement 1) first,
  wire count agrees with the header, all 66 bodies byte-intact, every
  console line cp874-encodable.
- `tests/test_world_bg0006_identity.py` (new, 15 tests, 100 subtests) and
  `tests/test_world_population_bg0006.py` (new, 15 tests) - table-shape
  controls, ASCII/cp874 checks (including a dedicated cp874 check the
  sibling scenes did not need), GT-078-regression check on the actual wire
  bytes, refusal tests, console-line shortfall tests.

Following round `l03cgh`'s compressed precedent for scene 5 (the generic
contract test `tests/test_lane_a_scene_census.py::ComposerContractTests`
already assumed every scene this lane composes for is also open at login,
since scenes 4/5/10/14 all were by the time this round started), this round
also wires and opens the door in the same pass, rather than the three-round
split scenes 4's and 10's own first rounds used:

- `src/pirateforce_foundation/world_scene_travel.py` - added
  `OCEAN_WALLED_CITY_SCENE_ID = 6` and a `bg0006_roster` row in
  `CENSUS_SOURCES`.
- `src/pirateforce_foundation/world_population_handoff.py` - imported
  `world_population_bg0006`, added a `bg0006_roster` entry to
  `ROSTER_COMPOSERS` (same `_SceneComposer` shape as siblings').
- `src/pirateforce_foundation/lane_hooks/lane_a_scene_census.py` - imported
  `world_population_bg0006`, added a `bg0006_roster` entry to
  `_CONSOLE_LINES_OF`.
- `src/pirateforce_foundation/mob_scene_recompose.py` - added
  `ACKNOWLEDGED_WITHOUT_COMPOSER[6]`, mirroring the scene 5 entry;
  `field_mobs.scene_for_scene_id(6)` verified to also return `None`.
- `scenarios/world_scene_registry_001.json` - scene 6's row (`n_id: 6`)
  flipped `login_entry_allowed` from `false` to `true`; `status` and
  `login_entry_allowed_because` rewritten with the D1/D2/D3 safety case
  (checked against THIS scene, confirmed it does **not** carry the
  elevated `the_two_interiors` flag); `why_the_ten_doors_are_shut` updated
  with a FOURTH UPDATE paragraph naming scene 6.
- `tests/test_lane_a_scene_census.py` - imported `world_population_bg0006`;
  added `OCEAN_WALLED_CITY = 6` / `OCEAN_WALLED_CITY_ROSTER_COUNT = 66`;
  added `OceanWalledCityRegistrationTests` (3 tests, mirroring
  `EvilPortRegistrationTests`).
- Eight admissible-scene-ids test files widened mechanically to include 6
  (same pattern round `l03cgh` used): `tests/test_gm_login_scene_admission.py`,
  `tests/test_gm_login_scene_override_position_resync.py`,
  `tests/test_gm_login_scene_registry_snapshot.py`,
  `tests/test_gm_login_scene_sanctioned_barred.py`,
  `tests/test_gm_login_scene_stage.py`, `tests/test_world_faction_admission.py`
  (also added `OCEAN_WALLED_CITY` constant and updated the derived-set
  assertions), `tests/test_world_scene_marker.py` (moved 6 out of the
  still-shut loop, added `test_scene_6_opened_separately_...`),
  `tests/test_world_scene_registry_rule_1_scenes.py` (narrowed
  `RULE_1_SCENES_STILL_SHUT`, added `test_the_fourth_scene_that_opened_...`).

## Fallout from adding a new actor-entry-building module (fixed this round)

Adding `world_population_bg0006.py` moved the same three numbers every
earlier sibling's own build round moved: `tools/pf_runtimeres_actor_entry_static.py`'s
`SRC_ACTOR_ENTRY_SITES` 20->21, `SRC_ACTOR_STREAM_SITES` 29->30,
`SRC_MODULES_WITH_ACTOR_ENTRY` 19->20 (new name inserted alphabetically
between `world_population_bg0005.py` and `world_population_bg0010.py`).
Re-pinned in the same commit: `tools/pf_runtimeres_actor_entry_static.py`
(guard + name tuple), `tests/test_runtimeres_actor_entry_static.py` (the
bridge-only test module's own copy), and
`reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (the
`RUNTIMERES_COUNTS` JSON block re-pinned, plus a new NOTE section).
`tests/test_static_verifier_pins_cloud.py` failed before this fix (7
sub-failures) and passes clean after.

## Manual adversary pass (no subagent tool available in this environment,
## same limit every LANE-A round since `i95a1z` has reported)

1. Simulated a table drift where a resolved row ships its own Mob-Set
   number as its identity (the exact GT-078-class regression) - `_self_check()`
   raised `Bg0006IdentityError("a row ships its own Mob-Set number as an
   identity")` before any test ran. Restored; re-ran `_self_check()` clean.
2. Called `build_bg0006_population` with `scene_id=999` directly (bypassing
   the normal call site) - raised `Bg0006CensusError` naming the refusal,
   confirming the guard is what refuses wrong scenes.
3. Ran the FULL suite before and after, not just the four new test files -
   this found the same class of fallout `test_static_verifier_pins_cloud.py`
   caught for every sibling scene's own build round, and confirmed nothing
   else regressed.

## Player-visible claim

A character whose own persisted row names scene 6, or a GM `/warp 6`, now
lands on Ocean Walled City and sees up to 66 of its 80 native placements (14
excluded: 2 leaders have no `CONSTDATA MOBS` row at all, 9 more have an
empty `s_OUTFIT`, and 3 more resolve to a real MOBS row whose
`MOBS_TIP.s_NAME` is non-ASCII CJK script that cp874 cannot ship - a new
failure shape no earlier scene needed) instead of being refused at login.
No ordinary player's stored row can come to name scene 6 by itself (no
production path writes one), so this reaches only a staged GM account or a
hand-edited config - the same reach scenes 4/5/10/14 had on the day their
own doors opened. Reversible in exactly one boolean.

## What's blocked / waiting

- Whether the marker landing point (772.0 units from the nearest native
  placement) is standable ground - unmeasured, same open question every
  door carries until an attended round looks. `GT-173
  OCEAN-WALLED-CITY-FIRST-EYES-001` opened this round in
  `pf_bridge/GAME_TEST_QUEUE.md` (checked for a duplicate against `GT-171`/
  `GT-165`/`GT-166`, none found).
- Whether any of this scene's monster-shaped placements (sets 25-35 of the
  38 resolved, rank-1, ai-combat-nonzero) should be hostile is a LANE-B
  decision, not made here.
- The three CJK-named teleporter drops: whether an ASCII/Thai alternate
  name exists in a table this round did not open. Opened as `RE-171` in
  `pf_bridge/CLIENT_RE_QUEUE.md` rather than guessed at.

## Numbers measured this round

Placements: 80 total, 66 shippable, 14 unshippable (2 no-MOBS-row + 9
empty-outfit + 3 non-ASCII-name sets). Mob-Set numbers: 52 distinct used
(CLINE type 6's entire key range), 38 resolved, 14 unresolved. Multi-variant
outfits: 10 sets, 36 of 66 shippable placements affected. Targeted
regression (4 new/widened test files' own new classes): 33 new/changed
tests, 100+ new subtests. Full test suite (this repo,
`python3 -m pytest tests -q`): **5791 passed, 327 skipped, 11136 subtests
passed, 0 failed** (132s) - up from this round's own directly-measured
baseline (round `l03cgh`'s own final numbers: 5742 passed / 327 skipped /
10708 subtests). Delta: +49 passed, +428 subtests, skipped unchanged.
`python3 tools/verify_hypothesis_ledger.py`: `PASS entries=47` (unchanged).
`python3 tools/verify_functional_coverage.py`: `PASS domains=8`, `OPEN
DOMAINS: 8` (unchanged).
`git diff --stat` on `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`:
empty (none touched, none needed).

## CORE-REQUEST

None this round. Same finding every earlier door-opening round already
established: the registry-generic census-selection modules
(`world_faction_admission`, `lane_hooks/lane_a_scene_census.py`, the
scene-admission gate) needed no `runtime.py`/`app.py` change to wire scene 6
either.

## ASK-COO

None this round. Continuing the already-approved door sequence
(`COO-DECISION 2026-08-30T14:41+07:00`'s own instruction: "no need to ask
again per door absent an irreversible fork"). The CJK-name drop is a data
fact handled the same fail-closed way every prior unresolved-set family was
handled (dropped, documented, ticketed) - not a new judgment call.

## Tickets opened for lane C

- `RE-171` (`pf_bridge/CLIENT_RE_QUEUE.md`): does an ASCII/Thai alternate
  name exist for leaders 939/940/941 (Mob-Set 111/112/113) in a table this
  round did not open, that would let these three placements ship?

## Tickets opened for attended testing

- `GT-173` (`pf_bridge/GAME_TEST_QUEUE.md`): OCEAN-WALLED-CITY-FIRST-EYES-001,
  same shape as `GT-171`/`GT-165`.
