# LUA_HOST_API_MAP

Per `notes_to_chief/20260906_1704_KA1A-PANYA-DECISION...md` (PANYA, relayed by ka1-A) and `20260906_1745_COO-DECISION...md`: every host-API function the 616-file corpus (`gamedata/lua/`) calls, mapped to the server system it implies, so COO can rank which system to build next. **No code changed this round** -- read-only research. Full 160-row machine table: `LUA_HOST_API_MAP.tsv` (11 cols: fn/namespace/call_count/files/hook_side/args_returns/system/status/system_exists/blocker/milestone).

## Count: 160, not 152
Official count = this lane's own census (`gamedata/pf_lua_api_census.py` -> `api_spec.tsv`), re-run fresh this round: **160 names / 12,653 call sites / 8 namespaces**, byte-identical to the 2026-08-24 baseline. ka1-A's letter's 152 (regex over 6 namespaces: Player 73, Quest 34, Trigger 18, Mob 10, Instance 9, Scene 8) both **omits Guild(8)+Party(11)=19 entirely** and **over-counts Quest/Trigger/Scene by 11** (34/18/8 vs the measured 25/17/7) -- net -8, coincidentally close to 160 for unrelated reasons. This map uses 160 throughout.

## hook_side correction (measured this round from the corpus, not assumed)
The letter assumed `Mob.ShowAnimation`(499)/`Quest.PlayNPCMovie`(100)/`Quest.PlayNPCVoice`(4) are UI-only ("found only in OpenAcceptUI_Run/OpenReportUI_Run"). Measured by finding each call site's enclosing top-level Lua function across all 616 files: only **`Quest.PlayNPCMovie` (100 calls) is actually UI-only**. `Mob.ShowAnimation` (716 calls, official count) and `Quest.PlayNPCVoice` (8 calls, official count) are **BOTH** -- both also called from `Accept_Run`/`Report_Run` (AUTH phase), e.g. `gamedata/lua/Quest/q_con_new.lua:218,367` calls `Quest.PlayNPCVoice` from inside `OpenReportUI_Run` AND `Report_Run`. Per spec item 6, UI-only names are no-op+log and not counted as backlog; **BOTH names still are** (they run during AUTH resolution too, even though their visible effect is a client animation/voice line).

## Systems ranked by total call_count -- what COO uses to rank milestones

| system | fn | total calls | system_exists | size | why |
|---|---:|---:|---|---|---|
| inventory | 15 | 3537 | PARTIAL | L | item/equip grant+read seam; inventory.py/store.py exist but nothing wired to Lua |
| spawn | 1 | 3532 | NO | L | 1 fn, 3532 calls, top gap; LANE-A confirms no add-mob-to-live-scene fn exists |
| flag-quest-state | 12 | 1502 | NO | L | needs new per-char quest-state table; blocks 24 Quest.*+2 Trigger.* names |
| movie-ui (client-only) | 3 | 824 | NO | S | no-op+log enough for the true UI-only case (see hook_side correction) |
| exp-level | 11 | 609 | PARTIAL/YES | M | read side real (GetLv/GetClass); needs a bounded grant/write seam |
| trigger-status | 6 | 543 | NO/YES | S | 5/6 real; GetContactMode blocked only on an RE ticket |
| buff | 5 | 495 | NO | M | new buff-state subsystem (apply/remove/check/duration), nothing exists yet |
| scene-placement | 7 | 442 | PARTIAL | M | LANE-A territory; registry exists, not wired to Lua, cross-lane |
| cash | 4 | 236 | PARTIAL | S | already a persisted typed attribute; only grant/spend seam missing |
| message-wire | 7 | 183 | NO | M | one generic open-UI/movie/message wire type would serve all 7 |
| other:vfx-wire | 3 | 119 | NO | S | small self-contained effect/animation wire encoders |
| instance | 14 | 108 | PARTIAL/YES | M | registry mostly real (9/9); dungeon world-entry frame cross-lane w/ A, missing |
| combat-skill | 7 | 105 | PARTIAL | L | full skill-cast wire + damage resolution, cross-lane w/ B/CS, blocks M4 |
| teleport-warp | 8 | 84 | PARTIAL | M | M2 island-arrival proves the frame once; generalizing is bounded |
| timer | 2 | 63 | NO/YES | S | CheckOpenTime real; CountDownTime needs one narrow timer column |
| other:mob-lifecycle | 7 | 59 | PARTIAL | M | mob_ai_control.py/mob_combat.py exist; Lua wiring is bounded |
| guild | 12 | 56 | NO | L | entirely unbuilt subsystem, cross-lane w/ LANE-GUILD |
| other:calendar-enum | 1 | 48 | NO | S | blocked purely on an RE ticket, not engineering |
| other:moralized-grant | 2 | 35 | NO | S | one narrow new stat |
| party | 7 | 16 | NO | M | party-state subsystem unbuilt, low call volume |
| ship | 6 | 16 | NO | M | boat/vehicle subsystem unbuilt, low call volume |
| other:music | 1 | 8 | NO | S | cosmetic, self-contained |
| other:player-identity | 1 | 7 | PARTIAL | S | narrow read seam |
| store | 4 | 6 | PARTIAL | S | store.py exists; needs only a Lua-facing open-store seam |
| other:achievement | 1 | 4 | NO | S | narrow read seam |
| other:player-vitals-read | 4 | 4 | PARTIAL | S | persistence_vitals.py exists; needs Lua-facing read seam |
| other:pvp-arena-signup | 2 | 3 | NO | S | narrow, low call volume |
| other:camera-fx | 1 | 2 | NO | S | cosmetic, self-contained |
| other:penpal-letter | 1 | 2 | NO | S | narrow read seam |
| other:player-vitals-grant | 2 | 2 | NO | S | narrow, a combat-heal seam more than a new subsystem |
| storage | 2 | 2 | NO | S | narrow, low call volume |
| other:unclear-name | 1 | 1 | NO | S | 1 call site, name may be a typo (SurveyOwner?) |

