# PF RUNTIMERES-ENCODER-001 — the spawn-then-kill actor-entry encoder: a server-side sweep that can drive a **known** actor through the client's real engine death chain, and the one thing it still cannot do

2026-08-19 · lane worker · **server encoder + scenario + verifier + tests, additive, opt-in, fail-closed** · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · reproduce: `py -3 tools/pf_runtimeres_death_encoder_static.py` (**88 guards, 30 of them a regression gate, exit 0**), `py -3 tools/pf_runtimeres_death_encoder_static.py --json`, `py -3 -m pytest tests/test_runtimeres_death_hypothesis.py -q`

> **The answer, first, in one paragraph.** RUNTIMERES-ACTOR-ENTRY-001 (round 85) ended with a recipe and three countable zeros. All three are now non-zero. `src/pirateforce_foundation/runtimeres_death_hypothesis.py` composes **three `GSCN_RunTimeProtocolRes` id `0x6E9D` frames for one identity**: a live spawn, then the same identity again with `HP == 0` and the death timer **strictly positive** (the `vt+0x40` / `0x43BDA0` side, which latches `[actor+0x70] |= 0x200` at `0x44384C`), then the same identity a third time with the timer **explicitly `0.0f`** (the `vt+0x3C` / `0x43BD70` side, which is what opens `0x443990` → `0x4439E9 call 0x472810` → `CActorTask_Dead` → `L"_F_DIE_000"` @`0xF0F060`). Every frame carries the **inherited** change mask `0x00` and the **derived** change mask `0x02`, the bit `0x5E3EFD` binds to the object at `+0x1C`. The three PCs are pinned byte-for-byte (173 / 120 / 120 bytes) and the whole sweep is re-read by an independent tag walker before it is returned; a sweep that is missing the `0x02` mask, or whose timer never reaches `<= 0`, or whose kill frames name a different identity, produces **no bytes at all**. **What is NOT delivered: the dispatcher.** `runtime.py` was outside this lane's declared scope, so `make_state_class` has no branch for this scenario and `app.py` **refuses to boot** with the flag rather than start a server that answers nothing. That is the single remaining item between here and GT-022, and it is the chief's to place.

