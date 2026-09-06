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

### API status table (145/160 stub, 15/160 real, as of round `vmm7vf`)

Read from `src/pirateforce_foundation/lua_api/api_spec.tsv`; call_count is
the corpus-wide call-site count from the 2026-08-24 census
(`gamedata/PF_LUA_API_SPEC.md`).  Namespaces ordered Guild/Instance/Mob/
Party/Player/Quest/Scene/Trigger (alphabetical); within a namespace, most-
called first.  Status is one of `stub` (this file logs `LUA_API_STUB` and
returns a safe default) / `real` (implemented against the actual protocol,
backed by a test -- every `Trigger.*` real row is backed by
`tests/test_script_lua_api_trigger.py`, every `Instance.*` real row by
`tests/test_script_lua_api_instance.py` (round `4fxvsq`; `AddBonusPoint`/
`AddBonusReward` added round `vmm7vf` as pure invocation counters,
NOT SCORECOUNT-wired -- see `lua_api/instance.py`'s module docstring and
`InstanceRegistry.add_bonus_point`/`add_bonus_reward` for the explicit
non-claim), the one `Quest.*` real row (`CheckOpenTime`) by
`tests/test_script_lua_api_quest.py` (round `0rgg6q`, recovering the
round-after-`4jsydv` commit that the guard exemption named below unblocked
-- see "Round vqng2z" further down) / see below) / `proven` (real + a GT
ticket where a tester watched it work on screen -- none yet).  Next lane
priority, per charter: the remaining 12 `Trigger.*` rows (blocked on
`RE-273`), then the rest of `Quest.*` (24 names still blocked on the
LANE-DB per-character state door, `GetWeekDay` on an undocumented weekday
enum -- both named in "Round vqng2z" below).  `Instance.*` is now 9/9 real
-- no rows of that namespace remain in `STILL_STUBBED`.

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
| Instance | AddBonusPoint | 2 | real |
| Instance | RemoveKeyEvent | 2 | real |
| Instance | AddBonusReward | 1 | real |
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
| Quest | CheckOpenTime | 9 | real |
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
cross-lane wait).

## Round vqng2z (2026-09-06) -- Quest.CheckOpenTime, 1/25 Quest.* real

### All three named blockers, re-checked fresh, still blocked

Same three checked at round start, per `AGENTS.md` SS7 house rule (grep
before asserting "still blocked", never re-quote a stale round file):

