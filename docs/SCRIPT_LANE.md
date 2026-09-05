# SCRIPT_LANE -- LANE-Q (Lua quest/trigger scripts on this server)

Charter: `prompts/LANE-Q.md` (pf_bridge, owner Panya).  Mission: make the
game's own 616 shipped `.lua` files (`pf_bridge/gamedata/lua/`, 306 `q_*`
quests + 309 `t_*` triggers) run against this server through a real
implementation of the 160-name API surface they call
(`pf_bridge/gamedata/PF_LUA_API_SPEC.md`), instead of a Python
reimplementation of quest logic that already exists as Lua.

This file is the status table + design record every round updates.  It
does not repeat the charter's own numbers (see `PF_LUA_API_SPEC.md`); it
tracks what THIS repository has built against them.

## Round s2fxf6 (2026-09-05) -- spike, charter item 1

**Deliverable, per charter**: embed Lua in Python, load `t_nex_t6.lua` and
`Quest/q_kill5.lua` with all 160 API names stubbed, run their entry points
headless to completion with no error, and prove the loader can load all
616 shipped files.  All four done; see "Spike results" below.

### What was built

- `src/pirateforce_foundation/lua_api/api_spec.tsv` -- a frozen, ASCII-only,
  five-column vendor copy of `pf_bridge/gamedata/PF_GAMEDATA_LUA_API.tsv`
  (namespace, method, call_count, file_count, arity_min, arity_max; the
  RE-provenance columns -- `binding_status`/`delegate_va`/`registration_va`
  -- are the bridge repository's business, not vendored).  160 rows, one
  per API name, taken 2026-09-05.  This is what lets every test in this
  repository know the API surface's exact shape with no sibling checkout.
- `src/pirateforce_foundation/lua_api/spec.py` -- parses that TSV into
  `API_FUNCTIONS` / `NAMESPACE_METHODS` / `BY_QUALIFIED_NAME`.
- `src/pirateforce_foundation/script_host.py` -- the sandboxed Lua host:
  - `ScriptHost`: one `lupa.LuaRuntime` per loaded script (see the file's
    own docstring for why one-per-script, not one shared runtime), with
    all 8 namespace tables (`Player`/`Quest`/`Trigger`/`Party`/`Mob`/
    `Instance`/`Guild`/`Scene`) wired as `ApiNamespaceStub` objects and
    `io`/`os`/`require`/`load`/`loadstring`/`loadfile`/`dofile`/`package`/
    `debug`/`collectgarbage`/`python` wired to `nil`, plus
    `register_eval=False, register_builtins=False` on the runtime itself.
  - **The escape this spike nearly shipped with, measured and closed.**
    lupa injects a `python` table into every Lua state it builds, and with
    its default constructor flags that table carries `python.eval` and
    `python.builtins` outright - any of the 616 game scripts could have
    called straight out of the sandbox.  Turning both flags off nils
    `eval`/`builtins`/`globals`/`import_module` (measured) but leaves
    `python.as_attrgetter`, which flips Lua indexing on a wrapped Python
    object from `__getitem__` to `getattr` - and the API namespaces handed
    to the scripts ARE live Python objects, so
    `python.as_attrgetter(Quest).__class__` would have been step one of
    the ordinary `__class__`/`__bases__`/`__subclasses__` walk back to the
    interpreter.  `python` is therefore blanked outright as well, and the
    flags are kept anyway so two independent things have to fail before a
    script gets out.  Three regressions in
    `test_script_host_spike.py::SandboxActuallyBlocksTheBannedGlobalsTests`
    assert the walk actually dies, not merely that the flags were passed.
  - `ApiNamespaceStub`: indexing a name that IS one of that namespace's
    real API methods returns a callable that logs
    `LUA_API_STUB <Namespace>.<Method>` and returns `STUB_DEFAULT` (`0`);
    indexing anything else (`Quest.Var1`, `Quest.StringVar2`,
    `Quest.RewardItem3`, `Quest.Active`, `Quest.Finish`, ...) returns
    `STUB_DEFAULT` silently -- those are per-instance script data fields
    the API census never counted as call surface, not something this lane
    implements.  Writing into a namespace table is accepted and discarded
    (verified by grep across all 616 files: every `Quest.VarN=` hit is
    inside a `--[[ ... ]]` comment documenting the field, never executable
    code -- no script assigns into a namespace table at runtime).
  - `load_script_file(path)`: reads a `.lua` file as bytes decoded
    `latin-1` (these scripts carry Traditional Chinese and Thai comments
    in a legacy Windows codepage that is not valid utf-8; Lua's parser
    only needs ASCII syntax bytes to round-trip, which latin-1 guarantees).
  - `load_corpus(root)`: walks `root` for `*.lua`, loads each into its own
    `ScriptHost`, and is fail-closed per the charter -- a script that fails
    to parse or raises while its top-level chunk runs is logged as
    `LUA_SCRIPT <relative path> ERR <message>` and recorded, never allowed
    to raise out of the loader.
- Tests (`tests/test_script_*.py`, see each file's own docstring):
  - `test_script_lua_api_spec.py` -- the vendored 160/8-namespace/12,653
    numbers match the charter's own count, byte-for-byte no re-derivation
    needed on any machine.
  - `test_script_host_spike.py` -- the two named charter fixtures
    (byte-for-byte vendored copies, verified `cmp`-identical at vendor time
    and re-checked every run by `test_script_lua_corpus.py`) run headless
    to completion; the sandbox actually blocks the banned globals (not
    merely "unused" -- a script that reaches into `os` gets a catchable Lua
    error); every one of the 160 names is individually reachable and logs
    its own stub line; `load_corpus`'s fail-closed catch is exercised
    against a synthetic broken script.  No sibling checkout needed.
  - `test_script_lua_corpus.py` -- loads the REAL 616 files from
    `../pf_bridge/gamedata/lua/`, guarded by the new `BRIDGE_LUA_SCRIPTS`
    precondition (`tests/pf_preconditions.py`) plus `LUPA_PACKAGE`; skips
    with a declared, pinned reason where either is absent (a fresh clone
    with no bridge sibling and no `lupa` installed), runs for real on the
    bridge and on any cloud round paired with a `pf_bridge` checkout.
- `tests/pf_preconditions.py`: added `BRIDGE_LUA_SCRIPTS` (a
  `Precondition`, the sibling corpus) and a new `OptionalPackage` class +
  `LUPA_PACKAGE` instance (this repository's first *interpreter*-shaped
  precondition, as opposed to a *clone*-shaped one -- see the class's own
  docstring for why `Precondition`'s path-existence check does not fit a
  missing pip package).  Both registered in `REGISTRY`.

### Spike results (measured 2026-09-05, this cloud session, sibling
`pf_bridge` present)

- `pip install lupa` succeeds on Linux (`lupa==2.8`, manylinux wheel);
  `python3 -c "import lupa"` and the full test suite above ran clean.
- **616/616 files visited, 611 loaded clean, 5 failed closed** (caught,
  logged, loader continued -- none took the loop down):
  - `Quest/q_day_send_new.lua` -- real syntax error in the shipped source,
    line 137, `'then' expected near 'if'`.
  - `Quest/q_repeat_send_new.lua`, `Quest/q_send_new.lua` -- real syntax
    error, line 126, `')' expected near '='`.
  - `Quest/q_set_new.lua` -- real syntax error: an `if (...) then` chain
    (lines 115-122) is missing its `end` before the next `if`, so the
    parser runs off the end of the file looking for one it never finds.
    (The same family bug as `q_con_new.lua`'s *comment* block that
    documents these fields correctly -- the executable code in the sibling
    `*_new.lua` files is where the `end` went missing.)
  - `utility.lua` -- calls `os.time()` at its own top level (to seed
    `math.randomseed`), which the sandbox correctly blocks per the
    charter's own instruction ("sandbox: an script must never reach
    io/os/require/load").  This is the fail-closed behaviour working
    exactly as specified, not a defect in this host.  Follow-up for a
    later round, NOT done this round (scope discipline): give the host a
    narrow, safe clock/RNG-seed function instead of blocking `os` outright,
    so `utility.lua`'s one legitimate use case stops needing the sandbox
    widened wholesale.
  - These four-plus-one are pinned by name in
    `test_script_lua_corpus.py::KNOWN_LOAD_FAILURES` -- a new failure OR an
    old one silently disappearing both go red, per this project's
    "negative claims must be measured, both directions" house rule.
  - Also noted, not yet acted on: `Trigger.GetTeiggerStatus` (sic, one
    call site) is a literal typo of `Trigger.GetTriggerStatus` in one
    original script -- the census correctly treats it as its own distinct
    name because that is literally what that one script calls.  Whoever
    implements `Trigger.GetTriggerStatus` for real should decide then
    whether that one caller is worth aliasing or is dead/unreachable code
    in the original client too.
- **WINDOWS_WHEEL_UNVERIFIED** (per COO-DECISION 20260905_2055 item 1):
  PyPI publishes `lupa` wheels for Windows across every CPython series this
  project has touched, including the bridge's own -- checked against
  `https://pypi.org/pypi/lupa/2.8/json` 2026-09-05:
  `cp38`/`cp39`/`cp310`/`cp311`/`cp312`/`cp313` (`win32`+`win_amd64`, some
  also `win_arm64`) and `cp314`/`cp314t` (`win32`+`win_amd64`+`win_arm64`,
  matching `gate-windows.yml`'s pinned `3.14` series and
  `pf_diag_out.txt`'s bridge interpreter).  Not installed or run on an
  actual Windows machine by this round -- this is a PyPI catalog check, not
  a measurement on the bridge or the gate.  **`.github/workflows/
  gate-windows.yml` was deliberately NOT edited this round**: it is shared
  CI infrastructure outside LANE-Q's write zone (`prompts/LANE-Q.md`
  lists `src/pirateforce_foundation/script_*.py`, `lua_api/`,
  `tests/test_script_*`, `docs/SCRIPT_LANE.md`, `lane_hooks/lane_q_*`,
  `rounds/Q_*` -- not `.github/`), and a bad edit there would fail the
  Windows gate for all 8 lanes at once with nobody able to verify it from a
  cloud session.  Recommendation, sent to chief/COO
  (`notes_to_chief/`, this round's letter): add `lupa` to the
  `pip install --quiet pytest capstone pefile` line the same way
  `capstone`/`pefile` were added, ideally exercised once on the bridge
  first.  Every test that needs `lupa` skips cleanly with a declared,
  pinned reason (`LUPA_PACKAGE`) until that line lands, so nothing here is
  blocked on it landing.

### API status table (160/160, all stub this round)

Read from `src/pirateforce_foundation/lua_api/api_spec.tsv`; call_count is
the corpus-wide call-site count from the 2026-08-24 census
(`gamedata/PF_LUA_API_SPEC.md`).  Namespaces ordered Guild/Instance/Mob/
Party/Player/Quest/Scene/Trigger (alphabetical); within a namespace, most-
called first.  Status is one of `stub` (this file logs `LUA_API_STUB` and
returns a safe default -- every row today) / `real` (implemented against
the actual protocol, backed by a test) / `proven` (real + a GT ticket where
a tester watched it work on screen).  Next lane priority, per charter: the
17 `Trigger.*` rows unblock LANE-A's M2 ("leave town").

| namespace | method | call_count | status |
|---|---|---:|---|
| Guild | GetGuildLevel | 15 | stub |
| Guild | CheckPlayerGuildJob | 7 | stub |
| Guild | AddMeritExp | 6 | stub |
| Guild | GetPVPFaction | 4 | stub |
| Guild | CheckMeritExp | 2 | stub |
| Guild | GiveDailySalary | 1 | stub |
| Guild | OpenGuildStorage | 1 | stub |
| Guild | SetPVPFaction | 1 | stub |
| Instance | AddKeyEvent | 15 | stub |
| Instance | GetInstanceID | 14 | stub |
| Instance | CallScoreCount | 12 | stub |
| Instance | GetLastingTime | 7 | stub |
| Instance | AddBonusPoint | 2 | stub |
| Instance | RemoveKeyEvent | 2 | stub |
| Instance | AddBonusReward | 1 | stub |
| Instance | GetInstanceId | 1 | stub |
| Instance | SetLastingTime | 1 | stub |
| Mob | ShowAnimation | 716 | stub |
| Mob | AddBuff | 411 | stub |
| Mob | CallMob | 15 | stub |
| Mob | EndMove | 15 | stub |
| Mob | CheckApproachTarget | 8 | stub |
| Mob | StartMove | 8 | stub |
| Mob | CheckMobPosition | 6 | stub |
| Mob | CheckMobalive | 6 | stub |
| Mob | CheckMobbuff | 3 | stub |
| Mob | CheckMobAlive | 1 | stub |
| Party | EnterInstance | 5 | stub |
| Party | CastSkillAt | 3 | stub |
| Party | CheckPartyItem | 2 | stub |
| Party | GetNum | 2 | stub |
| Party | Love | 2 | stub |
| Party | PlayMovie | 2 | stub |
| Party | RemovePartyItem | 2 | stub |
| Party | SignUpArena | 2 | stub |
| Party | CheckSoulmate | 1 | stub |
| Party | PartySoul | 1 | stub |
| Party | ShowMessage | 1 | stub |
| Player | MobAppear | 3532 | stub |
| Player | AddItem | 1430 | stub |
| Player | RemoveItem | 367 | stub |
| Player | CheckItemNum | 211 | stub |
| Player | GetItemNum | 99 | stub |
| Player | GetLv | 91 | stub |
| Player | CastSkillAt | 69 | stub |
| Player | ShowMessage | 61 | stub |
| Player | GetClass | 60 | stub |
| Player | AddAndEquip | 48 | stub |
| Player | CheckBuff | 47 | stub |
| Player | Teleport | 35 | stub |
| Player | AddBuff | 32 | stub |
| Player | EnterInstance | 32 | stub |
| Player | OpenUI | 31 | stub |
| Player | OpenHelpUI | 26 | stub |
| Player | Addmoralized | 21 | stub |
| Player | CameraFocus | 16 | stub |
| Player | CheckGuild | 15 | stub |
| Player | CheckEquipItem | 14 | stub |
| Player | CheckMoralized | 14 | stub |
| Player | CheckCollect | 11 | stub |
| Player | OutVehicle | 11 | stub |
| Player | Warp | 10 | stub |
| Player | DropProcess | 9 | stub |
| Player | TeleportThenPlayMovie | 8 | stub |
| Player | CheckGender | 7 | stub |
| Player | GetCash | 7 | stub |
| Player | PlayMovie | 7 | stub |
| Player | ResetMarker | 7 | stub |
| Player | AddCash | 6 | stub |
| Player | CheckSkill | 6 | stub |
| Player | EnterInstanceThenPlayMovie | 6 | stub |
| Player | ItemAddon | 6 | stub |
| Player | LoadInstanceGroup | 6 | stub |
| Player | TeleportWithVehicle | 6 | stub |
| Player | CheckAchievement | 4 | stub |
| Player | CheckPartyLeader | 4 | stub |
| Player | CheckSoulmate | 4 | stub |
| Player | LeaveInstance | 4 | stub |
| Player | LoadStore | 3 | stub |
| Player | AddExp | 2 | stub |
| Player | AddPpClass | 2 | stub |
| Player | AddSkillPoint | 2 | stub |
| Player | CastSkillXYZ | 2 | stub |
| Player | CheckParty | 2 | stub |
| Player | CheckThrowAnyPenpalLetter | 2 | stub |
| Player | GetGuildRank | 2 | stub |
| Player | RemoveBuff | 2 | stub |
| Player | AddHP | 1 | stub |
| Player | AddST | 1 | stub |
| Player | AppraiseCollectPiece | 1 | stub |
| Player | AppraiseItem | 1 | stub |
| Player | BoatHealth | 1 | stub |
| Player | BookBattleField | 1 | stub |
| Player | ChangeShip | 1 | stub |
| Player | CheckAllCollectItemSynthesisBuff | 1 | stub |
| Player | EnableGlide | 1 | stub |
| Player | GetBoatHealth | 1 | stub |
| Player | GetCurrentHP | 1 | stub |
| Player | GetCurrentST | 1 | stub |
| Player | GetMaxHP | 1 | stub |
| Player | GetMaxST | 1 | stub |
| Player | GetPpClass | 1 | stub |
| Player | GiveLvCriteriaPercentageEXP | 1 | stub |
| Player | HasAnySailorBeenSummoned | 1 | stub |
| Player | LoadConditionStore | 1 | stub |
| Player | LoadItemExchangeStore | 1 | stub |
| Player | LoadSmithStore | 1 | stub |
| Player | OpenStorage | 1 | stub |
| Player | SuveryOwner | 1 | stub |
| Player | TeleportCheck | 1 | stub |
| Player | WarpNearestMarker | 1 | stub |
| Quest | RewardItemSelect | 1335 | stub |
| Quest | GetQuestFlag | 508 | stub |
| Quest | SetFlag | 417 | stub |
| Quest | AddCriteriaExp | 166 | stub |
| Quest | AddCriteriaSkillPoint | 166 | stub |
| Quest | AddCriteriaCash | 165 | stub |
| Quest | CheckMobKillCount | 138 | stub |
| Quest | MobKillCount | 128 | stub |
| Quest | PlayNPCMovie | 100 | stub |
| Quest | SetQuestFlag | 90 | stub |
| Quest | GetFlag | 67 | stub |
| Quest | CanReportDailyQuest | 61 | stub |
| Quest | ReportDailyQuest | 61 | stub |
| Quest | AddLvCriteriaExp | 59 | stub |
| Quest | AddLvCriteriaSkillPoint | 59 | stub |
| Quest | AddLvCriteriaCash | 58 | stub |
| Quest | CountDownTime | 54 | stub |
| Quest | GetWeekDay | 48 | stub |
| Quest | GetMobKillCount | 20 | stub |
| Quest | CheckOpenTime | 9 | stub |
| Quest | PlayNPCVoice | 8 | stub |
| Quest | CheckGuildOfflineQuest | 1 | stub |
| Quest | CheckWishQuest | 1 | stub |
| Quest | ReportGuildOfflineQuest | 1 | stub |
| Quest | StartGuildOfflineQuest | 1 | stub |
| Scene | PlacementOFF | 173 | stub |
| Scene | PlacementON | 96 | stub |
| Scene | CheckPlacementAlive | 65 | stub |
| Scene | PlacementCancel | 32 | stub |
| Scene | ChangeMainMusic | 8 | stub |
| Scene | CamaraShake | 2 | stub |
| Scene | CheckPlacementCombat | 1 | stub |
| Trigger | NextStatus | 353 | stub |
| Trigger | GetTriggerStatus | 134 | stub |
| Trigger | HideModel | 62 | stub |
| Trigger | PlayFx | 57 | stub |
| Trigger | TriggerShowMessage | 55 | stub |
| Trigger | SetTriggerStatus | 52 | stub |
| Trigger | StartTriggerAnimation | 43 | stub |
| Trigger | StartAnimation | 19 | stub |
| Trigger | HideTriggerModel | 13 | stub |
| Trigger | CastSkillXYZ | 11 | stub |
| Trigger | CastSkill | 9 | stub |
| Trigger | QuestActiveProgress | 8 | stub |
| Trigger | CastSkillBy | 5 | stub |
| Trigger | QuestFinishProgress | 3 | stub |
| Trigger | SetStatus | 2 | stub |
| Trigger | GetContactMode | 1 | stub |
| Trigger | GetTeiggerStatus | 1 | stub |

### Next round

1. `Trigger.*` (17 names, above) for real, wired to `TriggerVital`/
   `TriggerSyncVital` per `VITAL_REGISTRY`/`SERIALIZER_FIELDS` -- coordinate
   with LANE-A per the charter (A owns island entry, LANE-Q owns "the
   trigger script that decides what happens").  Closes with a GT: a tester
   sails into a trigger and the script fires.
2. `Quest.*` (25 names) for real, first full quest lifecycle from a real
   `q_kill*` script (accept -> `MobKillCount` -> report -> reward);
   `Quest.*` per-character state needs a LANE-DB column (letter already
   sent, `COO-DECISION 20260905_2058`).
3. Follow-up noted above, not done this round: a narrow safe clock/RNG
   surface so `utility.lua` stops failing closed on `os.time()`.
