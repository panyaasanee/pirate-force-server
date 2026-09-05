# UI Lane -- non-core buttons and player-facing functions

Owner order: PANYA-ORDER `pf_bridge/notes_to_chief/20260905_1911_KA1A-TO-COO-PANYA-ORDER-lane-ui-ship-ui-b-logout-headless-first-registry-plan.md`,
registered in the write zone by COO-DECISION `20260905_1948` / chief `20260905_1949`.

## What this lane is, in one sentence

"Clear out buttons/functions and small subsystems outside the core systems
(mob/quest/combat/skill are not this lane) -- back-to-character-select /
exit-game buttons, auto-walk to an NPC/monster, NPC shop as an example" --
Panya's own words, `notes_to_chief/20260904_0328...` (this lane's opening
order). A button "works" when the player sees what the button PROMISES on
screen for real, not "the server refuses with a message" (LANE-A's refusal
layer, `GT-205`/`GT-211`, is a starting point, not the finish line) and not
a report-only module that only logs a frame.

## Write zone

- `src/pirateforce_foundation/ui_*.py` -- all new modules for this lane
- `tests/test_ui_*.py`
- `docs/UI_LANE.md` (this file)
- `rounds/UI_*` (pf_bridge side)

`runtime.py`, `app.py`, `store.py`, `gm/`, and
`current/pf_login_game_server_v141.py` belong to chief/other lanes. Any
wiring into those files is one `CORE-REQUEST` letter per hookup point in
`pf_bridge/notes_to_chief/`, naming the module, the function to call, and
the exact dispatch spot (vital id / branch).

Not this lane: mob/combat/loot (LANE-B), quest, skill/profession (LANE-CS),
scene/travel/TriggerVital into an island (LANE-A, M2), GMUI + `/` commands
(LANE-GM), DB rows (LANE-DB -- a new column is a letter), `v141` (frozen,
forever).

## The three-file function map (Panya order `20260905_19:0x`)

