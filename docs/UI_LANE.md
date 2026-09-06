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
| core (exit/select) | `LogoutVital` `0x1B40` subcode 3 "back to character select" (c->s) | Click "Back" -> character-select screen renders | **BLOCKED-ON-RE-266, now STATIC-CEILING**: `RE-266` (`notes_to_chief/20260905_2242_RE-266-RESULT-*.md`) came back BOUNDED-NEGATIVE / STATIC ANSWERED -- the `0x709E` true branch does session/transport handoff only (no call opens the selection UI in that downstream), and `GetWorldInfoVital`'s natural R handler has no pending-reply flag/ack-clear/state-transition call; it fans out to three `SystemSetting_*` receivers instead. Static RE has hit method ceiling on this question (per RE-266's own BUILD_IMPACT: do not retry `0x709E` from HOME with a payload tweak, do not add a server-side wait-for-`0x3D4B` ack). Deciding whether the real character-select flow waits on world-info now needs an attended, dual-layer (client-observable + wire) capture, not another static ticket. | `GT-184`/`GT-186` updated this round with the narrowed question (does the client visibly wait after the ack, with the wire capture taken in the same pass) and an `ATTENDED:` block; queued behind `NEEDS-ATTENDED-CAPTURE` and Panya's machine per the RE->GT rule (`AGENTS.md` section 7, `COO-DECISION 20260904_2142` item 3) | `GT-205` (refusal layer, PASS-partial); `GT-184`/`GT-186` BLOCKED-ON-RE-266, method ceiling reached, waiting on attended capture |
| auto-walk / click-target | `CTracePathReqVital` `0x4391` (c->s) -> empty-vector reply (s->c) | Click ground/NPC/monster (incl. minimap, same frame per `FUNCTIONAL_COVERAGE.json` `MOVE-AUTHORITY-001/-002`) -> real auto-walk to that point | Empty-vector "unstick" fallback landed (`RE-119`, `GT-120` PASS) -- that only clears the "stuck forever" bug, it is NOT auto-walk. `CORE-REQUEST-025`/`20260905_0347` installed a log-only observer at the dispatch site (`lane_hooks.fire`), decides nothing about the request's own fields. `RE-236` item (b) (`u16@+0x14` = quest id / NPC id / list index) still open; tracepath CORE-REQUEST is `BLOCKED-ON-LANE-A accessor` per chief `20260905_1407`. | Wait on the LANE-A accessor unblock, then read the observer's captured payloads for the discriminator | queue item 4 in `prompts/LANE-UI.md`; no GT yet |
| NPC shop | buy/sell frames (LANE-A's `TradeCmdVital` family) | Open an NPC shop, buy/sell an item | `GT-230` OPEN (attended capture item, chief `20260904_0835`). Blocked on LANE-DB money/inventory interface (`20260904_0715`, queued behind all 5 PLAYER/CHARACTER pieces) | Wait on LANE-DB interface, then wire buy/sell | `GT-230` |
| Community/Party/Trade (8 classes) | friend/mail/party/trade vitals | Add friend, send mail, invite to party, propose trade | Layout resolved (`0400`/`1120` catalog), wiring CORE-REQUEST queued behind chief since 2026-09-04 (`0621`/`1120`) -- still 0 hits in `runtime.py`/`vital_walk.py` as of last check | Re-check `.CONSUMED.txt` for these two letters each round; write `ui_*.py` the round either lands | none yet |
| Options apply | settings vitals | Change a setting, see it take effect | RE ticket open, needs dynamic capture | wait for capture slot | none yet |
| Black market / ship survey window | 2 classes, fields incomplete | Open black-market or ship-survey UI | RE ticket open (`1137`), needs dynamic capture; fields incomplete even for static | wait for capture slot | none yet |
| Stall / Guild Storage | `Stall_*`/`GuildStorage_*` | Open personal stall / guild storage | Fields incomplete, needs more static RE (`RE-261` static-completeness measured `rp5tq1`) | continue field-by-field static RE | none yet |
| TreasureHunt (2 of 3 classes) | `TreasureHunt_StartExcavatingVital` `0xE40B` / `TreasureHunt_ExcavatingResultVital` `0xF33F` -- direction and caller/verb both `[UNKNOWN]`: `external/PF_FIELD_VALIDATION.tsv` rows for both classes read `status=NOT_OBSERVED`, `observed_frames=0` in both `W` and `R`, so nothing below claims which side sends which class or that either is an ack of the other -- that would be an unlabeled guess by analogy to the (separately, actually proven) `LogoutVital` ack pattern above, which this row does not make (pf-adversary D1, round `fzwt82`) | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_treasurehunt_wire.py` encodes/decodes both classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv:6341-6360` (all ten rows fully tagged, no `CALL_UNCLASSIFIED`, `W`/`R` rows identical) -- 9 tests (`tests/test_ui_treasurehunt_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `TreasureHunt_UpdateSceneTreasurePointVital` (`0x6D75`, the group's third class) is explicitly NOT covered: its rows mix real tags with ten `CALL_UNCLASSIFIED`/`PE_IMPORT_*` entries per direction. No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- this is the same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the eight `CORE-REQUEST 1120` classes, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; `0x6D75`'s `CALL_UNCLASSIFIED` rows separately need static RE before that class can join this row | none yet |
| Gathering (2 of 3 classes) | `Gathering_StartGatheringVital` `0xAFF7` / `Gathering_GatheringResultVital` `0xBD8E` -- direction and caller/verb both `[UNKNOWN]`: `external/PF_FIELD_VALIDATION.tsv` rows for both classes read `status=NOT_OBSERVED`, `observed_frames=0` in both `W` and `R`, same as the `TreasureHunt` row above, so nothing below claims which side sends which class or that either acks the other | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_gathering_wire.py` encodes/decodes both classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv:4315-4322` (`StartGathering`) and `:4323-4334` (`GatheringResult`) -- all rows fully tagged, no `CALL_UNCLASSIFIED`, `W`/`R` rows identical -- 9 tests (`tests/test_ui_gathering_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `Gathering_UpdateSceneGatheringPointVital` (`0x4966`, the group's third class) is explicitly NOT covered: its rows mix real tags with unresolved entries per direction (14 rows total, 10 `CALL_UNCLASSIFIED`/`PE_IMPORT_*`/atomic-helper entries and 4 real `0x12` tags). No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the sibling classes above, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; `0x4966`'s `CALL_UNCLASSIFIED` rows separately need static RE before that class can join this row | none yet |
| Winemaking (3 of 5 classes) | `Winemaking_LearnFomulaVital` `0x972E` / `Winemaking_StartWinemakingVital` `0xC8EB` / `Winemaking_FinishWinemakingVital` `0xD4D1` -- direction and caller/verb all `[UNKNOWN]`: `external/PF_FIELD_VALIDATION.tsv` rows for all three classes read `status=NOT_OBSERVED`, `observed_frames=0` in both `W` and `R`, same as the `TreasureHunt`/`Gathering` rows above, so nothing below claims which side sends which class or that any acks another | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_winemaking_wire.py` encodes/decodes all three classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv:4577-4580` (`LearnFomula`), `:4545-4552` (`StartWinemaking`), `:4553-4562` (`FinishWinemaking`) -- all rows fully tagged, no `CALL_UNCLASSIFIED`, `W`/`R` rows identical -- 15 tests (`tests/test_ui_winemaking_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `Winemaking_UpdateLearnedFormulaVital` (`0x0AEA`) and `Winemaking_UpdateWindPotSlotVital` (`0xE16E`), the group's other two classes, are explicitly NOT covered: their rows mix real tags with `CALL_UNCLASSIFIED`/`PE_IMPORT_INVALID_PARAMETER_NOINFO_CALL`/atomic-helper entries per direction, independently confirmed unproven in `pf_bridge/notes_to_chief/reference_codex_attr/PF_PROTOCOL_PRIORITY.md:113-114`. No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the sibling classes above, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; the two excluded classes' `CALL_UNCLASSIFIED` rows separately need static RE before they can join this row | none yet |
| BuildingCrystal (11 of 13 classes) | `BuildingCrystal_PurchaseServiceVital` `0x0D27` / `OpenCrystalSlotVital` `0x0ED3` / `IncreaseCrystalSlotMaxNutrientVital` `0x1C37` / `AddCrystalLusterVital` `0x1D0C` / `SpeedUpBuildCrystalVital` `0x4942` / `InsertCrystalToSlotVital` `0x4D86` / `ExtractCrystalFailedVital` `0x59AB` / `ExtractCrystalFromSlotVital` `0x80A0` / `ExtractCrystalSucceededVital` `0x8E98` / `AddNutrientToCrystalSlotVital` `0xA3CD` / `DoAbsorbingVital` `0xD339` -- direction and caller/verb all `[UNKNOWN]`: `external/PF_FIELD_VALIDATION.tsv` rows for all 11 classes read `status=NOT_OBSERVED`, `observed_frames=0` in both `W` and `R`, same as the `TreasureHunt`/`Gathering`/`Winemaking` rows above, so nothing below claims which side sends which class or that any acks another | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_buildingcrystal_wire.py` encodes/decodes all 11 classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv` (`:4085-4092`, `:4093-4102`, `:4103-4110`, `:4111-4120`, `:4121-4126`, `:4127-4136`, `:4137-4138`, `:4139-4146`, `:4147-4150`, `:4151-4154`, `:4155-4162`) -- all rows fully tagged, no `CALL_UNCLASSIFIED`, `W`/`R` rows identical -- 46 tests (`tests/test_ui_buildingcrystal_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `BuildingCrystal_UpdateCrystalSlotVital` (`0x2D5C`, `:4073-4084`) and `BuildingCrystal_UpdateNextAbsorbTime` (`:4163-4164`), the group's other two classes, are explicitly NOT covered: the first's rows mix real tags with `CALL_UNCLASSIFIED`/`DYNAMIC_INTERLOCKED_DECREMENT_ECX_PLUS_0C_VTABLE_PLUS_04`/`ATOMIC_INTERLOCKED_INCREMENT_ECX_PLUS_0C` entries per direction; the second has no vital id at all in `VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (not a real client-facing action) even though its own field row is fully tagged. No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the sibling classes above, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; `0x2D5C`'s `CALL_UNCLASSIFIED` rows separately need static RE before that class can join this row | none yet |
| Channel_ chat (10 of 17 classes; 5 owned by a sibling module, 2 deferred to LANE-CS) | `Channel_ForbidTalkNotificationVtial` `0xFDF2` / `Channel_WhisperVital` `0x556C` / `Channel_CustomChannelMessageVital` `0xE064` / `Channel_OriginalSinChannelMessageVital` `0x265C` / `Channel_JoinCustomChannelVital` `0xBA58` / `Channel_LeaveCustomChannelVital` `0xC663` / `Channel_OnActorJoinCustomChannelVital` `0x18DA` / `Channel_OnActorLeaveCustomChannelVital` `0x2770` / `Channel_JoinOriginalSinChannelVital` `0xFA07` / `Channel_LocalPerformanceVital` `0xAE8C` -- all `[UNKNOWN]` caller/verb semantics, `external/PF_FIELD_VALIDATION.tsv` reads `status=NOT_OBSERVED`, `observed_frames=0` for both `W`/`R` on every one of these ten (unlike `Channel_LocalTalkMessageVital`, which is separately `VALIDATED` with real captured frames -- that class is NOT this row's, see below) | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_channel_wire.py` encodes/decodes all ten classes field-for-field from `reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md`'s byte-exact static table (lines 63-76) -- deliberately NOT from `external/PF_SERIALIZER_FIELDS.tsv`'s own `UNTAGGED_WSTRING16LE_LEN32LE` label for these same fields, which that report proves is coarser than reality (every wstring here actually carries a leading tag byte `0x48`, confirmed by disassembly of the wire codec at `0x89A810`/`0x89A880`) -- 36 tests (`tests/test_ui_channel_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green (`pf-adversary` this round: found the 10th class, `ForbidTalkNotification`, missing from an earlier draft that only accounted for 9 of 17, plus two missing trailing-bytes test cases -- both fixed same round, no second adversary call needed, wording/coverage-only fix). Five classes sharing serializer `0x65AD40` (`LocalTalk`/`Party`/`Guild`/`ActorBoardcast`/`GMGlobal`) are explicitly OUT of scope here -- a sibling module in this same package already owns them under its own ownership-gate test (ids/codec not duplicated; grepped and confirmed no collision). Two more (`Channel_JoinClassChannelVital`/`Channel_ClassChannelMessageVital`) are also explicitly OUT of scope: only the first is a sourced LANE-CS grep-hint in `prompts/COMMON_LANE_ROUND.md`, the second is this round's own judgment call to keep the pair together (flagged as such, not presented as a second citation). No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- same "receive frame (decode) + compose the same shape back (encode), no business logic" scope as the sibling wire modules above. | none yet |
| Activity (7 of 12 classes; 1 owned by LANE-GM, 4 excluded) | `Activity_NewActivityVital` `0x858C` / `Activity_ActivityStateChangedVital` `0xEE8D` / `Activity_ActorJoinActivityVital` `0xCA78` / `Activity_ActorLeaveActivityVital` `0xD6CA` / `Activity_UpdateActivityPointVital` `0xE5C9` / `ActorActivity_ClientReportActivityResultVital` `0xAA3F` / `ActorActivity_ResetDailyActivityResultVital` `0x83B1` -- all `[UNKNOWN]` caller/verb semantics (`proven_semantics` = `UNKNOWN` for every row in `external/PF_SERIALIZER_FIELDS.tsv`) | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_activity_wire.py` encodes/decodes all seven classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv` (grep `^Activity_\|^ActorActivity_`); vital ids come from `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (grep `Activity_`), the id-on-the-wire source per item 1 above, not the serializer table (no id column there) -- all rows fully tagged (`0x0B`=u8, `0x0F`/`0x12`=u16, `0x14`/`0x26`=u32, the last confirmed by `external/PF_TAG_CENSUS.tsv` row `0x26 len=4 FIXED`), no `CALL_UNCLASSIFIED`, `W`/`R` rows identical -- 29 tests + 14 subtests (`tests/test_ui_activity_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `Activity_CheatCodeVital` (`0x6CEC`), the group's other fully-tagged class, is explicitly NOT covered here -- already owned by LANE-GM (`src/pirateforce_foundation/gm/activity_cheat_code_wire.py`). `Activity_BasicVital`/`Activity_ActorCommandVital` (registry rows `UNKNOWN(registry_serializer_unresolved:getter_hits=0)`, no tag), `Activity_SendRankingVital` (`CALL_UNCLASSIFIED`/`PE_IMPORT_*`/atomic-increment entries mixed with real tags), and `ActorActivity_UpdateDailyActivityStateVital` (single row is `JUMP_UNCLASSIFIED:INDIRECT(...)`, no proven serializer at all) are excluded -- same exclusion policy as the sibling rows above. No caller/verb semantics proven for any field -- same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the sibling wire modules above, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; the four excluded classes separately need static RE before they can join this row | none yet |
| Pets (10 of 16 classes; 6 excluded) | `Pets_SummonPetVital` `0x4CEC` / `Pets_UnsummonPetVital` `0x5E3C` / `Pets_UpdatePetPropertyVital` `0x9B50` / `Pets_RestorePetAmityVital` `0x83B5` / `Pets_NotifySailorDeadVital` `0x8B12` / `Pets_MergePetsVital` `0x4C4D` / `Pets_MergePetsResultVital` `0x845C` / `Pets_ClaimPetsMegringItemVital` `0xB96F` / `Pets_LearnPetSkillVital` `0x6E55` / `Pets_UpdateSummonPetsTimeOutVital` `0xE28A` -- all `[UNKNOWN]` caller/verb semantics, same as every sibling row above | -- (server side only so far; no client-visible claim) | **HEADLESS-DONE, pure wire shape only**: `ui_pets_wire.py` encodes/decodes all ten classes field-for-field from `external/PF_SERIALIZER_FIELDS.tsv` (grep `^Pets_`); vital ids come from `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (grep `Pets_`), the id-on-the-wire source per item 1 above -- all rows fully tagged (`0x0B`=u8, `0x0F`=u16, `0x14`=u32, `0x32`=u64), no `CALL_UNCLASSIFIED`, `W`/`R` rows identical -- 41 tests (`tests/test_ui_pets_wire.py`), round-trip + fail-closed (truncated/wrong-tag/trailing-bytes) all green. `Pets_MergePetsVital`'s 3rd/4th fields carry a `PHI(...)` `field_offset` (client-object address is a compiler-level merge of two call-site locations) instead of a plain `+0xNN` -- does not affect the wire shape, which is tag+len in `order` sequence only (see module docstring). `Pets_ChangePetEquipmentVital` (`0xA466`), `Pets_SetPetAIVital` (`0x4115`), `Pets_SetPetSkillVital` (`0x5C79`), `Pets_UpdateLearnedPetSkillVital` (`0xC574`), `Pets_UpdatePetsDataVital` (`0x76B9`), and `Pets_UpdatePetsMegringDataVital` (`0xC45C`), the group's other six classes, are explicitly NOT covered: each mixes real tags with `CALL_UNCLASSIFIED`/`PE_IMPORT_*` entries per direction. No caller/verb semantics proven for any field (`proven_semantics` = `UNKNOWN` throughout) -- same "รับเฟรม (decode) + ตอบ ack ที่วางเปล่า" scope as the sibling wire modules above, not business logic. | An attended capture (not a `CORE-REQUEST` hookup yet) is needed first to settle direction/verb before any dispatch wiring is proposed; the six excluded classes separately need static RE before they can join this row | none yet |
| everything else in item 1's 15 non-core groups not listed above (Equipment_/Express_/CollectionObj_/KnowledgeGuru_/HitParade_/NavigationEx_/UserSetting/Dyeing/Appraisal/Vehicle/Potion/Relive/ItemLock) | -- | -- | **NOT YET ITEMIZED** -- this table currently covers the rows this lane's rounds have actually touched (per the catalog letters `20260904_0400`/`0453`/`1159`/`1244`). Each future round expands only the row(s) it works on; do not re-derive all 327 rows in one sitting. | pick the next `LAYOUT-KNOWN` row from `external/PF_SERIALIZER_FIELDS.tsv` when the queue above is blocked | -- |

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
- The `TreasureHunt` row's "HEADLESS-DONE" is a wire-shape claim only (pure
  encode/decode functions, checked against the registry's own field rows) --
  it does not claim a live capture confirms these shapes against a real
  client frame, and it does not claim any field's meaning, or which side
  (client/server) sends either class, or that either class acks the other
  (`PF_FIELD_VALIDATION.tsv` shows `NOT_OBSERVED`/zero frames for both).
- The `Gathering` row's "HEADLESS-DONE" carries the identical nonclaim as
  the `TreasureHunt` row immediately above, for the same reason
  (`PF_FIELD_VALIDATION.tsv` shows `NOT_OBSERVED`/zero frames for both
  `Gathering_StartGatheringVital` and `Gathering_GatheringResultVital`).
- The `Winemaking` row's "HEADLESS-DONE" carries the identical nonclaim as
  the `TreasureHunt`/`Gathering` rows above, for the same reason
  (`PF_FIELD_VALIDATION.tsv` shows `NOT_OBSERVED`/zero frames for
  `Winemaking_LearnFomulaVital`, `Winemaking_StartWinemakingVital`, and
  `Winemaking_FinishWinemakingVital`).
- The `BuildingCrystal` row's "HEADLESS-DONE" carries the identical nonclaim
  as the `TreasureHunt`/`Gathering`/`Winemaking` rows above, for the same
  reason (`PF_FIELD_VALIDATION.tsv` shows `NOT_OBSERVED`/zero frames for all
  11 of `BuildingCrystal_PurchaseServiceVital`, `OpenCrystalSlotVital`,
  `IncreaseCrystalSlotMaxNutrientVital`, `AddCrystalLusterVital`,
  `SpeedUpBuildCrystalVital`, `InsertCrystalToSlotVital`,
  `ExtractCrystalFailedVital`, `ExtractCrystalFromSlotVital`,
  `ExtractCrystalSucceededVital`, `AddNutrientToCrystalSlotVital`, and
  `DoAbsorbingVital`).
- The `Channel_` chat row's "HEADLESS-DONE" is a wire-shape claim only, and
  unlike the `TreasureHunt`/`Gathering`/`Winemaking`/`BuildingCrystal` rows
  above it is sourced from a byte-exact STATIC disassembly report (grade A,
  reproducible spans/hashes), not from `PF_SERIALIZER_FIELDS.tsv` directly --
  it does not claim any of these ten classes has ever been seen on the wire
  in a live capture (`PF_FIELD_VALIDATION.tsv`: `NOT_OBSERVED`/zero frames
  for all ten, both directions), does not claim which side sends which
  class or what any field means, and does not claim the report's static
  grade extends to the two classes deferred to LANE-CS or the five owned by
  the sibling shared-serializer module (neither touched by this row's code).
- The `Pets` row's "HEADLESS-DONE" carries the identical nonclaim as the
  `TreasureHunt`/`Gathering`/`Winemaking`/`BuildingCrystal`/`Activity` rows
  above, for the same reason (`PF_FIELD_VALIDATION.tsv` shows
  `NOT_OBSERVED`/zero frames for all ten of `Pets_SummonPetVital`,
  `Pets_UnsummonPetVital`, `Pets_UpdatePetPropertyVital`,
  `Pets_RestorePetAmityVital`, `Pets_NotifySailorDeadVital`,
  `Pets_MergePetsVital`, `Pets_MergePetsResultVital`,
  `Pets_ClaimPetsMegringItemVital`, `Pets_LearnPetSkillVital`, and
  `Pets_UpdateSummonPetsTimeOutVital`, both directions). It additionally
  does not claim that `Pets_MergePetsVital`'s `PHI(...)` `field_offset`
  ambiguity has been resolved to a single client-memory address -- only
  that the ambiguity is irrelevant to this module's scope (wire tag/order/
  length, not client-object layout).
