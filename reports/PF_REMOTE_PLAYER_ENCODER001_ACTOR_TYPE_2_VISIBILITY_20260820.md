# REMOTE-PLAYER-ENCODER-001 + REMOTE-PLAYER-DISPATCH-001 — actor_type 2 visibility probe (HYP-PF-025)

Date: 2026-08-20 (chief round 96) · lane: `movement/remote_player_movement_projection` + world visibility (multiplayer chunk 2)
Status: **wire + dispatcher layer proven headless; client layer = attended queue, NOT RUN**

> **THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS UNRECOVERABLE.**
> The original server is closed, was never published, and no corpus holds one
> server→client capture of a remote human player (readiness audit §6.2;
> MPAUDIT-FOLLOWUP-001 §7.3).  Everything here is a shape OUR client will
> accept or reject.  Every value without a `[PROVEN ...]` label is ours.

## 1. What landed

The first frames in this project's history that carry **`actor_type 2`
(`CNetActor`, the remote-player branch of the client actor factory)** — every
prior "someone else is in the world" frame was `actor_type 4` (19 literal
call sites in v141, all four emitters in `src/`).  One opt-in lane, pattern
HYP-PF-023:

| piece | path |
|---|---|
| module | `src/pirateforce_foundation/remote_player_hypothesis.py` |
| scenario (exact allowlist) | `scenarios/remote_player_hypothesis_visibility_probe.json` |
| CLI flag | `--remote-player-hypothesis-scenario` (requires explicit existing `--db`, mutually exclusive with every other mode) |
| dispatch | `runtime.py::_dispatch_remote_player_hypothesis` (one-shot, trigger = accepted 34-byte ascii12 chat frame) |
| offline verifier | `tools/verify_remote_player_encoder.py` — **129 guards, 0 failures** (138 with `--binary`; the 9 image guards re-assert the jump table, the five bind thunks, the `+0x24` CopyTo load and the 0x6E9D literal from the read-only image, sha `96272114..B623`) |
| headless replay | `tools/pf_remote_player_headless_replay.py` — **162 guards, 0 failures** through the REAL dispatcher on a throwaway DB copy, frames re-read by an independent walker written inside the tool |
| tests | `tests/test_remote_player_hypothesis.py` (63) + `tests/test_remote_player_dispatch.py` (25) |

## 2. The sweep (five frames, one entry each, all actor_type 2)

Envelope per frame `[PROVEN SRC — v141:1267 make_runtime_remote_actors]`:
`0x6E9D` v4 · inherited mask `0x00` (PC offset 11) · derived mask `0x02`
(offset 13, actor-entry collection at object `+0x1C`) · count 1.