## Per-system detail
fn(call_count) per system, sorted high->low. blocker/system_exists/milestone: see TSV (per-fn, not repeated here).

### `inventory` -- 0/15 real
Player.AddItem(1430), Quest.RewardItemSelect(1335), Player.RemoveItem(367), Player.CheckItemNum(211), Player.GetItemNum(99), Player.AddAndEquip(48), Player.CheckEquipItem(14), Player.CheckCollect(11), Player.DropProcess(9), Player.ItemAddon(6), Party.CheckPartyItem(2), Party.RemovePartyItem(2), Player.AppraiseCollectPiece(1), Player.AppraiseItem(1), Player.CheckAllCollectItemSynthesisBuff(1)

### `spawn` -- 0/1 real
Player.MobAppear(3532)

### `flag-quest-state` -- 0/12 real
Quest.GetQuestFlag(508), Quest.SetFlag(417), Quest.CheckMobKillCount(138), Quest.MobKillCount(128), Quest.SetQuestFlag(90), Quest.GetFlag(67), Quest.CanReportDailyQuest(61), Quest.ReportDailyQuest(61), Quest.GetMobKillCount(20), Trigger.QuestActiveProgress(8), Trigger.QuestFinishProgress(3), Quest.CheckWishQuest(1)

### `movie-ui (client-only)` -- 0/3 real
Mob.ShowAnimation(716), Quest.PlayNPCMovie(100), Quest.PlayNPCVoice(8)

### `exp-level` -- 2/11 real
Quest.AddCriteriaExp(166), Quest.AddCriteriaSkillPoint(166), Player.GetLv(91), Player.GetClass(60), Quest.AddLvCriteriaExp(59), Quest.AddLvCriteriaSkillPoint(59), Player.AddExp(2), Player.AddPpClass(2), Player.AddSkillPoint(2), Player.GetPpClass(1), Player.GiveLvCriteriaPercentageEXP(1)

### `trigger-status` -- 5/6 real
Trigger.NextStatus(353), Trigger.GetTriggerStatus(134), Trigger.SetTriggerStatus(52), Trigger.SetStatus(2), Trigger.GetContactMode(1), Trigger.GetTeiggerStatus(1)

### `buff` -- 0/5 real
Mob.AddBuff(411), Player.CheckBuff(47), Player.AddBuff(32), Mob.CheckMobbuff(3), Player.RemoveBuff(2)

### `scene-placement` -- 0/7 real
Scene.PlacementOFF(173), Scene.PlacementON(96), Scene.CheckPlacementAlive(65), Trigger.HideModel(62), Scene.PlacementCancel(32), Trigger.HideTriggerModel(13), Scene.CheckPlacementCombat(1)

### `cash` -- 0/4 real
Quest.AddCriteriaCash(165), Quest.AddLvCriteriaCash(58), Player.GetCash(7), Player.AddCash(6)

### `message-wire` -- 0/7 real
Player.ShowMessage(61), Trigger.TriggerShowMessage(55), Player.OpenUI(31), Player.OpenHelpUI(26), Player.PlayMovie(7), Party.PlayMovie(2), Party.ShowMessage(1)

### `other:vfx-wire` -- 0/3 real
Trigger.PlayFx(57), Trigger.StartTriggerAnimation(43), Trigger.StartAnimation(19)

### `instance` -- 9/14 real
Player.EnterInstance(32), Instance.AddKeyEvent(15), Instance.GetInstanceID(14), Instance.CallScoreCount(12), Instance.GetLastingTime(7), Player.EnterInstanceThenPlayMovie(6), Player.LoadInstanceGroup(6), Party.EnterInstance(5), Player.LeaveInstance(4), Instance.AddBonusPoint(2), Instance.RemoveKeyEvent(2), Instance.AddBonusReward(1), Instance.GetInstanceId(1), Instance.SetLastingTime(1)

