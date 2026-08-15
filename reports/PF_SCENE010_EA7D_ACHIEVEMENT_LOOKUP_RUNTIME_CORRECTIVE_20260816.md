# SCENE-010 — EA7D numeric action-data lookup runtime trace

Date: 2026-08-16

## Claim

Exact static client proof and one checksum/code-guarded observe-only runtime trace
show that the numeric action-data registry is queried with key `0xEA7D` on both a
producer/control path and the inbound ActionVital acknowledgement path. All three
observed `0xEA7D` lookups returned null in this session.

The inbound null result explains a narrower part of the SCENE-008 inert lifecycle:
the ActionVital handler skips one optional registry-entry-dependent branch while
generic action construction and queueing can still continue. This does not prove
that the skipped branch is animation, combat or damage behavior.

## Static provenance

The exact numeric lookup is `0x702A10`, a `thiscall` over the action-data manager
whose sole raw key is the u32 stack argument and whose result is the returned entry
pointer. The guarded probe observes only this boundary and records the caller,
key and return value without dereferencing the entry or writing memory, input or
packets.

Producer/control function `0x44E890` calls the lookup at `0x44E925`, returning to
`0x44E92A`. A null result follows its default-initialization lane; a non-null entry
with entry `+0x28` bit 7 set takes a different lane. The function later contains
an exact `0xEA7D` branch and can call generic ActionVital producer `0x44D260`.
The two observed null lookups at this callsite do not prove two packets or explain
why the function invoked the lookup twice.

Inbound ActionVital handler `0x7516C0` calls the same lookup at `0x7517B0`, returning
to `0x7517B5`, using ActionVital field `+0x30` as the key. A null result still permits
generic constructor `0x47AB30` and actor queue path `0x4843F0`; it skips the later
entry-dependent bit-7 virtual-call branch. Static proof does not establish the
semantic meaning of that bit or branch.

Natural keys 278 and 279 returned non-null entries at caller `0x7555D2`. That
callsite performs an opaque table aggregation over entry `+0x30`; these are controls
only and have no promoted action, animation or combat meaning.

## Runtime evidence

The accepted probe attached to `GameClient.local.bin` at base `0x00CC0000`, giving
ASLR slide `+0x8C0000`. It emitted one `probe_ready` and 228 strictly sequenced
`numeric_lookup_result` events, no `probe_error`, exited zero, and left stdout and
stderr empty.

Three events used raw key 60029 (`0xEA7D`) on thread 23420:

- sequences 1 and 11 called from live `0xD0E92A`, static return `0x44E92A`, and
  returned entry zero;
- sequence 228 called from live `0x10117B5`, static ActionVital-handler return
  `0x7517B5`, and returned entry zero.

The paired uninstrumented server capture records exact P60 TargetVital identity
`0x203D` kind 1 at `02:30:32.940`, an ActionVital request carrying action `0xEA7D`
and target `0x203D` at `02:30:49.296`, and the 97-byte SCENE-007 acknowledgement at
`02:30:49.299`. The consumer lookup occurred at `02:30:49.317`, 18 ms after the
acknowledgement. Heartbeats continued through sequence 80 while the probe completed;
the socket reset appeared only during the controlled client close. Chief direct UI
observation found the client responsive after the probe. Server and database-guard
stderr are empty, and the database main file, WAL and SHM returned
`PASS_UNCHANGED`.

The `022000` and `022400` ready-only exit-1 attempts missed the acknowledgement
window. The `022656` exit-zero attempt observed only unrelated key 97. They are
retained as superseded operational timing diagnostics and are not acceptance inputs.

## Evidence ceiling

Proven at grade A static plus grade C instrumented runtime: the exact numeric
action-data lookup boundary, two producer/control lookups and one acknowledgement-
consumer lookup for `0xEA7D`, all returning null in this session. The consumer null
result skips the exact optional entry-dependent branch while the generic action path
remains available.

Not proven: that no metadata for `0xEA7D` exists elsewhere, a ScriptB stem-to-key
binding, the meaning of entry `+0x28` bit 7 or entry `+0x30`, visible animation,
implementation execution, hit/miss, damage or HP mutation, range/cooldown,
FightAttr, CHitResult ordering or payload, AI, death, loot, skills, or authentic
player faction. Do not synthesize or insert an `0xEA7D` registry entry and do not
send CHitResult, HP, UpdateAttr or FightAttr from this checkpoint.

The next safe boundary is read-only provenance for numeric-manager population and
entry fields, or an observe-only natural non-null ActionVital correlation. It must
not mutate the registry or invent a response packet.