1. **Trigger-id -> script-file mapping.** No `COO-DECISION` answering round
   `4jsydv`'s own ask (`notes_to_chief/20260906_0029_LANE-Q-ASK-COO-trigger-
   id-to-script-file-mapping-needs-an-RE-ticket.md`) exists yet on
   `origin/main` as of this round's start (checked every letter after it,
   oldest to newest, through `20260906_0130`) -- still open.
2. **LANE-DB's `Quest.*` state door.** `grep -rln "persistence_quest_state
   \|character_quest_state" src/` -- zero hits, fresh this round.
   `migrations/` still ends at `014_character_skills_learned_source.sql`,
   no `015`. LANE-DB's own round `9vzzn7` (letter
   `20260906_0108_LANE-DB-REPORT-...`) independently confirms the same
   thing from the DB side: chief's whitelist (`COO-DECISION
   20260905_2353`) has not landed on `main`, so the door's own code (built
   once already, lost with the scratchpad session that built it, per house
   rule "code that isn't on main doesn't exist") stays unbuilt until that
   whitelist lands -- not this lane's write zone either way.
3. **The remaining 12 `Trigger.*` names.** Unchanged: `lua_api/trigger.py`'s
   own `STILL_STUBBED` still names a seam this lane does not own for each
   of the 12 (a CS/A/UI wire-frame encoder, or `Quest.*` state per item 2,
   or `GetContactMode`'s own RE ticket, item 1's exact shape one level
   down).

### What this round built instead: `Quest.CheckOpenTime`, the one `Quest.*`
### name that needs neither the state door nor a wire frame

Per `prompts/LANE-Q.md`'s own backup-work item 1 ("implement the next stub
API that needs no other lane, highest call-site count first") and
`COMMON_LANE_ROUND.md`'s standing backup rule, re-audited `STILL_STUBBED`
plus every other stubbed namespace by the real call-volume ranking round
`4jsydv`'s own `run_corpus_entry_points` produced, rather than the static
`PF_GAMEDATA_LUA_API.tsv` call-site count alone. Every `Quest.*` name that
reads or writes per-character progress needs the LANE-DB state door
(blocker 2 above); every `Player.*`/`Mob.*`/`Scene.*`/etc. name with any
real call volume needs either that same door, a wire-frame encoder this
lane does not own, or LANE-A's world registry. Exactly one name in the
whole 160-function surface needs none of those: `Quest.CheckOpenTime`
(call count 9, 3 files) -- a pure question about the SERVER CLOCK, no
per-character state, no outbound frame. Full reasoning, grepped call
sites, and the Lua-numeral-truncation evidence for the `HH*100+MM`
encoding: `src/pirateforce_foundation/lua_api/quest.py`'s own module
docstring.

**Deliberately NOT made real alongside it**: `Quest.GetWeekDay` (call
count 48, the next-highest name that also touches no other lane) stays a
stub. `QUESTDATA_TH__QUEST.tsv` proves some small-int weekday enum exists
(`Q_WEEK3_KILL3`'s `n_VARI_9/10/11` read the constants 1/4/6 across every
level row) but nothing in the committed artifacts says which day of the
week `1` is or which direction the count runs -- guessing would silently
gate weekly quest availability on the wrong day, the exact guess the
charter forbids. Same posture `lua_api/trigger.py` already took on
`GetContactMode`; named in `lua_api/quest.py`'s own `STILL_STUBBED`, not
silently skipped.

**What "real" means here**: no registry at all, unlike
`lua_api.trigger.TriggerStatusRegistry` -- `CheckOpenTime` reads the
server's own wall clock (an injectable `Clock = Callable[[], datetime]`,
the same seam shape `build_namespace`'s `context`/`registry` params
already use for Trigger), nothing to remember between calls. The default
clock reads `Asia/Bangkok`, an explicit, tagged
`[assumption of LANE-Q - pending COO confirmation]` (this project's own
house convention for every other timestamp; nothing in the committed
artifacts states a server timezone to confirm or refute it against).

**A real finding from actually calling it against the shipped corpus**,
not assumed from the call-site table: of the 9 real call sites, only 2
(`Quest/q_con5.lua` and `Quest/q_arena2.lua`'s own `Accept_Check`) execute
under today's corpus. `Quest/q_sea_join.lua`'s own `Accept_Run` gates its
whole 7-window chain behind `if Player.CheckBuff(9903) then ... else <the
chain> end`, and `Player.CheckBuff` is still a stub returning
`STUB_DEFAULT` (0) -- TRUTHY in Lua, where only `nil`/`false` are falsy --
so the stubbed condition always takes the `then` branch and the chain
never runs today. Confirmed by printing `report.real_call_counts` directly
(`{'Quest.CheckOpenTime': 2, ...}`), not inferred. A future round making
`Player.CheckBuff` real can change this in either direction.

`tests/test_script_lua_corpus.py`'s own `BASELINE_TOTAL_STUB_CALLS`
(round `4jsydv`'s regression pin) moves **5057 -> 5055** in this commit
(2 calls, not 9, moved from stub to real -- see that constant's own
comment for the measured reasoning above), against a newly-required FIXED
`quest_clock` (`FIXED_QUEST_CLOCK`, noon, outside every literal window the
corpus uses) -- without it, `Quest/q_sea_join.lua`'s `or`-chain short-
circuit would make this file's own pinned call counts depend on the real
time of day the test suite happened to run, a flakiness class this
project's fail-closed posture forbids.

### Tests

- New: `tests/test_script_lua_api_quest.py` (mirrors
  `tests/test_script_lua_api_trigger.py`'s three-level shape: the pure
  namespace object with no Lua dependency, a `LUPA_PACKAGE`-gated class
  driving real Lua against an inline reproduction of `q_sea_join.lua`'s
  own seven-window chain, and a `LUA_CORPUS_RUNNABLE`-gated class against
  the actual shipped `q_con5.lua` file, not a copy).
- Updated: `tests/test_script_host_spike.py` (the "every still-stubbed
  name is reachable" probe now excludes `Quest.CheckOpenTime` the same way
  it already excluded the 5 real `Trigger.*` names, plus a new regression
  guard pinning `lua_api.quest.REAL_METHODS`) and
  `tests/test_script_lua_corpus.py` (fixed clock, updated baseline, see
  above).
- `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest
  tests/test_script_lua_api_trigger.py tests/test_script_host_spike.py
  tests/test_script_lua_api_spec.py tests/test_script_lua_api_quest.py
  tests/test_script_lua_corpus.py -q` = **89 passed, 244 subtests passed**
  (lupa 2.8 installed, bridge corpus present).
- `docs/PYTEST_SKIP_PINS.json`: `lupa_package`/`tests/test_script_host_
  spike.py` 19 -> 20 (one new regression guard); two new entries for
  `tests/test_script_lua_api_quest.py` (`lupa_package` count 2,
  `lua_corpus_runnable` count 1) -- all three RE-MEASURED (`pip uninstall
  -y lupa` then `pytest -rs`, counted from the `SKIPPED` summary lines),
  not guessed: 5/20/2/1/9 skips respectively under each key/module pair
  with lupa absent, 0 with it reinstalled.
- `python3 tools/pf_pytest_precondition_census.py --run` = **RESULT:
  PASS** (see round file for the sha this was checked against).

### ADVERSARY

`ADVERSARY_PENDING` or the result itself: see the `pf_bridge` round file
(`rounds/Q_20260906_0148_vqng2z_quest-check-open-time-1-of-25-real.md`)
for whichever landed before this commit's push, per `AGENTS.md` SS7's
own timing rule (ordered at round start, not before commit).

### `TWO_SESSIONS_SAME_SCENE:`

N/A -- `Quest.CheckOpenTime` touches no shared world state at all (no
registry, not even a private one): it reads a clock and returns a bool.
Nothing here reads or writes `world_scene_registry` or any process
singleton.

### nonclaims

1. Does not close any of the three queue items the charter itself tracks
   (Trigger.*/Quest.* full lifecycle/the remaining stubs) -- all three
   stay blocked outside this lane's write zone, re-confirmed fresh this
   round, not re-quoted from a stale file.
2. Does not make any change a player can see on screen: `CheckOpenTime` is
   called today only from `Accept_Check`/`Accept_Run`, which nothing in
   this server's own dispatch path calls yet (no live quest-accept flow
   exists) -- this is coverage over the sandbox's own regression harness,
   the same posture round `4jsydv`'s own work had.
3. Does not verify `Asia/Bangkok` against the real client or a table --
   tagged as an assumption pending COO confirmation, per house rule.
4. Does not implement `Quest.GetWeekDay` despite its higher call count --
   RE ambiguity, named above and in `STILL_STUBBED`, not silently skipped.
5. Does not touch `runtime.py`/`app.py`/`store.py` or any other lane's
   write zone. No new CORE-REQUEST.
6. `BASELINE_TOTAL_STUB_CALLS`'s new value (5055) reflects today's OTHER
   stub coverage (`Player.CheckBuff` still stub) as much as it reflects
   this round's own change -- a future round making `Player.CheckBuff`
   real can move this number again in either direction, not necessarily
   downward.
7. **CORRECTION (round `ksp5d3`, pf-adversary finding):** every number in
   this section (5057 -> 5055, 19 -> 20) was measured on this round's OWN
   branch state at the time, before the parallel `Instance.*` round
   (`4fxvsq`) landed on `main` with its own independent 5057 -> 5020 move
   and 19 -> 20 pin. This round's branch (`#874`) was then gate-closed
   (one-open-claude-PR lock) and sat unmerged until round `0rgg6q`
   cherry-picked it onto a `main` where `4fxvsq` had already landed --
   correctly re-deriving the numbers for that rebased state in the CODE
   (`BASELINE_TOTAL_STUB_CALLS=5018`, skip pin 21) but never updating THIS
   narrative section to match, leaving the two self-contradictory. The
   numbers actually in force today are the ones in the API status table
   at the top of this file and in `docs/PYTEST_SKIP_PINS.json`, not the
   5055/20 quoted above and below -- left uncorrected in place (this
   project's own house rule against silently rewriting a past round's
   measured record) rather than edited to look consistent in hindsight.

