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
`StartTriggerAnimation`, `HideModel`, `HideTriggerModel` (each needs a
wire frame encoder this server does not have; `TriggerShowMessage`, listed
here when this section was written, went real in round `6775u1` -- it needs
no encoder because it records a message id rather than building a frame); `QuestActiveProgress`, `QuestFinishProgress` (needs per-character
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

### API status table (126/160 stub, 34/160 real, as of round `wn088m`)

**Round `wn088m` changed no status.**  It changed a NUMBER: the six
criteria rows were flooring the wrong float.  `f_EXP` is a float32 column,
so `1.4` reaches the mirror as `1.399999976158142`; `int(base * that)`
floors to one LESS than the intended reward whenever the true product is
whole.  Measured on the shipped mirrors: **14 of the 4632 plain-triple
resolutions** (quests 2170-2177, `Exp` and `SkillPoint`) and **3632 of the
1181160** `(row, level)` products a player-level triple can reach.
`0.1`/`0.3`/`0.85` widen UPWARD and never lost a unit, which is why only
`1.4` shows and why this survived a round.  The mirror was NOT hand-edited
(a mirror that differs from its source is not a mirror):
`quest_criteria.multiplier_decimal()` recovers, at parse time, the
shortest decimal that round-trips through float32 to the same bits, and
the product is taken in `Decimal`.  All 12 distinct multipliers in the
mirror are exactly float32 (tested), which is the evidence the recovery
reads a float32 column rather than inventing precision.

Rounding itself is now **floor at exactly one place** --
`quest_criteria.ROUNDING_MODE` / `round_amount()`, with a test asserting
the module contains exactly one `to_integral_value` -- per COO-DECISION
`20260907_0845`.  That letter chose floor as an INTERIM and forbids
writing "the client floors" anywhere as a fact; the RE ticket body sent to
LANE-K this round (`notes_to_chief/20260907_0905_LANE-Q-TO-K-re-body-how-
the-client-rounds-and-where-Lv-reads-level.md`) is what would make it
measured.  The same letter re-labelled the level-source mapping from a
lane assumption to `[COO-ASSUMPTION 0845 - NOT A PROOF]`; the refusal when
a player level is unknown stays, and may not be softened into a fallback.

Six of the 126 stub rows now read `stub (+reward line)`: the three
`Quest.AddCriteria*` and three `Quest.AddLvCriteria*` names.  That is a
THIRD status, deliberately, and it is not a softer word for `real` -- the
grant still does nothing and still logs `LUA_API_STUB`, so the count above
is unchanged at 34/160.  What changed is that each of them now also logs
one `LUA_QUEST_CRITERIA` line: the exact reward it WOULD have paid,
resolved out of the game's own two tables, or the reason it refused.

🔴 **Read that as "+reward line", not "amount real", because against the
shipped corpus TODAY the line is always a refusal.**  Measured, not
assumed (pf-adversary, this round): 12 real corpus files, 36 criteria call
sites, **36 of 36 `refused=no_quest_row`**, and the same holds for all 225
criteria call sites in all 616 files.  The reason is one number: nothing
supplies a quest id.  `Quest.AddCriteriaExp()` takes no arguments because
the ENGINE knows which quest instance dispatched the script; this server
has no such dispatch, so `QuestContext` defaults to `quest_id=0` and the
mirror's lowest id is 12.  The read half is therefore complete and tested
and reaches nobody until a dispatcher exists -- which is the honest state,
and the next thing this lane needs.

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
non-claim), the 10 `Quest.*` real rows (`CheckOpenTime` -- round `0rgg6q`,
recovering the round-after-`4jsydv` commit that the guard exemption named
below unblocked, see "Round vqng2z" further down -- plus 9 flag/counter/
daily-stamp names added round `7v7yn2`, COO-DECISION `20260906_1846`, see
"Round 7v7yn2" below) by `tests/test_script_lua_api_quest.py`, the 6
`Player.*` real rows (`GetLv`, `GetClass` from round `gqjas5`,
`CheckItemNum`/`GetItemNum`/`CheckEquipItem` -- the inventory seam's read
side, round `qbr5h8` -- plus `MobAppear`, a per-player visibility FLAG
NOT a world spawn, round `x6gxzd`, COO-DECISION `20260907_0043`, see
"Round x6gxzd" below) by `tests/test_script_lua_api_player.py`, and the 7
`Trigger.*` real rows (the original 5 plus
`QuestActiveProgress`/`QuestFinishProgress`, round `7v7yn2`, sharing
`Quest.*`'s own state door) by `tests/test_script_lua_api_trigger.py` /
`proven` (real + a GT ticket where a tester watched it work on screen --
none yet).  Next lane priority, per charter and `COO-DECISION
20260906_1846`'s system-wide ranking: the remaining 10 `Trigger.*` rows
(`GetContactMode` needs no RE ticket any more -- `RE-285` closed that
path negative, see "Round lvoma1" below; the rest need wire-frame
encoders this lane does not own), then the rest of `Quest.*` (15 names:
`CountDownTime`/reward-and-grant names still need a LANE-DB column or a
`Player.*` grant seam this lane does not own yet, `GetWeekDay`/
`CheckWishQuest` on undocumented enums/cross-lane guild state -- see
"Round 7v7yn2" below), then the rest of `Player.*` (67 names, grouped by
blocker in `lua_api/player.py`'s own `STILL_STUBBED` -- item/equipment
WRITE state (the inventory seam's write side, blocked on `RE-280`), a
stat-grant write seam, other per-character stat reads, skill/buff state,
teleport/vehicle/camera frames, UI/cutscene frames, and the instance-entry
frame).  `Instance.*` is now 9/9 real -- no rows of that namespace remain
in `STILL_STUBBED`.

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
| Player | MobAppear | 3532 | real |
| Player | AddItem | 1430 | stub |
| Player | RemoveItem | 367 | stub |
| Player | CheckItemNum | 211 | real |
| Player | GetItemNum | 99 | real |
| Player | GetLv | 91 | real |
| Player | CastSkillAt | 69 | stub |
| Player | ShowMessage | 61 | real |
| Player | GetClass | 60 | real |
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
| Player | CheckEquipItem | 14 | real |
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
| Quest | GetQuestFlag | 508 | real |
| Quest | SetFlag | 417 | real |
| Quest | AddCriteriaExp | 166 | stub (+reward line) |
| Quest | AddCriteriaSkillPoint | 166 | stub (+reward line) |
| Quest | AddCriteriaCash | 165 | stub (+reward line) |
| Quest | CheckMobKillCount | 138 | real |
| Quest | MobKillCount | 128 | real |
| Quest | PlayNPCMovie | 100 | stub |
| Quest | SetQuestFlag | 90 | real |
| Quest | GetFlag | 67 | real |
| Quest | CanReportDailyQuest | 61 | real |
| Quest | ReportDailyQuest | 61 | real |
| Quest | AddLvCriteriaExp | 59 | stub (+reward line) |
| Quest | AddLvCriteriaSkillPoint | 59 | stub (+reward line) |
| Quest | AddLvCriteriaCash | 58 | stub (+reward line) |
| Quest | CountDownTime | 54 | stub |
| Quest | GetWeekDay | 48 | stub |
| Quest | GetMobKillCount | 20 | real |
| Quest | CheckOpenTime | 9 | real |
| Quest | PlayNPCVoice | 8 | stub |
| Quest | CheckGuildOfflineQuest | 1 | stub |
| Quest | CheckWishQuest | 1 | stub (refused; see round Q_<this round> -- no table/doc defines "wish", needs RE) |
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
| Trigger | TriggerShowMessage | 55 | real |
| Trigger | SetTriggerStatus | 52 | real |
| Trigger | StartTriggerAnimation | 43 | stub |
| Trigger | StartAnimation | 19 | stub |
| Trigger | HideTriggerModel | 13 | stub |
| Trigger | CastSkillXYZ | 11 | stub |
| Trigger | CastSkill | 9 | stub |
| Trigger | QuestActiveProgress | 8 | real |
| Trigger | CastSkillBy | 5 | stub |
| Trigger | QuestFinishProgress | 3 | real |
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

## Round 7v7yn2 (2026-09-06) -- flag-quest-state, 9/25 more Quest.*, 2/17 more Trigger.* real

**Deliverable, per COO-DECISION `20260906_1846`**: `GetQuestFlag`/`SetFlag`/
`SetQuestFlag`/`GetFlag`/`MobKillCount`/`CheckMobKillCount`/`GetMobKillCount`/
`CanReportDailyQuest`/`ReportDailyQuest` (`Quest.*`, now 10/25 real) and
`QuestActiveProgress`/`QuestFinishProgress` (`Trigger.*`, now 7/17 real),
all backed by a new injectable `lua_api.quest.QuestStateStore` seam
(`QuestContext`, the `QuestStateStore` `Protocol`, and
`InMemoryQuestStateStore` -- explicitly NOT the production persistence
answer). Full grep evidence, the exact 9-name derivation from
`Quest/q_kill5.lua` and 68 sibling files, and `Quest.None`/`Active`/
`Finish`'s derivation (0/1/2, the first two proven by a cross-script
correlation between `t_opnq_t1.lua`/`t_clsq.lua` -- previously all three
silently collapsed to `STUB_DEFAULT`, a real bug this round fixed): both
modules' own updated docstrings.

**Refused, one name short of COO's 12**: `CheckWishQuest`. A first grep
pass (filenames + a column named after the quest) found nothing and an
early draft of this round said so; pf-adversary caught that this was
wrong -- a wider pass over TABLE CONTENTS finds
`CONSTDATA_TH__VARIABLE_INTEGER.tsv`'s `GUILD_MAKEWISH_GUILDLV`/
`GUILD_MAKEWISH_CDTIME`, `CONSTDATA_TH__GUILD_MEMBER.tsv`'s
`f_CharWish_Chance`, and `TEXTDATA_TH__HELP_CONTENT.tsv` row 2028's own
description of a guild "Wishing Crystal" mechanic. The corrected reason:
this is CROSS-LANE with LANE-GUILD (which of a guild-level floor, a
1200-unit cooldown, or a chance roll gates quest ACCEPTANCE is not pinned
by any single table row, and the guild-level check needs a `Guild.*`/
`Player.*` accessor this lane has no seam for), not "undocumented" --
same refusal category as `CheckGuildOfflineQuest`/`ReportGuildOfflineQuest`/
`StartGuildOfflineQuest`, corrected reasoning in `lua_api/quest.py`'s own
`STILL_STUBBED` dict.

**NOT done this round, said plainly**: no production persistence
(`InMemoryQuestStateStore` does not survive a relog -- a CORE-REQUEST
asks chief for the real DB-backed accessor); no live dispatch (nothing
binds a script run to a real player session yet); `script_host.ScriptHost`
does not share one `QuestStateStore` between its `Trigger`/`Quest`
namespaces (a first draft did, reverted before push -- it trips
`tests/test_npc_interaction_wire.py`'s foundation quest/shop guard, a
second CORE-REQUEST asks chief for that exemption, same pattern round
`vqng2z` used successfully); `MobKillCount`'s `target` argument is not
persisted (only progress, reset to 0, is -- every corpus call site
re-supplies the same literal to `CheckMobKillCount` directly); no
player-visible impact yet (no wire frame changes, no live dispatch).

### Tests + gates

`tests/test_script_lua_api_quest.py` (new `QuestFlagAndCounterTests`, 15
tests) and `tests/test_script_lua_api_trigger.py` (3 new tests) exercise
every newly-real closure directly. Ran the full 616-file corpus through
`script_host.run_corpus_entry_points` (`lupa==2.8` installed this
session) against a fixed clock: no regression in
`KNOWN_LOAD_FAILURES`/`KNOWN_ENTRY_POINT_CALL_FAILURES`;
`BASELINE_TOTAL_STUB_CALLS` re-measured 4937 -> 3931 (measured, not
computed by hand -- see `tests/test_script_lua_corpus.py`'s own updated
comment for the exact breakdown and the branch-shift phenomenon this
produced in `Player.GetClass`'s own count, untouched this round).
`q_kill5.lua`'s own full-lifecycle test updated: `MobKillCount`/`SetFlag`/
`CheckMobKillCount` moved from the expected-stub set into an asserted
real-call set. `docs/PYTEST_SKIP_PINS.json` updated for two renamed
regression-guard test names. Full `pytest tests/` (12,495 passed) run on
this branch as the last commit before push.
`python3 tools_bridge/pf_gate_preflight.py --repo ../pirate-force-server`:
PREFLIGHT PASS.

### ADVERSARY

Invoked at round start. Findings: two would-be-red test failures (the
foundation quest/shop guard trip from the reverted `ScriptHost` wiring,
and a stale `docs/PYTEST_SKIP_PINS.json` entry from a test rename) --
both already fixed before the adversary's own report landed, confirmed
independently re-verified by it afterward. Two real findings fixed
after the report: the `CheckWishQuest` refusal reason was factually
wrong (see above); this file's own status-table header and prose were
stale (still said "17/160 real" and "the one `Quest.*` real row" inside
the same commit that made 11 more names real). One minor finding not
fixed this round (logged as a next-round item below): 9 of the 11 new
real closures do not log a line on a same-arity-but-bad-VALUE call
(e.g. NaN/negative/oversized), unlike `GetQuestFlag`'s own precedent --
not a crash risk (fuzzed through real Lua, never raises), an
observability gap.

### รอบหน้าทำอะไร

1. Check both CORE-REQUEST letters (persistence accessor, guard
   exemption) and act on whichever answered.
2. Add a bad-VALUE log line to the 9 closures pf-adversary named, matching
   `GetQuestFlag`'s own pattern, for observability parity.
3. `CheckWishQuest` needs LANE-GUILD's own state door or an RE ticket
   before it can go real -- not blocking, 1 call site.
4. Per `COO-DECISION 20260906_1846`'s ranking, item 2 (`inventory seam`,
   read side) is next once this item closes, except the write side
   (blocked on `RE-280`).

SCOREBOARD: COMING | ผู้เล่นยังไม่เห็นอะไรใหม่บนจอ -- ตรรกะฝั่งเซิร์ฟเวอร์ของ 9 Quest.* + 2 Trigger.* ถูกต้องและมีเทสยืนยันแล้ว แต่ยังไม่ต่อกับ session ผู้เล่นจริงและยังไม่มีที่เก็บถาวรข้าม relog | pirate-force-server PR, quest-flag fns real 9/12, Trigger fns real 2/2
## Round qbr5h8 (2026-09-06) -- Player.* inventory seam, read side: CheckItemNum/GetItemNum/CheckEquipItem real

**Charter priority for this round, per `COO-DECISION 20260906_1846`'s
system-wide ranking** (mailbox was empty this round -- every LANE-Q letter,
`pf_bridge/notes_to_chief/20260906_1846_COO-DECISION-q1812-host-api-map-
ranking-LANE-Q.md` included, already carries a `.CONSUMED.txt` twin;
`1846` itself was consumed by round `7v7yn2`, which acted on its item 1.
This round's authority is `pf_bridge/rounds/
Q_20260906_1950_7v7yn2_flag-quest-state.md`'s own "รอบหน้าทำอะไร" section,
citing `1846`'s item 2 as next -- see that round file's own mailbox
correction for the full story): item 1 (flag-quest-state) closed last
round (`7v7yn2`, PR pirate-force-server#947, still open pending gate at
this round's own start -- not this round's lock, not waited on, per house
rule); item 2 is "inventory seam, **read side first**":
`Player.CheckItemNum`/`GetItemNum`/`CheckEquipItem` bound to
`inventory.py`/`store.py`'s existing types, no byte-guessing; the WRITE
half (`AddItem`/`RewardItemSelect`/`AddAndEquip`) stays explicitly blocked
on `RE-280` per that same letter and is untouched this round.

### What was built

`src/pirateforce_foundation/lua_api/player.py`'s `PlayerContext` widens by
two fields -- `backpack: inventory.BackpackState` and
`equipped_template_ids: frozenset[int]` -- both defaulting to empty (no
items, no equips), the same "inert default, not a guess" posture
`level`/`class_id` already established. Three new real closures:

- `GetItemNum(templateId)` (99 calls/72 files, arity 1) -- sums
  `ItemAttrState.quantity` across every backpack row whose `template_id`
  matches (a stack split across two rows, e.g. a pre-merge V111 bag, adds
  up; grepped call sites, e.g. `Quest/q_gather_new.lua:205`, always assign
  the result into a local for later comparison, never read it as a bool).
- `CheckItemNum(templateId, count)` (211 calls/105 files, arity 2) --
  `GetItemNum(templateId) >= count`, matching every grepped call site's own
  boolean-gate usage (e.g. `Quest/q_guildgather1.lua:41`,
  `if(Player.CheckItemNum(Quest.Var2,Quest.Var3))and...`).
- `CheckEquipItem(templateId)` (14 calls/2 files, arity 1) -- template-id
  membership in `equipped_template_ids`, matching the only two files that
  call it (`Quest/q_kill1_2.lua`, `Quest/q_con3.lua`, both OR/AND-chaining
  several literal template ids as a plain boolean).

All three fail closed exactly like every other real closure in this
package: wrong arity logs `LUA_PLAYER_BAD_ARITY` and returns
`STUB_DEFAULT`; an argument that will not coerce to a bounded int (own
`_coerce_int`, identical shape to `lua_api.trigger._coerce_int`, kept as a
separate copy per this package's own established no-cross-namespace-import
convention) makes `GetItemNum` answer 0 and `CheckItemNum`/`CheckEquipItem`
answer `False` rather than raising or guessing.

**What this round does NOT do, said plainly**: no live dispatcher exists
yet (same gap `GetLv`/`GetClass` already documented) -- nothing calls
`store.get_backpack`/`store.list_equipped_items` and builds a real
`PlayerContext` from an actual session; every test today (unit and Lua)
supplies its own `PlayerContext` directly. `store.py`/`migrations/` are not
this lane's write zone and were not touched. The write half of the
inventory seam (`AddItem`/`RewardItemSelect`/`AddAndEquip`, still `stub` in
the table below) stays blocked on `RE-280` exactly as COO's ranking letter
says -- no bytes were guessed ahead of it.

### Evidence, two layers

- **Server-side, direct**: `tests/test_script_lua_api_player.py` -- 21 new
  unit tests against `RealPlayerNamespace` directly (no lupa): default
  context reads as empty/zero, quantity sums across matching rows only and
  ignores non-matching ones, threshold comparison both sides, unheld/
  unequipped items answer false, wrong arity for all three degrades to
  `STUB_DEFAULT` rather than raising, a non-numeric or boolean argument
  refuses (`_coerce_int`) rather than guessing -- plus 3 new
  `LUPA_PACKAGE`-guarded Lua-integration tests reproducing the exact
  grepped call shapes above through a live `ScriptHost`.
- **Corpus-wide, measured not assumed**: ran the full 616-file corpus
  through `script_host.run_corpus_entry_points` against a fixed clock.
  `report.real_call_counts` -- `{'Player.GetItemNum': 88,
  'Player.CheckItemNum': 154}` (`CheckEquipItem`'s 2 call sites do not
  execute under `STANDARD_ENTRY_POINTS` today, contributing 0, same as
  `Quest.CheckOpenTime`'s own partially-unreached call sites documented for
  round `gqjas5`) -- folded into `tests/test_script_lua_corpus.py`'s
  updated `BASELINE_TOTAL_STUB_CALLS` (4937 -> 4715; see that file's own
  updated comment for the full measured-not-naive derivation, including the
  20-call branch-shift remainder). `test_every_present_entry_point_gets_
  called_or_its_failure_is_pinned`'s `KNOWN_LOAD_FAILURES`/
  `KNOWN_ENTRY_POINT_CALL_FAILURES` both pass unchanged -- no new load or
  call failure introduced.

### Tests + gates

`PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_player.py
tests/test_script_lua_api_quest.py tests/test_script_lua_api_trigger.py
tests/test_script_lua_api_instance.py tests/test_script_host_spike.py
tests/test_script_lua_corpus.py -q` -- 156 passed, 306 subtests passed, 0
failed (includes the two pinned regression guards this round updated:
`test_the_5_real_player_names_are_excluded_above_not_forgotten` in
`test_script_host_spike.py`, `BASELINE_TOTAL_STUB_CALLS` in
`test_script_lua_corpus.py`). Full `pytest tests/` and
`tools_bridge/pf_gate_preflight.py --repo .` run before push, folded in
below if finished in time.

### ADVERSARY

Invoked at the point this round noticed the diff was ready for review (not
strictly round-start, this round's own process gap -- next round should
invoke it as the very first action instead, per house rule), via the
`pf-adversary` subagent against `lua_api/player.py`'s new code in an
isolated worktree. Result returned before push, folded in:

- **Real defect found and fixed**: `PlayerContext(backpack=None)`,
  `PlayerContext(equipped_template_ids=None)`, and a backpack row with a
  non-numeric `quantity` each raised a raw `TypeError`/`AttributeError`
  straight out of `ScriptHost.call` instead of degrading like every other
  real closure in this file. Not exploitable today (no dispatcher builds a
  `PlayerContext` from live data; every test hand-builds a well-formed one)
  but a live crash surface for whichever future dispatcher round trusts a
  `store.get_backpack` decode failure unconditionally. Fixed:
  `_item_count`/new `_is_equipped` now catch and degrade to `0`/`False`
  (see `player.py`'s own updated docstrings on both), with 3 new regression
  tests reproducing the adversary's exact three inputs.
- **Confirmed, not a new defect**: an arity-mismatch on `CheckItemNum`/
  `CheckEquipItem` returns `STUB_DEFAULT` (Python `0`), truthy in real Lua
  -- but `Quest.CheckOpenTime` (already shipped, real, boolean-shaped)
  has the identical shape and the identical test-suite gap (checked at the
  Python-return level, never real-Lua-truthiness level); this round
  inherits, not introduces, that landmine.
- **No crash from Lua-controlled arguments**: fuzzed every argument
  position of all three names (`None`/bools/lists/dicts/bytes/nan/inf/
  huge ints/non-integral floats/complex/arbitrary objects) through
  `ScriptHost` -- zero exceptions, `_coerce_int` holds.
- **Semantics re-verified independently against the corpus** (not trusted
  from the module docstring alone): call counts/arities/sum-not-count
  aggregation all matched grepping the real files directly; mutation
  testing (`>=`->`>`, dropping the template-id filter, `CheckEquipItem`
  forced `True`) caught by the existing test suite in all three cases.
- **Sandbox posture preserved**: all three closures return only plain
  `int`/`bool`/`STUB_DEFAULT` to Lua, no `BackpackState`/`ItemAttrState`/
  frozenset object ever crosses the boundary.
- **Open question raised, not yet answered** (left for whichever round
  builds the live dispatcher): should that wiring re-validate through
  `inventory.require_backpack_shape` before constructing a `PlayerContext`,
  or should these closures keep defending themselves the way they do now?
  This round picked "closures defend themselves" (see the fix above) as
  the immediate, in-scope answer; a future dispatcher revalidating too is
  defense in depth, not required by this round's fix.

### TWO_SESSIONS_SAME_SCENE

Not applicable the way it usually is for a shared-world door: a backpack
and an equipment set are per-CHARACTER state (`PlayerContext.backpack`/
`equipped_template_ids`, mirroring `store.get_backpack`/
`store.list_equipped_items`'s own `character_id` keying), never a scene
string -- two sessions in the same scene share nothing through this seam,
and no live dispatcher exists yet for two sessions to race through anyway
(same posture this file's own module docstring already states for
`level`/`class_id`).

### รอบหน้าทำอะไร

1. Check the two open CORE-REQUEST letters from round `7v7yn2` first
   (quest-flag-counter-daily-stamp-columns, quest-store-wiring-trips-the-
   foundation-guard) -- if either is answered, wire it in citing the grant/
   answer as authority, before claiming new work.
2. Per `COO-DECISION 20260906_1846`'s own ranking, the inventory seam's
   read side is now fully real (all three names); its WRITE side stays
   blocked on `RE-280` -- do not guess bytes ahead of it. If `RE-280` has
   answered by the next round, that is the next item in this lane's own
   priority order, still ranked above item 3 (`Player.MobAppear`, LANE-A's
   territory, explicitly not this lane's to build per that same letter).
3. `CheckWishQuest` (Quest namespace, refused round `7v7yn2`) still needs an
   RE ticket -- not blocking, low call count (1).
4. If CI/gate surfaces a `lupa`-version or Windows-specific difference this
   Linux-container run could not catch (same risk every prior LANE-Q round
   flagged), fix it here rather than starting over, per `SYNC-NOTICE`'s own
   standing instruction.

SCOREBOARD: COMING | ผู้เล่นยังไม่เห็นอะไรใหม่บนจอ -- ตรรกะฝั่งเซิร์ฟเวอร์ของ 3 Player.* (นับของ inventory ที่มีอยู่ในกระเป๋า/สวมใส่) ถูกต้องและมีเทสยืนยันแล้ว แต่ยังไม่มี dispatcher จริงต่อกับ session ผู้เล่น (เหมือน GetLv/GetClass เดิม) | pirate-force-server PR (เปิดแล้ว, ดูหัวข้อ "จบรอบ" ในไฟล์รอบ pf_bridge), Player.* fns real 5/73 (+3 this round), inventory-seam read side 3/3 done

## Round uadtc7 (2026-09-06) -- recovered #947, wired one shared QuestStateStore between Trigger and Quest

### What changed

Two parts.

1. Recovered `pirate-force-server#947` (closed by the reaper, never merged)
   by cherry-picking its two commits unchanged onto fresh `origin/main`
   (`fd82da2`, `13f4c02`) -- the same 9 more `Quest.*`/2 more `Trigger.*`
   real closures round `7v7yn2`'s own `docs/SCRIPT_LANE.md` section above
   already describes in full; nothing about that code changed here.

2. New this round: `script_host.ScriptHost.__init__`/`load_script_file`
   gained `quest_context`/`quest_store` parameters and now build ONE
   shared `lua_api.quest.QuestStateStore` (a fresh `InMemoryQuestStateStore`
   + `DEFAULT_CONTEXT` when neither is given), passed to BOTH
   `lua_api.trigger.build_namespace` (`quest_context=`/`quest_store=`) and
   `lua_api.quest.build_namespace` (`context=`/`store=`) -- the exact gap
   `lua_api.trigger.build_namespace`'s own docstring named ("NOT WIRED IN
   `script_host.ScriptHost` THIS ROUND, SAID PLAINLY"), reverted before
   push in `#947` because it tripped `tests/test_npc_interaction_wire.py`'s
   `QuestAndShopStateGuardTests` (three new symbols with no exemption).
   Chief (LANE-E) round `awnjat` pre-approved exactly three new symbol
   names for `ALLOWED_SYMBOLS["script_host.py"]`
   (`pf_bridge/notes_to_chief/20260906_2151_CHIEF-REPLY-LANE-Q-quest-
   state-door-granted-1950-1951-not-yet-earned.md`), landed in the same
   commit as the wiring it exempts, per that guard's own rule (an
   exemption cannot be granted for code that does not exist yet). The
   three actual offending symbols, measured by running the guard test
   before adding the exemption (not assumed from the letter's own draft):
   `quest_context`, `quest_store`, `_in_memory_quest_state_store` --
   matches the letter's pre-approved list exactly. Local variable names
   inside `ScriptHost.__init__` were kept as the bare parameter names
   `quest_context`/`quest_store` (rebound in place) rather than new names
   like `shared_quest_context` specifically because the guard flagged
   those too on a first attempt and neither was in the pre-approval.

### What this does NOT do yet, said plainly

Still no production persistence -- `InMemoryQuestStateStore` is still the
only `QuestStateStore` implementation in this codebase; chief's own
DB-backed accessor (`store.py`'s `get_quest_flag`/`set_quest_flag`/
`get_quest_counter`/`set_quest_counter`, `migrations/016_character_quest_
state.sql`) is store.py's own write zone, not this lane's, and its own PR
(`#954`) is ALSO closed unmerged -- re-landing it is chief's (LANE-E)
job, not this lane's, and this round does not touch `store.py` or
`migrations/`. Still no live dispatch -- nothing binds a `ScriptHost` run
to a real player session/character id yet, same gap every prior round in
this file already states. Player-visible impact: none yet.

### Tests + gates

Three new tests, `tests/test_script_host_spike.py`'s
`OneScriptHostSharesOneQuestStateStoreTests`: the two namespaces hold the
IDENTICAL store/context object (`is`, not equality); a
`Trigger.QuestActiveProgress` write is visible to a later
`Quest.GetQuestFlag` read in one `ScriptHost` run with no store/context
injected (the default-sharing path every existing caller takes); an
explicitly-injected store/context pair is the one both namespaces
observably share (checked both through the Lua call and by reading the
injected store object directly afterward). `docs/PYTEST_SKIP_PINS.json`'s
`tests/test_script_host_spike.py` entry updated 22 -> 25, MEASURED via
`tests/test_pytest_precondition_census.py`'s own AST walker, not counted
by hand.

`PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_quest.py
tests/test_script_lua_api_trigger.py tests/test_script_lua_api_instance.py
tests/test_script_lua_api_player.py tests/test_script_host_spike.py
tests/test_script_lua_corpus.py tests/test_npc_interaction_wire.py -q`:
194 passed, 333 subtests passed.

Full `pytest tests/` on this branch, `origin/main` merged in (no-op,
already current): 12544 passed, 327 skipped, 26403 subtests passed, 1
failed. The 1 failure
(`tests/test_lane_a_choose_npc_scene1.py::TheRegisteredResponderDropsTheTalkTriggerAtRealDispatchTests::test_the_talk_trigger_is_still_missing_at_real_dispatch_today`)
is `NOW.md`'s own `KNOWN_RED_MAIN` row -- confirmed pre-existing by
`git stash` (reverting this round's own diff back to `origin/main`) and
running that one test alone on the unmodified tree: fails identically.
LANE-A's own file, not touched by this round, not this lane's write zone.

`python3 tools_bridge/pf_gate_preflight.py --repo ../pirate-force-server`
(from `pf_bridge`): PREFLIGHT PASS.

### ADVERSARY

`ADVERSARY_PENDING pirate-force-server` (this round's branch) -- invoked
via the `pf-adversary` subagent after the diff was ready and the full
suite already run, not at round start (this round's own process gap,
same one round `qbr5h8` already logged and did not fix; next round
should invoke it as the very first action instead). Result not back by
push time; will be folded into this section or the next round file per
house rule.

### รอบหน้าทำอะไร

1. If pf-adversary's pending result (see above) finds anything, it lands
   as a follow-up commit on this branch or as this round file's own
   addendum, per house rule -- read `pf_bridge/rounds/Q_*uadtc7*` first.
2. `store.py`'s quest-state door (`pirate-force-server#954`, chief's own
   PR) is ALSO closed unmerged -- not this lane's to re-land (write-zone:
   `store.py`/`migrations/` are chief's), but the day it lands, switching
   `ScriptHost`'s default `InMemoryQuestStateStore` for a live dispatch to
   the real accessor is a one-parameter change per chief's own letter, not
   a new design.
3. Per `COO-DECISION 20260906_1846`'s ranking, item 2 (`inventory seam`)
   is read-side already 3/3 real (round `qbr5h8`, `pirate-force-
   server#953`, not yet merged) -- write side still blocked on `RE-280`.
4. `CheckWishQuest` (Quest namespace) still needs an RE ticket -- low call
   count (1), not blocking.
5. Add a bad-VALUE log line to the 9 closures pf-adversary named in round
   `7v7yn2` (still not done, carried forward again).

SCOREBOARD: COMING | ผู้เล่นยังไม่เห็นอะไรใหม่บนจอ -- สคริปต์หนึ่งตัวที่เรียกทั้ง Trigger.QuestActiveProgress/QuestFinishProgress และ Quest.* ในรอบเดียวกันตอนนี้เห็นค่าที่อีกฝั่งเขียนจริงแล้ว (ก่อนหน้านี้แยกคนละที่เก็บ) แต่ยังไม่มี dispatch จริงต่อกับ session ผู้เล่นและยังไม่มีที่เก็บถาวรข้าม relog | pirate-force-server branch claude/hopeful-hopper-dyqifb (recovers #947 + new wiring commit 16349f3), 3 new tests

## Round lvoma1 (2026-09-06) -- recovered both #953 and #947/#960 onto one branch, root cause was never this lane's

### Why this round exists

Three LANE-Q pull requests in a row died on the gate with the exact SAME
failure, none of them this lane's own code:
`tests/test_lane_a_choose_npc_scene1.py:1752`,
`TheRegisteredResponderDropsTheTalkTriggerAtRealDispatchTests`, an
`AssertionError` whose own message named its fix
("`runtime.py` is now queuing `extra_actions` (`CORE-REQUEST
20260904_0137` landed) -- invert this assertion to `assertIn`... rather
than deleting the test"). Confirmed with `get_job_logs` against all three
gate runs (947: run `34036020824`; 953: run `34039804808`; 960: run
`34043977287`) -- identical file, identical line, identical message each
time; none of the three PRs' own diffs ever touched that file.

`prompts/COMMON_LANE_ROUND.md`'s own house rule ("gate red, same cause,
two rounds running -> stop, write COO, do not send a third blind PR") was
already past its trigger by the time this round started (three failures,
not two). Did not need to write that letter: `NOW.md`'s own top line
already said the answer ("main เขียว (#957 merge 23:08) -> เปิด PR ได้
fetch main ซ้ำก่อน"). Read `tests/test_lane_a_choose_npc_scene1.py` on
fresh `origin/main` directly and confirmed the fix is there --
LANE-A's own round `eknq8d` (`pirate-force-server#957`, "invert the
talk-trigger assertion now that 0137 landed", merged
2026-09-06T23:08+07:00, `COO-DECISION 2026-09-06T21:41`).

### What this round built: nothing new -- recovered two dead branches onto the fixed main

Both `claude/hopeful-hopper-dyqifb` (#960: recovers #947, plus the shared
`QuestStateStore` wiring) and `claude/happy-tesla-qbr5h8` (#953:
inventory seam read side) still existed, unmerged, based on the SAME old
`origin/main` (`cf961be`). Cherry-picked all six commits from both
(chronological order: `31def53`, `a168250`, `fd82da2`, `13f4c02`,
`16349f3`, `88042c7`) onto one fresh branch from current `origin/main`
(`be06164`, which already carries `#957`'s fix) -- combined into ONE PR
because this lane may open only one PR per repo per round
(`prompts/AGENTS.md` ยง7).

Five merge conflicts, all bookkeeping (no logic conflict -- the two
deltas touch disjoint namespaces, `lua_api/player.py` vs
`lua_api/quest.py`+`lua_api/trigger.py`+`script_host.py`):

1. `docs/PYTEST_SKIP_PINS.json`'s `test_script_host_spike.py` pinned-test
   list -- combined delta (quest 1->10, player 2->5, trigger 5->7),
   verified against the actual method names in
   `tests/test_script_host_spike.py` after the auto-merge, not assumed.
2. `tests/test_script_lua_corpus.py`'s `BASELINE_TOTAL_STUB_CALLS` --
   RE-MEASURED from scratch rather than added (both deltas never ran in
   the same corpus pass before this round): 4715 -> 3716, a 3-call
   branch-shift gap from `Player.CheckItemNum` (154 -> 145) and
   `Quest.GetQuestFlag` (159 -> 160) shifting once run together --
   neither shift visible when either delta ran alone. See that file's own
   comment for the full `report.real_call_counts` dump.
3. `tests/test_script_host_spike.py` -- auto-merged clean, verified by
   hand against (1) and (2) above.
4. `docs/SCRIPT_LANE.md`'s status-table header/prose -- rewrote combined
   (129/160 stub, 31/160 real: Quest 10, Player 5, Trigger 7, Instance 9).
5. `docs/SCRIPT_LANE.md`'s own round-history sections -- interleaved
   "Round 7v7yn2" / "Round qbr5h8" / "Round uadtc7" into chronological
   order (this file was two independent branches' own append-only logs,
   diverged after `7v7yn2`).

### What this round does NOT do, said plainly

No new API surface, no new player-visible behaviour beyond what rounds
`qbr5h8`/`7v7yn2`/`uadtc7` already built and already got clean adversary
results for (pf_bridge#1583 for the `QuestStateStore` sharing; round
`qbr5h8`'s own three fixed crash bugs for the inventory seam). Did not
chase `RE-285`'s own two not-RE follow-up leads (grep the corpus for
other `Trigger.*` literal-argument calls; check the `.tgr` table `RE-273`
opened) -- this round's whole budget went to the recovery above.

### Tests + gates

`PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_player.py
tests/test_script_lua_api_quest.py tests/test_script_lua_api_trigger.py
tests/test_script_lua_api_instance.py tests/test_script_host_spike.py
tests/test_script_lua_corpus.py tests/test_npc_interaction_wire.py -q`:
212 passed, 334 subtests passed, 0 failed (after the
`BASELINE_TOTAL_STUB_CALLS` fix above -- red at 4715, green at 3716,
confirmed by running it both ways rather than trusting the arithmetic).

Full `pytest tests/` run before push -- see this round's own "จบรอบ"
section in `pf_bridge/rounds/Q_20260906_2358_lvoma1_*.md` for the final
count, folded in once it finishes (started as a background run; this
section written while it was still in flight, per house rule against
holding the round waiting on a single long command when other real work
remains).

`python3 tools_bridge/pf_gate_preflight.py --repo ../pirate-force-server`:
folded in below once run.

### ADVERSARY

`pf-adversary` invoked at round start against the diff so far (the
recovery/merge itself, not the already-adversary-clean logic underneath
-- see prompt for the exact scope), in parallel with the full test run
above. Result folded in below once it lands, or `ADVERSARY_PENDING` per
house rule if it has not returned by push time.

### TWO_SESSIONS_SAME_SCENE

Not applicable, same reasoning both recovered deltas already established
on their own branches: quest flag/counter state and backpack/equipment
state are both keyed by `character_id`, never by scene; no live dispatch
exists yet for two sessions to race through either seam.

### รอบหน้าทำอะไร

1. If this round's own `pf-adversary`/full-suite results (see above) were
   still pending at push time, read them first, per house rule.
2. `store.py`'s quest-state door (`pirate-force-server#954`, chief's own
   PR, closed unmerged) is still not this lane's to re-land -- three of
   this lane's own PRs (`#947`, `#960`, now this one) have each been
   blocked or delayed waiting near it; worth a status check with
   COO/chief if it is still unmerged next round.
3. `RE-285`'s own two not-RE leads (grep the corpus for other `Trigger.*`
   literal-argument calls near `GetContactMode`'s own shape; check the
   `.tgr` per-trigger table `RE-273` opened for a contact-mode-shaped
   column) -- neither chased this round.
4. Per `COO-DECISION 20260906_1846`'s ranking: inventory seam write side
   (`AddItem`/`RewardItemSelect`/`AddAndEquip`) still blocked on `RE-280`.
5. Add a bad-VALUE log line to the 9 closures pf-adversary named in round
   `7v7yn2` -- still not done, carried forward again.
6. `CheckWishQuest` (Quest namespace) still needs LANE-GUILD's own state
   door or an RE ticket -- low call count (1), not blocking.

SCOREBOARD: COMING | ผู้เล่นยังไม่เห็นอะไรใหม่บนจอ -- โค้ดของ 12 ฟังก์ชันจริง (Quest.* 9 เพิ่ม, Trigger.* 2 เพิ่ม, Player.* 3 เพิ่ม) ที่หายไปสามรอบติดเพราะเกตแดงจากไฟล์ของ LANE-A (ไม่ใช่ของสายนี้) กลับมาอยู่บน PR เดียวแล้วหลัง main เขียว แต่ยังไม่ต่อกับ session ผู้เล่นจริงและยังไม่มีที่เก็บถาวรข้าม relog | pirate-force-server PR (ดูหัวข้อ "จบรอบ" ในไฟล์รอบ pf_bridge), API status 31/160 real

## Round x6gxzd (2026-09-07) -- Player.MobAppear real (a per-player visibility FLAG, not a world spawn), plus a cross-lane accessor for LANE-A's future NPC filter

### Why this round exists

Two mailbox letters landed since round `lvoma1`'s own close, both
`ADDRESSEE: LANE-Q`, both flowing from the same owner decision: `pf_bridge/
notes_to_chief/20260907_0039_KA1A-PANYA-DECISION-COO-shared-world-plus-per-
player-npc-visibility-rank-rule.md` (`PANYA-DECISION 20260907_0039`, via
ka1-A) and `pf_bridge/notes_to_chief/20260907_0043_COO-DECISION-panya0039-
quest-state-table-feeds-visibility-filter-LANE-Q.md` (`COO-DECISION
20260907_0043`, the COO's own routing of that decision to this lane).
Design, in the owner's own words: NPCs are per-player visibility FLAGS,
monsters/loot/bosses stay one shared world (`rank 0` = flag, `rank>0` =
shared world, decided by `n_RANK`/`n_AI_COMBAT`, no hand list). Two
concrete asks land on this lane specifically:

1. This lane's own item-1 quest-state door (`#965`, `QuestStateStore`)
   must answer, per character: "has quest X been accepted yet / reported
   yet" -- LANE-A's future NPC-visibility filter reads exactly that
   against `CONSTDATA_TH__MOBS.tsv`'s `s_QUEST_BEGIN`/`s_QUEST_END`
   columns, and the letter says add the accessor NOW, not wait for item 3.
2. `Player.MobAppear` -- until now `STILL_STUBBED`, category "world spawn,
   not nameable by this lane" (LANE-A's own `20260906_0727` letter) --
   should become a stub THAT RECORDS the per-player flag (or stay a
   documented no-op), because the owner's decision makes clear it was
   NEVER meant to be a world spawn/despawn call in the first place: it is
   `Player.*` (a per-player calling convention), not `Scene.*`, and ka1-A's
   own measurement backs this from the corpus itself (1,766 `(id, true)` +
   1,766 `(id, false)` calls, always through `Accept_Run`/`Report_Run`).
   A third instruction accompanies this one: if any call site's `id`
   argument is provably a `rank>0` mob (the 24 quest-tied monster rows),
   do not decide anything -- write to COO with the id(s).

### What this round built

**`lua_api/player.py`: `Player.MobAppear` moves from `STILL_STUBBED` to
`REAL_METHODS` (6/73 `Player.*` real now).** New seam,
`PlayerMobAppearStore` (`Protocol`) / `InMemoryPlayerMobAppearStore`
(default), the exact same shape `lua_api.quest.QuestStateStore` /
`InMemoryQuestStateStore` already established: per-(character_id, mob_id)
boolean flag, keyed and capped the same way, injectable via
`build_namespace(..., store=...)` and now `ScriptHost(..., player_store=
...)` / `load_script_file(..., player_store=...)`. `PlayerContext` gained
one new field, `character_id: int = 0` (the only field this closure
reads), same "0 = not a real character" sentinel `lua_api.quest.
DEFAULT_CONTEXT` already uses. The closure itself does exactly one thing:
coerce `(mob_id, visible)`, write through the store, log
`LUA_PLAYER_REAL Player.MobAppear character=<n> mob_id=<n> visible=<bool>
(per-player flag only, not a world spawn)`, return the value read back.
It does NOT import, call, or reference `world_scene_registry`/
`mob_ground_persistence`/`mob_death_persistence` (LANE-A's write zone) --
confirmed by this file's own import list, unchanged (`.. inventory`,
`..player_wire` only).

**`lua_api/quest.py`: `is_quest_accepted`/`is_quest_reported`, the cross-
lane accessor `COO-DECISION 20260907_0043` item 1 asked for.** Two plain
functions, not new `QuestStateStore` methods and not new Lua-facing
`Quest.*` names -- they wrap the SAME `store.get_quest_flag` the real
`Quest.GetQuestFlag` closure already calls, compared against the SAME
`QUEST_ACTIVE`/`QUEST_FINISH` constants this file already derived (see the
module's own "QUEST.NONE/ACTIVE/FINISH, DERIVED NOT INVENTED" section).
`is_quest_accepted` is `True` only while the flag equals `QUEST_ACTIVE`
(NOT "ever accepted" -- a finished quest's flag is `QUEST_FINISH`, so this
flips back to `False` once reported, matching `s_QUEST_BEGIN`/
`s_QUEST_END`'s own "appear while active, vanish once reported" shape).
LANE-A's own future filter calls these directly from Python; this lane
does not read either `MOBS.tsv` column itself and does not decide which
mob ids they gate -- that composition stays entirely LANE-A's item 3, per
the decision's own "ลำดับ 1->2->3->4->5 ไม่เปลี่ยน" line.

**The rank>0 question: checked, not decided, reported honestly.** Every
one of the 3,532 `Player.MobAppear(...)` call sites in the corpus
(`grep -rhoE "Player\.MobAppear\([^)]*\)" gamedata/lua/`, all 616 files)
passes a table-driven `Quest.VarN` argument (`Var13`-`Var20`, 294-295
sites each) -- ZERO literal mob-template-id calls. Which real `n_ID` (and
therefore which `n_RANK`) any given call names lives in each quest's own
`QUESTDATA_*.tsv` row (`n_VARI_13`..`n_VARI_20`-shaped columns, per the
protocol map's own "Quest.Var1..Var20 come from game tables" rule), not
mined this round -- so this round genuinely cannot say yes or no to "does
any call site collide with a rank>0 mob id" from the script text alone.
Reported plainly (see the module docstring's own "WHAT THIS ROUND
DELIBERATELY DOES NOT DO" section, point 3) rather than guessed either
way; NOT escalated to COO as a conflict, because no conflicting evidence
was actually found -- an open measurement gap is a different thing from
the "found a rank>0 collision, don't know what to do" case the letter
asks to escalate.

**Checked, found already fixed: the bad-VALUE logging item carried
forward twice.** Round `lvoma1`'s own "รอบหน้าทำอะไร" repeated "add a
bad-VALUE log line to the 9 closures pf-adversary named in round
`7v7yn2`" as still-open. Re-read `lua_api/quest.py`'s own `_log_bad_value`
docstring and its five call sites (`SetFlag`/`SetQuestFlag`/
`MobKillCount`/`CheckMobKillCount`/`GetMobKillCount`) plus `GetQuestFlag`'s
own equivalent (`_log_flag` with a `quest_id=-1` sentinel, which that
function's own docstring explicitly calls out as already covering this
case) -- all 9 of round `7v7yn2`'s real closures that can receive a
right-arity, wrong-VALUE argument already log one. `GetFlag`/
`CanReportDailyQuest`/`ReportDailyQuest` take no arguments, so there is no
value to validate. This item was done in round `7v7yn2` itself; the
carry-forward note in two round files since was stale bookkeeping, not a
real gap. `lua_api/player.py` gained its OWN `_log_bad_value` this round
(`MobAppear` is the first `Player.*` real closure with a right-arity,
wrong-type failure mode), which is new work, not the carried-forward item.

### What this round does NOT do, said plainly

Does not implement `PANYA-DECISION 20260907_0039`'s own visibility filter
(point 2, "ส่งตัวละครนี้ให้คนนี้ไหม") -- that composition (three-way OR
across quest-state / `n_MOB_APPEAR` / the new flag store) stays LANE-A's
item 3, after P-2, unbuilt here on purpose. Does not wire `MobAppear` (or
`is_quest_accepted`/`is_quest_reported`) into any live network dispatch --
no `ScriptHost` run is bound to a real player session yet, same gap every
prior real-method round in this file has named. Does not touch
`world_scene_registry`/`mob_ground_persistence`/`mob_death_persistence`,
`runtime.py`, `app.py`, or `store.py`.

### Tests + gates

New tests: `tests/test_script_lua_api_player.py` (`MobAppear` --
namespace-contract tests: sets/clears the flag, per-character isolation
across two injected stores, wrong arity, wrong value type incl. a plain
int rejected same as `_coerce_int`'s own bool-vs-int posture, a broken
injected store raises rather than degrading since a store is a
collaborator not untrusted script input, one Lua-integration test
reproducing `q_kill5.lua`'s own `Delete_Run` call shape).
`tests/test_script_lua_api_quest.py` (`is_quest_accepted`/
`is_quest_reported` -- never-set/active/finished/none states, plus
per-character and per-quest isolation). Updated:
`tests/test_script_host_spike.py` (`q_kill5` fixture's own lifecycle test:
`Player.MobAppear` moves out of the stub-call assertion into a new
real-call assertion, 4 unconditional `Delete_Run` calls measured, not
guessed -- the other 12 call sites in this fixture sit behind `if
(Quest.VarN > 0)` and never fire under `STUB_DEFAULT=0`; renamed
`test_the_5_real_player_names_are_excluded_above_not_forgotten` ->
`test_the_6_..`). `tests/test_script_lua_corpus.py`:
`BASELINE_TOTAL_STUB_CALLS` RE-MEASURED against the real 616-file corpus
with `lupa` installed: 3716 -> 2620, EXACTLY (`report.real_call_counts`:
`Player.MobAppear` fires 1096 times under the fixed clock) -- no
branch-shift this time, unlike every prior real-method landing this file
documents, because `MobAppear` is a pure side-effecting call inside
branches other stub reads already gate, never itself a condition another
call sits behind.

`PYTHONPATH=src:tests python3 -m pytest tests/test_script_lua_api_player.py
tests/test_script_lua_api_quest.py tests/test_script_lua_api_trigger.py
tests/test_script_lua_api_instance.py tests/test_script_host_spike.py
tests/test_script_lua_corpus.py tests/test_npc_interaction_wire.py -q`:
225 passed, 335 subtests passed, 0 failed.
`tests/test_pytest_precondition_census.py` (the AST census over every
`docs/PYTEST_SKIP_PINS.json` pin, re-run after updating the two entries
this round's renames/additions touch --
`tests/test_script_host_spike.py`'s `lupa_package` pin, name only, count
unchanged at 25; `tests/test_script_lua_api_player.py`'s own `lupa_package`
pin, 6 -> 7): 69 passed, 1135 subtests passed.
`python3 tools_bridge/pf_gate_preflight.py --repo ../pirate-force-server`:
PREFLIGHT PASS.

### ADVERSARY

`ADVERSARY_UNAVAILABLE` -- this session's tool surface carries no `Task`/
`Agent`-shaped subagent launcher and no `pf-adversary` tool (checked via
`ToolSearch`, both a broad query and a direct `select:pf-adversary,Agent,
Task` query, zero hits). Per house rule, did the self-review by hand
instead: read every hunk in `git diff --cached` before each commit: (a)
`MobAppear`'s closure rejects a plain Lua/Python int (`0`/`1`) as the
visibility argument, not just non-bool garbage -- a script accidentally
passing `1` instead of `true` gets `STUB_DEFAULT` and a `LUA_PLAYER_BAD_
VALUE` line, not a silently-wrong "visible" write (a mutation test
confirmed: removing the `isinstance(visible, bool)` check makes
`test_mob_appear_bad_argument_type_refuses_rather_than_guesses` fail
exactly as expected); (b) the injected-store-vs-context isolation tests
mutate one namespace and assert the OTHER instance is untouched, not just
that both started empty (same shape `OneScriptHostSharesOneQuestStateStore
Tests` already established for the opposite claim -- shared, not
isolated); (c) `PlayerMobAppearStore.set_mob_appear_flag`'s cap-refusal
branches (`_MOB_APPEAR_CHARACTERS_CAP`/`_MOB_APPEAR_MOBS_PER_CHARACTER_
CAP`) mirror `InMemoryQuestStateStore`'s own tested shape, and a
non-positive cap raises `ValueError` in `__init__`, matching every sibling
store's own contract; (d) `is_quest_accepted`/`is_quest_reported` take the
store as an explicit argument rather than reading a module-global, so two
different tests using two different stores cannot leak into each other
(exercised directly by
`test_per_character_and_per_quest_isolation`). Next round of this lane:
try `pf-adversary` again as the FIRST action, per house rule for a session
that found the tool missing.

### TWO_SESSIONS_SAME_SCENE

Not applicable, on the same grounds every prior round in this file gives:
`PlayerMobAppearStore` is keyed by `character_id`, never by scene string,
and (like `QuestStateStore`) is explicitly a PER-PLAYER bucket by design
here, not a world-shared one -- two different `ScriptHost` runs still get
two different default stores unless a future caller explicitly shares one
object into both (no code does that today). This round's own design
citation (`PANYA-DECISION 20260907_0039` point 3) makes the "per-player,
not world" property a deliberate REQUIREMENT this round satisfies, not
merely an accident that happens not to collide.

### รอบหน้าทำอะไร

1. `store.py`'s quest-state door (`pirate-force-server#954`) -- still
   worth a status check with COO/chief if still unmerged.
2. `RE-285`'s own two not-RE leads (grep the corpus for other `Trigger.*`
   literal-argument calls; check the `.tgr` table `RE-273` opened) --
   neither chased this round either.
3. Inventory seam write side (`AddItem`/`RewardItemSelect`/`AddAndEquip`)
   still blocked on `RE-280`.
4. `CheckWishQuest` (Quest namespace) still needs LANE-GUILD's own state
   door or an RE ticket -- low call count (1), not blocking.
5. LANE-A's own item 3 (the actual NPC-visibility filter reading
   `is_quest_accepted`/`is_quest_reported` against `s_QUEST_BEGIN`/
   `s_QUEST_END`) is LANE-A's to build, after P-2 -- watch for a letter
   back if the two functions' own shape needs to change once a real
   caller exists.
6. If a future round DOES find a literal, provably `rank>0` mob id
   reaching `Player.MobAppear`, write to COO with the id per
   `PANYA-DECISION 20260907_0039` point 3 -- not decided here because none
   was found, not because the check was skipped.

SCOREBOARD: COMING | ผู้เล่นยังไม่เห็นอะไรใหม่บนจอ -- Player.MobAppear (1,766+1,766 จุดเรียกในสคริปต์เควสจริง) กับ accessor สถานะเควสสำหรับฟิลเตอร์การมองเห็น NPC ของ LANE-A ทำงานจริงแล้วฝั่งเซิร์ฟเวอร์ (เก็บ/อ่านธงต่อผู้เล่นได้ ไม่ใช่แค่ log stub) แต่ยังไม่มี dispatch จริงต่อกับ session ผู้เล่น ยังไม่มีที่เก็บถาวรข้าม relog และ LANE-A ยังไม่ได้ต่อฟิลเตอร์เข้ากับมัน | pirate-force-server PR (ดูหัวข้อ "จบรอบ" ในไฟล์รอบ pf_bridge), API status 32/160 real

## Round 6775u1 (2026-09-07) -- the message-wire: Player.ShowMessage and Trigger.TriggerShowMessage real against the game's own message table

**Charter position**: `NOW.md`'s LANE-Q system order (COO `20260906_1846`)
item 4, "message-wire" -- items 1 (flag-quest-state), 2 (inventory read
side) and 3 (`Player.MobAppear`) landed in rounds `7v7yn2`, `qbr5h8` and
`x6gxzd`.  116 of the corpus's call sites move from "logs a stub line" to
"validated and recorded".

### What a script means by "show a message" -- derived, not guessed

No script in the 616-file corpus ever hands a STRING to a message name.
Every call passes an INTEGER, and that integer is a row id in
`pf_bridge/gamedata/tables/TEXTDATA_TH__MESSAGE.tsv` (907 rows, ids 1..961
with holes; columns `n_ID  n_TYPE  n_NOTIFY_TYPE  s_MESSAGE`).

Evidence, all three legs, because coverage alone would not have settled it:

1. **Coverage.** Every literal id at a `Player.ShowMessage` /
   `Trigger.TriggerShowMessage` / `Party.ShowMessage` call site has a row:
   `1, 4, 421, 824, 855, 856, 859, 860, 882, 885, 890, 897` (Player) and
   `914..921` (Trigger).  Zero misses.
2. **Refutation of the competitors, not silence about them.**
   `TEXTDATA_TH__TIP_MESSAGE.tsv` stops at id 561 -- 17 of the 20 literal
   ids have no row there, so it is REFUTED outright.
   `TEXTDATA_TH__UI_MESSAGE.tsv` covers every id by range and is NOT
   refuted by coverage; it is refuted by CONTENT.  Its 855/856/859 are the
   UI labels "skill details" / "up status" / "skill points:", which is not
   what a quest bails out with.
3. **Meaning agrees with surrounding logic.**  `856` = "quest not
   accepted, or quest state does not match" and it is passed exactly where
   a quest script bails on a state check; `855` = "item count already at
   the cap"; `859` = "not enough of the related item"; `914..921` are
   arena-announcer broadcast lines, and every one of them is passed from a
   `t_*_msg` trigger.

**Audience** (`TriggerShowMessage`'s first argument) is the corpus's own,
from `gamedata/lua/t_msg_mod.lua`'s Big5 header comment ("Var2 = message
type (1 individual, 2 party, 3 scene, 4 channel)") read WITH that file's
own if-chain, which maps `Var2 == 1 -> TriggerShowMessage(0, ...)`,
`== 2 -> 1`, `== 3 -> 2`, `== 4 -> 3`.  So the wire value is the comment's
number minus one: `0 individual, 1 party, 2 scene, 3 channel`.  The only
literal audience anywhere in the corpus is `2`; `0/1/3` arrive through
those `Trigger.Var2` branches, which is where the domain comes from.

### What was built

- **`lua_api/message.py`** (new): `CATALOG` (907 rows, loaded from the
  vendored `lua_api/message_catalog.tsv`), `is_known_message_id`,
  `notify_type`, the four `AUDIENCE_*` constants + `AUDIENCES` domain, and
  the `MessageSink` `Protocol` / `InMemoryMessageSink` seam -- the same
  shape `lua_api.quest.QuestStateStore` and
  `lua_api.player.PlayerMobAppearStore` already established.
- **`lua_api/message_catalog.tsv`** (new): the ASCII half of the shipped
  table -- `message_id`, `message_type`, `notify_type`.  The localized
  `s_MESSAGE` text is deliberately NOT vendored, the same split
  `lua_api/api_spec.tsv` already took for its own source table.  Named as
  a real limit rather than a tidy one: whoever finally emits the frame
  needs the text, and it stays in the bridge table.
  **SUPERSEDED by round `7kxfe9`** (COO-DECISION `20260907_0405`, option
  (a)): the file is now a complete four-column mirror with the text
  vendored as `\uXXXX` escapes.  See that round's own section below --
  this bullet is kept as written because the reasoning it records is what
  the letter to COO argued against, and deleting it would hide that the
  lane changed its mind on instruction.
- **`lua_api/player.py`**: `ShowMessage` moves `STILL_STUBBED` ->
  `REAL_METHODS` (7/73 `Player.*` real).
- **`lua_api/trigger.py`**: `TriggerShowMessage` moves `STILL_STUBBED` ->
  `REAL_METHODS` (8/17 `Trigger.*` real).
- **`script_host.py`**: ONE `message_sink` per host run, normalized in
  `ScriptHost.__init__` (not left to each `build_namespace`'s own private
  default) so `Player.ShowMessage` and `Trigger.TriggerShowMessage` inside
  the same script land in one ordered record -- the same reason
  `quest_store` is normalized there.  Injectable through
  `ScriptHost(..., message_sink=...)` / `load_script_file(...)`.

Both closures REFUSE rather than clamp: an id with no row in the shipped
table is a message the client could never render, and an audience outside
`0..3` is not a neighbouring audience.  Both log a bad-value line and
return `STUB_DEFAULT` without recording anything.

### What this round does NOT do, said plainly

**Nothing reaches the client.**  This lane records WHICH message ids to
show, in order, per character.  It does not build `ShowMessageVital`
(`0x36D2`, proven layout in `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`:
one `UNTAGGED_WSTRING16LE_LEN32LE` at `+0x14`), and no module in this
package does.  The frozen legacy seam already has that builder
(`current/pf_login_game_server_v141.py`'s `make_show_message(text)`,
exercised by `tests/test_system_message_wire.py`), and the dispatch that
would call it lives in `runtime.py`/`app.py`, outside this lane's write
zone.  `tests/test_system_message_wire.py`'s own
`ShowMessageOwnershipGuardTests` scans `src/pirateforce_foundation/*.py`
non-recursively, so `lua_api/` is outside it -- this round therefore adds
the same guard for this lane's own directory
(`tests/test_script_lua_api_message.py::NoLaneQModuleBuildsTheVitalTests`,
AST-based so `message.py`'s docstring can NAME the vital in its handoff
note without being mistaken for owning it).  The coverage row
`chat/server_system_message` stays accurate.

`Party.ShowMessage` (1 call site) is NOT real: there is no `lua_api/party.py`
yet, and standing one up for a single call site was not worth the round.
It reads the same catalog when it lands; audience `AUDIENCE_PARTY`.

### Tests + measurement

New `tests/test_script_lua_api_message.py` (25 tests, lupa-free on purpose
so it adds no skip pin): catalog holes are real (a range check would wave
through ids the game never shipped), every literal corpus id resolves,
sink ordering/per-character isolation/cap refusal without eviction, both
closures' arity/bad-value/float-vs-bool doors, a broken sink raising rather
than degrading to silence, the shared-sink wiring through `ScriptHost`
(mutation guard: un-normalize the sink in `ScriptHost` and it fails), two
hosts not sharing a default, and the vital-ownership guard above.

`BASELINE_TOTAL_STUB_CALLS` RE-MEASURED: 2620 -> **2597**.  The drop is
exactly `Player.ShowMessage`'s own measured 23 calls, and
`Trigger.TriggerShowMessage` fires **zero** times in the corpus census.

**Why it fires zero times -- CORRECTED, because the first draft of this
paragraph was wrong and wrong in a way that would have sent the next round
to the wrong lane.**  The draft said `Scene.CheckPlacementAlive` gates it.
It does not.  Five of the eight calling files (`t_nex_msg`,
`t_nex_msg_ins`, `t_nex_msg_ins_t1`, `t_indanix2_msg`, `t_bg2017_msg`)
never call `Scene.*` at all, and in `t_msg_mod.lua` -- the file the draft
cited as the example -- the gate runs the OTHER way (`if
Scene.CheckPlacementAlive(...) == true then return 0 else <the
TriggerShowMessage block> end`), so a stubbed `0` REACHES the call instead
of skipping it.  What actually blocks it is the `Trigger.VarN` data every
one of those branches tests, which lives in the `.tgr` tables nobody has
mined (the `RE-273` lead).  `pf-adversary` proved it by mutation: feed
`Trigger.VarN` a 1, touch no `Scene.*` at all, and three of those files
reach the closure and log `LUA_TRIGGER_REAL`.  So the 55 call sites are
unreachable in THIS harness for want of trigger-table data, not for want of
LANE-A's `Scene.*` seam.

Landing two names at once is exactly how a branch shift hides, so both
halves are stated rather than one number reported.

### ADVERSARY

`pf-adversary` was ordered at the START of the round, with the work, and
its result came back BEFORE the round unlocked -- so this round owned the
findings rather than deferring them (`ADVERSARY_PENDING` does not apply).
It did not approve: 12 measured defects.  Six were fixed inside this round
(all of them in this lane's own write zone):

- **D1** -- the false `Scene.*` claim, corrected above and in
  `tests/test_script_lua_corpus.py`'s own pin comment.
- **D2** -- scene/channel audiences were being filed under one character;
  the sink now keys them by SCENE (see TWO_SESSIONS_SAME_SCENE below).
- **D3** -- a cap-refused write returned the current length, so a dropped
  message was indistinguishable from a stored one; it now returns `0`, and
  the log line says `stored=` with that meaning spelled out.
- **D4** -- the vendored catalog was checked only against itself
  (adversary garbled all 907 rows and all 25 tests still passed);
  `test_the_vendored_message_catalog_still_matches_the_real_table` in
  `tests/test_script_lua_corpus.py` now ties it to the bridge table, the
  same shape the two vendored `.lua` fixtures already use.
- **D6** -- stale pins in this very file ("128/160 stub, 32/160 real", both
  names still listed `stub`) and in `script_host.py` ("2 of `Player`'s 73",
  four rounds out of date).  The per-namespace counts were DELETED from
  `script_host.py` rather than updated, so they cannot go stale again.
- **D11 (this lane's half)** -- the AST vital-ownership guard for
  `lua_api/`.

Named and NOT fixed, so the next round can pick them up: **D5** (the
catalog loads at import with `encoding="ascii"`; one non-ASCII byte, or a
missing file, breaks `script_host`'s import and silently drops this lane's
own `lane_hooks` -- next round makes it lazy and loud), **D12** (51 of the
116 call sites pass `Trigger.VarN`, not a literal; ids landing in the
table's 54 holes are dropped with one log line and no counter), **D7**
(the audience meaning rests on ONE Big5 comment template, byte-identical in
7 of 8 files, and is Lua-layer evidence with zero wire-layer confirmation
-- labelled as such rather than presented as proven), **D8**
(`message_type` is vendored 907 rows deep and read by nothing but a log
line), **D9** (no `RLock`, unlike the two sibling stores; adversary tried
200 threads and could NOT produce a failure, so it is a structural
suspicion, not a bug), **D10** (the `api_spec.tsv` precedent for dropping
`s_MESSAGE` does not match shape -- letter to COO).

What adversary CONFIRMED, including a correction in this round's favour and
one against it: the table derivation holds, and it found further evidence
for it (`t_nex_colct_ins.lua` passes `860`, whose text carries both halves
of that call site's own `or` condition; `Quest/q_boat_health.lua:26` has
the script author's own Big5 comment `--金錢不足` next to
`Player.ShowMessage(1)`, matching id 1 = "not enough money" -- a Chinese
comment and a Thai table agreeing without coordination).  Against this
round: **seven** tables cover all 20 literal ids by range, not one, so
coverage alone settles nothing -- only content does; and the derivation
covers 20 ids across 65 of the 116 call sites, not all of them.

### TWO_SESSIONS_SAME_SCENE

Applicable, and this round's FIRST answer was wrong -- adversary caught it
(D2).  The draft argued "not applicable, because the sink always keys by
`character_id`", which describes the defect itself as though it were the
safety property: a scene announcement filed under one character is exactly
what a second session in that scene never sees, and every literal call site
in the corpus (`t_bg2017_msg.lua`) uses audience 2.

The answer after the fix: audiences `0/1` go to the character's bucket;
audiences `2/3` go to the SCENE's bucket, which every session in that scene
reads (`broadcasts_for(scene)`), each row carrying which character's
trigger fired it.  A test pins that a player who fired nothing reads the
same announcement.  Audience `1` (party) still files under the firing
character and is tagged, because fanning out to a party needs a party
registry this lane does not own -- a named gap, not a hidden one.  Caps are
per bucket, and nothing is sent on the wire either way.



## Round 7kxfe9 (2026-09-07) -- the message catalog becomes a checkable mirror, and four named debts from `6775u1` are paid

Round order came from the mailbox, not from the queue: COO-DECISION
`20260907_0405` answered this lane's `20260907_0322` letter and told it to
vendor the localized `s_MESSAGE` column as ASCII escapes, with a provenance
header and a regenerate script.  `NOW.md`'s LANE-Q ladder item 5
(exp-level) is the NEXT round's work and is not touched here.

### The vendored file is now a mirror, and "it still matches" is a command

`lua_api/message_catalog.tsv` carries all four columns of
`pf_bridge/gamedata/tables/TEXTDATA_TH__MESSAGE.tsv`.  Every character
outside printable ASCII -- and the backslash itself -- is written `\uXXXX`,
so the file is **ASCII by construction**: 0 non-ASCII bytes on disk,
measured, which is the class of failure that burned `#961`/`#967` on the
Windows gate.  180 KB.

Round-trip is EXACT, measured over all 907 rows rather than argued: encode
then decode reproduces the source string for every row, and the loaded
catalog compares equal to a fresh parse of the source table, all four
columns.  The source has no backslash today (0 of 907, grepped) -- that is
a fact about today's table, not a property of the format, so the encoder
escapes the backslash anyway and a test pins that a literal `\u0e40` typed
by a future translator survives as those six characters instead of turning
into a Thai letter.

Three obligations came attached to the permission, and all three are code:

1. `tools/pf_regen_lua_message_catalog.py` rewrites the file from the
   source; `--check` exits non-zero and prints the first differing line.
   It imports the encoder from `lua_api.message` rather than keeping a
   second copy that could drift from the decoder.
2. The file's header names the source path, a sha256 of the source, the row
   count, and the pull date.
3. The tie is a test, not a belief --
   `VendoredCatalogMatchesTheRealTableTests` compares all four columns AND
   runs the regenerate script's own `--check`.

### The drift test moved, because where it lived it was not running

The tie added in `6775u1` sat in `test_script_lua_corpus.py`, whose key is
`lua_corpus_runnable` = bridge corpus AND lupa.  Comparing two TSV files
needs no Lua runtime, so on a bridge machine without lupa the one test that
proves the vendored copy is honest was silently skipped.  It now lives in
`test_script_lua_api_message.py` under `BRIDGE_GAMEDATA`, which is a
strictly wider set of machines.  Pins re-measured, not predicted:
`lua_corpus_runnable` in `test_script_lua_corpus.py` 10 -> 9, and 2 new
`bridge_gamedata` skips here.

### A hole this round found in its own module while measuring

Running this module on a lupa-free interpreter was RED, not skipped: three
`OneScriptHostSharesOneMessageSinkTests` tests build a real `ScriptHost`,
which raises without lupa -- while the module's own header (written last
round) claimed every test in it ran with or without the Lua runtime.  That
sentence was false.  The class is now guarded by `LUPA_PACKAGE` and pinned
(3), the header says what is actually true, and the measurement is
recorded: before the fix `3 failed, 51 passed, 9 skipped`; after,
`51 passed, 12 skipped`; with lupa present, `132 passed` across the three
modules and 0 skips.

### The four named debts from `6775u1`

- **D5 (fail-closed load).** The catalog was read at import under
  `encoding="ascii"`, so one stray byte or a missing file became an
  ImportError from inside `lua_api/__init__` -- the module that installs
  every namespace hook -- and all 160 API names vanished with a traceback
  naming an import, not a data file.  It is now LAZY and cached behind a
  lock, and any failure raises `MessageCatalogError` naming the path.  A
  file with a header but no rows is an ERROR, not an empty catalog (an
  empty catalog would refuse every message in the game in silence).
  `MAX_MESSAGE_ID` became `max_message_id()` for the same reason: a module
  constant would have to be computed at import, which is the eager load
  this removes.
- **D8 (`message_type` had no reader).** It has one -- `message_type()` --
  and the column is now justified by the file's contract rather than by
  use: the file is a MIRROR of the source table, so every column belongs
  to it by definition.
- **D9 (no lock).** `InMemoryMessageSink` now holds an `RLock`, like both
  of its sibling stores in this package, because one world per scene is
  shared by every session in the process and read-then-append is not
  atomic.  Pinned by two concurrency tests: eight threads writing 400
  messages into a 200-cap bucket store exactly 200 and count exactly 200
  refusals; a reader never observes a half-written row.
- **D12 (drops were not countable).** 51 of the 116 corpus call sites pass
  an unmined `Trigger.VarN`, so an id landing in one of the table's 54 gaps
  is an EXPECTED recurring event that was leaving one log line and no
  number.  The sink now counts refusals by named reason
  (`unknown_message_id`, `bad_audience`, `bad_arity`, `no_scene`,
  `bucket_full`, `too_many_buckets`), read back with `refusals()`.  Bad
  audience and bad id are counted APART: a run dropping ids is an unmined
  `.tgr` table, a run dropping audiences is a misread of the `Var2`
  mapping, and one combined number cannot tell those two apart.

### pf-adversary came back BEFORE the unlock, and did not approve

13 defects, 12 of them measured with a control run.  Six are fixed in this
round; the rest are named below rather than tucked away.

The one that mattered most (D1) is that the drift tie STILL does not run on
the machine that decides whether a PR merges: `.github/workflows/
gate-windows.yml` fetches no bridge checkout, so `BRIDGE_GAMEDATA` skips
there.  Measured: all 907 text cells replaced with one repeated string,
`52 passed, 11 skipped, 0 failed`.  Moving the test was a real widening and
the claim "strictly wider" is true -- but it left out the machine that
matters, and saying "wider" without saying that is the half-truth this lane
keeps having to be caught at.

The fix is the adversary's own best proposal: the header now carries
`# body_sha256:` of the file's own body, checked by a class with NO
precondition, so it runs on the gate.  It does not prove the copy matches
the source -- only the source-digest test can -- it proves nobody has edited
the copy since it was generated, which was the unguarded half.  That single
change closes D1 (mass rewrite), D3 (a TAB inside a cell), D4 (eight rows
end in a trailing space that any whitespace-fixing tool removes) and D5 (a
provenance header nothing on the gate could check).

Also fixed:

- **D2 (the encoder corrupts silently above the BMP).** `"\u%04x" % 0x1F3C6`
  renders `\u1f3c6`, which the four-hex-digit decoder reads as U+1F3C plus a
  literal `6`.  It passed the round-trip test (which re-encodes what it just
  decoded) and `--check` (both sides share the encoder).  The shipped table
  is all-BMP today, measured -- so this is a tripwire, not a blocker:
  `escape_message_text` now raises rather than rewriting a message.
- **D3 (a malformed row).** `_read_catalog` refuses a row that is not
  exactly four fields, instead of handing back a truncated message with the
  row count still agreeing.
- **D6 (extending the sink protocol broke last round's sinks).** A sink
  written against `6775u1`'s protocol raised `AttributeError` out of the
  middle of a Lua call the first time a message was refused -- and 51 of the
  116 corpus call sites pass an unmined `Trigger.VarN`, for which the
  harness supplies 0, which has no row, so the refusal path is the one a
  corpus sweep takes constantly.  `check_sink` now refuses an incomplete
  sink AT INJECTION, naming the missing method.
- **D8 (`--check` conflated RED with INCONCLUSIVE).** No bridge checkout now
  exits 2 and says so; drift still exits 1.

NAMED, NOT FIXED: D7 (`refusals()` is not on the protocol, so a future
injected sink cannot be asked "how many did you drop"; three of the six
reasons are counted inside `InMemoryMessageSink` rather than at the
closure) · D9 (the bridge's `check_new_skips` does not recognise
`@X.skip_unless_present()`, the very idiom `pf_preconditions` orders every
lane to use -- a preflight hole, and chief's file) · D10 (this round's own
"no module logs the text" guard is a substring scan that misses
`script_host.py` one directory up and trips on the word in a comment) ·
D11 (`script_host.py`'s `except Exception` around entry points turns a
catalog failure into "this script failed", blaming the script rather than
the data file) · D13 (`AGENTS.md` forbids tracking decoded game data and
this vendors 907 rows of it; the adversary found precedent at a smaller
scale and could not settle whether this repository is public -- recorded
for COO, not acted on).

Two of its findings corrected THIS round's own prose, and both are in the
round file: there is no per-file or per-PR size ceiling for this repository
at all (the "400 KB" this lane cited is a bridge queue-file ceiling), and
62 of the 907 rows contain characters cp874 cannot represent, including
three ids the corpus really passes -- the table is not "Thai", it is Thai
with unlocalized CJK in it.

### What this round did NOT do

Nothing reaches a player's screen.  No frame is built here and no dispatch
exists; `runtime.py`/`app.py` remain outside this lane's write scope.  The
localized text is now AVAILABLE to whoever builds the frame -- that is the
whole change in reach -- and a test pins that no module in this package
passes it to a log line, because the bridge console is cp874.

`Party.ShowMessage` (1 call site) is still a stub.  D7 (audience meaning is
Lua-layer evidence only, zero wire confirmation) and the `.tgr` VarN mining
lead (`RE-273`) are unchanged and still named.

### TWO_SESSIONS_SAME_SCENE

Applicable, unchanged in shape from `6775u1` and now enforced under
concurrency as well as by keying: audiences `2/3` go to the SCENE bucket
every session in that scene reads, `0/1` to the character's own, and the
`RLock` added this round is what makes that true when two sessions in one
scene write at the same instant rather than only in a single-threaded test.

## Round 02mkqc (2026-09-07) -- paid three pf-adversary debts round 7kxfe9 named and deferred

No new API name became real this round: the count stays at 34/160.  What
changed is that three guards this lane wrote for itself stopped being
weaker than their own sentences claimed.

### D10 -- the "no module logs the localized text" guard was a substring scan

It asked whether the seven characters `message_text(` appeared in a file,
starting at `lua_api/` and stopping there.  Two holes, both now measured by
a control test that runs the mutation rather than arguing about it:

* `getattr(message, "message_text")(1)` never contains `message_text(` --
  the paren follows the `getattr`.  The old guard read that file and found
  nothing.
* The walk never reached `script_host.py`, one layer up, which owns the log
  callback every namespace writes through and is therefore the likeliest
  place for this defect to actually appear.

The guard is an AST walk now (`ast.Name` / `ast.Attribute` / an
`ast.Constant` string equal to the name, which is the `getattr` shape) over
`src/pirateforce_foundation/` entire.  Naming the function in PROSE stays
legal, which matters because the house rule tells every lane to leave
handoff notes and the honest note names things.

### D7 -- a write-only counter, with an unbounded dict behind it

`record_refusal` was on the `MessageSink` protocol; `refusals`, the reader,
was not, so a sink could satisfy `check_sink` and still have no way to
answer the one question the counter exists for.  It is on the protocol and
in `SINK_METHODS` now.

The dict behind it gave every string a caller passed its own key, in the
one path a corpus sweep takes constantly (51 of 116 call sites pass an
unmined `Trigger.VarN`), so a reason built out of runtime data grew it for
the life of the process.  An undeclared reason is now counted under
`REFUSE_OTHER`: the number stays exact, only the invented string is gone,
and `MAX_REFUSAL_KEYS` (7) is pinned by a test that feeds the sink a
thousand made-up reasons and reads the width back.

### D11 -- our own broken data wore the script's name

Every sweep body caught bare `Exception` and logged
`LUA_SCRIPT <file> ERR ...`, so a `MessageCatalogError` -- raised because
OUR vendored `lua_api/message_catalog.tsv` is missing or corrupt -- came
out as an accusation against whichever quest file happened to be loading,
and then the next one, up to 616 times, with the real cause named nowhere.

Host-side errors are caught first now and logged as
`LUA_HOST <type> ERR <message> discovered_at=<file>`, and recorded in a
separate `host_failed` list on both reports.  The two lists need opposite
responses: a name in `failed` means go read that quest file, a name in
`host_failed` means go fix this repository.  Fail-closed is unchanged --
this logs and continues, it never re-raises, so a bad vendored file still
cannot take a boot down.

### Two defects found while fixing those, both this lane's own

`tests/test_script_lua_api_message.py` had its `if __name__ == "__main__":
unittest.main()` block sitting two thirds of the way UP the file, so
running the module directly executed the classes above it and exited before
the twelve below were ever defined.  pytest never noticed, because pytest
imports a module and does not execute its `__main__` -- which is exactly
why it survived four rounds.  Moved to the end.

The first draft of the D11 comment spelled a vital's name in a comment
inside `script_host.py`, and LANE-E's own guard
(`test_no_foundation_module_emits_the_legacy_system_message`, a substring
scan over `src/` that does not skip comments) went red on the full suite.
Same class of defect as round `7kxfe9`'s docstring versus the n/327 census,
found the same way -- by running the whole suite, not by reading the diff.
The comment says what it means without the name, and says why.

### Numbers, all measured on this round's tree

* `tests/test_script_lua_api_message.py`: 79 tests (was 67), +12.
* Full suite before the de-naming fix: 3 failed / 12893 passed.  Two of the
  three (`test_ui_wire_name_census.py`) are red on `origin/main` `550a36d`
  itself, with nothing of this branch present -- see the round's ALERT
  letter; the pin now reads 161 while a fresh derive returns 160, the
  opposite direction from what `NOW.md` records.
* `lua_api.trigger`: 8 of 17 real, measured from `REAL_METHODS`, correcting
  the stale "5/17" carried in `RE-273`'s body.


## Round `xlk7hl` (2026-09-07) -- the READ half of the exp/level seam

COO-DECISION `2026-09-07T05:46` split system item 5 (exp-level) in two and
gave LANE-Q the read half only: "Q owns the read half through a Protocol;
the write half waits for real columns -- do not keep a competing in-memory
ledger, not even 'temporarily'".  This round is that read half.

### What the six zero-argument reward names actually read

`api_spec.tsv` gives all six an arity of exactly 0.  Zero arguments means
the amount is not in the script, so it is in the tables.  It is:

    CONSTDATA_TH__STANDARD_QUEST.tsv[level].<kind>
      * QUESTDATA_TH__QUEST.tsv[quest].<kind multiplier>

`CONSTDATA_TH__STANDARD_QUEST.tsv` is the standard per-level quest reward
curve -- 255 rows keyed by level, columns `n_QUEST_CASH`/`n_QUEST_EXP`/
`n_QUEST_SP`, rising monotonically (level 1 -> 90 exp, level 100 ->
100,520).  "Criteria" in the API names is that curve.

### This corrects LANE-Q's own previous round, which had it wrong

Round `02mkqc`'s letter to LANE-DB named `n_LEVEL_EXP` and `f_EXP` as the
two candidates for the AMOUNT.  Reading the values disproves both:

* `f_EXP` has 11 distinct values in all 1544 rows and every one is a small
  ratio (0.0, 0.1, 0.25, 0.3, 0.5, 1.0, 1.4, 1.5, 2.0, 3.0, 5.0; stored
  float32-widened, e.g. `0.10000000149011612` literally on disk).  A
  multiplier column, not an amount column.
* `n_LEVEL_EXP` runs 1..120 and **all 1544 rows resolve to a curve row, 0
  orphans**.  A level index, not an amount.

Both facts are pinned by tests that need no bridge checkout, so a future
change that re-points either column goes red instead of quietly paying
wrong rewards (`test_f_exp_is_a_multiplier_not_an_amount`,
`test_every_quest_rows_criteria_level_resolves_to_a_curve_row`).

### The one assumption, labelled

Which level each triple uses is NOT proven.  The 166 files calling the
plain triple and the 59 calling the `Lv` triple are disjoint (0 overlap,
measured), so the prefix is the only discriminator.  `LEVEL_SOURCE` reads
`Lv` as "the player's level" and plain as "the level on the quest row", on
two independent measurements:

1. `n_LEVEL_EXP` differs from `n_LEVEL_QUEST` on 647/1039 rows behind the
   plain triple (62%, actively tuned) but 32/174 behind the `Lv` triple
   (18%, only 31 distinct values at all -- the column reads as unused).
2. 53 of the 59 `Lv` files also call `Quest.ReportDailyQuest`, against 5 of
   the 166 plain files.  A daily repeatable pays whoever repeats it.

Neither is a proof, so `AddLvCriteria*` **refuses** (logs
`refused=player_level_unknown`) when no player level is supplied rather
than falling back to the quest row's level.  Falling back would pay a
level-15 reward to a level-90 player on every daily in the game and nothing
would look broken.  ASK-COO letter `20260907_0742` carries the question.

Rounding is unverified too: `CriteriaAmount` carries both the exact product
and its floor, and does not choose for whoever eventually grants.

### Files

* `lua_api/quest_criteria.py` -- loader, resolver, closed refusal set.
* `lua_api/quest_criteria_curve.tsv` (255 rows) and
  `lua_api/quest_criteria_rows.tsv` (1544 rows) -- vendored ASCII mirrors
  in the shape `message_catalog.tsv` established, each carrying a
  `# body_sha256:` of its own body so the Windows gate (no bridge checkout)
  can still check the copy is internally honest.
* `tools/pf_regen_lua_quest_criteria.py` -- `--check` exits 0 match / 1
  drift / 2 INCONCLUSIVE (no bridge beside the repo), the three states
  `pf_gate_preflight.py` already uses.
* `script_host._host_side_error_types()` gains `QuestCriteriaError`, so a
  corrupt mirror of OURS is logged `LUA_HOST ... discovered_at=<file>` and
  never as up to 616 `LUA_SCRIPT <file> ERR` accusations against innocent
  quest scripts (pf-adversary D11, round `7kxfe9`).
* `tests/test_script_lua_api_quest_criteria.py` -- 38 tests.


### Round `xlk7hl` addendum -- what pf-adversary found in this round's own work

Five findings landed inside the round and are fixed in the same PR:

1. **The mirrored columns were tied to the source FILE and not to the
   source COLUMN.**  `# source_sha256` / `# source_rows` / `# body_sha256`
   / `--check` all verify "the mirror equals what the tool produced from
   that file"; none verified the tool read the right column.  Re-pointing
   the regenerator from `n_LEVEL_EXP` to the adjacent `n_LEVEL_QUEST`
   (same 1..120 domain, same prefix) changed 647 of 1039 rewards and left
   all 38 tests green -- mutation-proven.  `test_each_mirrored_column_came
   _from_the_source_column_it_names` now reads both source tables BY COLUMN
   NAME and compares cell by cell; the same mutation now fails 729 subtests.
2. **`player_level=True` paid the level-1 reward.**  `bool` is `int` in
   Python, so `curve[True]` is level 1: a level-90 player would have been
   paid the newbie amount with nothing looking broken.  There is now a
   `bad_player_level` refusal, and whole-number floats are accepted the way
   this house already settled it for `Quest.CheckOpenTime` (`900.0` is 900).
3. **`_host_side_error_types()` was a hand-maintained tuple with no
   completeness test** -- the next vendored mirror would have raised an
   unlisted error and been blamed on a quest script again, through the door
   D11's own fix left open.  Every `lua_api` loader now raises a subclass of
   `lua_api.vendored.VendoredDataError` and the classification is complete
   by construction.
4. **`test_the_six_names_are_exactly_the_zero_arity_reward_names` never
   read an arity column**, although zero-arity is the premise the whole
   design rests on.  It does now.
5. **`docs` said `amount real`** for six names that refuse on 100% of real
   call sites.  Corrected above.

Carried to the next round, named rather than hidden:

* `gamedata/PF_GAMEDATA_LUA_API.tsv` records `AddLvCriteriaExp` as
  **`UNRESOLVED` -- the one of the six with no binding found in the client
  at all**, and it is exactly the name whose level source this round is
  assuming.  The other five carry a `delegate_va`; disassembling
  `0x00608D10` (plain) against `0x006092B0` (`Lv`) and reading which
  structure offset each loads is the disproof the ASK-COO letter asks for,
  and it is an RE ticket, not a round of grepping.  (Layer warning for
  whoever writes it: `delegate_body6` is six bytes of SEH prologue shared
  by unrelated names -- it is not a calling-convention signature.)
* `run_corpus_entry_points` still files an innocent script in `call_failed`
  and duplicates it in `host_failed` once per entry point, so the
  616-accusation shape D11 fixed in the log survives in the structured
  report.  The `except` clauses in both sweeps are also untested: deleting
  them keeps the suite green.
* `lua_api/spec.py` still reads `api_spec.tsv` at import time under
  `encoding="ascii"` with a bare `assert` -- the exact shape D11 fixed for
  its sibling, and it kills the boot before any fail-closed machinery runs.
* The D10 guard's `ast.Attribute` branch is dead code, and an aliased
  import (`from .message import message_text as mt`) or `catalog()[id][2]`
  evades it entirely.  `refusals()` is still never called outside tests.
* `int(raw)` is one short on 11 (quest, kind) pairs, all of them the
  float32-widened `1.4` multiplier.  Neither value the module offers is
  `round()`, which is the only one that recovers the designer's integer.
* `s_LUASCRIPT` is one-to-many: `q_con1` is the script of 160 quest rows
  carrying 86 distinct `(level, multiplier)` pairs.  So no per-file test
  can ever tie a resolved amount to an observed reward -- only a live quest
  instance can, which is the same missing dispatcher as above.