### `combat-skill` -- 0/7 real
Player.CastSkillAt(69), Trigger.CastSkillXYZ(11), Trigger.CastSkill(9), Player.CheckSkill(6), Trigger.CastSkillBy(5), Party.CastSkillAt(3), Player.CastSkillXYZ(2)

### `teleport-warp` -- 0/8 real
Player.Teleport(35), Player.CameraFocus(16), Player.Warp(10), Player.TeleportThenPlayMovie(8), Player.ResetMarker(7), Player.TeleportWithVehicle(6), Player.TeleportCheck(1), Player.WarpNearestMarker(1)

### `timer` -- 1/2 real
Quest.CountDownTime(54), Quest.CheckOpenTime(9)

### `other:mob-lifecycle` -- 0/7 real
Mob.CallMob(15), Mob.EndMove(15), Mob.CheckApproachTarget(8), Mob.StartMove(8), Mob.CheckMobPosition(6), Mob.CheckMobalive(6), Mob.CheckMobAlive(1)

### `guild` -- 0/12 real
Guild.GetGuildLevel(15), Player.CheckGuild(15), Guild.CheckPlayerGuildJob(7), Guild.AddMeritExp(6), Guild.GetPVPFaction(4), Guild.CheckMeritExp(2), Player.GetGuildRank(2), Guild.GiveDailySalary(1), Guild.SetPVPFaction(1), Quest.CheckGuildOfflineQuest(1), Quest.ReportGuildOfflineQuest(1), Quest.StartGuildOfflineQuest(1)

### `other:calendar-enum` -- 0/1 real
Quest.GetWeekDay(48)

### `other:moralized-grant` -- 0/2 real
Player.Addmoralized(21), Player.CheckMoralized(14)

### `party` -- 0/7 real
Player.CheckPartyLeader(4), Player.CheckSoulmate(4), Party.GetNum(2), Party.Love(2), Player.CheckParty(2), Party.CheckSoulmate(1), Party.PartySoul(1)

### `ship` -- 0/6 real
Player.OutVehicle(11), Player.BoatHealth(1), Player.ChangeShip(1), Player.EnableGlide(1), Player.GetBoatHealth(1), Player.HasAnySailorBeenSummoned(1)

### `other:music` -- 0/1 real
Scene.ChangeMainMusic(8)

### `other:player-identity` -- 0/1 real
Player.CheckGender(7)

### `store` -- 0/4 real
Player.LoadStore(3), Player.LoadConditionStore(1), Player.LoadItemExchangeStore(1), Player.LoadSmithStore(1)

### `other:achievement` -- 0/1 real
Player.CheckAchievement(4)

### `other:player-vitals-read` -- 0/4 real
Player.GetCurrentHP(1), Player.GetCurrentST(1), Player.GetMaxHP(1), Player.GetMaxST(1)

### `other:pvp-arena-signup` -- 0/2 real
Party.SignUpArena(2), Player.BookBattleField(1)

### `other:camera-fx` -- 0/1 real
Scene.CamaraShake(2)

### `other:penpal-letter` -- 0/1 real
Player.CheckThrowAnyPenpalLetter(2)

### `other:player-vitals-grant` -- 0/2 real
Player.AddHP(1), Player.AddST(1)

### `storage` -- 0/2 real
Guild.OpenGuildStorage(1), Player.OpenStorage(1)

### `other:unclear-name` -- 0/1 real
Player.SuveryOwner(1)

## Nonclaims
- **Called != implemented, on either side.** `gamedata/PF_LUA_API_SPEC.md`'s own nonclaims (RE-057): `Scene.PlacementOFF`/`PlacementON`/`PlacementCancel` bind to a client no-op in the shipped build. This map's `system_exists` judges OUR server, not the client -- unrelated facts, do not conflate.
- **`status`/`system_exists` measured from `script_host.py` + `lua_api/*` this round** (REAL_METHODS: trigger.py:309, instance.py:381, quest.py:233, player.py:83); Mob/Scene/Guild/Party have no dedicated module at all, fall to the generic `ApiNamespaceStub` (`script_host.py:270`) -- 0/36 real.
- **No name is MISSING** (the letter's third status value): every one of 160 names dispatches through either a real handler or the generic stub, so nothing is unreachable/undefined; MISSING is unused in the TSV.
- **`system`/`milestone` columns are this round's own judgment call**, grounded in `STILL_STUBBED` blocker text (Player/Trigger/Quest) and a repo grep for existing modules (Instance/Mob/Scene/Guild/Party had no such text to quote) -- not Panya's decision, COO should treat these as a starting proposal, not a ruling.
- **No production code, tests, or `docs/SCRIPT_LANE.md` touched this round** per the letter's own instruction.