### Next round

1. **Whichever of the three named blockers clears first is the next
   round's first job** (same as round `4jsydv`'s own instruction) -- check
   fresh, do not re-quote this file.
2. If all three stay blocked: audit the remaining stub surface (72
   `Player.*` + the rest of `Quest.*`/`Mob.*`/etc.) by real call-volume
   (`run_corpus_entry_points`'s own ranking) for anything else that,
   like `CheckOpenTime`, turns out to need neither the state door nor a
   wire frame -- `Quest.GetWeekDay` is the next-highest such candidate but
   is RE-blocked (see above); nothing else in `Quest.*` qualifies (every
   remaining name needs the state door). Worth checking `Guild.*`/
   `Party.*`/`Instance.*`'s own low-call-count names for a similar
   pure-function candidate this lane has not audited yet.
3. Follow-up named but not built this round: `Quest.GetWeekDay`'s RE
   ticket (weekday enum semantics) could be folded into the same ask as
   `GetContactMode`'s, if COO judges one RE runner slot can cover both --
   not decided this round, flagged here for COO to rule on rather than
   this lane opening a second RE ask on top of round `4jsydv`'s already-
   pending one.

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

## Round ksp5d3 (2026-09-06) -- recovered #900, fixed the Windows gate failure it never got to explain

Round `0rgg6q`'s recovery of `Quest.CheckOpenTime` (PR #900) was itself
closed by the Windows gate going RED (`pf_bridge/notes_to_chief/
20260906_0830_SYNC-NOTICE-pirate-force-server-pr900-closed-never-merged.md`),
its branch (`claude/hopeful-hopper-0rgg6q`) kept intact per that notice.
Per the notice's own instructions, read the gate log for the failing
commit (run `34003119697`) rather than re-doing the round from scratch:
exactly one pytest failure, `RealQuestNamespaceTests
.test_default_clock_reads_the_bangkok_timezone`, `ModuleNotFoundError: No
module named 'tzdata'`, raised inside `_server_clock()`'s own
`ZoneInfo("Asia/Bangkok")` call.

**Root cause.** Windows' stdlib `zoneinfo` carries no system IANA tz
database (unlike Linux, which is why this passed in every prior round's
own cloud-clone run of the suite -- not a flake, a real platform gap).
Resolving a named zone there needs the `tzdata` PyPI package, which this
repository pins no dependency on at all yet. `lua_api/quest.py`'s own
module docstring already states Bangkok as "an explicit, stated
assumption" for the timezone; what it did not yet account for is that
Bangkok (ICT) has been a fixed UTC+7 offset with no DST since 1920 -- a
fixed-offset `timezone` object is exactly equal to the named zone for
this project's purposes, not an approximation standing in for it.

**Fix.** `_server_clock()` now catches `ZoneInfoNotFoundError`
specifically (any other exception still propagates -- a real bug
elsewhere, e.g. a future typo in `SERVER_TIMEZONE_NAME`, is not masked)
and falls back to `timezone(timedelta(hours=7))`. Added
`test_default_clock_falls_back_to_a_fixed_offset_without_tzdata`, which
reproduces the failure on any platform (points `SERVER_TIMEZONE_NAME` at
an unresolvable zone name) rather than relying on a Windows-only machine
to catch a regression here again.

Cherry-picked `0rgg6q`'s own two commits (`e52220a`/`fb71ba5`) onto
current `main` first -- clean, no conflicts (main had not touched
`Quest.*`/`Instance.*` since) -- then added this fix as a third commit.
`docs/SCRIPT_LANE.md`'s API status table above (147/160 stub, 13/160
real) already reflects `CheckOpenTime` as `real` from that cherry-pick;
this round does not change its status, only its portability.

### Nonclaims

1. Does not claim the Windows gate itself is green on this round's
   commit -- out of scope for this cloud clone; claims only that the one
   named failure's root cause is fixed and covered by a new test that
   reproduces it on any platform.
2. Does not touch any other `Quest.*` name, any other lane's write zone,
   or `runtime.py`/`app.py`/`store.py`.
3. Does not add the `tzdata` PyPI package as a dependency -- the fixed-
   offset fallback makes that unnecessary for this one name; a future
   round adding a dependency on `lupa` (already needed for the Lua host,
   still unpinned per round `s2fxf6`) may want to revisit whether pinning
   `tzdata` too is worth it for other timezone-sensitive code, not
   decided here.

### Next round

Same three named blockers as round `vqng2z` left open (trigger-id ->
script-file mapping / RE-273, LANE-DB's `Quest.*` state door, the
remaining 12 `Trigger.*` names) -- check each fresh per house rule, do
not re-quote this file.