1. **Catalog of "what can this game do"** =
   `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (327 rows, id +
   name on the wire, one row = one real action). Grouped by the prefix
   before the first `_`: `Community_` 38 (friendship/soulmate/bottle
   letter/penpal/system mail), `Equipment_` 17, `Pets_` 16, `Channel_` 16
   (chat), `Express_` 12, `BuildingCrystal_` 12, `Activity_` 9,
   `CollectionObj_` 6, `Winemaking_` 5, `KnowledgeGuru_` 5, `HitParade_` 5
   (rankings), `TreasureHunt_` 3, `Gathering_` 3, `NavigationEx_` 2,
   `UserSetting`/`Dyeing`/`Appraisal`/`Stall`/`Trade`/`Party`/`Arena`/
   `Vehicle`/`Potion`/`Relive`/`ItemLock`/etc. 147 unprefixed names are
   core systems (mostly A/B/GM/CS's, not this lane's, per the mission).
2. **"How would it be built"** = `external/PF_PROTOCOL_REGISTRY.tsv` (519
   classes, VA of serializer/handler/getter for static RE) -- 209 names
   beyond item 1 are data structs/modules, not player actions; 17 names
   exist only in item 1. Read both, always, before assuming something is
   unbuilt.
3. **"Do we already know the wire shape"** = `external/PF_SERIALIZER_FIELDS.tsv`
   (proven layouts + W/R direction). Start at `external/00_SEARCH_HERE_FIRST.md`
   before declaring anything "unknown".

**Pickup order for every row below: layout already known (no RE needed) >
needs static RE > needs attended capture, last.** Every new RE ticket must
cite a row in this table and its own "grepped `external/`+`archive/`
first: found/not found" section (`AGENTS.md` section 7).

## Function table

Status legend: `LAYOUT-KNOWN` (item 3 proves the wire shape),
`NEEDS-RE-STATIC` (shape unknown, answerable from the client image),
`NEEDS-CAPTURE` (needs an attended live boot), `IN-PROGRESS`,
`HEADLESS-DONE` (server-side proven, no client-visible claim yet),
`DONE` (both evidence layers closed plus a GT ticket the tester actually
clicked), `BLOCKED-ON-RE-<id>` / `BLOCKED-ON-<LANE>`.

| Group (item 1) | Vital / id (dir) | Player sees | Status | Next step | GT/RE |
|---|---|---|---|---|---|
| core (exit/select) | `LogoutVital` `0x1B40` subcode 1 "exit game" (c->s), ack same id (s->c) | Click "Exit Game" -> session ends cleanly, can log back in | **HEADLESS-DONE this round**: `ui_logout_exit_game.dispatch_real_exit_game_logout` composes the pinned HYP-PF-012 ack, calls the same `close_connection()` every disconnect already uses, and schedules the HYP-PF-013-proved delayed socket close -- proven against a real `SQLiteStore` (session row closes, a fresh login re-selects the same character). Not yet wired into `runtime.py`'s dispatch (today that path only composes LANE-A's refusal notice) -- **CORE-REQUEST pending**, see this round's letter. | Land the CORE-REQUEST hookup; then a GT ticket for the client-observable half (does the real client actually accept the FIN and return control, i.e. does the process/UI actually end) | `GT-211` (refusal layer, PASS-partial) superseded for subcode 1 once wired; new GT ticket after hookup lands |
| core (exit/select) | `LogoutVital` `0x1B40` subcode 3 "back to character select" (c->s) | Click "Back" -> character-select screen renders | **BLOCKED-ON-RE**: needs a NEW screen after close, unlike exit-game. COO-DECISION `20260905_1352`: narrow RE on the `0x709E` (`ReturnSelectServerVital`/`GetWorldInfo`) handler + whether the client blocks waiting for a `WorldInfo` reply after ack, before any more live boots (two prior hypotheses already falsified: ack+close alone, and a zeroed `0x709E` push before ack -- neither moves the client's screen). | Wait for that RE ticket's numbered answer (ticket `1405`, promised by chief); then implement per its finding | `GT-205` (refusal layer, PASS-partial); `GT-184`/`GT-186` BLOCKED-ON-RE |
| auto-walk / click-target | `CTracePathReqVital` `0x4391` (c->s) -> empty-vector reply (s->c) | Click ground/NPC/monster (incl. minimap, same frame per `FUNCTIONAL_COVERAGE.json` `MOVE-AUTHORITY-001/-002`) -> real auto-walk to that point | Empty-vector "unstick" fallback landed (`RE-119`, `GT-120` PASS) -- that only clears the "stuck forever" bug, it is NOT auto-walk. `CORE-REQUEST-025`/`20260905_0347` installed a log-only observer at the dispatch site (`lane_hooks.fire`), decides nothing about the request's own fields. `RE-236` item (b) (`u16@+0x14` = quest id / NPC id / list index) still open; tracepath CORE-REQUEST is `BLOCKED-ON-LANE-A accessor` per chief `20260905_1407`. | Wait on the LANE-A accessor unblock, then read the observer's captured payloads for the discriminator | queue item 4 in `prompts/LANE-UI.md`; no GT yet |
| NPC shop | buy/sell frames (LANE-A's `TradeCmdVital` family) | Open an NPC shop, buy/sell an item | `GT-230` OPEN (attended capture item, chief `20260904_0835`). Blocked on LANE-DB money/inventory interface (`20260904_0715`, queued behind all 5 PLAYER/CHARACTER pieces) | Wait on LANE-DB interface, then wire buy/sell | `GT-230` |
| Community/Party/Trade (8 classes) | friend/mail/party/trade vitals | Add friend, send mail, invite to party, propose trade | Layout resolved (`0400`/`1120` catalog), wiring CORE-REQUEST queued behind chief since 2026-09-04 (`0621`/`1120`) -- still 0 hits in `runtime.py`/`vital_walk.py` as of last check | Re-check `.CONSUMED.txt` for these two letters each round; write `ui_*.py` the round either lands | none yet |
| Options apply | settings vitals | Change a setting, see it take effect | RE ticket open, needs dynamic capture | wait for capture slot | none yet |
| Black market / ship survey window | 2 classes, fields incomplete | Open black-market or ship-survey UI | RE ticket open (`1137`), needs dynamic capture; fields incomplete even for static | wait for capture slot | none yet |
| Stall / Guild Storage | `Stall_*`/`GuildStorage_*` | Open personal stall / guild storage | Fields incomplete, needs more static RE (`RE-261` static-completeness measured `rp5tq1`) | continue field-by-field static RE | none yet |
| everything else in item 1's 15 non-core groups not listed above (Equipment_/Pets_/Channel_/Express_/BuildingCrystal_/Activity_/CollectionObj_/Winemaking_/KnowledgeGuru_/HitParade_/TreasureHunt_/Gathering_/NavigationEx_/UserSetting/Dyeing/Appraisal/Vehicle/Potion/Relive/ItemLock) | -- | -- | **NOT YET ITEMIZED** -- this table currently covers the rows this lane's rounds have actually touched (per the catalog letters `20260904_0400`/`0453`/`1159`/`1244`). Each future round expands only the row(s) it works on; do not re-derive all 327 rows in one sitting. | pick the next `LAYOUT-KNOWN` row from `external/PF_SERIALIZER_FIELDS.tsv` when the queue above is blocked | -- |

## Nonclaims

- This table's group-level statuses are a compaction of catalog letters
  already sent to COO 2026-09-04 (`0400` 15-row survey, `0453`/`1159`
  status, `1244` closure at 14/15) -- it does not re-verify every one of
  those 327 rows fresh this round; a stale sub-claim in the source
  letters would still be stale here until a round re-checks it.
- The `LogoutVital` exit-game row's "HEADLESS-DONE" status is a claim
  about server-side behavior only (ack bytes, DB session row, relogin),
  proven against a real `SQLiteStore` and the real `pf_login_game_server_v141`
  legacy parser/composer -- it does NOT claim anything about what a real
  client does when the FIN actually arrives (no live boot performed this
  round; COO-DECISION `20260905_1352`'s no-more-guessing-boots rule is
  about the character-select transition, not this).
- The auto-walk row's "log-only observer" claim is unchanged from
  `CORE-REQUEST-025`'s own docstring in `runtime.py` -- not re-verified
  independently this round.
