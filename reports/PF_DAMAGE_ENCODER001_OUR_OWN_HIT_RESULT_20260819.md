# PF DAMAGE-ENCODER-001 / DAMAGE-DISPATCH-001 — a damage number on the wire, computed by a formula this project wrote down, because the one it replaces is gone forever

2026-08-19 · round 90 · **server encoder + dispatcher + scenario + verifier + headless replay + tests, additive, opt-in, fail-closed** · binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` · reproduce: `py -3 tools/verify_damage_model_encoder.py` (**322 guards, 39 of them a regression gate, exit 0**), `py -3 tools/pf_damage_model_headless_replay.py` (**136 guards, exit 0**), `py -3 -m pytest tests/test_damage_model_hypothesis.py tests/test_damage_model_dispatch.py -q` (**126 tests**)

> ### The one sentence that has to travel with everything this lane produces
> **The damage formula in this repository is OURS. It is not the original server's, and the original server's cannot be recovered — not now, not later, not by anybody.** That server was shut down years ago and was never published. Round 83 (`DAMAGE-MODEL-001`, 235 byte-exact guards) established the reason this matters more here than anywhere else in the project: **the client computes nothing.** It carries no damage formula, applies no scaling, and never subtracts damage from hit points. The figure a player sees floating over a target is the signed 32-bit integer the server placed at hit-entry `+0x08`, passed through `abs()` and printed with a plain integer format, with no multiply or divide anywhere on the path. So there was never a formula inside the client to recover; there is only a slot to put one in. The owner approved designing one on 2026-08-19 11:45, with the scope she set herself: **one signed i32 plus one flag word per target.** That is exactly what this lane ships.

> **The answer, in one paragraph.** `src/pirateforce_foundation/damage_model_hypothesis.py` composes **four `GSCN_RunTimeProtocolRes` id `0x6E9D` version 4 frames**, each carrying one `CHitResult` (**wire id `0x16F7`, version byte `0`**) as the single element of the **VitalData collection** — the **BASE** change mask `0x02`, the object at `this+0x18` — which is precisely what the frozen V141 helper `make_runtime_vitals` already emits. Each frame is an 84-byte PC and a 95-byte framed payload: a 22-byte header whose four non-identity fields are pinned at zero, a 3-byte count of one, and one 37-byte hit entry. The four steps are `HIT_WEAK` (**-63**, flags `0x0001`), `HIT_STRONG` (**-379**, flags `0x0001`), `MISS` (**0**, flags `0x0000`) and `HIT_REACTION` (**-63**, flags `0x0009`). `runtime.py` answers one accepted 34-byte ascii12 chat-input frame with the whole sweep, one-shot, and the headless replay proves all four frames leave the **real dispatcher** byte for byte against the session's own actor, on a throwaway database, read back by a tag walker that never calls the module's own decoder.

**Grade:** wire contract · version byte · construction path · sign semantics · byte pins · fail-closed gating · dispatcher emission = **A** (every structural claim re-derived from the read-only image or from the composed bytes, by a pure-stdlib verifier whose first 39 guards reproduce round 83's published answers before it is allowed to assert anything new; 6 traps prove the verifier can go red, 45 traps prove the validator can) · **the formula itself = a design, not a finding, and is graded only on being deterministic, reproducible and range-checked** · **client acceptance of any of these bytes = not claimed, that is GT-024** · one ledger entry added (`HYP-PF-024`), no coverage row flipped.

---

## 0. Files touched — the complete list

| file | status |
| --- | --- |
| `src/pirateforce_foundation/damage_model_hypothesis.py` | **new** — the encoder, the formula, the validator, the exact-allowlist loader |
| `scenarios/damage_model_hypothesis_hit_sweep.json` | **new** — the opt-in scenario, generated from the module's `_expected_scenario()` so the two cannot drift |
| `src/pirateforce_foundation/app.py` | **modified** — `--damage-model-hypothesis-scenario`, mutual exclusion, `--db` requirement, console mode, dispatcher kwarg |
| `src/pirateforce_foundation/runtime.py` | **modified** — `_dispatch_damage_model_hypothesis`, the unlock derivation, the one-shot counter, the dispatch branch |
| `tools/verify_damage_model_encoder.py` | **new** — pure-stdlib offline verifier, 322 guards |
| `tools/pf_damage_model_headless_replay.py` | **new** — dispatcher-level replay, 136 guards |
| `tests/test_damage_model_hypothesis.py` | **new** — 88 tests, 45 of them traps |
| `tests/test_damage_model_dispatch.py` | **new** — 38 tests |
| `docs/HYPOTHESIS_LEDGER.json` | **modified** — entry 31, `HYP-PF-024`, `active`, `production_allowed: false` |
| `tools/verify_hypothesis_ledger.py` | **modified** — one line registering the new id in `EXPECTED_META` |
| `.gitignore` | **modified** — allowlist for the two new tools, this report, and the two cited design documents |
| `drafts/DAMAGE_MODEL_UNKNOWNS_R90_STATIC.md` | **new** — the static pass that closed the two blocking unknowns |
| `reports/PF_DAMAGE_ENCODER001_OUR_OWN_HIT_RESULT_20260819.md` | **new** — this file |

Nothing else was touched. `current/pf_login_game_server_v141.py`, `state/pirateforce.sqlite3`, `references/`, `evidence/` and everything under `pf_bridge/` were **not** modified. No server was booted, no GameClient opened, no socket opened, no database written, no capture taken, no coverage row flipped.

---

## 1. What was blocking this lane, and how it was unblocked

The design draft (`drafts/DAMAGE_MODEL_LANE1_DESIGN_20260819.md`, round 89) ended by naming three things it was still guessing and refusing to write an encoder until they were closed. Two of them were load-bearing:

**① The version byte of `0x16F7` was unknown.** Every element of a VitalData collection is `u16 tag 0x12 id`, then `u8 tag 0x0B` **version**, then the payload. Send the wrong version and the frame is refused by the reader, not merely misread.

The answer is **0**, and it is `PROVEN`. The version is **not** a vtable slot — the wire classes' vtables are nine slots and `0x24` bytes long, which is why `0xF48AA0 + 0x24` lands exactly on `CMissileHitResult`'s vtable and misled an earlier reading. It is an **instance field at `obj+0x10`**:

| VA | file offset | bytes | meaning |
| --- | --- | --- | --- |
| `0x5F3EFC` | `0x1F32FC` | `3A 4E 10` | `cmp cl,[esi+0x10]` — the collection reader comparing the version it read against the prototype's; a mismatch throws `0xE0000031` |
| `0x74F968` | `0x34ED68` | `33 C0` | `xor eax,eax` in `CHitResult::CHitResult` |
| `0x74F979` | `0x34ED79` | `88 46 10` | `mov [esi+0x10],al` — the version stored, therefore **0** |

The method was cross-checked against four classes whose versions this project already ships before it was allowed to answer a new one: `SelectActorVital` → **10** (`0x5ED71E`, `C6 46 10 0A`), `UpdateNPCAppearVital` → **0** (`0x7389A0`), `CreateActorVital` → 8, `TeleportVital` → 4. All four agree with what V141 already sends.

**② It was unknown whether the collection could construct `0x16F7` at all.** It can, and there is no allowlist to be excluded from. `0x5F3EA1` enters the registry singleton (`0x5E3260`) and `0x5F3EA8` creates by id (`0x5E2E00`), which resolves through `0x731380` — a **red-black tree lookup on a u16 key** (`0x7313A0`, `66 39 48 0C`), with no switch and no jump table anywhere on the path. `CHitResult` is registered like any other: `0x75501E` pushes its `sizeof` (`6A 48`), `0x75503A` calls its ctor, and `0x755048` (`E8 A3 ED E9 FF`) calls `RegisterVitalPrototype` at `0x5F3DF0`. The dispatch precondition at vtable `+0x20` is the stub `0x710440` = `B0 01 C2 04 00`, which returns **true unconditionally**, and the handler is vtable `+0x1C` = `0x750770`.

One honest caveat travels with ②: that the registration code at `0x754EB0` **actually runs at boot** is `DERIVED`, not `PROVEN`. It is reached through the same vtable slot (`+0x28`) that `NPCAppearModule_Client` uses to register a vital this project has already driven through a real client, which is why the reading is a derivation rather than a guess — but only a live run can settle it.

**③ The four unknown header fields.** The plan was to pin them at zero; the question was whether zero is *inert*. Traced branch by branch, it is: `+0x22 == 0 != 0xEA7A` skips the bail at `0x7507FE`; `+0x24 == 0` **skips** a second effect at `0x750E0A` without returning; `+0x28` is only passed along as a parameter and never compared; and `+0x20 == 0` makes the lookup at `0x702A10` return NULL (`0x702A1A`, `33 C0`), which leaves the gate at `0x5CAE00` false and the number path open. "Inert on the branches read" is not "we know what these fields are for" — see §6.

---

## 2. The wire, byte for byte

```
12 9d 6e            u16  tag 0x12  envelope id 0x6E9D   (GSCN_RunTimeProtocolRes)
14 00 00 00 00      u32  tag 0x14  error data 0
08 04               u8   tag 0x08  protocol version 4
0b 02               u8   tag 0x0B  BASE change mask 0x02  -> VitalData collection at this+0x18
12 01 00            u16  tag 0x12  collection count = 1
  12 f7 16          u16  tag 0x12  vital id 0x16F7        (CHitResult)
  0b 00             u8   tag 0x0B  vital VERSION = 0
  32 <8 bytes>      qword tag 0x32 performer identity     (obj +0x18)
  12 00 00          u16  tag 0x12  reserved, pinned 0     (obj +0x20)
  12 00 00          u16  tag 0x12  reserved, pinned 0     (obj +0x22)
  14 00 00 00 00    u32  tag 0x14  reserved, pinned 0     (obj +0x24)
  0b 00             u8   tag 0x0B  reserved, pinned 0     (obj +0x28)
  12 01 00          u16  tag 0x12  hit entry count = 1
    32 <8 bytes>    qword tag 0x32 target identity        (entry +0x00)
    14 c1 ff ff ff  u32  tag 0x14  DAMAGE, READ SIGNED    (entry +0x08)  = -63
    2a 2a 2a        3x f32 tag 0x2A hit position          (entry +0x0C)
    2a 00 00 00 00  f32  tag 0x2A  yaw, pinned 0.0f       (entry +0x18)
    12 01 00        u16  tag 0x12  result flags           (entry +0x1C)