## Round 92j6so (2026-09-06) -- re-checked the three named blockers fresh, one doc fix, closed the SCORECOUNT trace lead negative

### Blocker re-check (per `AGENTS.md` SS7's "do not trust a round file once it
is more than one round old")

1. `pirate-force-server#904` (round `ksp5d3`'s tzdata fix): confirmed merged
   -- `git merge-base --is-ancestor <904 head sha> origin/main` on this
   round's fresh `git fetch origin main`, `main` at `c16dbb4` already
   contains it (`c8c3227 Merge pull request #904`). No recovery needed this
   round.
2. `RE-273` (trigger-id -> `.lua` file mapping, `GetContactMode`'s own
   blocker, the one remaining named blocker of this lane's charter
   milestone): still `OPEN` in `pf_bridge/CLIENT_RE_QUEUE.md` line 1783 as
   of this round's own check (grepped fresh, not quoted from a prior round
   file). Nothing to do but wait for an RE runner slot.
3. `persistence_quest_state.py` (LANE-DB's per-character `Quest.*` state
   door): still does not exist anywhere in this repository (`find . -iname
   persistence_quest_state.py` and `git log --all --oneline -- '*quest_state*'`
   both empty this round). The remaining 24 `Quest.*` names stay blocked.

All three blockers unchanged versus round `ksp5d3`'s own re-check -- per
the standing backup rule, moved to the two items below instead.

### Small cleanup (pf-adversary's own follow-up from round `ksp5d3`)

Fixed `lua_api/quest.py`'s `_decode_hhmm` docstring: it claimed "lupa hands
every Lua number back as a float", which is empirically false for
`lupa==2.8`/Lua 5.5's integer subtype (an integer Lua literal comes back as
a Python `int`; only Lua-side arithmetic that produces a genuine float
comes back as one). No behavior change -- `_decode_hhmm` already accepted
both `int` and whole-number `float` before this fix; only the comment's
claim was wrong. Doc/comment-only, so not treated as requiring a fresh
`pf-adversary` pass this round (no production logic touched) -- flagged
here plainly rather than silently assumed exempt.

### Backup work: closed the `AddBonusPoint`/`AddBonusReward` SCORECOUNT
### trace lead that round `4fxvsq` left open, result is a clean negative

Both remaining blockers above stayed blocked, so per the standing backup
rule this round chased the one concrete, un-exhausted lead named in round
`4fxvsq`'s own "Next round" item 3: whether
`CONSTDATA_TH__INSTANCE.tsv`'s `n_SCORECOUNT_ID` column resolves to a real
`CONSTDATA_TH__SCORECOUNT.tsv` row for the instance(s) that run
`t_insbospnt_himdfx.lua`/`t_insbosev_himdfx.lua`/
`t_drp&insbospnt_himdfx.lua`.

**Result: it cannot be traced from anything committed to either repo.**
Grepped every `gamedata/tables/*.tsv` file and all 289
`gamedata/scene/*.placements.tsv` files for the three script names (bare,
no extension) -- zero hits anywhere outside the two files that are
themselves generated by scanning the `.lua` sources
(`PF_GAMEDATA_LUA_INDEX.tsv`, `PF_GAMEDATA_LUA_API.tsv`). Read
`gamedata/pf_extract_gamedata.py` (the tool that produced every scene TSV
in this repo) end to end: it has no code path that reads or emits a
trigger-to-script binding at all, only mob-placement records (confirmed
against every `*.placements.tsv` file sharing the same column header, none
of which has a trigger-name or script-id field). So the join key needed to
identify WHICH `CONSTDATA_TH__INSTANCE` row(s) run these three scripts does
not exist in any committed artifact -- this is not "the id was 0 or
ambiguous", it is that nothing here names these three scripts at all
outside their own source files.

The table mechanics themselves were also checked directly (not re-quoted
from round `4fxvsq`): `CONSTDATA_TH__INSTANCE.tsv` has 338 rows, 73 with a
nonzero `n_SCORECOUNT_ID`; every nonzero value does resolve to a real
`CONSTDATA_TH__SCORECOUNT.tsv` row on that table's own `n_ID` primary key.
But of those 87 SCORECOUNT rows, 79 hold the sentinel `4294967295` (unset)
in `n_COLLECT_BONUS_SCORE`; only 7 hold a real value (`5`), and the
`n_RANKC_REWARD`..`n_RANKSSS_REWARD` columns everywhere hold 7-digit
values that read as item-id references, not point counts (no `ITEM` table
cross-check done, out of scope for this question). So even a resolved row
would not obviously hand back a plain "bonus point" scalar.

Updated `lua_api/instance.py`'s module docstring and `STILL_STUBBED`
entries for both names to say this plainly -- this is now a closed dead
end for static tracing from committed data, not "unfinished work" the way
round `4fxvsq` left it. `AddBonusPoint`/`AddBonusReward` stay named stubs;
no behavior change, no test change (nothing about their observable
behavior moved, only the accuracy of the comment describing why they are
stubs).

### Tests

- `PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_quest.py tests/test_script_lua_api_instance.py -q -rs`
  (no `lupa` in this clone): `15 passed, 3 skipped, 37 subtests passed` /
  instance module unaffected (doc-only edit, no test file touched for it).
