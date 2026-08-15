# SCENE-009 — CHitResult consumer provenance and ready-only negative

Date: 2026-08-16

## Claim

Exact static client proof identifies `CHitResult` Vital ID `0x16F7` as a distinct
inbound result/reaction consumer with a bounded target-side implementation path.
A checksum/code-guarded observe-only probe can attach to the exact original and
local-runtime client profiles and monitor that path without writing client memory,
input or packets.

In one controlled Port Royal P60 run, the corrected ready-only probe emitted only
`probe_ready` while the existing hostile TargetVital -> `0xEA7D` -> SCENE-007
ActionVital acknowledgement sequence completed. This is an operational absence
negative, not proof that `CHitResult` is unrelated to combat.

## Static provenance

The client registers the `CHitResult` name-derived ID `0x16F7`, constructor
`0x74F940`, vtable `0xF48AA0`, serializer `0x750040` and inbound handler
`0x750770`. The handler resolves the performer and each record target. The bounded
implementation lane requires record flag bit 0 and bit 3 set, bit 4 clear, a
resolved target and a non-null return from `0x48D870`. It marks the returned
implementation with `0x40000000` and reaches the preparation boundary for the
target actor's `+0x40` queue.

Proven native fields are performer qword, action u16 and per-record target qword.
The remaining header and record values stay opaque. In particular, the signed dword
at record `+0x08` reaches a presentation path but is not proven damage or an HP
mutation. This bounded audit identifies no exact producer/data binding that fixes
a safe server payload, and no static edge proves `0xEA7D` must be followed by
`CHitResult`.

## Runtime evidence

The first `015059` attempt is retained only as a superseded tooling diagnostic:
Frida 17.17 rejected interception of a two-byte indirect call before observation.
The correction moved the affected hooks to relocatable, branch-selected preparation
blocks and renamed their events `*_prepared` so they do not claim call completion.

The fresh `020135` probe attached to `GameClient.local.bin` at runtime base
`0x00CC0000`, passed its checksum/PE/code guards and emitted one exact
`probe_ready` event. It emitted no `hit_result` or downstream lifecycle event
during the controlled observation window. No stdout/stderr or exit-status sidecar
was frozen for this probe process, so this report does not claim artifact-backed
clean or bounded probe exit.

The paired server capture independently records exact TargetVital kind 1 for P60
identity `0x203D`, one 113-byte RuntimeReq whose ActionVital is `0xEA7D` targeting
`0x203D`, and one 97-byte SCENE-007 ActionVital acknowledgement. Heartbeats continue
through 72 after the acknowledgement. Server and database-guard stderr are empty.
Chief direct UI observation after the probe window found the client responsive.
The database main file, WAL and SHM returned `PASS_UNCHANGED`.

No `CHitResult` packet was sent in this experiment.

## Evidence ceiling

Proven at grade A static: the exact `CHitResult` registration, native object
consumer layout, performer/target resolution and the conditional target-side
implementation preparation lane described above.

Proven at grade C instrumentation readiness: the corrected guarded hooks install
and emit `probe_ready`. Grade E operational negative: the existing SCENE-007
acknowledgement did not expose a `CHitResult` event in this single observation
window.

Not proven: `0xEA7D` to `CHitResult` ordering, authentic server payload values,
attack animation, hit/miss/critical semantics, damage or HP mutation, range or
cooldown authority, FightAttr, UpdateAttr, AI, death, loot, respawn, skills or
authentic player faction. Do not compose or send a `CHitResult`, HP, UpdateAttr or
FightAttr packet from this checkpoint.
