# PF DYING-HOLD-001 — the twenty-second dying hold

**Date:** 2026-08-19
**Hypothesis:** HYP-PF-022 (HP-DEATH-002) — **no new ledger entry, no ledger edit**
**Status:** offline / headless only. **Not flipped in `docs/FUNCTIONAL_COVERAGE.json`.**
**Attended follow-up:** not run. Nothing here has been in front of a client.

---

## 0. One paragraph

HYP-PF-022 already had one step plan: arm the client's death timer, zero current
HP, then put the HP value back. That plan is a **diagnostic** — it deliberately
ends with the character alive so an attended tester is never stranded. It cannot
answer the one question that matters most about the death surface: *what happens
when the dying countdown actually runs out?* This milestone adds a **second
named profile** under the same hypothesis, the same ledger entry and the same
unlock token — `dying_hold` — which arms the timer at the **20.0 seconds the
client image itself carries**, zeroes HP, and then **stops**. No frame restores
the HP value, on purpose, because that frame is exactly the thing that would
prevent the answer from ever being observable.

---

## 1. What is byte-proven (round 83 static RE, not this milestone's claim)

These were established at the byte level against the read-only client image
before this milestone started. This milestone **consumes** them; it does not
re-derive them and does not extend them.

| Fact | Evidence |
|---|---|
| `DURATION_DYING` compiled into the image = **20** | int global `0x102249C`, bound by name at `0x483476` to the literal L"DURATION_DYING" at `0xF118FC` |
| That global has exactly **one reader** | `0x44A572` |
| The L"Main_Dead" window (`0xF0D738`) opens iff `DURATION_DYING - 0.5 <= timer` | `cvtsi2sd` from `0x102249C`, `subsd` the double `0.5` at `0xF092D0`, `comisd` against the f32 at `attr+0x58`, `ja` → do not open |
| "still dying" = HP == 0 **and** timer > 0 | `0x454AC0` (this module's pin is named `IS_DEAD_PLAYER_VA`, kept) |
| "timer elapsed" = HP == 0 **and** timer <= 0 | `0x454A70` (pin `IS_DEAD_PLAYER_TIMER_ELAPSED_VA`, kept) |
| The screen that follows the countdown is a **different window** — L"Common_Death" `0xF0D860` — opened from `CMyActor::Update` once the elapsed predicate is true | round 83 static pass |

Consequence, and the whole reason for this milestone: **a timer of exactly 20.0
clears the window gate exactly** (20.0 ≥ 19.5) while being the client's own
number rather than a margin invented by this project.

The two predicate pins have been given **alias names** in the module
(`IS_DYING_PLAYER_VA`, `IS_DEAD_ELAPSED_PLAYER_VA`) so a cold reader can tell
the two states apart. The **original constant names and values were not
touched**, so no existing pin, test or report reference moved.

---

## 2. What is a design choice (and is labelled as one)

| Choice | Why | Not evidence of |
|---|---|---|
| `death_sweep` keeps its **60.0 s** timer | its pins, hashes and tests are load-bearing and frozen; changing it would move bytes for no gain | anything about the deployed value of `DURATION_DYING` |
| `dying_hold` sends **20.0 s** | it is the image's own value, and it clears the gate exactly | that a deployed server ever sent 20.0 |
| `dying_hold` has **no restoring step** | the question is what happens *after* the countdown, and a restore frame closes the window before it can be read | that leaving the character dead is "correct" behaviour |
| spacing stays **6.0 s**, first delay **0.0 s** | an attended tester needs the frames separable | anything |
| the label prefix is `HYP_PF_022_DYING_HOLD_` | so an attended log can tell the two profiles apart at a glance | anything |

---

## 3. What has NEVER been seen by a client

State this plainly, because the rest of the document is engineering and this is
the part that limits every claim in it:

* **No client has ever been shown one byte of the `dying_hold` profile.**
* **L"Common_Death" (`0xF0D860`) has never been observed by this project** — not
  in a capture, not on a screen, not in any corpus.
* Whether the on-screen countdown moves at all is **unobserved**.
* Whether the client crosses from "dying" to "timer elapsed" on its own is
  **unobserved**; it is derived from the image's code, not from a frame.
* There is **no persistence**: HP has no write path in this project and this
  lane opens none. The dispatch test asserts the database file does not move one
  byte across an accepted sweep.
* **None of this is a rule of the original server.** The original server is gone
  and was never published; this project cannot read its death rules and does not
  claim to.

---

## 4. What the attended tester is being asked to look at

Three questions, in this order, once a `dying_hold` sweep has been dispatched:

1. **Does the countdown on screen actually move?** (The L"Main_Dead" window is
   expected to open on the HP_ZERO frame, because 20.0 clears its gate.)
2. **When it reaches zero, does the client cross into the elapsed state?**
   (`0x454A70`: HP == 0 and timer <= 0.)
3. **Does L"Common_Death" appear?** This is a *different window* from
   L"Main_Dead" and is the actual object of the experiment.

Expected non-events, so nobody reads them as failures: this transport does not
reach the dead-state sync `0x4437C0` (its only caller is `0x4566A7`, the
actor-entry path), so **no death animation and no L"TargetIsDead"** should be
expected from these frames.

---

## 5. What changed in the code

### 5.1 The step plan became a named profile

`HYP-PF-022` now carries two `HpDeathStepProfile` objects instead of one
module-level plan:

| | `death_sweep` | `dying_hold` |
|---|---|---|
| steps | BASELINE → TIMER_ARMED → HP_ZERO → HP_RESTORED | BASELINE → TIMER_ARMED → HP_ZERO |
| timer | 60.0 s | **20.0 s** |
| `ends_dead` | `False` | **`True`** |
| lethal steps | `("HP_ZERO",)` | `("HP_ZERO",)` |
| scenario file | `scenarios/hp_death_hypothesis_death_sweep.json` | `scenarios/hp_death_hypothesis_dying_hold.json` |
| action prefix | `HYP_PF_022_HP_DEATH_` | `HYP_PF_022_DYING_HOLD_` |

**Every original symbol still exists and still names `death_sweep`** —
`HP_DEATH_TIMER_SECONDS`, `HP_DEATH_STEPS`, `HP_DEATH_STEP_ORDER`,
`HP_DEATH_STEP_FIELDS`, `HP_DEATH_LETHAL_STEP_LABELS`, `HP_DEATH_SCENARIO_ID`,
`HP_DEATH_SPACING_SECONDS`, `HP_DEATH_FIRST_DELAY_SECONDS`,
`HP_DEATH_ACTION_LABEL_PREFIX`, and all six `HP_DEATH_PROBE_*` tables. No
existing caller and no existing test was modified.

Every function that takes a step now takes an optional `profile` whose default
is `death_sweep`: `hp_death_step_fields`, `hp_death_step_is_lethal`,
`make_hp_death_response`, `make_hp_death_step_response`,
`_require_pinned_death_composition`.

### 5.2 The validator got STRICTER, not looser

`_require_hp_death_step_plan(profile)` validates one profile at a time. Rules
kept for both profiles: open on a BASELINE that carries no field; no duplicate
label; each later step changes exactly one field the lethal table knows; the
timer is armed **before** the kill; exactly one lethal step and it is the one
that zeroes HP; the armed step's value equals the profile's declared timer.

New, and the point of the refactor — a profile must declare `ends_dead`
explicitly, and each answer is enforced separately:

* `ends_dead=False` → a restoring step must exist, must come after the kill,
  must set hp > 0, and must be the **last** step. (Unchanged from before.)
* `ends_dead=True` → a restoring step **must not exist at all**, the last step
  **must** be `HP_ZERO`, and the timer must be
  `>= DURATION_DYING_IMAGE_DEFAULT - DURATION_DYING_WINDOW_MARGIN` (19.5).

`ends_dead` is never inferred from the step list. Inferring it is exactly how a
plan that silently stopped restoring HP would get past a reviewer.

### 5.3 Fail-closed properties preserved

* Same single unlock token (`_HP_DEATH_UNLOCK`, identity-compared). **A second
  profile did not add a second key** — asserted by both the verifier and a test.
* `production_allowed: false`, `test_only: true`, `lethal: true`,
  `database_write: "none"` in the new scenario file.
* The loader still matches **exactly**: the id must be one of the two names, and
  the whole document must then equal the shape the matching profile declares,
  key for key and type for type.
* An unregistered profile object is refused by the composer with
  `hp death step rejected: unknown_step_profile` — a profile assembled elsewhere
  cannot compose bytes even if it compares equal.

### 5.4 Runtime dispatch

`make_state_class` derives the profile **once**, from the same allowlisted
scenario object, next to where it derives the unlock token. The dispatch loop
reads the plan, prefix and first-frame delay off that profile, so it cannot pick
a plan of its own. There is still exactly **one** call site of
`make_hp_death_step_response(` in `runtime.py`, and the lane still sits behind
`if hp_death_hypothesis_scenario is not None:`.

A drift check was added: under the `death_sweep` profile the profile-carried
label prefix and first-frame delay must still *be* `HP_DEATH_ACTION_LABEL_PREFIX`
and `HP_DEATH_FIRST_DELAY_SECONDS`, so the ledger's source pins, the headless
replay tool and the attended playbook cannot disagree with the dispatcher about
what went on the wire.

---

## 6. Evidence produced

### 6.1 The `dying_hold` pins (computed from bytes the encoder produced)

Probe actor is the same one both existing profiles pin (identity_lo
`0x10010001`, scene 1, seq 0, name `test01`, cash 10000).

| step | mask | attr body | pc | frame |
|---|---|---|---|---|
| BASELINE | `0x030C` | 73 B / `479ED77D…96C4` | 106 B / `DB3CE0B5…0049` | 117 B / `04E2B401…9FBC` |
| TIMER_ARMED | `0x038C` | 78 B / `877A7E0A…25EB` | 111 B / `F08E53D3…7932` | 122 B / `01E1B9E6…611F` |
| HP_ZERO | `0x038C` | 78 B / `857AC3F2…8873` | 111 B / `1099931C…7E44` | 122 B / `77E98AD6…200D` |

`scenarios/hp_death_hypothesis_dying_hold.json` was **generated from the
encoder's own output**, not hand-written, and a test reloads it off disk and
re-compares every hash and every size against freshly composed bytes.

### 6.2 The two profiles differ only where they are meant to

* **BASELINE is byte-identical** across both profiles, and is still the
  `player_wire.make_actor_attr_with_name` projection a real client has accepted
  since NAME-002. (Same sha256 `479ED77D…96C4` as HYP-PF-020's BASELINE.)
* **TIMER_ARMED differs only inside the four f32 bytes of the timer.** 60.0f is
  `00 00 70 42` and 20.0f is `00 00 A0 41`, so two of the four bytes coincide;
  the load-bearing assertion is that *nothing outside the f32 moved* — not the
  tag `0x2A`, not the BasicAttr mask `0x038C`, not one other field, not the
  envelope. Verified as a set-inclusion on the differing byte indices.

### 6.3 Trap tests — the validator can fail

Twelve deliberately broken profiles are built in the test file and every one is
refused, each for the right reason. The four mandated cases:

| trap | refusal |
|---|---|
| `ends_dead=True` but still carries `HP_RESTORED` | `a profile that ends dead must carry no restore step` |
| `ends_dead=True` with timer 19.0 (under the 19.5 gate) | `a profile that ends dead must clear the death-window gate` |
| `ends_dead=False` but stops on `HP_ZERO` | `the sweep does not end alive` |
| kill before arm | `the sweep order is not arm/kill/restore` |

Eight more are covered as subtests: no baseline, a baseline that already carries
a field, a step changing two fields, a kill step that does not zero HP, more
than one lethal label, an armed step disagreeing with the declared timer, a step
naming a field the lethal table does not know, and a restore step that leaves HP
at zero. Each broken profile is *also* refused outright by the composer.

---

## 7. Verification run

| gate | result |
|---|---|
| `tools/verify_hp_death_encoder.py` | **exit 0**, `guards run: 99 (skipped: 9)` — up from 57; **no pre-existing guard was removed**, both profiles now covered, still pure stdlib (no `pefile`, no `capstone`) |
| `tools/pf_hp_death002_headless_replay.py` | exit 0, 33 guards |
| `tools/pf_hp_death_respawn_static.py` | 191 guards, 0 failures |
| `tests/test_hp_death_encoder.py` + `tests/test_hp_death_dispatch.py` | **59 passed** (unmodified) |
| `tests/test_hp_death_dying_hold.py` (new) | **31 passed, 11 subtests passed** |
| `tests/test_hypothesis_ledger.py` | 8 passed, 29 subtests |
| whole `tests/` tree, Linux sandbox | **904 passed, 702 subtests passed**; 33 failed + 36 collection errors, **all** in the known `capstone`/`pefile`-missing family (`test_actor_type_dispatch_static`, `test_login_vital_req_static`) plus the documented `test_server_shutdown` red — none of them touched by this milestone |

Sandbox note: the Linux sandbox is Python 3.10 without `pefile`/`capstone`, so
the disassembler-backed static suites cannot collect there. That is an
environment limit, not a result.

---

## 8. Explicitly NOT done

* **`docs/FUNCTIONAL_COVERAGE.json` was not touched.** No matrix flip. Chief's call.
* **`docs/HYPOTHESIS_LEDGER.json` was not touched.** No new hypothesis was opened
  and no entry was edited — `dying_hold` lives under the existing HYP-PF-022
  entry as a second profile. The ledger's existing source pins for HYP-PF-022
  (including its `HP_DEATH_ACTION_LABEL_PREFIX` marker on `runtime.py`) still
  resolve, and `tests/test_hypothesis_ledger.py` is green without a ledger edit.
  **No ledger change is being requested.**
* **`.gitignore` was not touched.** See §9.
* `current/pf_login_game_server_v141.py` was not touched.
* `src/pirateforce_foundation/app.py` was not touched: the existing
  `--hp-death-hypothesis-scenario` flag takes a path and hands it to the loader,
  which now accepts either of the two allowlisted files, so no new flag exists
  and no new CLI surface was opened.
* The `death_sweep` scenario file on disk was not modified — `git status` shows
  it unchanged, and a test asserts its step order, its 60.0 s timer and its four
  pc hashes are still what they were.
* No client was opened, no server was booted, no socket was opened, no capture
  was taken, no commit was made.

---

## 9. `.gitignore` allowlist needed (chief)

`reports/` is deny-by-default (`/reports/*`), so this report is currently
ignored. One line has to be added by whoever commits:

```
!/reports/PF_DYING_HOLD001_TWENTY_SECOND_DYING_HOLD_20260819.md
```

The other two new files are already allowlisted by the existing
`!/scenarios/**` and `!/tests/**` negations and need nothing:

* `scenarios/hp_death_hypothesis_dying_hold.json` — not ignored ✔
* `tests/test_hp_death_dying_hold.py` — not ignored ✔

No manifest is required: this report pins no external byte artefact; every
number in it is reproducible from the repository by running
`tools/verify_hp_death_encoder.py`.

---

## 10. Files touched

| file | change |
|---|---|
| `src/pirateforce_foundation/stats_progression_hypothesis.py` | module docstring block on why there are two profiles; three added VA pins (two aliases + L"Common_Death"); `HpDeathStepProfile`; both profile objects; `dying_hold` step plan, pins and metadata; per-profile validator; profile-aware step/compose functions; two-name scenario allowlist; `hp_death_profile_for_scenario` |
| `src/pirateforce_foundation/runtime.py` | derives the profile once from the allowlisted scenario; dispatch reads plan/prefix/delay off it; drift check against the two legacy constants; docstring updated for the two end states |
| `tools/verify_hp_death_encoder.py` | both profiles pinned; cross-profile byte-diff guards; validator trap guards; allowlist and nonclaim guards. 57 → 99 guards, still pure stdlib |
| `scenarios/hp_death_hypothesis_dying_hold.json` | **new**, generated from encoder output |
| `tests/test_hp_death_dying_hold.py` | **new**, 31 tests |
| `reports/PF_DYING_HOLD001_TWENTY_SECOND_DYING_HOLD_20260819.md` | **new**, this file |