| # | label (`HYP_PF_025_REMOTE_PLAYER_` + …) | identity | attrs | delay |
|---|---|---|---|---|
| 1 | `SPAWN_BARE` | A `0x00A00001` | ActorAttr(`0x12AD`: name "ProbePlayer01", HP 100/100, scene 1/0, 64-bit mask **0**, extra-group **1**) + MovementAttr(`0x2067`, mask `0xFF`) at placement-0 XYZ | 0.0 s |
| 2 | `SPAWN_AVATAR` | B `0x00A00002` | same ActorAttr shape + MovementAttr(`0xFF`) at X+150 + **opaque `AvatarAttr 0x16A0` tail** (selected character's `characters.avatar_wire`, identity rebound to B) | 15.0 s |
| 3 | `MOVE_A_1` | A | MovementAttr **only**, mask `0x01`, X+300 | 15.0 s |
| 4 | `MOVE_A_2` | A | MovementAttr only, mask `0x03`, heading π/2 | 15.0 s |
| 5 | `NEGATIVE_CONTROL` | C `0x00A00003` | **wrong-class `NPCAttr 0x0AD5`** (name "ProbeControl03", template 1, preset `P_MALE_002_000_SP1`, straight from `legacy.make_npc_attr`, unmodified) + MovementAttr(`0xFF`) at X−150 | 15.0 s |

Anchor position = placement 0 of the frozen, hash-pinned
`PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS` (115 rows, SHA-256 `22D7430E..9618`),
nearest to the frozen V135 player spawn — the same rule and the same pinned
answer HYP-PF-023 uses.  Identities/offsets/names are `[DESIGN CHOICE]`.

Pins (module `REMOTE_PLAYER_PINS` = scenario `probe.per_step` = recomputed by
verifier, replay and tests): PC sizes 169 / 61 / 66 / 206 bytes for steps
1/3/4/5 with full sha256 pins; step 2 is a **SKELETON pin** (172 bytes,
`F4F72429..5E75`) because the avatar tail is per-character database content —
the tail is structurally checked instead (common-Attr prefix `0x0B`/bit
`0x01`/`0x32`, rebound identity == B, and it must be the LAST attr).  On the
canonical-copy database the replay observed the tail as 103 bytes, sha256
`FF790EA9..3A58` (an observation, not a pin).

## 3. What the CHUNK2 static findings changed (Q1/Q2/Q3, imported as reports)

`reports/PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md` ·
`reports/PF_CHUNK2_Q2_MOVEMENT_MERGE_FINDINGS_20260819.md` ·
`reports/PF_CHUNK2_Q3_BIND_THUNK_FINDINGS_20260819.md`
(round-90 lane worker output, imported verbatim under a provenance header —
the R90 design draft named its §10 rows 1, 4, 5 as "must close before the
encoder is written", and these closed rows 1, 2, 4, 5 and 13.)

* **Q1** — `ActorAttr` 64-bit mask `0` is legal (`0x4667AD`/`0x466B5C` are
  short-circuits, not error paths), **but** the actor-entry pipe binds via
  vtable `+0x24 = 0x464F30`, a CopyTo with **zero mask tests in 143
  instructions**; the masked merge (`+0x30 = 0x465E60`) is never called on
  this pipe.  Consequences built in: BasicAttr probe mask `0x030D` always
  ships (an all-default attr would land HP 0 = the death predicate
  `0x43BD7A`/`0x43BDAA`); the 43 mask-gated ActorAttr fields land as ctor
  defaults and that is recorded, not hidden; the `+0x1BC` gate byte ships as
  `1` (at `0`, the client skips 25/43 fields); HP < 1 is refused by name.
* **Q2** — the mask-gated movement merge `0x467130` runs inside `0x5E4060`
  against the **previous RuntimeRes frame's collection copy** (singleton
  `[0x01081A90]+0x154`), not against the actor and not against history.
  Prediction recorded for the attended run: `MOVE_A_1`'s unsent fields reach
  the actor as ctor zeros (the previous frame holds B, not A); mask `0x01`
  still moves the actor.
* **Q3** — bind `+0x38` never swaps the attr pointer; a re-sent identity
  updates values (no leak, no free).  That is what makes frames 3/4 safe.

## 4. Deviations from the R90 design draft (both rows were `[DESIGN CHOICE]`)

1. **AvatarAttr rides LAST** in frame 2 (draft sketched it second).  The tail
   is opaque; an independent walker can only find its boundary at end-of-
   frame.  Q3 proved the binds are independent per-attr CopyTo calls; nothing
   orders them.
2. **Spacing 15.0 s** (draft said 6.0).  Rounds 84 and big-round #8 both lost
   evidence to 6-second photography; the damage lane's npc profile moved to
   15 s for the same reason.

## 5. Fail-closed inventory

`production_allowed = False` everywhere it appears.  Exact-allowlist scenario
file.  Wire unlock compared by identity (value-equal forgery opens nothing);
without it `actor_type 2` cannot be named on the wire at all.  37+ named
refusals, each proven to raise with its name and emit no bytes — actor types
0/1/7 (outside the jump table), 3 (`CMyActor` singleton), 4-with-ActorAttr
(silent-drop trap), the death-timer bit `0x0080` (HYP-PF-023's field), HP 0,
identity collisions (selected character / NPC band / character space),
off-pin masks, off-placement positions, malformed avatar bodies, forged
unlocks, off-plan labels/delays/counts, and the scenario allowlist.  Sweep
one-shot; compose-time refusals surface as a named `..._compose_refused_
no_reply_*` event and silence.

## 6. What the attended run must answer (queued as GT-030; ceiling until then)

Headless proves the WIRE and DISPATCHER layer only.  Not proven: whether
anything renders at all; whether it looks like a person; whether A vs B
answers the AvatarAttr question; whether the name board fills from BasicAttr
`+0x28`; whether frames 3/4 move/turn the actor; whether the control stays
nameless.  **Stop-the-lane outcomes:** a NAME over the negative control
(falsifies chunk 1's bind-gate claim) or `ErrorData=28317` in the server log.
**No despawn exists on this lane** — a probe stays until the client
disconnects.  Ground Z at the offset points is unchecked.

## 7. Nonclaims

The module's `REMOTE_PLAYER_NONCLAIMS` tuple, verbatim in the scenario file:
our design, not recovery; no client has seen one byte; no rendering claim; no
claim which ActorAttr mask bits a `CNetActor` needs; no claim the avatar is
accepted under a foreign identity; no name-board claim; no despawn; ground-Z
unchecked; no interest management / cadence / interpolation (chunk 3); no
second connection, no broadcast, no `send_lock`, no `population.py` change
(the audit's 52 pinned tests are NOT re-proven and W01/W02/W04/W05/W10 are
NOT touched — this lane closes part of W03 only); the 229 unresolved vtable
`+0x20` dispatch sites are inherited, not narrowed; the wiring is opt-in and
test-only.
