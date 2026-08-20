# PF DAMAGE-NPC-TARGET-001 — the second (and last) profile of HYP-PF-024

- **date:** 2026-08-20 (chief round 95)
- **milestone:** DAMAGE-NPC-TARGET-001 — the third and FINAL tracked version of HYP-PF-024 (budget now 3/3, ZERO remain)
- **claim grade:** wire + dispatcher layer only (headless-proven); the client layer is GT-027, attended
- **AMENDED 2026-08-21:** the line above originally read "the client layer is GT-027, attended, NOT run". GT-027 HAS
  since run. The attended rerun of 2026-08-20, driven by Panya, is recorded in
  `reports/PF_NPC_HP_LINK029_GT027_RERUN_ATTENDED_RESULT_20260820.md`: the number rendered over the NPC, and 505 points
  of cumulative damage did not move the target's HP bar by one unit. Read that report's provenance caveat before citing
  it -- the result is testimony plus surviving screenshots, not a re-derivable receipt, and it is a client-observable
  layer result only. Nothing else in this document changed.
- **whose numbers these are:** OURS. The original server is closed, was never published, and cannot be read. Nothing in
  this document is evidence about the original server's damage rules.

## What this version is

One new named profile of the existing HYP-PF-024 hit sweep, `npc_target`, behind its own opt-in scenario file
`scenarios/damage_model_hypothesis_npc_sweep.json` and its own identity-compared unlock token. It exists because GT-024
answered every question the first profile could ask — numbers render, they are exactly 63/379, MISS draws the marker and
no number, flag 9 is distinguishable — and left exactly one it cannot: **has the client ever been asked to draw our
number over an actor that is not the player?**

Changed against `hit_sweep`, and NOTHING else:

| field | hit_sweep | npc_target | why |
|---|---|---|---|
| hit entry target (`+0x00`) | the session actor (player) | **`0x2001` fixed** | `0x2000 + placement_idx + 1`, first Port Royal placement; the identity HYP-PF-023 already drives |
| performer (header `+0x18`) | the session actor | the session actor (unchanged) | one side must be the player or the six-stage visibility filter at `0x43FEF0` draws nothing (FINDINGS_R93) |
| spacing | 6.0 s | **15.0 s** | photograph each frame without racing capture latency (round-84 lesson) |
| action label prefix | `HYP_PF_024_DAMAGE_MODEL_` | `HYP_PF_024_DAMAGE_NPC_` | the console log must say which experiment ran |
| dispatcher event | `damage_model_hypothesis_hit_sweep_sent` | `damage_model_hypothesis_npc_sweep_sent` | same reason; the old string is unchanged down to the byte |

Both profiles hold the **same step tuple object** (`DAMAGE_MODEL_STEPS`), so the damage values (−63/−379/0/−63), the
flag words (1/1/0/9), the MISS control and the step order cannot fork between them. The 0x2001 constant is COPIED from
the death lane (`RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY`) with a drift test in
`tests/test_damage_model_hypothesis.py::NpcProfileTests`, never imported — an encoder does not import a neighbouring
lane.

## The pinned bytes

Composed from the fixed probe performer `0x10010001` against the fixed target `0x2001`; PC 84 bytes, frame 95 bytes,
every step. The only bytes that differ from the hit_sweep pins are the eight of the entry target qword
(`01 00 01 10 00 00 00 00` → `01 20 00 00 00 00 00 00`), which is itself asserted byte-for-byte in the tests.

| step | damage | flags | pc_sha256 | frame_sha256 |
|---|---|---|---|---|
| HIT_WEAK | -63 | 0x0001 | D07A4F48E56085982E511FF24E4C4C079DF1318E60A7386BF1B93F5D54A8A4C3 | 0B4537B6240F7C202B5FAF1A9BADCB0E0F7BAFC40191724DFDE953F797F89706 |
| HIT_STRONG | -379 | 0x0001 | 237CB09D44742068F8304FF02CFDA4E61E1045719DE00BE06F0B2CBAAA1E41A5 | 3363C2A44878732D97F204987963B277E47DAF4016F6BDA27D0E92E2F0128FA9 |
| MISS | 0 | 0x0000 | 36702C4201652DBB84C5F712515D28729AC994D07353AAE069D53E454DDD3891 | E369DDC41CA253CBE3ABD5474760C2F0F4C9D76FD12A7BD1783B1D68D67E7458 |
| HIT_REACTION | -63 | 0x0009 | 5765546FC310F909F39899497472FEE58B4B1825537226FDE71E54D2CFE07F1A | 166C53D856C974CB009C34423757F09D3CB441D576585E6D3BA3F29B3E7F3FC1 |