0b 00               u8   tag 0x0B  DERIVED change mask 0  -> no actor-entry collection
```

**Header 22 bytes + count 3 + entry 37 = 62-byte payload; 84-byte PC; 95-byte frame.** All six widths are asserted against the real encoder rather than trusted from the arithmetic.

### 2.1 The correction this lane had to make first

Two rounds have now confused two different collections that happen to share the bit number `0x02`:

| | HYP-PF-023 (spawn-then-kill) | **HYP-PF-024 (this lane)** |
| --- | --- | --- |
| mask | **DERIVED** (`0x5E3EE0`) | **BASE** (`0x5F4070`) |
| object | `this+0x1C` | `this+0x18` |
| reader | actor-entry element `0x5E21D0` | VitalData collection `0x5F3E20` |
| element shape | `0B actorType · 32 id64 · 0B attrCount · [12 attrId + payload]*` | `12 id · 0B version · payload` |

Both readings are correct; they are different bytes. `0x5E3EE0` calls the base serializer `0x5F4070` **first** (`0x5E3EEF`, `E8 7C 01 01 00`), which is why the wire order is base mask, collection, derived mask — and why V141's `make_runtime_vitals`, which emits `0B 02 … 0B 00`, has been byte-correct all along.

---

## 3. The formula — ours, and labelled as ours everywhere

```
ATK(a) = 100 + 7 * (a.str + a.bonus_str) + 3 * a.level
DEF(d) =  10 + 2 * (d.con + d.bonus_con) + 1 * d.level
base   = max(ATK(a) - DEF(d), 1)
damage_wire = -base                     # negative on the wire; the player sees abs()
```

Integer-only, no RNG, no floats, no clocks, no dict ordering. Computed with unbounded Python ints and **range-checked at the end** — never wrapped, masked, or silently clamped into the band, because a formula that quietly clamps can never be caught drifting.

| attacker | str | level | ATK | DEF (player) | wire | on screen |
| --- | --- | --- | --- | --- | --- | --- |
| `MOB_WEAK` | 3 | 1 | 124 | 61 | **-63** | **63** |
| `MOB_STRONG` | 40 | 20 | 440 | 61 | **-379** | **379** |
| floor case (test only) | 0 | 0 | 100 | 160 | **-1** | 1 |

The defender is the character **as the HYP-PF-020 sweep leaves it** (level 7, con 22), so an attended tester can check the arithmetic against the character sheet GT-017 already put on screen. 63 and 379 are deliberately not round, not squares, and not values any UI element produces on its own: if the tester sees a different number, the client scales after all and `damage_field_scale_factor = 1` is falsified.

### 3.1 The sign is the meaning

`entry+0x08` is compared **signed** at four `cmp dword ptr [ebx+8], 0` / `jge` sites. Negative is the took-damage side; the player still sees a positive figure because the display path calls `abs()`. Two refusals guard the two ways to get this wrong:

* **a positive value is refused outright** — what a non-negative value means (heal? absorb? no-op?) is genuinely unknown, and unknown means we do not send it;
* **`INT32_MIN` is refused as its own rejection** — `abs()` built from `cdq/xor/sub` returns `0x80000000` unchanged, so `"%d"` would print `-2147483648`: a minus sign on screen, out of the one path designed never to show one.

### 3.2 The flag word

Whole-value allowlist `{0x0000, 0x0001, 0x0009}`, plus a mask check against `0x0009`, plus a forbidden mask of `0xF184`. Bit 0 is **chosen deliberately** rather than left at zero: `0x7509DA` (`0F 84 77 02 00 00`) gates the entire reaction block on it, while the number is drawn by a second pass that does not read it. Bit 4 is refused on every frame of this sweep because it makes the client play `_F_KNOCKED_002` **instead of** showing the figure, and bit 7 is refused because `0x750A84` tests it and nobody here can say what it does — *tested but unexplained* is the strongest case for not sending something.

**No bit is given a name this project cannot prove.** "Block", "critical" and "overkill" are inferences from a flag-to-texture map elsewhere in the image; they are not adopted.

### 3.3 `MISS` is the control, not filler

`validate_damage_model_sweep` refuses a sweep with no miss frame. If every frame showed a number, a tester could not distinguish *the client is reading our bytes* from *the client draws something of its own*. The miss frame is what makes a positive result falsifiable.

---

## 4. What was proven, and at which layer

| layer | proven | by |
| --- | --- | --- |
| the image | version byte, construction path, sign sites, flag gates, header inertness, vtable shape | `tools/verify_damage_model_encoder.py` — 322 guards over 16 hashed ranges and 21 point-byte sites, plus a 39-guard regression gate that reproduces round 83's answers and exits 2 without asserting anything new if it fails |
| composition | four frames, byte for byte, against a fixed probe identity | pinned sha256 of PC and frame per step, re-derived on every build |
| the plan | every rejection produces **no bytes at all** | 25 named reasons across 54 verifier guards and 45 test traps, each asserting the call returned nothing rather than merely raising |
| the dispatcher | the same four frames leave the **real** `make_state_class`, in order, with the pinned labels and delays, against the session's own actor | `tools/pf_damage_model_headless_replay.py` — 136 guards on a throwaway database, read back by a tag walker written inside the tool that never calls the module's decoder |
| **the client** | **nothing** | — |

The traps matter as much as the guards. A verifier that has never been seen to fail is a printout: six of them mutate copies of pinned spans and require the same guards to reject. A validator that cannot be made to fail is a comment: forty-five of them build deliberately malformed sweeps — a positive damage, `INT32_MIN`, a forbidden bit, the number-suppressing bit, a zero paired with the reaction bit, a non-zero without it, a forged unlock token that compares `==` but is not `is`, a scenario file with one key added, a step index of `True`, an invented position, a `nan` yaw — and require each to be refused by name.

---

## 5. The one-shot rule, and why it is correctness rather than convenience

A repeat trigger returns `[]` with `damage_model_hypothesis_already_sent_no_reply`. The value of this sweep is that a tester can **predict both numbers before they appear**; a second sweep interleaved with the first turns a legible four-step sequence into noise, and an observer who cannot say which frame produced which figure has measured nothing.

---

## 6. What is NOT claimed — read this before writing anything downstream

1. **No client has ever been shown one byte of this profile.** Whether a number renders at all is **GT-024**, attended, **not run**.
2. **One named runtime risk sits behind that test and static reading cannot settle it.** The gate at `0x5CAE00` begins `mov ecx,[0x10339B0]; test ecx,ecx; jne …` and returns **true when that singleton is NULL** — and a true there suppresses the figure no matter what this lane sends. The pointer is set in a ctor at `0x491D0C` and cleared in a dtor at `0x491C65`; its state in a live game is unknown. If GT-024 shows no number, this is the first place to look, not the encoder.
3. **The formula is ours.** It is graded on being deterministic, reproducible and range-checked. It is **not** claimed to be good, balanced, or to resemble the original server's in any respect.
4. **The four reserved header fields are pinned, not understood.** `+0x20` and `+0x22` are keys into the same table through `0x4162A0` → `0x702A10`, and that table has not been mapped.
5. **The flag bits are gates, not names.** Bit 0 opens the reaction block; bits 3 and 4 select the knocked-down branch; bit 7 does something unnamed. Nothing else is asserted.
6. **A non-negative damage value is unexplored, deliberately.** Heal and absorb are not implemented and not guessed at.
7. **Nothing here connects the number to hit points.** No HP is read, changed or persisted, and no table is opened for one. The ring "hit → blood → death" still has an unbuilt middle, and building it needs its own checkpoint and its own entry.
8. **Nothing is claimed about the original server**, which is closed, was never published, and about whose damage rules this project cannot read a single byte.
9. **The proof stops one layer below the socket.** No server process was booted and no byte of this profile has ever been on a network.

---

## 7. Three defects this lane found in its own first draft, and fixed rather than filed

Written down because the pattern — *a constant nothing reads is a constant nothing checks* — has now cost this project three rounds in different disguises.

1. **Eight PC offset constants were each one byte early.** They assumed a change-mask byte with no tag in front of it. Nothing in the repository read them, so nothing went red. They are corrected **and made load-bearing**: `validate_damage_model_sweep` now indexes every composed PC positionally with them as a second reading of the same frame, so the next drift is a failing test rather than a comment that quietly disagrees with the bytes.
2. **Two byte-site decimals in the scenario file were wrong** (`0x5F40FC` where the proven compare is `0x5F3EFC`, and a `+0x08` compare site that is not one of the four). They agreed with the module, which is exactly why the exact-tree loader accepted the file: two readers copying the same wrong number agree. Both corrected, and the verifier now guards that every declared site is a real `.text` address **and** matches `STATIC_ANCHORS`.
3. **`sweep_does_not_contain_a_miss_frame` is unreachable from any external input**, because the per-step value checks fire first. It is kept as defence in depth against a future edit of the shipped plan, and the fact that it is unreachable today is written here rather than left for a reader to discover.

---

## 8. What the next round should do with this

* **GT-024 is queued and ready to run as-is.** Boot with `--damage-model-hypothesis-scenario scenarios/damage_model_hypothesis_hit_sweep.json` on a copy of the canonical database, enter the world, send one ordinary chat line, and watch four frames arrive six seconds apart. The tester should be told the two numbers in advance — that is the point.
* **Do not extend this entry to a fifth frame, a second target or a new flag bit.** `max_versions` is 3 and two are spent; a widening is a new version or a new entry, per the stop rule.
* **The middle of the ring is the obvious next lane**, and it is deliberately not started here: connecting a damage number to a hit-point value needs a write path, a table, and an entry of its own.
