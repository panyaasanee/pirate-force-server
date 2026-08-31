# LANE-A round u3jo4g

2026-08-31T06:43+07:00 - 2026-08-31T07:43+07:00 (approx).

## Step A / B (mandatory, start of round)

Checked the GitHub REST API directly (the orchestrating session holds a token this
sandbox can use via `$GH_TOKEN`, unlike some earlier rounds' notes): the newest `[LANE-A]`
PR in each repo (`pirate-force-server#365` / `pf_bridge#571`, round `bq4mst`) is
`merged=true` in both repos, no `[LANE-A]` PR was open going in
(`pirate-force-server#367`/`#363` open this round belong to LANE-GM/LANE-B and were not
touched), and both working trees fast-forwarded cleanly to `origin/main`. Nothing to
recover.

Mailbox: grepped `notes_to_chief/` for unconsumed items addressed to this lane
(`ADDRESSEE: LANE-A` with no `.CONSUMED.txt` stub, and any `FROM_CHIEF_*_TO_LANE-A_*`
without one). The two hits on the literal string were both false positives - the grep
command being quoted inside this lane's own prior STATUS letters (`6oyud5`, `pbpkv4`),
not a real header. `FROM_CHIEF_R256_TO_LANE-A` was already consumed last round (`bq4mst`).
No `CLAIM-LANE-A-*` files under 90 minutes old. Nothing to consume this round.

## What this round found and built

Continued the multi-round door sequence `COO-DECISION 2026-08-30T14:41+07:00` approved
(round `12lyda`'s own placement-count table, ten still-shut doors surveyed, no per-door
re-approval needed absent an irreversible fork). Scene 4 (116 placements) went first over
rounds `6p22bu`/`2jdde8`/`bq4mst` (build, wire, open). This round starts the second door:
scene 10, Bg0010 ("Deep Sea Temple floor 1"), the next-highest native placement count
(100) in that table, same build-only granularity round `6p22bu` used for scene 4's first
round.

Read the join by script (not by hand this time - the tables are large enough that hand
transcription would itself be an error source, so a throwaway script did the extraction
and its own output is what appears in the module, unedited except formatting) directly
off the bridge clone's own committed tables: `CONSTDATA_TH__SCENE_NAME.tsv` (scene 10 ->
`n_CLINE_TYPE=10`, `n_SCENE_LV=92`), `CONSTDATA_TH__CLINE.tsv` (type 10's 41 rows),
`CONSTDATA_TH__MOBS.tsv`, `TEXTDATA_TH__MOBS_TIP.tsv`, `CONSTDATA_TH__STANDARD_MOB.tsv`,
and `gamedata/scene/Bg0010/Bg0010.placements.tsv` (100 rows). Digests re-derived and
matched what `world_bg0004_identity.py` already pins for the four shared tables; the
scene's own placements TSV got its own fresh digest.

Measured: 40 distinct Mob-Set numbers used across 99 of the 100 placements (the 100th is
a new failure shape, below), all 40 present in CLINE type 10's block. 35 of the 40 resolve
to a real body; 5 do not (all five have a MOBS row but no `s_OUTFIT` avatar template - the
same "pathfinding helper, not a creature" shape both sibling scenes' 101+ blocks carry).
94 of the 100 placements ship; 6 are dropped. Control 2 (declared level vs. CLINE-reading
median) reproduces EXACTLY this time (99.0 both ways), unlike scene 4's one-point gap.
Twelve sets carry a `;`-separated multi-variant outfit (59 of the 94 shippable placements
affected, well over half); shipped first-variant only, same [LANE-A ASSUMPTION] carried
over from both sibling crosswalks.

**A shape not seen in either sibling scene:** placement index 50's own machine-parsed
`template_ids` column is the literal string `UNRESOLVED` - not a Mob-Set number CLINE
fails to resolve, but no Mob-Set number assigned at all by the extraction step. The
free-text columns claim `Mob_Set_99`, but `world_bg0004_identity.py`'s own precedent
(placements 82/83 there) already established this project trusts the machine-parsed
column over free text when the two disagree, and "the machine-parsed column refuses to
say" is not the same fact as "the free-text column says 99" (99 is also outside CLINE
type 10's own 1-41 key range). Dropped, given its own sentinel `template_id = -1`, and
named with its own distinct reason string rather than merged into the five empty-outfit
drops. `grep -rn UNRESOLVED gamedata/scene/*/*.placements.tsv` on the bridge clone found
exactly one other scene with the same literal (`Bg5004`, untouched by this project) - not
unique to this scene, but new to this crosswalk pass.

Unlike scene 4: no name-vs-template_ids disagreement anywhere in the 99 real-template
rows, no extra spawn triple, no multi-template row, and no INVISIBLE-marker/empty-name
placement family (all 35 resolved leaders carry a real `MOBS_TIP.s_NAME`).

## What shipped in `src/`

- `src/pirateforce_foundation/world_bg0010_identity.py` (new) - the crosswalk table:
  `SceneIdentity`, `Bg0010Placement`, `IDENTITIES`/`UNRESOLVED`,
  `EXTRACTION_UNRESOLVED_REASON`, `shippable_placements()`, `unshippable_placements()`,
  `_self_check()`. `production_allowed = True` (convention marker, matching the sibling
  modules' own value).
- `src/pirateforce_foundation/world_population_bg0010.py` (new) - the census composer,
  reusing the exact frozen encoder every sibling composer already uses; wire header
  constants and `INITIAL_REAPPLY_MS` imported from `world_population`, not redefined.
  Verified end to end against the real frozen `v141` encoder this round: builds a
  94-actor collection at the scene's own registry spawn, wire count agrees with the
  header, all 94 bodies byte-intact, every console line cp874-encodable.
- `tests/test_world_bg0010_identity.py` (new, 14 tests) and
  `tests/test_world_population_bg0010.py` (new, 14 tests) - table-shape controls,
  ASCII/cp874 checks, GT-078-regression check on the actual wire bytes, refusal tests,
  console-line shortfall tests, and a "nothing under `src/` imports this module yet"
  AST-walk pin (this round's build-only state, same as `6p22bu`'s equivalent test before
  bg0004 was wired).

Not registered anywhere a player can reach: `world_scene_travel.CENSUS_SOURCES`,
`world_population_handoff.ROSTER_COMPOSERS` and `lane_hooks/lane_a_scene_census.py`'s
console-reader table are all untouched this round, and scene 10's `login_entry_allowed`
stays `false`.

**Landing-geometry caution, read and recorded, not acted on.**
`scenarios/world_scene_registry_001.json`'s own `table_row_differences.the_two_interiors`
(pf-adversary, round `ga91m5`) names scene 10 as one of the two scenes an attended round
should check FIRST if a landing goes wrong (marker point 5174.7 units from the nearest
native placement, OUTSIDE the placement extents; placement z floor -4532.9 vs marker z
465). That finding is about the ARRIVAL POINT, not this round's composer - the composer
assembles a roster around whatever anchor a caller gives it, same as every other
composer. Recorded in both new modules' docstrings so a future door-opening round reads it
before flipping `login_entry_allowed`, not touched by this round.

## Fallout from adding a new actor-entry-building module (fixed this round)

Adding `world_population_bg0010.py` moved the same three numbers scene 4's build round
moved: `tools/pf_runtimeres_actor_entry_static.py`'s `SRC_ACTOR_ENTRY_SITES` 18->19,
`SRC_ACTOR_STREAM_SITES` 27->28, `SRC_MODULES_WITH_ACTOR_ENTRY` 17->18 (new name inserted
alphabetically between `world_population_bg0004.py` and `world_population_bg0015.py`).
Re-pinned in the same commit: `tools/pf_runtimeres_actor_entry_static.py` (guard + name
tuple), `tests/test_runtimeres_actor_entry_static.py` (the bridge-only test module's own
copy), and `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (the
`RUNTIMERES_COUNTS` JSON block re-pinned, plus a new append-only NOTE section - no
existing prose rewritten). `tests/test_static_verifier_pins_cloud.py` (the test that
re-derives these numbers from `src/` and catches a lane that skips this step) failed
before this fix and passes after.

## Manual adversary pass (no subagent tool available in this environment, same limit
## every LANE-A round since `i95a1z` has reported)

1. Removed the `scene_id` refusal guard from `build_bg0010_population` in a scratch copy -
   `test_it_refuses_every_scene_but_ten` failed on all 8 subtests immediately (no
   exception raised for any wrong scene id, including the anchor scene's own string form
   `"10"`). Reverted; `diff` against the backup confirmed byte-identical restoration.
2. Changed resolved row 1's `mobs_n_id` from 644 to 1 (its own Mob-Set number) in a
   scratch copy of the identity table - import-time `_self_check()` raised
   `Bg0010IdentityError("a row ships its own Mob-Set number as an identity")` before any
   test even ran, the exact GT-078-class regression this control exists to catch.
   Reverted; `diff` confirmed byte-identical restoration.
3. Ran the FULL suite before and after both mutations (not just the two new test files),
   specifically because scene 4's build round found six re-pin sites the targeted run
   alone would have missed - this round found the same class of fallout
   (`test_static_verifier_pins_cloud.py`) the same way, by running the whole suite first.

## Player-visible claim

**None.** Scene 10's door (`login_entry_allowed`) is unchanged (`false`), no scene reaches
a player differently than yesterday, and no other scene's behavior changed. This round is
identity-table + census-composer construction and test coverage only.

## What's blocked / waiting

- The pairing (which Mob-Set number is which leader) is table inference only - no human
  has stood in this scene (registry `status: never_sent_to_any_client_by_this_project`).
  No ticket number opened for it this round since nothing is wired to a login path yet.
- Whether any of this scene's monster-shaped placements (the rank-1, ai-combat-nonzero
  sets) should be hostile is a LANE-B decision, explicitly not made here.
- Wiring (`CENSUS_SOURCES` / `ROSTER_COMPOSERS` / `lane_hooks` console reader) - next
  round of this same multi-round order, same as scene 4's `2jdde8`.
- The landing-geometry caution above - a future door-opening round's job, not this one's.

## Numbers measured this round

Placements: 100 total, 94 shippable, 6 unshippable (5 empty-outfit sets + 1
extraction-unresolved sentinel row). Mob-Set numbers: 40 distinct used, 35 resolved, 5
unresolved. Multi-variant outfits: 12 sets, 59 of 94 shippable placements affected.
Targeted regression (2 new test files): 28 passed, 362 subtests. Full test suite (this
repo, `python3 -m pytest tests -q`): **5692 passed, 327 skipped, 10123 subtests passed, 0
failed** (140s) - up from round `bq4mst`'s baseline of 5664 passed / 9759 subtests; the
skip count is unchanged from before this round (pre-existing image-gated/capstone-gap
modules this environment cannot run).
`python3 tools/verify_hypothesis_ledger.py`: `PASS entries=47` (unchanged).
`python3 tools/verify_functional_coverage.py`: `PASS domains=8`, `OPEN DOMAINS: 8`
(unchanged). `git diff --stat` on `runtime.py`/`app.py`/
`current/pf_login_game_server_v141.py`: empty (none touched, none needed).

## CORE-REQUEST

None this round. The four census-selection modules `world_faction_admission`,
`lane_hooks/lane_a_scene_census.py` and the scene-admission gate already read the
registry generically (per round `bq4mst`'s own finding) - wiring scene 10 in next round
will need no `runtime.py`/`app.py` change either, on the same evidence.

## ASK-COO

None this round. Continuing the already-approved door sequence (`COO-DECISION
2026-08-30T14:41+07:00`'s own instruction: "no need to ask again per door absent an
irreversible fork").