**Grade:** envelope · derived mask · spawn-then-kill identity discipline · timer polarity · byte pins · fail-closed gating = **A** (every claim re-derived from the image and from the composed bytes by a pure-stdlib verifier whose first 30 guards reproduce round 85's published answers before it is allowed to assert anything new; 6 trap tests prove the validator can reject) · **client acceptance of any of these bytes = not claimed, that is GT-022** · **dispatcher wiring = not delivered, and said so out loud** · no ledger entry added, no coverage row flipped.

---

## 0. Files touched — the complete list

| file | status |
| --- | --- |
| `src/pirateforce_foundation/runtimeres_death_hypothesis.py` | **new** — the encoder, the polarity constants, the validator, the exact-allowlist loader |
| `scenarios/runtimeres_death_hypothesis_spawn_then_kill.json` | **new** — the opt-in scenario, generated from the module's `_expected_scenario()` so the two cannot drift |
| `src/pirateforce_foundation/app.py` | **modified** — `--runtimeres-death-hypothesis-scenario`, mutual exclusion, `--db` requirement, console mode, and the refuse-to-boot check |
| `tools/pf_runtimeres_death_encoder_static.py` | **new** — pure-stdlib verifier, 88 guards |
| `tests/test_runtimeres_death_hypothesis.py` | **new** — 39 tests / 26 subtests, 6 trap tests |
| `reports/PF_RUNTIMERES_ENCODER001_SPAWN_THEN_KILL_20260819.md` | **new** — this file |

Nothing else was touched. `current/pf_login_game_server_v141.py`, `state/pirateforce.sqlite3`, `references/`, `evidence/`, `.gitignore`, `runtime.py`, `docs/HYPOTHESIS_LEDGER.json`, `docs/FUNCTIONAL_COVERAGE.json` and everything under `pf_bridge/` were **not** modified. No server was booted, no GameClient opened, no socket, no database write, no capture.

### 🔴 STOP — two of these five files are currently GITIGNORED

`.gitignore` line 8 is `/reports/*` and line 99 is `/tools/*`: both directories are deny-by-default with a per-file allowlist, exactly as `pf_runtimeres_actor_entry_static.py` (line 272) and its report (line 273) had to be added last round. `git check-ignore -v` says:

```
.gitignore:99:/tools/*    tools/pf_runtimeres_death_encoder_static.py      <- IGNORED
.gitignore:8:/reports/*   reports/PF_RUNTIMERES_ENCODER001_..._20260819.md <- IGNORED
```

They do **not** appear in `git status` and **a commit made now would silently drop the verifier and this report**. `.gitignore` is on this lane's do-not-touch list, so the chief must add exactly these two lines:

```
!/tools/pf_runtimeres_death_encoder_static.py
!/reports/PF_RUNTIMERES_ENCODER001_SPAWN_THEN_KILL_20260819.md
```

The other three (`src/…/runtimeres_death_hypothesis.py`, `scenarios/…json`, `tests/…py`) are covered by the existing `!/src/**`, `!/scenarios/**` and `!/tests/**` negations and need nothing. Per the standing rule, a change that touches `.gitignore` runs the seam test first.

---

## 1. What the sweep actually is

Three frames, one identity, in this order. Every byte below is reproduced by the verifier.

```
                                             inherited  derived
                                             mask +0x18 mask +0x1C
SPAWN        actor_type 4 (CNetNPC)              0x00      0x02     173 B PC / 185 B frame
             NPCAttr 0x0AD5 + MovementAttr 0x2067
             BasicAttr mask 0x030C   HP 100/100, bit 0x0080 ABSENT
             -> identity unknown -> 0x446F91 lookup MISSES -> 0x446990 spawn
                -> applied through vtable +0x10, which never touches 0x4437C0

DYING_LATCH  actor_type 4, SAME identity          0x00      0x02     120 B PC / 131 B frame
             NPCAttr only (the corpse is not re-placed)
             BasicAttr mask 0x038C   HP 0/100, bit 0x0080 = 20.0f
             wire bytes:  2A 00 00 A0 41
             -> identity KNOWN -> 0x446F98 FOUND -> vtable +0x20 -> 0x4446F0
                -> 0x444705 call 0x4437C0
                -> vt+0x40 0x43BDA0 TRUE  (HP==0 AND timer>0)
                   0x44384C sets [actor+0x70] |= 0x200        (DYING latch)
                -> vt+0x3C 0x43BD70 FALSE, so 0x443990 stays shut: NO task yet

DEATH_TASK   actor_type 4, SAME identity          0x00      0x02     120 B PC / 131 B frame
             BasicAttr mask 0x038C   HP 0/100, bit 0x0080 = 0.0f
             wire bytes:  2A 00 00 00 00
             -> vt+0x3C 0x43BD70 TRUE  (HP==0 AND timer<=0)
                0x443990 OPENS -> 0x4439C7 allocates 0x24 -> 0x4439E9 call 0x472810
                CActorTask_Dead, vtable 0xF0F048, task id 0x80000005
                -> 0x472850 / 0x4765C0, behind [actor+0x70] & 0x40 (model loaded)
                -> push 0xF0F060 -> actor vtable +0x28 -> L"_F_DIE_000"
```

Gaps 0.0 s / 6.0 s / 6.0 s on the frozen V141 cumulative deadline — the same spacing the attended HP-death rounds already used. No new timing is invented.

**Pinned bytes** (the verifier and the tests both check these, so they cannot agree with each other while disagreeing with the encoder):

| step | PC size | PC SHA-256 | frame size | frame SHA-256 |
| --- | --- | --- | --- | --- |
| `SPAWN` | 173 | `8965DCF2574B733B119741D2350FB5BAB6D416A9168113AA3E95A5F2FBAC698C` | 185 | `E7E2B0C671C1B023F5FD6FAE4D6489CC670F648DBD3802A67B760816A78AB0C4` |
| `DYING_LATCH` | 120 | `451D73AD2AB0360D206DDD3A3C4CED9A7A328FFD8455B84C4018A27B635D21EA` | 131 | `CDBFED6788E418110C1D8FE177BE9D4275DC7FF376A8E654F3B734C14BCDA2E4` |
| `DEATH_TASK` | 120 | `0116A7300814CA53F38668B2CAA193123324360F172EE2A9F9B5791BDE81BF0C` | 131 | `D545EC392D880D96BBC669A1F5646741268E8D0E29FD32B90474FF080160D1A0` |

### Nothing about the target actor is invented

The probe is **selected**, not typed. `resolve_probe()` loads the frozen, hash-pinned `PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS` (115 rows, SHA-256 `22D7430E..9618`) through the existing `population.load_port_royal_placements`, and takes the single placement nearest the frozen `V135_PLAYER_*` spawn — the same distance rule `population.py` already uses to decide who the client is told about. That is deterministically:

| field | value | where it comes from |
| --- | --- | --- |
| placement index | `0` | frozen source |
| template id | `1` | frozen source |
| visual preset | `P_MALE_002_000_SP1` | frozen source |
| source name | `Navy Transfer` | frozen source |
| actor identity | `0x2001` | `population.py`'s existing `0x2000 + index + 1` |
| XYZ | `(-9139.957, -2780.045, 223.292)` | frozen source, ~111.8 units from the player spawn |

All six are re-pinned as module constants, so a drift in either frozen source turns the lane red instead of silently killing a different NPC somewhere else.

### The encoder is a superset that degrades to the known-good body

`legacy.make_npc_attr` cannot emit BasicAttr bit `0x0080`. `encode_death_capable_npc_attr` can, and on **every call where the timer is absent it asserts that its output equals `legacy.make_npc_attr` byte for byte** (82 bytes for this probe). The lethal body is that same body plus **exactly the five bytes** of the tag-`0x2A` f32, and the mask differs by exactly bit `0x0080` (`0x030C` → `0x038C`). That equality is the whole reason to believe the widened encoder puts the field in the right place: it is the frozen projection this project's actor-entry emitters already ship, plus one field, in ascending mask-bit order.

---

## 2. GT-022's four unblock conditions, one line each

| # | condition | status | evidence |
| --- | --- | --- | --- |
| 1 | encoder emits `0x6E9D` with change-mask bit `0x02` and object `+0x1C` | ✅ **met** | verifier s.2: all three PCs carry id `0x6E9D` (re-derived by hashing the `.rdata` literal at `0xF2FFF8`), version 4, inherited mask byte `0x00` at PC offset 11, derived mask byte `0x02` at PC offset 13; `0x5E3EFD` pinned as the instruction that binds bit `0x02` to `+0x1C`; envelope produced by the frozen `make_runtime_remote_actors`, not by new code |
| 2 | spawn-first, kill-second, same identity | ✅ **met** | verifier s.3: all three frames carry identity `0x2001`; frame 1 has `HP = 100` and no `0x0080` and carries MovementAttr; frames 2–3 have `HP = 0` and re-use that identity, so `0x446F91`'s lookup hits and `0x446F98` takes the vtable `+0x20` branch instead of the spawn `0x446990` |
| 3 | the timer sweep reaches `<= 0`, polarity explicit | ✅ **met** | verifier s.4: frame 2 timer `20.0f > 0` satisfies `0x43BDA0` (vt`+0x40`) and **not** `0x43BD70`; frame 3 timer `0.0f <= 0` satisfies `0x43BD70` (vt`+0x3C`); the raw bytes `2A 0000A041` and `2A 00000000` are asserted present; named constants `DYING_LATCH_TIMER_SECONDS` / `DEATH_TASK_TIMER_SECONDS` / `DEATH_TASK_TIMER_CEILING` each carry a comment naming the vtable slot they gate; the validator **refuses** a sweep that stays positive |
| 4 | headless proof to the wire layer + ledger/verifier/matrix per the standard pattern | 🟡 **partly met** | **Wire layer: yes** — `tools/pf_runtimeres_death_encoder_static.py` composes the real frames and re-reads them with an independent tag walker (88 guards, exit 0), and `tests/test_runtimeres_death_hypothesis.py` asserts the complete hex of all three PCs. **Dispatcher replay: no** — see §3. **Ledger/matrix: not done, deliberately** — see §5 |

**So GT-022 is not yet PENDING.** Conditions 1–3 are closed. Condition 4 is closed at the wire layer and open at the dispatcher.

---

## 3. What is NOT delivered, stated plainly

**There is no dispatcher branch.** The lane's declared deliverables were the module, the scenario, the `app.py` flag, the verifier, the tests and this report. `src/pirateforce_foundation/runtime.py` was not among them, so `make_state_class` has no `runtimeres_death_hypothesis_scenario` parameter and no `_dispatch_runtimeres_death_hypothesis` method.

**A dispatcher-level headless replay is therefore unreachable, and not because a server would be needed.** `tools/pf_hp_death002_headless_replay.py` proves the pattern works without booting a listener — it builds a `make_state_class` state on a throwaway SQLite file, feeds it a login / create / start-game / chat-input sequence and reads the returned frames. That harness is available and I would have used it. It cannot see this lane because the keyword it would have to pass does not exist. **I did not fake it and I did not stub it**; the byte-level proof is delivered instead, exactly as instructed.

**`app.py` fails closed rather than lying.** With the flag present, the scenario is loaded and validated against the exact allowlist, the `--db` requirement and mutual exclusion are enforced, and then `app.py` inspects `make_state_class`'s signature and calls `pre.error(...)`:

```
app.py: error: --runtimeres-death-hypothesis-scenario is accepted and its scenario
validates, but make_state_class has no runtimeres_death_hypothesis_scenario
parameter, so no frame would ever be dispatched. Refusing to boot.
```

No listener binds; argparse exits 2 before anything opens. The day `runtime.py` grows the parameter, that check passes by itself and the flag goes live with no further edit to `app.py` — and `tests/…::AppWiringTests` skips itself instead of going red. The scenario file also states it in the data: `"dispatch": {"wired": false, "wiring_owner": "chief_…"}`.

---

## 4. Fail-closed, and the guards that prove it can fail

* `production_allowed = False` in the module and `"production_allowed": false` / `"test_only": true` / `"lethal": true` in the scenario, all asserted.
* The scenario is checked against an **exact allowlist** — one extra key, one missing key, one changed value anywhere in the tree and the loader raises. Ten mutation variants are tested, including a flipped polarity value and an edited byte-pin.
* **BasicAttr bit `0x0080` cannot be named without the lethal unlock**, and the only way to obtain that token is `runtimeres_death_lethal_unlock(scenario)` on the allowlisted scenario object. A hand-built look-alike `RuntimeResDeathLethalUnlock` with identical fields is rejected (identity, not equality). With the flag absent, nothing in the process can emit a death timer on the actor-entry path.
* Every sweep is validated **and** hash-pinned before `build_runtimeres_death_sweep` returns.

**Six trap tests, each pinning the message it expects** so a trap cannot pass by tripping over something else:

| trap | what it builds | required rejection |
| --- | --- | --- |
| 1 | derived mask byte cleared to `0x00` (and, separately, set to the neighbouring `0x04`, which selects `+0x24`) | *"missing bit 0x02"* — the `ErrorData=28317` over-read shape, and the shape whose `+0x1C` object is never read at all |
| 2 | the final timer left at `5.0f` | *"never reaches <= 0"* |
| 2b | the two kill frames swapped, so the sweep re-arms after opening the gate | *"re-arms the timer after opening the task gate"* |
| 3 | frame 1 replaced with a dead frame | *"an actor cannot be born dead"* |
| 4 | **both** identities in the kill frame moved to `0x2002` | *"that is a second spawn"* |
| 5 | a spawn whose NPCAttr carries no visual preset | *"carries no visual preset"* — `[actor+0x70] & 0x40` at `0x47289E` would never open, so the actor would latch, get a task, and never animate |

Plus structural traps: truncated frame, wrong frame count, relabelled step, envelope id swapped to `UpdateAttrVital 0x309A`, `actor_type 9` (outside the 2..6 jump table), and a kill frame that drops the timer entirely.

**Three whole-encoder mutations were run by hand and all three were killed:** a step plan whose last timer stays `20.0` (killed by the polarity guard), a plan that spawns already dead (killed by the born-dead guard), and a plan that changes spawn HP from 100 to 99 (killed by the byte pin — a one-byte change).

### The verifier reproduces a known answer before asserting a new one

`tools/pf_runtimeres_death_encoder_static.py` opens with a **regression gate**: 30 guards that reproduce seven answers round 85 already published, each cited by address —

* `0x446F30` has exactly one direct `E8` caller, `0x5E4085`, and **zero** dword pointers anywhere in the 14,759,424-byte file (R85 §5 #3);
* `0x4437C0` → one caller `0x444705`; `0x472810` → one caller `0x4439E9`, both zero-pointer (R85 §5 #4);
* `L"_F_DIE_000"` at `0xF0F060`, exactly one occurrence, exactly two reference sites `0x4728B0` / `0x476710` (R85 §5 #6);
* `0x5F2400..0x5F261A` contains **zero** `mov r,[reg+0x20] … call r` shapes (R85 §5 #8);
* the two predicate spans at `0x43BD70` and `0x43BDA0`, byte-exact, and the `0.0f` at `0xF0989C` (R85 §5 #9);
* `0x446F87` find-or-create and `0x446AAD` spawn-applies-through-`+0x10` (R85 §5 #10);
* the actor-type gate `0x4469C8` and all five jump-table cases at `0x446B2C` (R85 §5 #11).

**If any of those fail the tool prints them, asserts nothing new, and exits 2.** Reproducing an old answer is the licence to state a new one. The censuses are byte matching over **both** executable sections (`.text` and `.code`) — no disassembler, so the round-83 "linear decoder stopped early" failure mode cannot recur. The tool is pure stdlib (`hashlib`, `json`, `os`, `struct`, `sys`); a test asserts it imports no `capstone`, `pefile`, `numpy`, `yaml` or `requests`.

---

## 5. What I did NOT do, and what I recommend the chief do

I did not add a ledger entry and did not flip a coverage row, as instructed. Two notes on **why the encoder had to be built without one**:

`tools/verify_hypothesis_ledger.py`'s `verify_source_annotations` scans `src/**/*.py` and `scenarios/*.json` for `# PF-HYPOTHESIS-LEDGER: <ID> <state>` and raises `unregistered emitter annotation` for any id not in the ledger — and, symmetrically, `declared emitter is missing adjacent annotation` for a ledger entry whose `source_refs` carry no annotation. **The ledger entry and the annotation must therefore land in the same change**, which is the chief's. So this lane carries the proposed id `HYP-PF-023` as data (module constant, `"hypothesis_id"` field, `HYP_PF_023_…` action labels) and **no annotation comment anywhere**. `verify_hypothesis_ledger.py` stays green today.

**Recommended ledger change — APPEND `HYP-PF-023`, count 29 → 30:**

* *transform*: emit `GSCN_RunTimeProtocolRes 0x6E9D` with inherited mask `0x00` and derived mask `0x02` (object `+0x1C`), carrying one `actor_type 4` entry, three times for one identity — spawn alive, then `HP=0` with BasicAttr bit `0x0080` `> 0`, then `HP=0` with bit `0x0080` `<= 0`.
* *ceiling / stop rule*: one scenario file, one identity, three frames, `actor_type 4` only, timer values `{20.0, 0.0}` only. A fourth frame, a second identity or a different actor type is a new version.
* *falsification*: the client does not animate, or raises `ErrorData=28317`, or the dying pose is identical to what GT-019 already showed (which would mean GT-021's prediction #4 was wrong and the GT-019 pose was `_F_DIE_000` all along).
* *evidence_gap*: **no client has seen one byte of this profile.** Offline only.
* *source_refs*: the module, the scenario, `app.py` — each with the adjacent annotation the verifier demands.
* `production_allowed: false`.

**Recommended coverage change — none yet.** `combat/hp_death_and_respawn` should stay exactly where it is until GT-022 runs. Round 85 §6 already flagged that the round-84 `runtime_pass` flip on that row was made on a lane that cannot animate anything; this lane does not resolve that, and flipping anything on the strength of an offline composition would repeat the mistake. If the chief wants to act on §6, that is a separate decision about the *existing* row, not about this one.

**Recommended next lane (small, one file):** `RUNTIMERES-DISPATCH-001` — add `runtimeres_death_hypothesis_scenario` to `make_state_class` and a `_dispatch_runtimeres_death_hypothesis` branch keyed on `CHAT_INPUT_VITAL_ID` (the same trigger the three existing sweeps use, for the same reason: it is the only action an attended tester can fire on demand), plus a `tools/pf_runtimeres_death001_headless_replay.py` modelled on `pf_hp_death002_headless_replay.py`. That closes GT-022 condition 4 completely.

---

## 5b. 🔴 THIS LANE TURNS ROUND 85's OWN VERIFIER RED — on purpose, and it needs a chief edit

`tools/pf_runtimeres_actor_entry_static.py` §5 counts our side's *absence* of this capability. Round 85 §4 tabulated three "actionable gaps, each a countable zero today" and said GAP 1 "would take one new emitter". **This module is that emitter**, so five of that tool's 150 guards now fail — not because a fact drifted, but because the gap they measured has been closed:

| counter | round-85 pin | now | why |
| --- | --- | --- | --- |
| `src_actor_entry_call_sites` | 4 | **5** | one new `make_remote_actor_entry(` call |
| `src_actor_stream_call_sites` | 4 | **5** | one new `make_runtime_remote_actors(` call |
| `src_modules_building_actor_entries` | 3 | **4** | `runtimeres_death_hypothesis.py` joins population / scenario / scene_object |
| `src_modules_setting_basicattr_bit_0x0080` | 2 | **3** | it joins runtime / stats_progression |
| `src_modules_doing_both` | **0** | **1** | ⭐ **GAP 1, closed.** This is the number the whole round-85 recommendation was about |

`tests/test_runtimeres_actor_entry_static.py` therefore goes red **in its entirety**, because its `load_tool()` executes the verifier and the verifier now exits 1.

**The one-edit fix (chief's, three files in one change):** re-pin those five numbers in `tools/pf_runtimeres_actor_entry_static.py` §5, update the `RUNTIMERES_COUNTS` block in `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` in the same change (its own §7 says to), and reconsider `actionable_server_gaps`, which is still hardcoded `3` and is now arguably `1` (only the dispatcher remains). I did **not** make that edit: those three files are outside this lane's declared scope and re-pinning another lane's published counts is a decision, not a chore.

⚠️ **One honesty note on GAP 2.** `server_call_sites_emitting_zero_current_hp` did **not** move and is still `0`, because its detector is the text proxy `current_hp\s*=\s*0` and this module reaches zero HP through the named constant `RUNTIMERES_DEATH_HP_ZERO` in a step table. The gap is **closed in substance** — frames 2 and 3 carry `HP == 0` on the wire, asserted byte-for-byte — while its regex still reads clean. That counter should not be trusted as-is; the chief may want to point it at the composed bytes instead of at source text.

**Also fixed inside this lane's own scope:** an early draft of the module's `nonclaims` tuple contained the word *respawn*, which falsified HP-DEATH-001's negative "no come-back-to-life encoder or dispatch exists in v141 or `src/`" and turned all 19 of that file's `load_tool()` tests red. The nonclaim was reworded (the meaning is unchanged — this lane still opens no way back). `tools/pf_hp_death_respawn_static.py` is **191 guards, 0 failures, exit 0** again and its test file is **36 passed**. That verifier's negative is a *substring scan over our whole source tree*, so future lanes should know a comment or a nonclaim string can break it.

---

## 6. Exact server args, for when the dispatcher exists

**These will not work today** — `app.py` will refuse to boot until `runtime.py` carries the branch. That refusal is the point.

```
py -3 -u -m pirateforce_foundation.app
   --db "<run copy of canonical>"
   --capture-root "<a folder OUTSIDE the repo, e.g. GameClient\capture_gt022_<stamp>>"
   --second-password-mode bypass
   --runtimeres-death-hypothesis-scenario "<repo>\scenarios\runtimeres_death_hypothesis_spawn_then_kill.json"
```

⚠️ `--capture-root` is **mandatory and must live outside the repo** (round-81 lesson: the server writes captures into cwd and corrupts the pinned corpus).
⚠️ Use a **copy** of the canonical DB, never the real one; compare the SHA against `CANON_SHA.txt` before and after. This lane opens no write path — HP has none in this project — but the rule stands.
⚠️ The flag is mutually exclusive with every other scenario flag, in `app.py` and again in `make_state_class`.

**What the tester should expect if the dispatcher is wired:** an NPC appears ~112 units from the spawn point (frozen placement 0, "Navy Transfer", template 1); 6 s later it should adopt the dying state; 6 s after that it should play `_F_DIE_000`. **The character will not recover** — this sweep has no restoring frame, on purpose. Nothing is written to the database.

---

## 7. Test and verifier results, honestly

| what | result |
| --- | --- |
| `python3 -m pytest tests/test_runtimeres_death_hypothesis.py -q` | **39 passed, 26 subtests passed** |
| `python3 tools/pf_runtimeres_death_encoder_static.py` | **88 guards (30 regression-gate), 0 failures, exit 0** |
| `python3 tools/pf_runtimeres_death_encoder_static.py --json` | valid JSON, `regression_gate: PASSED` |
| `python3 tools/pf_hp_death_respawn_static.py` (HP-DEATH-001) | **191 guards, 0 failures, exit 0** — green; `tests/test_hp_death_respawn_static.py` **36 passed** |
| `python3 tools/pf_runtimeres_actor_entry_static.py` (round 85) | 🔴 **150 guards, 5 failures, exit 1** — the five gap counters of §5b, closed on purpose. `tests/test_runtimeres_actor_entry_static.py` red in its entirety until the chief re-pins them |
| `PYTHONPATH=src python3 -m pirateforce_foundation.app --self-test-only` | exit 0, frozen self-test unchanged |
| full `tests/` run vs. the pre-change baseline | **one new red file, understood and itemised in §5b**; nothing else moved |

🔴 **The sandbox is Python 3.10 and has neither `capstone` nor `pefile`; the real gate runs on Windows `py -3` (3.14). These results are indicative, not authoritative.** 17 test modules cannot even be collected here (`ModuleNotFoundError: capstone` / `pefile`) and were excluded from both the baseline and the after-run; a further set fails for the same environment reason. The pre-change baseline on this machine was **33 failed / 1000 passed / 5 skipped / 19 errors**, confined to exactly three files — `test_actor_type_dispatch_static.py` (29, capstone), `test_login_vital_req_static.py` (3 + 19, pefile) and `test_server_shutdown.py` (1, timing). **None of those three is touched by this lane and none of them changed.** The only new red is `tests/test_runtimeres_actor_entry_static.py`, itemised in §5b. The chief should treat the Windows gate run as the authoritative number.

The after-run totalled **33 failed / 1037 passed / 5 skipped / 19 errors**, and the failing *files* are the same three as the baseline, with the same counts: `test_actor_type_dispatch_static.py` 29 (the tool prints `capstone required: pip install capstone`), `test_login_vital_req_static.py` 3 + 19 errors (pefile), `test_server_shutdown.py` 1 (timing).

⚠️ **The after-run was executed in four chunks, not one invocation.** The sandbox shell caps a single command at ~178 s and the whole suite needs longer. That is a weaker check than one green run and I am naming it rather than implying otherwise. `tests/test_runtimeres_actor_entry_static.py` could not be run to completion here at all — its verifier's image-wide `+0x20` dispatch census is minutes of pure-Python scanning and the trap tests re-run it — so it is excluded from those totals and its redness was established by running the verifier directly (§5b). Its exact failing-test count on the gate machine is therefore **not measured here**.

⚠️ **The working tree was not clean when this lane started.** `git status` showed another lane's uncommitted edits to `docs/PF_VITAL_NAMES.json`, `src/pirateforce_foundation/runtime.py`, `src/pirateforce_foundation/stats_progression_hypothesis.py`, `tools/pf_vital_name_thunk_static.py` and an untracked `tests/test_names_fold003_thunk_census.py`. **I did not touch any of them**, and both the baseline and the after-run were taken with them present, so the comparison is valid — but the chief should be aware that two lanes' work is sitting in the tree at once.

**Checks I did not run, named:** I did not run the Windows `py -3` gate. I did not run the seam test on a machine with `capstone`/`pefile`. I did not run `git check-ignore` on the new files (no commit was made — the chief commits). I did not boot a server, open the GameClient, or put a single byte of this profile on a socket.

---

## 8. Nonclaims

* **No client has ever seen one byte of this profile.** Everything here is composition and static re-derivation.
* Not proven: that the dying latch is a **prerequisite** for the death task. The two predicates are mutually exclusive branches inside `0x4437C0`; the task gate at `0x443990` does not read the `0x200` flag. `DYING_LATCH` is in the sweep because it exercises the positive side and matches what an attended tester wants to see, not because it is required.
* Not closed: the **229 unresolved vtable-`+0x20` dispatch sites** round 85 named. "One way in" remains ②-grade at that link, and this lane inherits that bound rather than narrowing it.
* Not claimed: anything about the ORIGINAL server, which is closed, was never published, and about which this project cannot read a single rule. This is a shape **our** client accepts (or will reject) — nothing more.
* Not claimed: respawn, corpse persistence, damage model, death penalty, or any recovery path out of the state this sweep leaves behind.
* Not claimed: any database effect. HP has no write path in this project and this lane opens none.
* Not claimed: production behaviour. `production_allowed` is `False` everywhere it appears.


---

# APPENDED 2026-08-19 — RUNTIMERES-DISPATCH-001: the headless replay, and the dispatcher §3 said was missing

> **Append-only.** Everything above this line is RUNTIMERES-ENCODER-001's report as delivered and is left exactly as written, including the sentences that are now out of date by one lane. This section says which ones, and why.

## 9. What this follow-up lane added

| file | change |
| --- | --- |
| `src/pirateforce_foundation/runtime.py` | new kwarg `runtimeres_death_hypothesis_scenario`; added to the mutual-exclusion tuple and its message; the scenario is re-validated through `require_runtimeres_death_hypothesis_scenario`, the lethal unlock is derived ONCE at construction, and the probe is resolved ONCE at construction (a placement drift now refuses at boot, not mid-session); new `_dispatch_runtimeres_death_hypothesis` keyed on `CHAT_INPUT_VITAL_ID`, placed after the HP-DEATH-002 branch |
| `src/pirateforce_foundation/app.py` | the refuse-to-boot stub is **gone** (and with it the `inspect` import and the `**{KWARG: …}` splat); the flag is now passed as a plain keyword like every neighbouring lane. **Every other guard is unchanged**: mutual exclusion with all twelve other modes, the explicit-existing-`--db` requirement, the `FileNotFoundError` on a missing DB, `store.migrate()` + `expire_open_sessions()`, and the deliberate absence of a `PF-HYPOTHESIS-LEDGER` annotation |
| `tools/pf_runtimeres_death_headless_replay.py` | **new**, pure stdlib, 64 guards, exit 0 |
| `tests/test_runtimeres_death_dispatch.py` | **new**, 25 tests, 3 traps |

**Nothing else was touched.** The encoder module, the scenario file, the static verifier, `tests/test_runtimeres_death_hypothesis.py`, the ledger, the coverage matrix and the HP-DEATH-002 lane are all byte-identical to how RUNTIMERES-ENCODER-001 left them.

## 10. The dispatcher, and why it is a forwarder and not a second composer

One accepted 34-byte ascii12 chat-input frame — the same trigger the three existing sweeps use, and nothing in it is read — is answered with the encoder's whole three-frame sweep. The dispatch method calls `build_runtimeres_death_sweep` and returns its list unchanged: it does not compose, does not re-label, does not re-time and does not touch the store. That is testable, and it is tested on the raw bytes rather than on a summary (§11).

**The lane is ONE-SHOT**, and that is a correctness requirement rather than a convenience. The scenario file already declared `"one_shot": true`. A second sweep would re-send `SPAWN` for an identity the client now knows, which takes the vtable `+0x20` **update** path instead of `0x446990` — HP back at 100 on an actor that had just been killed. A repeat trigger therefore returns `[]` with `runtimeres_death_hypothesis_already_sent_no_reply`. HP-DEATH-002 is deliberately *not* one-shot; this lane must be, and the difference is the born-dead/known-identity asymmetry, not a style choice.

Fail-closed discipline is unchanged from the neighbouring lanes: wrong shape, no selected character and not-yet-runtime-ready each return `[]` with a named `runtimeres_death_hypothesis_*_no_reply` event, no bytes and no write. `production_allowed` stays `False`.

## 11. What the headless replay proves — and what it does not

`tools/pf_runtimeres_death_headless_replay.py` boots a **real `make_state_class`** on a throwaway temporary SQLite file (the canonical DB is never opened), drives login → create → start-game → one chat-input frame **in process**, and checks 64 guards. No socket is bound, no server process is started, no client is opened.

**Proven, at the wire layer:**

1. **The dispatcher's bytes ARE the encoder's bytes.** The tool composes the sweep independently via `build_runtimeres_death_sweep` and compares the dispatcher's output to it with `==` — label, PC, framed bytes and delay, per step, and the whole action list as one object. If the dispatcher ever invents a frame, drops one, reorders one or shifts a delay, this goes red on the raw bytes. This is the guard the task asked to fail loudly, and it does.
2. **The frames are what round 85 says can reach the death chain**, re-read by a tag walker written inside the tool that does **not** import `decode_runtimeres_actor_entry_frame`: id `0x6E9D`, version 4, inherited mask `0x00`, derived mask bit `0x02`, count 1, `actor_type 4`, entry identity == NPCAttr identity, visual preset present (the `[actor+0x70] & 0x40` gate at `0x47289E`), every byte accounted for with none trailing. The walker's constants are cross-checked against the module's in guard section 0, so the two cannot drift apart silently.
3. **Spawn-then-kill on one identity**: all three frames name `0x2001`; frame 1 is alive with a MovementAttr and carries no bit `0x0080`; frames 2 and 3 carry `HP == 0` on that same identity.
4. **The inverted polarity, in order**: frame 2 satisfies `vt+0x40` (`0x43BDA0`, timer `20.0f > 0`) and **not** `vt+0x3C`; frame 3 satisfies `vt+0x3C` (`0x43BD70`, timer `0.0f <= 0`) and **not** `vt+0x40`; the last frame is the one that opens the task gate.
5. **Pins**: every dispatched frame reproduces its module pin *and* its scenario-file pin (173/120/120 bytes and the three PC hashes), so the tool, the tests, the module and the scenario cannot agree with each other while disagreeing with the encoder.
6. **Containment**: the sweep is one-shot; the database file is byte-identical across the whole window; every action is a 4-tuple, so no socket action is taken; and with the scenario absent the same trigger keeps its frozen baseline answer (`V99_SHOW_MESSAGE…` / `V100_MUSIC_CONTROL…`) and composes **no HYP-PF-023 label and none of the sweep's bytes**.

**NOT proven — nonclaims, stated as plainly as §8 does:**

* **No client has ever been shown one byte of this profile.** This is composition and dispatch, not observation. Whether anything renders is **GT-022, attended, not run.**
* Not proven: that the dying latch is a prerequisite for the death task. Unchanged from §8.
* Not narrowed: round 85's **229 unresolved vtable `+0x20` dispatch sites**. This lane inherits that bound.
* Not proven: that a real client accepts this envelope *with the actor-entry sub-object*. The envelope shape is the one NAME-002/DELETE-SOFT-002 made deliverable, but no capture in the corpus shows an actor-entry collection carrying BasicAttr bit `0x0080`.
* Not proven over TCP: unlike CHAT-ECHO-002, this lane has never been driven through a real server process on a socket. Dispatcher-level only, by design and by LOCK.
* Not claimed: anything about the original server, any damage model, any death penalty, any recovery path out of the state this sweep leaves behind, or any persistence — nothing on this path has a write path and this lane opens none.
* Not claimed: production behaviour. `production_allowed` is `False` everywhere it appears.

## 12. GT-022 condition 4 — now closed

**§2 line 4 (🟡 partly met) is superseded: condition 4 is ✅ fully met.** The wire-layer half was already closed by `tools/pf_runtimeres_death_encoder_static.py` (88 guards). The dispatcher half — the *only* thing §3 named as missing — is closed by `tools/pf_runtimeres_death_headless_replay.py` (64 guards, exit 0) plus `tests/test_runtimeres_death_dispatch.py` (25 tests, 3 traps), both of which drive the real `make_state_class` and measure the bytes it actually emits.

**Therefore §3's three headline sentences are now out of date, and the correction is:** there IS a dispatcher branch; the dispatcher-level headless replay is no longer unreachable and has been run; and `app.py` no longer refuses to boot with the flag — it boots the wiring path (`--self-test-only`, exit 0, no listener bound).

**Two things §2 line 4 also asked for are still deliberately NOT done, exactly as §5 recommended:** no ledger entry for `HYP-PF-023` and no coverage-matrix change. Both must land in the chief's own change (the ledger entry and its source annotations must be one commit, or `tools/verify_hypothesis_ledger.py` goes red), and flipping a coverage row on an offline composition would repeat the round-84 mistake §5 names. **GT-022 is unblocked; whether it is PENDING is the chief's call once the ledger row exists.**

## 13. The three traps, and what each would catch

| trap | the failure mode it exists to catch | how it catches it |
| --- | --- | --- |
| 1 — *the dispatcher fires when the lane is not enabled* | someone adds the branch and forgets the `is not None` gate, or a later refactor drops it | with no scenario: no `HYP_PF_023_*` label, none of the sweep's PCs anywhere in the answer, no sweep event, counter 0 — **and** calling `_dispatch_runtimeres_death_hypothesis` directly still cannot emit anything, because the lethal unlock and the profile are closed over as `None` and the composer **raises** rather than putting a death frame on a wire. Two independent locks, and the second one holds even if the first is deleted |
| 2 — *the frames arrive in the wrong order (kill before spawn)* | the sweep is reordered, or a future "optimisation" drops the spawn as redundant. An actor cannot be born dead: an unknown identity takes `0x446990` → vtable `+0x10` and never touches `0x4437C0`, so the result is a stuck live NPC and no animation | the frames the dispatcher **really emitted** are re-ordered kill-first with the labels left in the pinned order, and the validator must refuse with *"an actor cannot be born dead"* — pinned by message, not just by exception type. The same unmodified action list from the same dispatch is asserted to **pass**, so the trap cannot be passing because the validator rejects everything |
| 3 — *the sweep fires twice* | a second trigger re-sends `SPAWN` for a now-known identity, which is a vtable `+0x20` update with HP 100 and silently resurrects the probe | a second and third trigger must both return `[]`, the counter must stay 1, the sweep event must appear exactly once, `runtimeres_death_hypothesis_already_sent_no_reply` exactly twice, and the database digest must not move |

## 14. Test results, honestly

| what | result |
| --- | --- |
| `python3 -m pytest tests/test_runtimeres_death_dispatch.py -q` | **25 passed** |
| `python3 tools/pf_runtimeres_death_headless_replay.py` | **64 guards, 0 failures, exit 0** |
| `python3 -m pytest tests/test_runtimeres_death_dispatch.py tests/test_runtimeres_death_hypothesis.py tests/test_hp_death_dispatch.py tests/test_hp_death_encoder.py -q` | **122 passed, 1 skipped, 26 subtests passed** |
| `python3 -m pytest tests/test_runtimeres_actor_entry_static.py -q` | **21 passed** — the §5b redness is gone; those files were re-pinned in the tree by another lane, not by this one |
| `python3 -m pytest tests/test_foundation_legacy_seam.py tests/test_stats_progression_dispatch.py tests/test_channel_message_dispatch.py tests/test_chat_input_echo.py tests/test_item_move_hypothesis.py tests/test_item_move_capture.py -q` | **112 passed, 220 subtests passed** |
| whole `tests/` tree, two chunks, `--continue-on-collection-errors` | **33 failed / 1082 passed / 6 skipped**, and the failing FILES are exactly the three pre-existing environment ones: `test_actor_type_dispatch_static.py` 29 (capstone), `test_login_vital_req_static.py` 3 (pefile), `test_server_shutdown.py` 1 (timing). **Nothing new is red** |
| `PYTHONPATH=src python3 -m pirateforce_foundation.app --self-test-only` | exit 0 |
| the same **with** `--db <temp> --runtimeres-death-hypothesis-scenario …` | exit 0 — the flag boots the wiring path (scenario load → mutual exclusion → `--db` check → `make_state_class` with the kwarg) and the frozen self-test returns **before any listener binds** |

The one skip is `AppWiringTests::test_the_flag_exists_and_refuses_to_boot_while_unwired`, which RUNTIMERES-ENCODER-001 wrote to skip itself the day the kwarg appeared. It now skips. That is the designed signal, not a hole.

🔴 **Same caveat as §7: the sandbox is Python 3.10 without `capstone`/`pefile`, the suite was run in two chunks rather than one invocation, and the real gate is Windows `py -3`.** These numbers are indicative.

**Checks I did not run, named:** the Windows `py -3` gate. `git check-ignore` on the two new files (no commit was made — the chief commits, on the Windows bridge). No server was booted on a socket, no GameClient was opened, no byte of this profile reached a network.

## 15. Judgement calls, named

1. **`app.py` passes the kwarg plainly** (`runtimeres_death_hypothesis_scenario=runtimeres_death_hypothesis`) instead of keeping the `**{RUNTIMERES_DEATH_DISPATCH_KWARG: …}` splat, which made `RUNTIMERES_DEATH_DISPATCH_KWARG` and `import inspect` dead. Both were removed from `app.py`. The constant itself is untouched in the module and `tests/test_runtimeres_death_hypothesis.py` still reads it.
2. **I did not remove the refusal in favour of an inverted assertion.** Keeping a signature check that *requires* the kwarg would have preserved a boot-time safety net, but the instruction was to remove the stub and the mutual-exclusion/`--db` guards already fail closed. Named here so the chief can add it back cheaply if wanted.
3. **The scenario file still says `"dispatch": {"wired": false, "wiring_owner": "chief_…", "app_policy_when_unwired": "refuse_to_boot"}`, and the module still carries the nonclaim `production_dispatch_wiring_which_this_lane_deliberately_does_not_add`.** Those three strings are now **stale by one lane.** I did not fix them on purpose: `load_runtimeres_death_hypothesis_scenario` checks the file against an **exact** allowlist derived from `_expected_scenario()`, so changing the data means changing the encoder module and the scenario file together — both outside this lane's deliverables, and the module is under a do-not-touch rule. **The chief should flip those three when the `HYP-PF-023` ledger row lands**, in the same change, and re-run the encoder tests.
4. **The lane is one-shot** even though HP-DEATH-002 is not. Justified above (§10) by the known-identity/update-path asymmetry, and it is what the scenario already declared.
5. **The probe is resolved once at `make_state_class` time**, not per dispatch. It makes a frozen-source drift a boot-time refusal instead of a mid-session surprise; the cost is that the placement source is read once per state class rather than once per sweep.
6. **The branch is placed after the HP-DEATH-002 branch** and keyed on the same vital id. Ordering cannot matter — `make_state_class` refuses any pair outright and `app.py` refuses the flags together — and the comment at the branch says so, as its three neighbours do.

## 16. Exact server args — these now work

`--capture-root` outside the repo, a **copy** of the canonical DB, and every §6 warning still applies verbatim.

```
py -3 -u -m pirateforce_foundation.app
   --db "<run copy of canonical>"
   --capture-root "<a folder OUTSIDE the repo, e.g. GameClient\capture_gt022_<stamp>>"
   --second-password-mode bypass
   --runtimeres-death-hypothesis-scenario "<repo>\scenarios\runtimeres_death_hypothesis_spawn_then_kill.json"
```

**The trigger, for the attended tester:** log in, select the character, wait for the runtime ack, then send the ascii12 chat probe `PFCHATPROBE1` in local chat — the same probe GT-006/GT-017/GT-019 used. Nothing in the message is read; it is a trigger. **Once per session:** the sweep is one-shot and a second send is silently refused by design.

**Expected, if the hypothesis holds:** the "Navy Transfer" NPC (frozen placement 0, template 1) appears ~112 units from the spawn point; +6 s it should adopt the dying state; +6 s it should play `_F_DIE_000`. It does not recover. Nothing is written to the database — verify the DB SHA against `CANON_SHA.txt` before and after anyway.
