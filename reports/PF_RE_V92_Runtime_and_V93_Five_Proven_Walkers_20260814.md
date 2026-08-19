# Pirate Force V92 runtime result and V93 five proven walkers

Date: 2026-08-14

## V92 runtime result

The user reported that V92 looked okay. This accepts both parts of its focused
hypothesis:

- all 20 authoritative members remained visible after cadence began;
- retaining 17 static members as NPCAttr-only entries did not reproduce the
  distant same-position stutter reported in V90.

V92 is therefore the current proven representation for a mixed moving/static
RemoteActors snapshot. An actor must remain listed to remain in the scene, but
a static actor does not need a repeated MovementAttr.

The V92 live cadence sent all 20 expected frames with sender lateness 0.2-1.1
ms (average 0.71 ms), so the accepted observation was not confounded by sender
drift.

## Additional inbound protocol identification

The V92 capture contained previously unnamed runtime vital IDs. Applying the
already recovered protocol-name ID algorithm to class names embedded in
GameClient.local.bin resolves them without guessing:

- `0x1EB4` = `COnLandVital`
- `0x0F01` = `UserSetting_UpdateServerSettingVital`

These packets are not NPC interaction evidence and do not justify a server
response in this version.

## V93 focused change

V93 preserves V92's stable bootstrap, 20-member population, actor identities,
authoritative membership semantics, and NPCAttr-only representation for actors
that are not moving.

It promotes only P84 and P89 from static to moving. Both were members of the
runtime-confirmed smooth V72 set. They retain their authentic placement homes
and receive the already confirmed walk formula:

- BasicAttr movement speed 150 in every generation;
- 150-unit target advance every 0.50 seconds;
- no corner hold packet;
- two closed square cycles and exact return home;
- staggered starts on the same absolute-deadline sender.

P5, P144, and P50 retain their complete V89/V92 lane routes. Thus each cadence
snapshot has 20 members: five NPCAttr+MovementAttr walkers and 15 NPCAttr-only
static actors. No unknown field, ActionVital, movement mode, or new route is
introduced.

## Verification

- Python compile: PASS
- project self-test: PASS
- stable bootstrap regression: PASS
- baseline actor count 20 / MovementAttr count 20: PASS
- cadence actor count 20 / MovementAttr count 5: PASS
- 15 static cadence entries omit MovementAttr: PASS
- five speed-150 fields in every cadence generation: PASS
- all five walkers complete two cycles and return home: PASS
- no ActionVital in cadence generations: PASS
- Snappy response roundtrip: PASS
- near/far population uniqueness and forced P84/P89 membership: PASS

Package: `packages/PF_Login_Game_Test_v93.zip` (exactly three files)

SHA-256: `B05D4634CEC5146A2A6C2E0904D7E584EA3B4E6D30602C9D8670CB38BF454236`
