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
    `register_eval=False, register_builtins=False` and a deny-all
    `attribute_filter` on the runtime itself.
  - **THE escape, and why the first fix for it was not one.**  After the
    `python`-table fix below was written, `pf-adversary` measured that the
    sandbox was still fully open through a path that touches neither the
    `python` table nor any blocked global:
    `Quest.GetQuestFlag.__globals__["__builtins__"]["__import__"]("os")`
    reached `__import__` and ran `os.system` as the server process,
    returning `uid=0`.  Root cause: `ApiNamespaceStub.__getitem__` hands a
    script a live Python closure for every real API name, and lupa lets
    Lua `getattr` any Python object it can see.  The three tests written
    with the first fix all probed attributes of the NAMESPACE object -
    `Quest.__class__`, `Quest.__dict__` - which `__getitem__` intercepts
    and answers `0`; none probed an attribute of the CLOSURE the namespace
    returns, which is where the hole was.  Six passing tests and a live
    root shell at the same time.
    Closed with a deny-all lupa `attribute_filter`
    (`deny_every_attribute`): nothing in this design needs attribute
    access from Lua - scripts index namespaces and call what comes back -
    so the filter refuses every read and every write rather than
    allow-listing, and every future real API inherits that.  Four tests
    now probe the closure itself, the whole import chain, an attribute
    write, and every name on `BLOCKED_GLOBALS` derived from the tuple
    rather than retyped (a mutant dropping `loadstring`/`loadfile`/
    `dofile`/`package`/`debug`/`collectgarbage` from it had left the whole
    module green; `debug.getregistry` and `package.loadlib` are escape
    vectors in their own right).
  - **The first escape, also measured and closed.**
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
    script gets out.  Three regressions assert that walk dies - and, as the
    entry above records, those three were not enough on their own.
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
    `latin-1`, the one codec that never raises on any input byte - these
    scripts carry Traditional Chinese and Thai comments in a legacy
    Windows codepage that utf-8 refuses outright.  It is NOT byte-
    preserving end to end, and the module docstring says so: lupa encodes
    the str back to utf-8 for Lua, so a source byte `0xE4` inside a string
    LITERAL arrives as two bytes (`string.len` 2, `string.byte` 195).
    Nothing in this round can observe that - every stub returns `0`, so no
    script compares a literal against a real table value - but the round
    that lands the first string-returning API owes a runtime encoding that
    matches the scripts' own codepage.  (pf-adversary, measured.)
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

## Round 456vso (2026-09-05) -- Trigger.* status machine, 5/17 real

**What moved**: charter queue item 2, "`Trigger.*` 17 functions of real, to
unblock M2 for LANE-A" -- partially.  Grepped the corpus first (per
`AGENTS.md` house rule) rather than guessing: the 17 names split cleanly
into a pure STATUS STATE MACHINE (read/write an int per trigger, no
outbound frame, no Quest state) and everything that needs a wire frame,
skill-cast encoder, animation/fx encoder, or Quest per-character state this
server does not have yet.  This round makes the first group real; the
second stays `stub`, each with the specific missing seam named rather than
"not done" (see `src/pirateforce_foundation/lua_api/trigger.py`'s
`STILL_STUBBED` dict).

**Real now (5 names, 542/828 call sites, 65%)**: `GetTriggerStatus`,
`GetTeiggerStatus` (the game's own shipped misspelling, aliased to the
same handler -- 1 call site, `t_getm_t1.lua`), `SetStatus`, `NextStatus`,
`SetTriggerStatus`.  Backed by `lua_api.trigger.TriggerStatusRegistry`: one
int per (scene, trigger id), process memory, same shape and caps as
`world_scene_registry.WorldSceneRegistry` and for the same reason
(`PANYA-DECISION 20260905_1057`: world state is server-process memory,
shared by every session in a scene, gone on reboot) -- but a SEPARATE book,
not a second front door into LANE-A's: trigger status is not a monster
vital, and the charter draws the ownership line explicitly (LANE-A owns
island ENTRY; LANE-Q owns "the trigger script deciding what happens").

Corpus-grepped semantics (not invented): `GetTriggerStatus(id)`/
`GetTeiggerStatus(id)` read ANOTHER trigger's status by id.
`SetStatus(n)`/`NextStatus()` take no id in any of their call sites (grepped
across all 616 files) because the game's own engine always knows which
trigger is running the script that called them -- this server has no such
call stack yet, so a `TriggerContext(scene, trigger_id)` supplies the
answer, provided by the caller (today: tests only -- see nonclaims).
`SetTriggerStatus(id, n)` writes ANOTHER trigger's status.  Worked example
proving this is real gating logic and not coincidence:
`tests/test_script_lua_api_trigger.py::RealTriggerLuaIntegrationTests
::test_a_six_gate_trigger_only_advances_when_every_prerequisite_is_ready`
runs the real shape of `t_nex_t6.lua`'s `ScriptStart` against six DISTINCT
real prerequisite triggers, shows it correctly refuses to advance while
they are not all at the target status, and correctly advances the instant
they are (round `s2fxf6`'s own version of this test only covered the
trivial case where every `Trigger.VarN` stub collapsed to the same value,
which passes regardless of whether the gating logic is real).

