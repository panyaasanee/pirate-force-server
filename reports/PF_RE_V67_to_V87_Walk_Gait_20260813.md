# Pirate Force NPC movement — V67/V68/V69/V85 gait finding and V87

Date: 2026-08-13

## Corrected runtime observations

- P5 is the large blue tiger-like model. It visibly walked in V67, V68, and
  V69. V68 was especially smooth; V67 had a walk/stop cadence.
- P50 is Atlantis Prime Minister. It still stuttered in V68, and visibly ran in
  V69.
- P144 is the pink-haired, rabbit-eared beer tray carrier. This mapping follows
  from the separated V84 lanes: P84 was the green/gold Fighter Apprentice,
  P89 was the striped female, and P144 occupied the remaining right lane.
- In V85 the large blue P5 model visibly ran rather than walked.

## Static/source finding

The walk/run presentation is controlled by decoded `MOBS.n_SPEED_WALK`, carried
as `BasicAttr` bit `0x0040`, float field `+0x54`.

- V67 and V68 included value `150.0` for P5 in every generated state.
- V69 continued doing so only for P5. Its other movers omitted the value in
  movement generations, matching the user's observation that P5 walked while
  Atlantis, Fighter Apprentice, Panic Slave, and the beer carrier ran.
- V75 and descendants changed the experiment to baseline-only speed pinning.
  V85 therefore sent `150.0` only in its initial/reapply snapshot and omitted
  it from every movement snapshot. This exactly accounts for P5 changing from
  its V67–V69 walk gait to a clear run gait in V85.

MovementAttr `+0x38`, ActionVital, and unknown fields are not required to test
this hypothesis.

## V87 focused test

V87 derives from V85's stable bootstrap and V83 absolute-deadline sender. It
spawns exactly three models in separated Port Royal lanes:

1. P5 — large blue tiger-like model
2. P144 — beer tray carrier
3. P50 — Atlantis Prime Minister

They move one at a time. Each uses the V72 target cadence: two 150-unit targets
at 0.50-second intervals, a 2.50-second far hold, then the same two-step return.
The evidence-backed V87 change is that `movement_speed=150.0` is serialized for
all three actors in baseline, reapply, and every movement generation.

No bootstrap field, unknown movement field, ActionVital, position height, or
sender timing behavior was changed.

## Verification

- Python compile: PASS
- Project self-test: PASS
- 12 movement frames: PASS
- actor phase order P5 -> P144 -> P50: PASS
- three `150.0` speed values in every movement snapshot: PASS
- no ActionVital in movement frames: PASS
- Snappy response roundtrip: PASS

The user requested that V87 be prepared but not launched. No runtime verdict is
recorded yet.
