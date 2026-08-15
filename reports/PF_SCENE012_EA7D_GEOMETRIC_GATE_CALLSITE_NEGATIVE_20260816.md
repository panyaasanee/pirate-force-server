# SCENE-012 — EA7D geometric-gate callsite boundary and operational negative

Date: 2026-08-16

## Claim

Exact static client proof identifies the EA7D geometric-threshold gate at
`0x44EB1D -> 0x4758D0` and its boolean return site at `0x44EB22`. A narrowed,
checksum/code-guarded observe-only probe installed only at those two callsite
boundaries. It captured one exact EA7D gate entry, but a duplicate operator
gesture triggered the designed fail-closed path before any gate result was
observed. SCENE-012 is therefore not a runtime gate-result pass.

## Static provenance

The caller pushes the action held in `EBX` and calls `0x4758D0` at `0x44EB1D`.
For exact action `0xEA7D`, the callee resolves two runtime object chains and calls
`0x755540` in mode 0. That helper selects the minimum BEHAVIOR `n_RANGE` from its
collection, with a raw default integer of 10. The accepted SCENE-011 trace
observed natural keys 278 and 279 at this helper lookup, both with raw
`n_RANGE=75`.

The gate adds the helper result to an unresolved live object scalar at `+0x1C`,
squares that threshold, computes squared XYZ separation from two resolved live
object chains, and returns boolean true only when threshold squared is strictly
greater than separation squared. The post-call instruction at `0x44EB22` sees
that boolean in `AL` before stack cleanup.

The live scalar, exact runtime identities of the object chains and their XYZ
values at comparison time are not present in the accepted wire evidence.
Equating them with server spawn/ActionVital coordinates, or assuming the threshold
is simply 75, would be a hypothesis. No authoritative offline boolean can be
computed from this checkpoint.

## Runtime evidence

The paired uninstrumented control first completed exact P60 TargetVital kind 1 at
05:04:06, an EA7D/target-`0x203D` ActionVital at 05:04:32, and the one-shot
SCENE-007 acknowledgement. This control predates every probe event described
below and is not correlated to the instrumented callsite entry.

The `050459` attempt emitted only `probe_ready` and exited 1 because no gate result
arrived in its observation window. The client remained active and the server later
received another EA7D request at 05:05:47.

The `050640` attempt emitted `probe_ready`, followed by exact `gate_enter` at live
address `0xD0EB1D`, caller/return `0xD0EB22`, action `0xEA7D`, thread 2956 and
invocation 1 at 05:07:02.328. A second operator click reached the same gate 297 ms
later. The probe cleared the owned state, emitted `duplicate gate invocation`,
returned no result and exited 1. It emitted no `gate_result`.

The server capture records request/heartbeat traffic through 05:07:01.622 and then
records the client closing. A later `050726` host attempt could no longer query the
client process image and exited 1 without producing JSONL. Server stderr is empty.
The database main file, WAL and SHM returned `PASS_UNCHANGED`.

## Evidence ceiling and stop rule

Grade A static: the exact EA7D callsite, helper selection structure, squared
geometric comparison and boolean return boundary.

Grade B control: the earlier uninstrumented TargetVital-kind1 -> EA7D -> one-shot
ActionVital acknowledgement sequence and unchanged database.

Grade C instrumentation: one exact EA7D `gate_enter` at the guarded live callsite.
Grade E operational negative: no gate result, a fail-closed duplicate gesture, and
the later unavailable client process.

Not proven: boolean true/false, exact threshold, range units, in/out-of-range,
attack success, animation, hit/miss/critical semantics, damage or HP mutation,
FightAttr, cooldown, AI, death, loot, respawn, skills or authentic player faction.

Do not add further hooks to this live path and do not synthesize CHitResult, HP,
UpdateAttr or FightAttr. The next safe evidence boundary is a structured offline
audit for a complete original/natural server-to-client combat-result envelope,
using decoded outer ID/version/count/tag structure and temporal adjacency rather
than raw byte scanning. If the bounded corpus contains none, record only a corpus
negative and require a lawful original-server capture.