**Still stub (12 names, 286/828 call sites, 35%)**, one seam each,
`lua_api.trigger.STILL_STUBBED`: `GetContactMode` (1 site; the one call in
the corpus, `t_popmo_ui1.lua`, compares its return to a literal with no
other example to derive the enum from -- needs an RE ticket, not a guess);
`CastSkill`/`CastSkillBy`/`CastSkillXYZ` (needs a skill-cast wire frame
encoder, LANE-CS territory); `PlayFx`, `StartAnimation`,
`StartTriggerAnimation`, `HideModel`, `HideTriggerModel`,
`TriggerShowMessage` (each needs a wire frame encoder this server does not
have); `QuestActiveProgress`, `QuestFinishProgress` (needs per-character
Quest state -- charter queue item 3 and the LANE-DB column asked for in
`COO-DECISION 20260905_2058`).

**NOT done this round, said plainly**: nothing wires a live `TriggerVital`
(0x1FB2) arrival to a specific script file.  That needs the trigger-id ->
script-file mapping the charter names (`gamedata/scene/*.placements.tsv` /
a trigger table) -- not mined this round, to keep this diff to the state
machine itself.  `lane_hooks.lane_a_island_trigger_log` (LANE-A's own
module) is still the only subscriber to `vital_inbound_trigger_vital` and
still prints `no_responder bytes_out=0`; this round changes nothing about
that frame or that hook.  **A player sailing into a trigger sees no change
on screen from this round** -- the charter's closing criterion for this
queue item ("a GT where a tester sails into a trigger and the script
fires") is NOT met yet; it needs the mapping above as a follow-up round.
SCOREBOARD below is `COMING`, not `DONE`, for exactly this reason.

Tests: `tests/test_script_lua_api_trigger.py` (31 tests / 12 subtests --
registry alone with no lupa dependency, the namespace's `__getitem__`
contract, and lupa-guarded real-Lua integration including the six-gate
proof above and the shared-world property of two hosts sharing one
registry vs. two hosts with no registry given not leaking into each
other). `tests/test_script_host_spike.py`'s two assertions that assumed
`Trigger` was still all-stub are updated to match.

### API status table (141/160 stub, 12/160 real, as of round `4fxvsq`)

Read from `src/pirateforce_foundation/lua_api/api_spec.tsv`; call_count is
the corpus-wide call-site count from the 2026-08-24 census
(`gamedata/PF_LUA_API_SPEC.md`).  Namespaces ordered Guild/Instance/Mob/
Party/Player/Quest/Scene/Trigger (alphabetical); within a namespace, most-
called first.  Status is one of `stub` (this file logs `LUA_API_STUB` and
returns a safe default) / `real` (implemented against the actual protocol,
backed by a test -- every `Trigger.*` real row is backed by
`tests/test_script_lua_api_trigger.py`, every `Instance.*` real row by
`tests/test_script_lua_api_instance.py`, round `4fxvsq`, see below) /
`proven` (real + a GT ticket where a tester watched it work on screen --
none yet).  Next lane priority, per charter: the remaining 12 `Trigger.*`
rows and 2 `Instance.*` rows (each named, one seam apiece, in
`STILL_STUBBED`), then `Quest.*` (queue item 3, still blocked on the guard
exemption named in round `4fxvsq` below).

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
| Instance | AddKeyEvent | 15 | real |
| Instance | GetInstanceID | 14 | real |
| Instance | CallScoreCount | 12 | real |
| Instance | GetLastingTime | 7 | real |
| Instance | AddBonusPoint | 2 | stub |
| Instance | RemoveKeyEvent | 2 | real |
| Instance | AddBonusReward | 1 | stub |
| Instance | GetInstanceId | 1 | real |
| Instance | SetLastingTime | 1 | real |
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
| Trigger | NextStatus | 353 | real |
| Trigger | GetTriggerStatus | 134 | real |
| Trigger | HideModel | 62 | stub |
| Trigger | PlayFx | 57 | stub |
| Trigger | TriggerShowMessage | 55 | stub |
| Trigger | SetTriggerStatus | 52 | real |
| Trigger | StartTriggerAnimation | 43 | stub |
| Trigger | StartAnimation | 19 | stub |
| Trigger | HideTriggerModel | 13 | stub |
| Trigger | CastSkillXYZ | 11 | stub |
| Trigger | CastSkill | 9 | stub |
| Trigger | QuestActiveProgress | 8 | stub |
| Trigger | CastSkillBy | 5 | stub |
| Trigger | QuestFinishProgress | 3 | stub |
| Trigger | SetStatus | 2 | real |
| Trigger | GetContactMode | 1 | stub |
| Trigger | GetTeiggerStatus | 1 | real |

### Next round

1. **Wire a live `TriggerVital` (0x1FB2) arrival to a real script file.**
   This is what actually closes the charter's GT criterion ("a tester
   sails into a trigger and the script fires") -- round `456vso` built the
   state machine the scripts run against but did NOT do this part.  Needs,
   first, the trigger-id -> script-file mapping (`gamedata/scene/
   *.placements.tsv` / a trigger table per the charter -- grep for it
   before assuming it does not exist) and a `lane_hooks/lane_q_*` subscriber
   to `vital_inbound_trigger_vital` (LANE-A's existing hook point, still
   the only subscriber, still `no_responder bytes_out=0`) that resolves the
   wire trigger id to a script, builds its `TriggerContext` from the real
   scene, and calls `ScriptStart` against the process-singleton
   `lua_api.trigger.trigger_status_registry()` (NOT a private one -- that
   is the one piece of this round's design that exists specifically for
   this call site).  Sending anything back to the client is still a
   separate, later step (no response frame is decoded for this vital yet;
   `world_island_dock_table.py`'s own docstring names that gap).
2. The remaining 12 `Trigger.*` names, one seam each (see `STILL_STUBBED`
   in `lua_api/trigger.py` and the round `456vso` section above) --
   `GetContactMode` needs an RE ticket (semantics unclear from 1 call
   site); the rest need wire-frame encoders this lane does not own or
   `Quest.*` per-character state (item 3 below).
3. `Quest.*` (25 names) for real, first full quest lifecycle from a real
   `q_kill*` script (accept -> `MobKillCount` -> report -> reward);
   `Quest.*` per-character state needs a LANE-DB column (letter already
   sent, `COO-DECISION 20260905_2058`).
4. Follow-up noted above, not done this round: a narrow safe clock/RNG
   surface so `utility.lua` stops failing closed on `os.time()`.

## Round 4jsydv (2026-09-05) -- entry-point call census, stub-count baseline

### Why this round did not touch `Trigger.*`/`Quest.*` themselves

All three "next round" items above were checked, in order, and all three
are genuinely blocked, not skipped:

1. **Trigger-id -> script-file mapping.** Grepped for it before assuming
   absent, per house rule (`AGENTS.md` SS7): `gamedata/tables/` (no file
   name matches, no column matches `\.lua|ScriptStart|script_name|s_Script`
   in any table), `external/` (only hit is `PF_SERIALIZER_FIELDS.tsv`,
   already known -- the `TriggerVital` wire layout, not an id->script
   table), `archive/` and `notes_to_chief/consumed/` (no hit).
   `gamedata/scene/*/*.placements.tsv` has no script-name column (checked
   its header row). The script filenames themselves do not encode a
   numeric trigger id either (`t_nex_t6.lua` is not "trigger 6 in scene
   nex" -- read the file: its own `Var1..Var6` are SIX OTHER trigger ids it
   gates on, unrelated to its own filename suffix). This is a real gap in
   the committed artifacts, not a grep miss -- it needs either an RE
   ticket or a capture, not a guess. Not opened this round (see nonclaims).
2. **LANE-DB's `Quest.*` state-door contract.** Declared in two letters
   this round consumed (`pf_bridge/notes_to_chief/consumed/
   20260905_2212_LANE-DB-TO-LANE-Q-*` and its `2237` correction), but the
   PR is NOT on `main` -- confirmed with `git log`/`git merge-base
   --is-ancestor`, not assumed from the letter (the `2237` letter itself
   says the PR tripped a chief-owned coverage guard and is waiting on
   chief's read, not code review). `grep -rl "quest_flag\|quest_counter"
   src/` in this repo: no hits. Building `Quest.*` against a contract that
   is not live yet would be inventing the door myself.
3. **The other 12 `Trigger.*` names.** Re-read `lua_api/trigger.py`'s own
   `STILL_STUBBED` -- every one of the 12 names the previous round left
   named its missing seam explicitly (a CS/A/UI wire-frame encoder this
   lane does not own, `Quest.*` state per item 2, or an RE ticket for
   `GetContactMode`). None is free to implement without one of those.

### What this round built instead: does the corpus get RUN, not just loaded

`load_corpus()` (round `s2fxf6`) proves all 616 files PARSE and their
top-level chunk executes without raising. It never calls a single one of
the functions those chunks DEFINE, so it has never actually exercised the
API surface at anything like realistic volume -- every existing
`lua_api_*` unit test calls one function, by hand, once. The charter's own
backup-work item 2 (`prompts/LANE-Q.md`: "regression test: load all 616
scripts every round, count remaining `LUA_API_STUB`, this number must fall
every week") asks for exactly the thing that was still missing.

`script_host.run_corpus_entry_points()` (new): loads every script (same
isolation as `load_corpus`), then calls every one of
`STANDARD_ENTRY_POINTS` -- the eight zero-argument names the ORIGINAL
engine calls (`ScriptStart`, `Accept_Check`, `Accept_Run`, `Report_Check`,
`Report_Run`, `Delete_Run`, `OpenAcceptUI_Run`, `OpenReportUI_Run`,
measured by grepping every top-level `function Name(...)` definition in
the real corpus: these eight account for 2396 of ~2451 definitions; the
rest are internal helpers a script calls on itself, not something an
outside caller invokes) -- that the script actually defines, and tallies
every `LUA_API_STUB`/`LUA_TRIGGER_REAL` call each one made, reading each
namespace's own `.calls` list rather than parsing log text.

**Measured on the real corpus this round: 5057 total STUB calls across 137
distinct `<Namespace>.<Method>` names** (`BASELINE_TOTAL_STUB_CALLS` in
`tests/test_script_lua_corpus.py`, pinned exact-match, same idiom as
`KNOWN_LOAD_FAILURES`) -- separately, **346 calls landed on Trigger's 5
REAL methods** (`Trigger.NextStatus` 201, `GetTriggerStatus` 121,
`SetTriggerStatus` 23, `GetTeiggerStatus` 1; `report.total_real_calls`/
`real_call_counts`), which this function deliberately does NOT fold into
the stub count -- a first draft summed every namespace's raw `.calls` list
length and got 5403, silently counting those 346 real calls as if they
were still-stubbed (`RealTriggerNamespace` appends both real and stub
calls to the same `.calls` list); caught by hand before push, now pinned
against regressing back by `test_stub_vs_real_call_split_is_not_conflated`.
Top five STUB names by volume: `Player.MobAppear` (1096),
`Mob.ShowAnimation` (658), `Quest.SetFlag` (405), `Player.RemoveItem`
(289), `Scene.PlacementOFF` (173). This is the FLOOR this
lane's future rounds should watch fall -- undercounts on purpose (every
`Quest.VarN`/`RewardItemN`/`StringVarN` field this harness supplies reads
`STUB_DEFAULT=0`, so a branch gated on one being nonzero, e.g. half of
`q_kill5.lua`'s own `Report_Run`, never runs here), documented as a
nonclaim on the dataclass itself.

**Two real bugs in the SHIPPED scripts found by actually calling them**,
neither visible from `load_corpus`'s load-only check (pinned in
`KNOWN_ENTRY_POINT_CALL_FAILURES`, 17 `(path, entry_point)` pairs):

- 4 files (`Quest/q_gather_anticlass.lua`, `q_kill_anticlass.lua`,
  `q_repeat_gather_new.lua`, `q_repeat_kill_new.lua`) declare `local
  check_N` INSIDE nested `if`/`else` blocks in `Report_Check`, then read
  `check_N` again after those blocks close -- ordinary Lua lexical scoping
  resolves that later read to a stray, ever-nil GLOBAL `check_N`, and
  `check_1 * check_2 * check_3` on a nil raises. Read straight from the
  source (`grep -n "check_1" gamedata/lua/Quest/q_gather_anticlass.lua`);
  not a guess about Lua semantics.
- 13 files (`t_ge2tm_rat.lua` and 12 more matching `*rat*.lua`) call a bare
  global `rate(dicevalue)` that is defined in a DIFFERENT file,
  `utility.lua` -- this host gives every script its OWN Lua state
  (deliberate, `script_host.py`'s own module docstring: stops 616 files
  sharing one global table from overwriting each other's same-named entry
  points), so a name defined in one file is never visible from another.
  `utility.lua` is itself one of the 5 `KNOWN_LOAD_FAILURES` (calls
  `os.time()` at its own top level, sandbox-blocked), so even a
  shared-preload design would not make `rate` real without also widening
  the `os` sandbox (named as unfinished follow-up by round `s2fxf6`).

### Nonclaims

1. Does not close the charter's GT criterion for ANY queue item -- no
   player-visible change this round; this is instrumentation over the
   existing sandbox, not a new feature a tester can see on screen.
2. Does not open the trigger-id -> script-file RE ticket -- the grep in
   the section above establishes the gap is real, not that this round
   asked the RE runner to close it (RE runner time is scarce, one ticket
   per machine round per `AGENTS.md` SS7; a status letter to COO carries
   this forward instead, see `pf_bridge/notes_to_chief/`).
3. Does not claim `rate`'s original-engine behavior -- plausibly the real
   client loads `utility.lua` once into a shared global environment before
   running any trigger/quest script, which this per-script-isolated host
   does not attempt. Not measured against the real client either way.
4. `BASELINE_TOTAL_STUB_CALLS` is a floor, not a live-game call count --
   see the dataclass docstring; do not read 5057 as "how many times a
   player's actions call a stub", only as "how many times these 616 files'
   own zero-arg entry points call one with no per-instance data".
5. Does not touch `runtime.py`/`app.py`/`store.py` or any other lane's
   write zone. No new CORE-REQUEST.
6. `run_corpus_entry_points`/`ScriptHost.call` has no instruction-count or
   wall-clock budget (pf-adversary, this round): a Lua entry point that
   never returns (adversary's repro: `function f() return f() end`, a
   proper tail call that never overflows the C stack into a catchable
   error) hangs the call with nothing to except-catch. `grep -rlE
   "\bwhile\b" gamedata/lua` is empty (checked independently this round)
   and no confirmed unbounded-recursion pattern exists in the real 616
   files today, so this has no known live trigger in the current corpus --
   but it is the same `host.call` path `lua_api/trigger.py` names as the
   template a future live `TriggerVital` dispatch reuses, so a hang there
   would wedge a listener thread for a whole scene, not just fail a test.
   Not fixed this round (see `run_corpus_entry_points`'s own docstring for
   what a fix needs); named so the next round that wires live dispatch
   does not rediscover it.

### ADVERSARY

Ordered at round start, per the mandatory rule (`AGENTS.md` SS7: any
session with the Agent tool runs it every round that changes more than a
typo). Reported on the diff's first draft; **4 real findings, all fixed
before this round's commit, one already covered above (nonclaim 6)**:

1. **HIGH, fixed**: the first draft's `total_stub_calls`/`stub_call_counts`
   summed every namespace's raw `.calls` list length, which silently
   folded 346 calls to Trigger's 5 REAL methods into a number that is
   supposed to mean "still stubbed" (`RealTriggerNamespace` appends both
   kinds of call to one shared list) -- caught independently by adversary
   AND by hand before adversary's report came back (see the "STUB VS REAL"
   discussion above); both arrived at the same corrected split (5057
   stub / 346 real), which is strong corroboration the fix is right, not
   just silencing. Fixed: `REAL_QUALIFIED_NAMES` + a structural split, with
   its own regression test (`test_stub_vs_real_call_split_is_not_conflated`).
2. **HIGH, no fix landed this round**: no timeout/instruction budget on
   `host.call` -- see nonclaim 6.
3. **MEDIUM-HIGH, fixed**: the first draft's `actual_failures` test
   reconstruction checked `name in (run.error or "")` -- a SUBSTRING search
   over a concatenated error string, not a structural match. Adversary
   built a counter-example (`Accept_Check` returning cleanly but appearing
   in the pinned-failure set because its name was a substring of a
   DIFFERENT entry point's error message) and confirmed it actually
   reproduces against the code. Fixed: `EntryPointRun.errors` is now a
   `dict` keyed by entry-point name, no string search.
4. **NIT, fixed**: a leftover duplicate `return report` (dead, unreachable
   second line) at the end of `run_corpus_entry_points`.

One claimed finding did not hold up on independent re-derivation: adversary
reported `Accept_Run` at 306 definitions (comment said 305); re-counting
with `find ... -print0 | xargs -0 grep -c` (needed because one file,
`t_test auto.lua`, has a space in its name and silently splits under a
bare `xargs`) reproduces 305, matching the comment -- not changed.

### Next round

Unchanged from round `456vso` (all three still blocked, see "Why this
round did not touch" above for the fresh evidence): (1) trigger-id ->
script-file mapping needs an RE ticket or capture, (2) `Quest.*` needs
LANE-DB's PR to land on `main`, (3) the remaining 12 `Trigger.*` names
each need a seam this lane does not own. Whichever unblocks first is the
next round's first job. If both stay blocked, the next backup-work slot is
`STILL_STUBBED`'s highest-call-volume name that turns out NOT to need a
wire frame after all (re-check `GetContactMode`'s RE ticket status first;
it is the only one of the 12 that is a pure RE gap like item 1, not a
cross-lane wire-frame wait).

## Round 4fxvsq (2026-09-06) -- Instance.* status machine, 7/9 real

**Why `Instance.*`, not `Trigger.*`'s remaining 12 or `Quest.*`.**  Checked
fresh at round start, not assumed from the previous round's file (all still
true, re-confirmed via `pf_bridge` mailbox and `notes_to_chief/`, not
guessed):

1. **Trigger-id -> script-file mapping.**  The RE ticket content
   (`pf_bridge/notes_to_chief/20260906_0155_LANE-Q-RE-TICKET-*`) is written
   but chief has not yet assigned it a number or answered it -- confirmed by
   reading `pf_bridge/notes_to_chief/20260906_0256_COO-DECISION-*`, which
   orders chief to do exactly that as item 1 of chief's OWN next round, and
   by the absence of any chief round file after that COO-DECISION's own
   `02:56` timestamp (`FROM_CHIEF_R362_TO_ALL_20260906_0210.md` is chief's
   latest, dated BEFORE the decision that tells chief to act).  Still
   blocked, not this lane's to unblock.
2. **`Quest.*`'s guard exemption AND LANE-DB door.**  Round `vqng2z`'s own
   `pirate-force-server#874` (`Quest.CheckOpenTime`, the first `Quest.*`
   real implementation) was gate-closed
   (`pf_bridge/notes_to_chief/20260906_0226_SYNC-NOTICE-*`): the branch
   `claude/hopeful-hopper-vqng2z` still exists but never merged, because
   ANY reference to the bare token `quest` from `script_host.py`'s new
   `Quest` wiring trips `tests/test_npc_interaction_wire.py`'s
   `QuestAndShopStateGuardTests` -- a chief-owned cross-cutting guard
   outside this lane's write zone.  Round `vqng2z` already sent the
   proposed `ALLOWED_SYMBOLS` patch
   (`pf_bridge/notes_to_chief/20260906_0209_LANE-Q-CORE-REQUEST-*`); this
   round confirmed by reading `tests/test_npc_interaction_wire.py`'s
   `ALLOWED_SYMBOLS` dict directly (grepped for `script_host`/`lua_api`: no
   hit) that the patch has NOT landed yet -- same COO-DECISION as above
   orders chief to decide it, not yet done.  Separately, LANE-DB's
   per-character Quest-state column (`COO-DECISION 20260905_2058`) is also
   still not on `main` (`grep -rl "quest_flag\|quest_counter" src/`: no
   hit).  So `Quest.*` stays untouched this round on BOTH doors, not just
   one -- starting a SECOND `Quest.*` implementation before either door
   opens would only produce a second gate-closed PR.
3. **The other 12 `Trigger.*` names.**  Re-read `lua_api/trigger.py`'s own
   `STILL_STUBBED`: unchanged, each still names a wire-frame encoder this
   lane does not own or `Quest.*` state (blocked per item 2) --
   `GetContactMode`'s own RE ticket (semantics unclear from 1 call site)
   has still not been opened by anyone (`grep -rl "GetContactMode"
   pf_bridge/notes_to_chief/*.md`: no hit; only this lane's own round files
   mention the name).  None free to implement.

With all three named blockers genuinely still blocked, this round follows
the charter's own backup-work rule (`prompts/LANE-Q.md`, "implement the next
API in the table that is still a stub and does not need to wait on another
lane, highest call count first") -- across the WHOLE table, not just
`Trigger.*`/`Quest.*`, since those two are exhausted for this round.  The
top of the table by real call volume (`Player.MobAppear` 3532,
`Quest.RewardItemSelect` 1335, `Player.AddItem` 1430, `Mob.ShowAnimation`
716, ...) all need a wire-frame encoder, a spawn/roster door this lane does
not own (LANE-A/LANE-CS territory), or `Quest.*` state (blocked).
`Instance.*`'s 9 names, grepped fresh across the real 616-file corpus
before writing a line of code (same discipline `456vso` used for
`Trigger.*`), split the identical way: a PURE STATE MACHINE with no
outbound frame and no cross-lane data (52 of 55 call sites, 94.5%) plus two
names whose ARGUMENT semantics are genuinely ambiguous from the corpus
alone.

### What was built

- `src/pirateforce_foundation/lua_api/instance.py` (new) -- `InstanceContext`
  (which running instance is asking, supplied by the caller today, same
  shape as `TriggerContext`), `InstanceRegistry` (process memory: a
  per-instance lasting-time int, a per-instance key-event id set, a
  per-instance score-count-call counter -- three independent books, one
  process-memory registry, same caps-and-refuse-by-name posture as
  `TriggerStatusRegistry`), `RealInstanceNamespace` (the same three-way
  `__getitem__` contract, the same `*args`-first arity door logging
  `LUA_INSTANCE_BAD_ARITY` instead of raising, so a wrong-arity call from a
  corrupted or future script degrades safely exactly like `Trigger.*`
  already does), `build_namespace()`.
- `src/pirateforce_foundation/script_host.py` (edited) -- `Instance` wired
  the same way `Trigger` is: `ScriptHost.__init__`/`load_script_file` grow
  `instance_context`/`instance_registry` params (default: an isolated
  context and a private, throwaway registry, so no existing caller or test
  changes behaviour); `REAL_QUALIFIED_NAMES` extended so
  `run_corpus_entry_points`'s real/stub split does not fold `Instance.*`'s
  new real calls into the stub tally (the exact bug `456vso` caught for
  `Trigger.*` and pinned a regression test against -- checked this file's
  own tally logic is namespace-agnostic already, so no second bug to fix
  here, only the frozenset to extend).

**Real now (7 names, 52/55 call sites, 94.5%)**: `GetInstanceID` and its
shipped alternate-case alias `GetInstanceId` (1 call site,
`t_indanix2_colct_ins.lua` -- same treatment `456vso` gave
`GetTeiggerStatus`), `GetLastingTime`/`SetLastingTime`, `AddKeyEvent`/
`RemoveKeyEvent`, `CallScoreCount`.  Corpus-grepped semantics, not invented:
`GetInstanceID()` takes no argument in any of its 15 call sites and reads
which instance the running script belongs to (compared against
`Trigger.Var4`/`Var5` literals in `t_nex_t1_ins.lua`/`t_nex_msg_ins*.lua`,
and against a bare literal in `t_bg2017_msg.lua` -- an instance ROUTING
decision this lane does not make, just answers); `GetLastingTime()`/
`SetLastingTime(n)` take zero/one argument in every call site (grepped, no
exception; 7 of the `GetLastingTime()` sites branch on the value, e.g.
`t_opnplc_tim.lua`: `local T = Instance.GetLastingTime(); if (T >
Trigger.Var2) then return 0 else ... end`); `AddKeyEvent(id)`/
`RemoveKeyEvent(id)` always take exactly one argument (`Trigger.Var1`/
`Var2`/`Var4` at every call site); `CallScoreCount()` is always a bare
zero-argument statement whose own return value no script reads.
`CallScoreCount`'s registry method counts INVOCATIONS, not a score --
a candidate reward table DOES exist
(`gamedata/tables/CONSTDATA_TH__SCORECOUNT.tsv`'s `n_COLLECT_BONUS_SCORE`/
rank-tiered reward columns, keyed from `CONSTDATA_TH__INSTANCE.tsv`'s
`n_SCORECOUNT_ID`, found this round after pf-adversary caught the first
draft claiming no such table existed), but tracing whether it resolves for
any instance that actually runs a `CallScoreCount`-calling script is
unstarted work, so this function still only advances an int the same
"gone on reboot, no invented game rule" shape `TriggerStatusRegistry.
next_status` already uses, and does not itself look up or apply that
table.

**Still stub (2 names, 3/55 call sites, 5.5%)**, named in
`lua_api.instance.STILL_STUBBED`: `AddBonusPoint` (called both
`Instance.AddBonusPoint()` and `Instance.AddBonusPoint(Trigger.Var1)` in
the corpus's only 2 call sites -- unclear whether the argument is a point
value or a bonus-category id; the same `CONSTDATA_TH__SCORECOUNT.tsv`
candidate table above is untraced for this name too);
`AddBonusReward` (1 call site, zero arguments, gives an actual reward to
instance participants -- the same candidate table is untraced for this name
too, and item/currency composition crosses into inventory territory this
lane does not own regardless).  Both need the SCORECOUNT trace above (or an
RE ticket if the trace comes up ambiguous) before becoming real logic
instead of a guess, per charter ("the original script is the spec, do not
guess logic").

**NOT done this round, said plainly.**  Nothing routes a live inbound frame
to a specific running instance -- an `InstanceContext` is supplied by the
CALLER (a test today; a future dispatch module later), the identical
posture `TriggerContext` has had since `456vso` and still has.  No player
sees any change on screen from this round.  This lane also does not claim
ownership of instance ENTRY/lifecycle (spawning an instance, routing a
party into one) -- only of the script running inside one reading/writing
its own scratch state, the same ownership line the charter draws between
LANE-A's island entry and this lane's trigger scripts.

Tests: `tests/test_script_lua_api_instance.py` (35 tests -- registry alone
with no lupa dependency, the namespace's `__getitem__` contract including
the wrong-arity degrade-safely proof, lupa-guarded real-Lua integration
including two hosts sharing one registry vs. two hosts with no registry
given not leaking into each other -- the same shared-world property proof
`456vso` wrote for `Trigger.*` -- and a worked example against the REAL
shipped `gamedata/lua/t_inscnt.lua`, guarded by the combined
`LUA_CORPUS_RUNNABLE` key rather than a bare `BRIDGE_LUA_SCRIPTS`
decorator stacked under a class-level `LUPA_PACKAGE` guard -- round
PIN-DRIFT-FIX found the stacked form was exactly the shape
`pf_preconditions.AllOfThese`'s own docstring warns against: on a
machine without lupa, `unittest.TestCase.run()` uses the class's own
skip reason for every method once the class is skipped, so the stacked
method-level decorator's own reason never fired, and a real gate
measured it as `PIN DRIFT: ... 'bridge_lua_scripts': pinned 1, observed
0`. The other 3 methods in this class now each carry their own
`LUPA_PACKAGE` decorator directly instead of one class-level decorator).
`tests/test_script_host_spike.py`'s `test_every_still_stubbed_name_is_
reachable_from_every_namespace_table` now also excludes `Instance.*`'s 7
real names (same treatment as `Trigger.*`'s 5), plus a new regression guard
pinning `Instance.REAL_METHODS` itself
(`test_the_7_real_instance_names_are_excluded_above_not_forgotten`), mirror
of the existing `Trigger.*` guard.  `tests/test_script_lua_corpus.py`'s
`BASELINE_TOTAL_STUB_CALLS` measured down from 5057 to 5020 (37 calls moved
to real when `run_corpus_entry_points` was re-run against the real corpus
with the new namespace installed: 12 `CallScoreCount`, 9 `AddKeyEvent`, 7
`GetLastingTime`, 5 `GetInstanceID`, 2 `RemoveKeyEvent`, 1 `GetInstanceId`,
1 `SetLastingTime`).  `docs/PYTEST_SKIP_PINS.json` updated in the same
commit for both the widened `test_script_host_spike.py` `lupa_package`
count (19 -> 20) and the two new pins this round's own test module needs
(`lupa_package` 4, `bridge_lua_scripts` 1) -- verified against
`tools/pf_pytest_precondition_census.py`'s own static walker, not
hand-counted.

### ADVERSARY

Ordered at round start per the mandatory rule (`AGENTS.md` SS7), result
returned before push. Independently re-ran the full suite in its own
worktree (11671 passed / 323 skipped / 0 failed, matching this round's own
run) and re-derived every measured claim rather than trusting this round's
numbers. **4 real findings, all fixed before this round's commit:**

1. **MEDIUM-HIGH, fixed**: the first draft's `CallScoreCount`/
   `STILL_STUBBED["AddBonusReward"]` docstrings claimed "no reward/score
   table has been found committed anywhere" -- false.
   `gamedata/tables/CONSTDATA_TH__SCORECOUNT.tsv` exists (columns include
   `n_COLLECT_BONUS_SCORE` and rank-tiered `n_RANKC_REWARD`..
   `n_RANKSSS_REWARD`), and `CONSTDATA_TH__INSTANCE.tsv`'s own
   `n_SCORECOUNT_ID` column keys into it -- a plain `grep -rliE score
   gamedata/tables` (which this round's first draft did not run) surfaces
   it immediately. Fixed: docstrings now name the table and its columns
   precisely, and say plainly what is still untraced (whether the
   instance rows that run the affected scripts actually resolve through
   that column, and what `AddBonusPoint`'s one argument indexes) rather
   than claiming the table does not exist.
2. **MEDIUM, fixed**: `InstanceRegistry`'s class docstring claimed "no
   script in the corpus checks a richer return value from any of these 7
   names" -- false. 7 scripts branch on `GetLastingTime()`
   (`t_opnplc_tim.lua`: `local T = Instance.GetLastingTime(); if (T >
   Trigger.Var2) then return 0 else ... end`, and 6 more of the same
   shape) and several branch on `GetInstanceID()` (`t_bg2017_msg.lua`:
   `if (Instance.GetInstanceID() == 1005) then`). Fixed: docstring now
   names the real comparisons and states precisely what still holds (every
   `SetLastingTime` call site in the corpus passes a plain literal, so the
   refusal path has no live trigger today) instead of the broader false
   claim.
3. **LOW, fixed**: "53 of 55 call sites (96%)" was arithmetically wrong.
   Re-summed against `REAL_METHODS`/`api_spec.tsv`: 15+14+12+7+2+1+1 = 52
   real, 2+1 = 3 stub, 55 total -- 52/55 (94.5%). Fixed everywhere this
   round's own text repeated the number.
4. **LOW, cosmetic, fixed**: `lua_api/__init__.py` still imported only
   `.trigger` and said "every other namespace is still all-stub" -- stale
   the moment this round's `instance.py` landed, even though
   `script_host.py` imports the submodule directly and nothing was
   functionally broken. Fixed: `__init__.py` now imports and lists
   `instance` too.

Verified as correct, not defects: `BASELINE_TOTAL_STUB_CALLS=5020` and the
37-call breakdown (re-run independently, matched digit-for-digit);
`AddBonusPoint`/`AddBonusReward`'s arity claims; no sandbox-escape reopened
(same hardened `__getitem__`/`__setitem__`/`__slots__` shape as
`trigger.py`); thread-safety (8 threads x 2000 calls each against
`call_score_count`, exact count, no lost updates); `_coerce_int` edge
cases; no regression to `Trigger`'s own wiring.

**Open question the design has not answered** (adversary's own words,
carried forward rather than silently dropped): has anyone actually traced
whether `n_SCORECOUNT_ID` on the specific instance rows that run
`t_insbospnt_himdfx.lua`/`t_insbosev_himdfx.lua`/
`t_drp&insbospnt_himdfx.lua` resolves to a real `SCORECOUNT` row, or was
this table simply never opened before the first draft wrote "no table
found"? Not answered this round -- named as the concrete first step for
whoever traces `AddBonusPoint`/`AddBonusReward` next.

### Nonclaims

1. Does not close the charter's GT criterion for ANY queue item -- no
   player-visible change this round.
2. Does not touch `Quest.*`, the remaining 12 `Trigger.*` names, or any
   other lane's write zone -- confirmed unblocked-vs-blocked status is
   stated above with its own evidence, not assumed from a stale round file.
3. Does not claim `AddBonusPoint`'s or `AddBonusReward`'s real-engine
   semantics, and does not claim the candidate `CONSTDATA_TH__SCORECOUNT.tsv`
   table (found this round, see ADVERSARY below) is definitely the right
   one or definitely wired to these two names for any given instance --
   named as an open trace, not guessed either way.
4. `CallScoreCount`'s registry counts INVOCATIONS, not points or a score --
   see the class docstring; a future round tracing and wiring the candidate
   reward table is not blocked by this round's naming choice, since nothing
   here invents a scoring rule to later contradict.
5. Does not trace `CONSTDATA_TH__INSTANCE.tsv`'s `n_SCORECOUNT_ID` column
   against the actual instance rows that run `AddBonusPoint`/
   `AddBonusReward`-calling scripts this round, and does not open a
   numbered RE ticket for either name (RE runner time is scarce, per
   `AGENTS.md` SS7); both named as follow-up, not silently dropped.
6. `BASELINE_TOTAL_STUB_CALLS`'s new value (5020) reflects today's OTHER
   stub coverage as much as this round's own change, same caveat round
   `4jsydv` wrote for its own baseline move.

### Next round

1. **First job, already done this round** (adversary's result returned
   before push -- see ADVERSARY above): all 4 findings fixed in this same
   commit, so the next round's first job is item 2 below, not re-reading a
   pending result.
2. Re-check the same three named blockers fresh (do not trust this round's
   file once it is more than one round old): chief's guard-exemption
   decision on `0209`/RE-number on `0155`
   (`pf_bridge/notes_to_chief/20260906_0256_COO-DECISION-*` item 1),
   `persistence_quest_state.py` landing on `main`
   (`git merge-base --is-ancestor`), `GetContactMode`'s RE ticket status.
   Whichever clears first is the next round's first real-API job.
3. If all three stay blocked again: trace `CONSTDATA_TH__INSTANCE.tsv`'s
   `n_SCORECOUNT_ID` column against the instance rows that actually run
   `t_insbospnt_himdfx.lua`/`t_insbosev_himdfx.lua`/
   `t_drp&insbospnt_himdfx.lua` (adversary's own closing question, not
   answered this round) -- if it resolves cleanly to a real `SCORECOUNT`
   row for those instances, `AddBonusPoint`/`AddBonusReward` may not need
   an RE ticket at all; if it does not resolve cleanly, THAT is the
   narrowed question an RE ticket should ask, per
   `AGENTS.md` SS7's one-ticket-per-machine-round-per-lane budget.
4. Otherwise: re-audit the remaining stub surface for another pure-function
   candidate with no cross-lane dependency, using
   `run_corpus_entry_points`'s real call-volume ranking (`stub_call_counts`)
   rather than the static census table alone, the same method this round
   used to find `Instance.*`.