- Full suite, this round's final commit, `PYTHONPATH=src:tests python3 -m
  pytest tests/ -q`, on `origin/main` `c16dbb4`: `12071 passed, 369
  skipped, 23532 subtests passed in 469.37s`, exit 0.
- `python3 tools_bridge/pf_gate_preflight.py --repo .` (run from the
  `pf_bridge` sibling clone): PREFLIGHT PASS.

### ADVERSARY

Not run this round. Every change is a docstring/comment correction with
zero production-behavior delta (verified: `git diff` touches only string
literals inside docstrings and the `STILL_STUBBED` dict's own text; no
`if`/`return`/control-flow line changed in either file, and the full suite
above is byte-for-byte the same pass/skip shape modulo the one pre-existing
`CheckOpenTime`-area count). Treated as within `AGENTS.md` SS7's
"correcting a typo" exemption from the mandatory-adversary rule, stated
here explicitly per that rule's own "must say so, never silent" clause
rather than assumed quietly.

### `TWO_SESSIONS_SAME_SCENE:`

N/A -- no shared-world/scene state touched; both changes are docstring
text only.

### Nonclaims

1. Does not implement `AddBonusPoint`/`AddBonusReward` for real, and does
   not claim the SCORECOUNT trace failing means these two names can never
   be real -- only that static tracing from what is committed to either
   repo is exhausted; the recommendation below names the two remaining
   paths.
2. Does not claim the client's shipped binary does or does not execute
   real logic for these two names -- `PF_GAMEDATA_LUA_API.tsv`'s own
   `STUB_NOOP`/`delegate_va=0x0045FA00` rows for both are a committed
   static-image-derived claim this round only READ, not one it
   re-derived (no client binary exists in this cloud clone); that row's
   own source method (bulk-resolve vs. the verified RE-057 single-name
   method) was not re-checked either, named as an open question for
   whoever opens an RE ticket next.
3. Does not open a new `.npc` binary parser, and does not confirm whether
   the raw `Data/Scene/**/*.npc` source bytes (as opposed to this repo's
   already-extracted `.placements.tsv` files) exist anywhere in this
   clone -- out of scope for this round, named as one of the two paths
   forward.
4. Does not touch `RE-273`, LANE-DB's state door, `runtime.py`/`app.py`/
   `store.py`, or any other lane's write zone. No new mail arrived this
   round (`grep -rl "ADDRESSEE: LANE-Q" notes_to_chief/*.md`, skipping any
   with a `.CONSUMED.txt` stub, came up empty).
5. Does not claim `pirate-force-server`'s own PR for this round is merged
   -- only that it is open, not draft, with the full suite green and gate
   preflight passed on the final commit. Landing on `main` is next round's
   job to confirm.

### Recommendation for whoever picks up `AddBonusPoint`/`AddBonusReward` next

Two paths, named so the choice is a decision and not a re-discovery: (a) a
scoped RE ticket against the live client's raw scene/trigger definition
structure (needs the bridge machine, and needs to name a specific scene
first since the file names alone do not say which one runs these scripts),
or (b) accept the negative result and implement both names as pure
state-only stubs (same "advances an int, no invented game rule" shape
`CallScoreCount` already uses) without claiming any SCORECOUNT wiring --
explicitly documented as unresolved rather than guessed. Not decided this
round; a design call for whoever has charter priority on `Instance.*` next
(currently backup-work priority only, per the "Next round" item 4 rule
below and the two Trigger/Quest blockers still standing above it).

### Next round

1. Re-check the same three named blockers fresh again (do not trust this
   round's file once it is more than one round old): `RE-273`'s status in
   `CLIENT_RE_QUEUE.md`, `persistence_quest_state.py` landing on `main`
   (`git merge-base --is-ancestor`). Whichever clears first is the next
   round's first real-API job.
2. If both stay blocked: this round's own recommendation above is the
   fresh backup-work candidate (choose path (a) or (b) for
   `AddBonusPoint`/`AddBonusReward`) -- prefer it over a brand new stub
   audit, since the trace work is already done and named, not because a
   pure-function candidate audit elsewhere would be wrong to also try.
3. If path (b) is chosen: implement both as `InstanceRegistry`-backed
   counters (same shape `CallScoreCount` uses), one test module addition,
   and update the API status table above from `stub` to `real` for both
   rows -- but do NOT claim SCORECOUNT semantics in the commit message,
   docstring, or `docs/SCRIPT_LANE.md` entry; name the counter for what it
   counts (an invocation count, exactly like `CallScoreCount`), not for
   what round `4fxvsq` guessed it might mean.

## Round vmm7vf (2026-09-06) -- Instance.* reaches 9/9 real, path (b) chosen

Lock check at round start: GitHub search on `pf_bridge`, open PRs titled
`[LANE-Q] round *: claim` -- zero found, lock free. Mailbox check
(`grep -rl "ADDRESSEE: Q" notes_to_chief/*.md`) -- zero unconsumed letters.

Re-checked both of the lane's two remaining named blockers fresh, per
`prompts/COMMON_LANE_ROUND.md`'s priority order and round `92j6so`'s own
"Next round" list:

1. `RE-273` (the trigger-id-to-lua-file mapping, the one remaining blocker
   of the charter's own M2 milestone sentence): still `OPEN` in
   `pf_bridge/CLIENT_RE_QUEUE.md` line 1783 as of this round's own grep.
   Its own `[STATIC-ON-BRIDGE]` first path is explicitly noted in that
   ticket as needing a pass "beside the bridge's own client copy", which a
   cloud clone with no `GameClient` binary cannot do -- still blocked,
   waiting on an RE runner slot or the bridge-side static pass, not on
   this lane.
2. `persistence_quest_state.py` (LANE-DB's per-character `Quest.*` state
   door): `find` across `pirate-force-server` and `git log --all --oneline
   -- '*quest_state*'` both still empty. Still not landed; the remaining
   24 `Quest.*` names stay blocked.

Both unchanged versus round `92j6so`. Per the standing backup rule, this
round picked up round `92j6so`'s own named recommendation for
`Instance.AddBonusPoint`/`AddBonusReward`: two forward paths, (a) a scoped
RE ticket, or (b) accept the SCORECOUNT trace's negative result and
implement both as pure invocation counters with no reward semantics
claimed. This round chose **path (b)**, per the "Next round" item 3 spec
directly above.

### What was built

- `InstanceRegistry.add_bonus_point(instance_id, point_arg=None)` and
  `.add_bonus_reward(instance_id)`: two new per-instance-id counters, same
  cap/refusal shape as the existing `call_score_count`/`set_lasting_time`
  (bad instance id or a full book both degrade to `STUB_DEFAULT`, never
  raise). `add_bonus_point`'s second argument is accepted (both real call
  shapes in the corpus -- zero args in `t_drp&insbospnt_himdfx.lua`, one
  arg, `Trigger.Var1`, in `t_insbospnt_himdfx.lua` -- are real, not
  hypothetical) and discarded unread: the argument's meaning is still
  unknown (point value vs. bonus-category id), and this round does not
  guess it.
- Two new dispatch handlers in `RealInstanceNamespace.__getitem__`,
  `AddBonusPoint` (arity 0 or 1) and `AddBonusReward` (arity 0 only,
  matching its one real call site), same `LUA_INSTANCE_REAL`/
  `LUA_INSTANCE_BAD_ARITY` logging contract every other real `Instance.*`
  name already uses.
- Both names moved from `STILL_STUBBED` (now empty) to `REAL_METHODS`.
  `Instance.*` is 9/9 real as of this round -- the first namespace in this
  lane's charter to reach 100%.
- `tests/test_script_lua_api_instance.py`: six new registry-level tests
  (tally-per-instance, argument-independence from `add_bonus_point`,
  independence from the pre-existing `call_score_count` counter, bad-
  instance-id refusal for both, per-instance cap enforcement for both) and
  two new namespace-level tests (both real corpus call shapes for
  `AddBonusPoint`, a plain round-trip for `AddBonusReward`), plus the
  arity-guard and correct-arity tests extended to cover both new names.
  The two tests that had hardcoded `AddBonusPoint` as a still-stubbed
  worked example were replaced -- one now asserts `STILL_STUBBED == {}`
  instead.

### What this does NOT do, said plainly

Does not implement any SCORECOUNT-table lookup, does not compute or award
an actual point value or item, and does not resolve which
`CONSTDATA_TH__SCORECOUNT.tsv` row (if any) either calling script's
instance actually uses -- round `92j6so`'s trace stands, unchanged, as a
closed dead end for static tracing. The day path (a) (an RE ticket) or a
new `.npc` scene parser answers that question, this counter is what gets
replaced, not extended. Does not move `RE-273` or land
`persistence_quest_state.py` -- both re-checked fresh this round and both
still blocked, unchanged from round `92j6so`.

### Tests + gates

- `PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_instance.py
  tests/test_script_lua_api_trigger.py tests/test_script_lua_api_quest.py
  tests/test_script_host_spike.py tests/test_script_lua_corpus.py -q -rs`
  (no `lupa` in this cloud clone, same gap every prior round has recorded):
  `84 passed, 42 skipped, 67 subtests passed`.
- Full suite and `pf_gate_preflight.py` run as the last commit before push,
  per `prompts/COMMON_LANE_ROUND.md`'s "before push" ordering -- see this
  round's `pf_bridge/rounds/Q_*.md` file for the exact counts (kept out of
  this design doc so this doc does not need editing every round just to
  restate a number the round file already owns).

### ADVERSARY

`pf-adversary` invoked at round start (own isolated git worktree) against
the new registry methods, dispatch handlers, and tests. Result returned
before push -- two confirmed findings, both fixed in a follow-up commit
before this round closed:

1. `call_score_count`'s own docstring still said "`AddBonusPoint`/
   `AddBonusReward` (which stay named stubs, see `STILL_STUBBED`)" -- a
   stale cross-reference this round's own diff made false three lines
   away from the correctly-updated module docstring. Fixed.
2. `test_every_still_stubbed_name_is_reachable_and_logs_its_own_line`
   iterates `for name in instance.STILL_STUBBED`, which this round's own
   change emptied -- the loop became silently vacuous (0 iterations,
   always green, no assertion ever executes) the moment `STILL_STUBBED`
   became `{}`. Removed; the sibling `test_still_stubbed_is_empty_now_
   all_9_names_are_real` already covers the fact directly.

No concurrency bug, sandbox-escape, or arity/coercion defect found:
adversary stress-tested `add_bonus_point`/`add_bonus_reward` with 32
threads x 5000 calls (exact tally, no lost updates) and fuzzed
`AddBonusPoint`'s discarded argument (NaN/inf, huge ints, objects with a
raising `__repr__`) with no crash. Adversary also flagged (informational,
not blocking) that this counter has no named trigger for ever being
revisited if the SCORECOUNT join stays unresolved -- recorded here so it
is a decision for whoever next has charter priority on `Instance.*`, not
silently forgotten: the trigger is either path (a) (an RE ticket answer)
or a new `.npc` scene parser landing, per this doc's own recommendation
above; absent either, this counter is the permanent real implementation
by design, not a placeholder with an unstated expiry.

### Recommendation for whoever finishes `Trigger.*`/`Quest.*` next

`Instance.*` is now fully real and out of this lane's remaining work
entirely (no rows left in `STILL_STUBBED` for it). The lane's only two
named blockers are `RE-273` (12 `Trigger.*` names) and
`persistence_quest_state.py` landing (24 `Quest.*` names) -- both are
external dependencies, not audit work. The next backup-work candidate,
absent either clearing, is a fresh pure-function stub audit across
`Guild.*`/`Party.*`/`Mob.*`/`Player.*` for a name with the same
"unambiguous from every call site, no state door needed" shape
`Instance.*`'s first seven had -- not attempted this round, named here so
it is a decision for whoever picks it up next, not a re-discovery.

## Round gk0dz4 (2026-09-06) -- recover #915, fix stale REAL_METHODS guard, Instance.* 9/9 lands

`pirate-force-server#915` (round `vmm7vf`, above) was closed unmerged by
the gate's one-open-`claude/*`-pull-request lock after a real test
failure (job `34013631038`, head `e9dedc8`) --
`pf_bridge/notes_to_chief/20260906_1246_SYNC-NOTICE-pirate-force-server-pr915-closed-never-merged.md`.
This session's own branch is fixed by its harness rather than freely
assigned, so recovery here is by cherry-picking `vmm7vf`'s four kept
commits from `claude/happy-tesla-vmm7vf` (base `4e64b7d`, already an
ancestor of `main` at cherry-pick time) onto this branch, unchanged, then
fixing the actual cause in one more commit.

**Root cause**: round `vmm7vf` widened `lua_api/instance.REAL_METHODS`
from 7 to 9 names and correctly updated
`tests/test_script_lua_api_instance.py`, but left a second, independent
regression guard on the same constant --
`tests/test_script_host_spike.py`'s
`test_the_7_real_instance_names_are_excluded_above_not_forgotten` --
unrenamed and unwidened. That guard exists specifically to catch
`REAL_METHODS` drifting without its own update; it caught its own
author's drift, via the gate's `pytest_subset` step and independently via
`PinFileTests` in `tests/test_pytest_precondition_census.py` (which checks
the pin file's recorded test names against the source).

**Fix**: renamed the guard to
`test_the_9_real_instance_names_are_excluded_above_not_forgotten`,
extended its frozenset with `AddBonusPoint`/`AddBonusReward`, and updated
`docs/PYTEST_SKIP_PINS.json`'s `lupa_package` pin for that module to the
new name (count unchanged at 21 -- rename only).

### ADVERSARY

`pf-adversary` invoked at the point this round found the root cause (own
isolated worktree, detached at the fix commit). Result: **no real defects
found**. Independently read `lua_api/instance.py`'s actual `REAL_METHODS`
(not the commit message) and confirmed the renamed guard's frozenset
matches it member-for-member; `git grep`'d the whole tree for the old test
name and found only the already-correct pin-file rename plus one
historical-narrative reference in this doc's own `vmm7vf` section above
(left alone, correctly, as an accurate record of what that round did at
the time); verified `PYTEST_SKIP_PINS.json` stays valid JSON with its
`lupa_package`/`test_script_host_spike.py` entry's `count` (21) matching
its `tests` array length; ran the three affected test files clean (106
passed, 25 skipped for missing `lupa`, 1103 subtests, 0 failed); and
proved the fix is not vacuous by reverting just the frozenset body while
keeping the rename, which reproduced a fresh, correct failure (calling the
test function directly, bypassing `unittest`'s class-level skip
dispatch, since this interpreter has no `lupa`).

Adversary raised one open, unresolved design question rather than a
defect, recorded here verbatim rather than answered: is there a static
check (beyond each module's own hand-maintained guard test) that would
catch the *next* time a `REAL_METHODS`/`STILL_STUBBED`-shaped set in any
`lua_api/*.py` module widens without its sibling guard test in
`test_script_host_spike.py` being updated -- or does every future
widening rely on a human (or another gate run) noticing the same two-file
coupling by hand, as happened here? Named as a decision for whoever next
touches this pattern, not resolved this round.

### Tests + gates

Full suite, `PYTHONPATH=src:tests python3 -m pytest tests/ -q -rs`, run
three times this round on progressively later trees: once on the four
cherry-picked commits alone (`1 failed` -- reproduced the exact original
gate failure, confirming root cause before any fix); once after the fix,
before merging `origin/main` a second time (`12209 passed, 369 skipped,
25084 subtests passed`); once more on the final tree after merging
`origin/main` again mid-round (LANE-A's `#919` landed, zero file overlap):
`12258 passed, 369 skipped, 25095 subtests passed in 607.15s`, exit 0.
`python3 tools_bridge/pf_gate_preflight.py --repo ../pirate-force-server`
(from `pf_bridge`): PREFLIGHT PASS, re-verified after each merge.

### Recommendation for whoever finishes `Trigger.*`/`Quest.*` next

Unchanged from round `vmm7vf`: this lane's only two named blockers are
`RE-273` (still `OPEN`, needs the bridge's own client copy) and
`persistence_quest_state.py` landing (still does not exist anywhere in
this repository) -- both re-checked fresh this round. `Instance.*` stays
9/9 real; this round changed no API behavior, only recovered the already-
real work's path onto `main` and fixed the test-suite regression that had
blocked it.

## Round bxly5p (2026-09-06) -- first live wire into TriggerStatusRegistry (plumbing, not a new real name)

**Both named blockers re-checked fresh, both still open, both re-confirmed
with a new fact each**, before doing anything else this round:

- `RE-273` result letter landed since round `gk0dz4`
  (`pf_bridge/notes_to_chief/
  20260906_1340_RE-273-RESULT-TGR-FILE-IS-THE-TRIGGER-ID-TO-LUA-TABLE.md`):
  every scene's `.tgr` file DOES carry a trigger-ordinal -> `.lua` filename
  table (267 files, 3,942 records, 156 of 160 unique script names match a
  real `gamedata/lua/t_*.lua` file) -- but the letter's own "what this
  ticket does not answer" section is explicit that the `.tgr` ordinal has
  **not** been shown to be the same number as the wire `TriggerVital`
  (0x1FB2) frame's own `0x0F` tag value (`lane_a_island_trigger_log.py`'s
  own R308 measurement: wire ids observed so far are 2 and 3, small
  per-scene integers, same SHAPE as a `.tgr` ordinal but not proven the
  SAME NUMBER SPACE). Guessing they are equal is exactly the "same because
  the numbers look alike" pairing `AGENTS.md` Section 7 forbids. This
  round's decision (see letter to chief/K below, and RE-273's own
  "สถานะที่ขอให้ chief พิจารณา"): continue the SAME ticket, narrowed to the
  one remaining question, `[STATIC-ON-BRIDGE]`, no game boot needed --
  disassemble the `.tgr` loader / `TriggerVital` dispatch in the client
  image for the field that carries an ordinal across that boundary, per
  RE-273's own suggested path 1.
- `persistence_quest_state.py`: re-confirmed absent
  (`grep -rln "persistence_quest_state\|character_quest_state" src/` = 0
  hits, `migrations/` still ends at `014_character_skills_learned_source.
  sql`, no `015`). Root cause, traced through the bridge's own letters
  this round (`pf_bridge/notes_to_chief/
  20260906_0108_LANE-DB-REPORT-COO-863-merged-2354-consumed-
  migrate_with_backup-question-closed-empty-round.md`): the code LANE-DB
  built for this (migration + module + 5 store methods + 59 tests) lived
  only in that session's own scratchpad and was lost when the session
  ended, because chief's own guard whitelist for DB's module names
  (`COO-DECISION 20260905_2353` item, "chief reads and whitelists") has
  not landed since -- this is a DB/chief-side blocker, not something this
  lane's write zone can build (`src/pirateforce_foundation/lua_api/`, not
  `store.py`/`migrations/`).

**What this round built instead, in its own write zone, needing neither
blocker**: `lane_hooks/lane_q_trigger_vital_dispatch.py` -- the first
production wiring from a real inbound `TriggerVital` frame into
`lua_api.trigger.trigger_status_registry()`, the exact process-memory book
`Trigger.GetTriggerStatus`/`SetStatus`/`NextStatus` already read and write
when a script calls them. LANE-A's own letter this round
(`pf_bridge/notes_to_chief/
20260906_0727_LANE-A-TO-LANE-Q-world-registry-interface-and-trigger-hit-
hook-point.md`) named the hook point (`vital_inbound_trigger_vital`,
already wired live in `runtime.py` by LANE-A/chief) as safe to share
without asking permission per round; this module registers on it (picked
up automatically by `lane_hooks`'s own `pkgutil.iter_modules` discovery,
no call-site change needed) and, on every real frame, reads the wire's own
`0x0F` trigger id (via `lane_a_island_trigger_log.first_tag_value`, the
already-proven walker -- not a second parser), resolves the session's
scene through `world_scene_folder.scene_folder_for_scene_id`, and advances
the registry keyed by (scene folder, WIRE id) -- named in both the module
and every log line as `WIRE_NATIVE_ID_UNPROVEN_VS_TGR_ORDINAL`, so nothing
downstream can mistake this key for a proven `.tgr` crosswalk.

**What this is not, said plainly**: no `.lua` file is looked up or run; no
`REAL_METHODS` count changed (still 5/17); nothing reaches the client;
nothing is player-visible yet. It is COMING, not DONE (see this round's own
`rounds/Q_*.md` SCOREBOARD line) -- real, tested, live-wired plumbing that
the still-missing script dispatch will need regardless of how the ordinal
question resolves, since something has to turn a wire frame into a
registry key before any script logic can run at all.

### Tests + gates

New file `tests/test_lane_q_trigger_vital_dispatch.py` (12 tests): the pure
`dispatch_line` function (real R307 capture frame payloads, reused verbatim
from `tests/test_lane_a_island_trigger_log.py` rather than invented bytes)
covering a resolved hit, two hits on the same key advancing by one each,
two different wire ids in one scene not colliding, the same wire id in two
scenes not colliding, a missing trigger-id tag, a session missing the
attribute chain, a `None` session, a `bool` scene id (refused the same way
every `_coerce_int` door in this codebase refuses one), and an unaddressed
scene id -- plus three tests through `lane_hooks.fire()` itself (the actual
call shape `runtime.py` uses): the hook fires and writes the registry, a
non-bytes payload does not raise out of `fire()`, and LANE-A's own hook
still fires alongside this one on the same point. Ran alone first (12
passed), then with the neighboring trigger/hook test files
(`test_lane_a_island_trigger_log.py`, `test_script_lua_api_trigger.py`,
`test_script_host_spike.py`, `test_lane_a_trigger_vital_dispatch_wiring.py`,
`test_dispatch_nested_vital_visibility.py`): all passed, no regressions
(counts in the round file). `PYTHONPATH=src python3 -m pirateforce_foundation.
gm.lane_gate_name_audit` (the point-name-agreement guard both this file's
own module docstring and `lane_a_island_trigger_log.py`'s cite) ran clean,
exit 0, and printed `LANE_HOOK_REGISTERED ...lane_q_trigger_vital_dispatch
vital_inbound_trigger_vital` alongside LANE-A's own registration on the same
point.

### ADVERSARY

`ADVERSARY_UNAVAILABLE` this round (ToolSearch found no `pf-adversary` tool
in this session). Self-review performed per `AGENTS.md` Section 7's
fallback: read every hunk of `git diff --cached` before each commit;
re-derived the wire trigger ids by hand from the raw frame bytes
(`0F 28 00` -> tag 0x0F, u16 LE `28 00` = 40; `0F 33 00` -> 51) rather than
trusting the module's own arithmetic, and asserted those exact literals in
the test file; deliberately fed the dispatcher a `bool` scene id, a `None`
session, a bare `SimpleNamespace()` with no attributes, and a non-bytes
payload through the real `lane_hooks.fire()` entry point (not just the
pure function) to confirm the fail-closed contract holds at the actual
call shape production uses, not only in the unit under test. Next round
for this lane should invoke `pf-adversary` on this branch as its first
action, per house rule, before claiming new work.