The pins live in three places that must agree and are checked against each other: `DAMAGE_MODEL_PINS_NPC` in the
module, `target.per_step` in the scenario file, and the composed bytes themselves on every build
(`_require_pinned_composition` re-composes the probe on every `build_damage_model_sweep` call).

## Fail-closed additions

Two new named refusals, each driven through its red path by tests and by the verifier:

- `npc_target_identity_not_pinned` — an npc-profile entry whose target is not exactly `0x2001`.
- `npc_performer_must_not_be_the_npc_target` — a performer that IS `0x2001`; the profile's whole point is that the two
  sides differ, and a frame where they do not must never leave the process.

And one new pairing refusal across the whole lane, `wire_unlock_is_for_a_different_profile`: each profile now carries
its own unlock token compared by identity (the round-91 HYP-PF-023 repair), so the key minted from one scenario file
opens no byte of the other. Proven in both directions.

## Proof, and where it stops

- `tools/verify_damage_model_encoder.py` — **350 guards PASS** (was 322; +28 in the new section D2): the npc file loads
  to the module's own profile object, the pins reproduce, the npc pins differ from the hit_sweep pins on every step,
  the identities read back as performer=probe / target=0x2001, and the new refusals fire by name.
- `tools/pf_damage_model_headless_replay.py --profile npc_target` — **141 guards PASS**: a real `make_state_class`
  dispatcher on a throwaway database answers one accepted chat frame with the four npc frames, byte-for-byte the
  encoder's composition for the same session actor, read back by the tool's own independent tag walker; performer is
  the session's selected character, target is `0x2001` on every frame, delays 0/15/15/15; one-shot holds; no database
  file or logical content changed; no socket was constructed. The `--profile hit_sweep` run still passes (140 guards).
- `tests/test_damage_model_hypothesis.py` (102) and `tests/test_damage_model_dispatch.py` (68) — the dispatch class is
  now SUBCLASSED under the npc profile, so the whole refusal ladder, the one-shot rule and the containment guards run
  under both profiles; the npc-specific tests pin the full PC hex of all four frames.

**Where the proof stops:** no client has ever been shown one byte of the npc profile. Whether `0x2001` is in the
client's identity map AT RUNTIME is unproven — round-93 static proved the placement exists in map data and that a
target the client cannot resolve is skipped silently at `0x750D27`. GT-027 (attended, queued) measures exactly that,
and **"no number over the NPC" is its meaningful negative**, worth as much as the positive. The entry position field
still carries the pinned V135 player spawn: the round-93 reading is that the rendered number anchors to the RESOLVED
ACTOR, not to this field, and that is a reading, not an observation — recorded as a nonclaim.

## Version accounting

This is the third of `max_versions: 3` for HYP-PF-024 (`DAMAGE-ENCODER-001`, `DAMAGE-DISPATCH-001`,
`DAMAGE-NPC-TARGET-001`). It is counted as a full version although it adds no new frame shape, because it lets the lane
address an identity no earlier version could — the conservative accounting is the honest one. **The budget is now
full.** A third target, a new spacing, a fifth frame or any other widening needs a NEW ledger entry or a scoped
approval in `extension_approval_ref`, not another profile.

## Erratum carried in the same commit

The module docstring called the MISS frame "the control: NO number" as if nothing should appear. Per
`FINDINGS_R93_CHITRESULT_DISPLAY_TARGET_STATIC.md`, `bit0 clear AND damage == 0` selects FxNumber type 6
(`0x440093`, key `0x2D`, texture `bm_miss.tga`): the client is designed to draw a MISS marker, and GT-024 observed it.
Only a floating NUMBER must be absent. The docstring now says so; no pinned byte changed.

## How to run

```
py -3 tools\verify_damage_model_encoder.py
py -3 tools\pf_damage_model_headless_replay.py --profile npc_target
py -3 -m pirateforce_foundation.app --db <existing db> ^
    --damage-model-hypothesis-scenario scenarios\damage_model_hypothesis_npc_sweep.json
```

`production_allowed` is False everywhere it appears; the scenario is test-only, opt-in, mutually exclusive with every
other mode, writes nothing, and takes no socket action of its own.
