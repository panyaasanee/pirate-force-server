# DAMAGE-HP-LINK-001 — the hit -> bleed -> die link: our damage arithmetic reduces a server-held HP balance, and the client is told both halves (HYP-PF-026)

Date: 2026-08-20 (chief round 97) · lane: combat, between the proven ends of `damage_and_hit_result`'s designed successor (HYP-PF-024) and `hp_death_and_respawn` (HYP-PF-022/023) · Status: **wire + dispatcher layer proven headless; client layer = attended queue (GT-031), NOT RUN**

> **THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS UNRECOVERABLE.**
> No capture in any corpus links damage to hit points in either direction. Round 83
> proved the client computes no damage of its own and never subtracts it from hit
> points; GT-024 confirmed on a real screen that the floating number leaves the HP
> bar untouched (two witnesses). So if a hit is ever to cost hit points, the server
> must say both halves itself — and this lane is that sentence said once, end to
> end. Every value without a `[PROVEN ...]` label is ours.

## 1. What landed

| piece | path |
| --- | --- |
| module (composer + balance ladder + validator + independent walker) | `src/pirateforce_foundation/damage_hp_link_hypothesis.py` |
| opt-in scenario (whole-tree allowlist, all numbers decimal) | `scenarios/damage_hp_link_hypothesis_link_sweep.json` |
| CLI flag (requires an explicit existing `--db`, mutually exclusive with every other mode) | `--damage-hp-link-hypothesis-scenario` (`app.py`) |
| dispatch entry point (one-shot, identity-pinned) | `runtime.py :: _dispatch_damage_hp_link_hypothesis` |
| offline verifier (**270 guards**, pure stdlib, no client image needed) | `tools/verify_damage_hp_link_encoder.py` |
| headless replay through the real dispatcher on a throwaway DB copy (**198 guards**) | `tools/pf_damage_hp_link_headless_replay.py` |
| tests (**141 + 44 = 185**, plus 360+ subtests) | `tests/test_damage_hp_link_hypothesis.py`, `tests/test_damage_hp_link_dispatch.py` |
| ledger | `docs/HYPOTHESIS_LEDGER.json` entry 33, HYP-PF-026, 1 of 3 versions used |

## 2. The sweep — eight frames, one opt-in, one balance

Envelope for every frame: `GSCN_RunTimeProtocolRes` id 0x6E9D version 4 over the
**VitalData collection** (BASE change mask 0x02, object +0x18, trailing derived
0x00) `[PROVEN SRC — v141:689 make_runtime_vitals]`. Two carriers alternate
inside it: `CHitResult` 0x16F7 v0 `[PROVEN RENDERING — GT-024]` and
`UpdateAttrVital` 0x309A v0 / `ActorAttr` 0x12AD `[PROVEN RENDERING — GT-019]`.

| # | label | carrier | payload | balance after |
| --- | --- | --- | --- | --- |
| 1 | `HP_BASELINE` | ActorAttr | hp 100/100 + full proven baseline field set | 100 |
| 2 | `HIT_WEAK` | CHitResult | damage **-63**, flags 0x0001 | 100 |
| 3 | `HP_AFTER_WEAK` | ActorAttr | hp_current **37** = 100 - 63 (derived, not hand-pinned) | 37 |
| 4 | `MISS` | CHitResult | damage 0, flags 0x0000 — the control | 37 |
| 5 | `HP_AFTER_MISS` | ActorAttr | hp_current **37** — a miss moves nothing (frame is byte-identical to #3 by design) | 37 |
| 6 | `HIT_STRONG` | CHitResult | damage **-379**, flags 0x0001 | 37 |
| 7 | `HP_ZERO_DYING` | ActorAttr | hp_current **0** + death timer **20.0f** in ONE frame (37 - 379 **clamped at the floor** — the only step allowed to clamp) | 0 |
| 8 | `DYING_ELAPSED` | ActorAttr | death timer **0.0f** | 0 |

Labels `HYP_PF_026_HP_LINK_<STEP>` · delays 0.0 then 15.0 s x7 (cumulative
deadline; the round-84 photography lesson) · one-shot · event
`damage_hp_link_hypothesis_link_sweep_sent`.

The balance ladder `(100, 100, 37, 37, 37, 37, 0, 0)` is re-walked by real
arithmetic (`apply_hit_to_balance`) on every composition and the sweep refuses
if it does not reproduce (`hp_arithmetic_not_reproducible`). The replay's
independent walker re-derives the same ladder **from the dispatched bytes**:
walker-read hp values must equal walker-read damage arithmetic applied to the
walker-read baseline. The damage values themselves are recomputed from the
copied formula constants (`ATK 100 + 7*str + 3*lv`, `DEF 10 + 2*con + 1*lv`,
floor 1) and refused on mismatch (`formula_output_not_reproducible`).

### Pins (probe identity 0x10010001/0 — and at dispatch, ONLY that identity)

| label | pc size | pc sha256 | frame size |
| --- | --- | --- | --- |
| HP_BASELINE | 106 | `DB3CE0B5..0049` | 117 |
| HIT_WEAK | 84 | `D824597F..84D4` | 95 |
| HP_AFTER_WEAK | 106 | `EFF10D93..A75E` | 117 |
| MISS | 84 | `A1A746E4..B77A` | 95 |
| HP_AFTER_MISS | 106 | == HP_AFTER_WEAK | 117 |
| HIT_STRONG | 84 | `D7A708CB..5665` | 95 |
| HP_ZERO_DYING | 111 | `1099931C..7E44` | 122 |
| DYING_ELAPSED | 111 | `7C1951CE..7F35` | 122 |

Full 64-hex values are pinned in the module (`DAMAGE_HP_LINK_PINS`) and in the
scenario's `per_step` block; the verifier recomposes all eight and compares.

## 3. The strongest guard this lane has: cross-lane byte equality

The lane **copies** its layout and formula constants (never imports — the
containment censuses forbid the module names in src/), and then both the
verifier and the tests compose the same frames **through the parent lanes' own
composers and their own unlocks** and compare with `==` on bytes:

* `HIT_WEAK` / `MISS` / `HIT_STRONG` are **byte-identical** to the HYP-PF-024
  composer's output for the same identity — the exact bytes a real client
  rendered at GT-024.
* `HP_BASELINE` is **byte-identical** to the HYP-PF-022 BASELINE a real client
  accepted at GT-019; `HP_ZERO_DYING` to dying_hold's `HP_ZERO`;
  `DYING_ELAPSED` to dying_hold's `TIMER_ELAPSED` (GT-023's proven frames).

So the only NEW wire claim this lane makes is the **interleaving and the
arithmetic between the frames** — every individual frame is a byte-for-byte
re-statement of something a real client has already been shown, or (for the
mid-ladder hp 37 frames) the same shape with a derived value.

## 4. Design choices (each with the lesson that caused it)

* **[DESIGN CHOICE] Identity is pinned at dispatch.** Every neighbouring lane
  validates live sweeps structurally because live bytes depend on the session
  identity; this lane refuses to fire at all
  (`damage_hp_link_hypothesis_identity_not_pinned_no_reply`) unless the selected
  actor IS the canonical smoke identity 0x10010001 the pins were computed for.
  A tester sees the pinned bytes byte for byte, or nothing.
* **[DESIGN CHOICE] The clamp.** 37 - 379 = -342 is clamped to the floor 0 at
  `HP_ZERO_DYING` and nowhere else (`hp_clamp_outside_the_pinned_step`); healing
  (positive damage) is refused by name (`damage_positive_heal_semantics_unknown`)
  because its semantics were never observed anywhere.
* **[DESIGN CHOICE] The control re-sends 37.** Whether a real client re-renders
  an hp value it already holds is unknown and informative either way; the frame
  being byte-identical to #3 makes the question clean.
* **[DESIGN CHOICE] 15 s spacing** (round 84: attended tests are photography).
* **[DESIGN CHOICE] hp frames carry the full proven baseline field set** (scene,
  sequence, cash, name) exactly as the HYP-PF-022 frames the client accepted did
  — mirroring proven bytes beats minimal masks (round-96 lesson: the CopyTo
  binds are not masked merges).

## 5. Fail-closed inventory

`production_allowed = False` in module and scenario · whole-tree `_exact_equal`
scenario allowlist (one extra/missing/renamed key anywhere refuses) ·
identity-compared wire unlock, minted once at `make_state_class` construction,
compared with `is` (an equal-but-not-identical forgery opens nothing) · lethal
fields (hp at the floor, any death-timer field) composable only at the two
pinned lethal steps · **48 named refusals**, each driven red by the verifier
and/or tests · with no scenario: no flag, no object, no unlock, no dispatch
branch, zero events, zero bytes.

## 6. What the attended run must answer (queued as GT-031; ceiling until then)

1. Does the HP bar track **100 -> 37 -> 0**, moving at the **hp frames** and not
   at the hit frames? (The bar moving at a hit frame BEFORE the linked hp frame
   would falsify round 83's "client never subtracts" — the most valuable
   possible negative, and the damage lane's whole reading re-opens.)
2. Do the floating numbers still render as at GT-024 while the bar moves —
   visibly simultaneous or visibly ordered?
3. Does the dying window open at `HP_ZERO_DYING` exactly as GT-019's isolated
   frame did when it arrives seventh in a linked sweep, and does `Common_Death`
   follow `DYING_ELAPSED` as at GT-023?
4. Does the client visibly re-render (blink, refresh) at `HP_AFTER_MISS`, whose
   value it already holds?

A client that renders the numbers but never moves the bar does **not** falsify
the wire claim — it answers the link question in the negative and is recorded
as a result, not a failure.

## 7. Version accounting

Budget: **1 of `max_versions: 3`** (DAMAGE-HP-LINK-001 — the whole lane in one
round). Widening (another target, another identity, a persistent balance, a
database column, any death-window exit mechanism, jitter, a second profile) is
a NEW VERSION or a new entry, per the stop rule.

## 8. How to run

```
py -3 tools\verify_damage_hp_link_encoder.py
py -3 tools\pf_damage_hp_link_headless_replay.py
py -3 -m pytest tests\test_damage_hp_link_hypothesis.py tests\test_damage_hp_link_dispatch.py -q
py -3 -m pirateforce_foundation.app --db <existing db> ^
    --damage-hp-link-hypothesis-scenario scenarios\damage_hp_link_hypothesis_link_sweep.json
```

## 9. Nonclaims

Restating `DAMAGE_HP_LINK_NONCLAIMS` (the same list rides the scenario JSON
verbatim): this_is_our_design_not_the_original_servers_which_is_unrecoverable ·
no_capture_shows_damage_linked_to_hit_points_in_either_direction ·
the_client_does_not_subtract_damage_that_is_why_the_server_must_say_both_halves ·
no_claim_the_original_server_ever_linked_these_frames ·
no_database_write_no_hp_column_exists_and_none_is_added ·
wire_and_dispatch_layer_only_no_client_has_seen_these_bytes ·
one_shot_per_process · no_claim_about_any_death_window_exit_path ·
miss_control_proves_only_that_our_arithmetic_holds_not_that_the_client_checks_it ·
production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false ·
production_baseline_behavior
