# HOTBAR-001 — SetItemOnParticularHotKeyPosVital static checkpoint

Date: 2026-08-16  
Classification: Grade A exact static proof; no runtime or packet experiment

## Primary claim

The exact `SetItemOnParticularHotKeyPosVital` protocol object has a three-field
structural codec `(u32, i8, i8)`. Its class-specific consumer calls one client
state method with logical arguments `(raw +0x14 u32, sign-extended +0x18,
sign-extended +0x19 minus 1)`. This checkpoint does not establish a local
producer, field meanings, item-versus-skill discrimination, persistence or
reconnect behavior.

## Grade A facts

- Registration at `0xBEE9A0` hashes the ASCII class name at `0xF30B50` and stores
  the deterministic registered value in `0x10820A4`. The class-name registration
  hash is `0xE0AC`.
- The standalone class getter at `0x5E4A40` reads `0x10820A4`. This is distinct
  from vtable method `0x5E4AE0`, which belongs to the following
  `LoginVerifyVital` class and reads its separate global `0x1081FC0`.
- The exact vtable is `0xF30134`. Its relevant methods are factory `0x5EB310`,
  codec `0x5E6DE0` and class-specific consumer `0x5EFAF0`.
- Generic pool/prototype paths at `0x5E9C1B..0x5E9C49`,
  `0x5E9CA9..0x5E9CCA` and `0x5EEC16..0x5EEC43` allocate or initialize the
  0x1C-byte object. They are construction infrastructure, not proof of a UI
  producer.
- Codec `0x5E6DE0` symmetrically reads/writes, in order:
  1. object `+0x14`, four bytes, wire tag `0x14`;
  2. object `+0x18`, one signed/raw byte, wire tag `0x08`;
  3. object `+0x19`, one signed/raw byte, wire tag `0x08`.
- Consumer `0x5EFAF0` sign-extends `+0x19`, decrements it, sign-extends `+0x18`,
  loads raw `+0x14`, and calls `0x5C5080` on client state
  `0x1093198 + 0x4E0` with logical arguments `(raw +0x14 u32,
  signed +0x18, signed +0x19 - 1)`. It then returns true. This proves the exact
  transformation and call structure, not the meanings of the arguments.
- The registration, getter, vtable, construction, codec and consumer bytes are
  identical in exact `GameClient.bin` and `GameClient.local.bin` profiles.

## Inference and bounded negative

The class name and client-state call support a hotkey-setting protocol role, but
no direct UI setter/factory/submission chain was recovered. No exact save/load or
StartGame attachment path reaches this class or the target state object. Named UI
strings such as `HotKeyMappingTable` are not a dataflow proof.

## Hypothesis D

One or more raw fields may identify a position and an assigned object category,
but neither that mapping nor an item/skill discriminator is established.

## Nonclaims and stop rule

Do not name `+0x14`, `+0x18` or `+0x19`; do not synthesize this vital; do not add
hotkey state to StartGame; and do not claim item/skill ownership, persistence,
cooldown, casting or combat behavior. Resume only after an exact UI producer and
submission edge, or a natural observe-only occurrence. Persistence additionally
requires an exact save/load/reconnect path.
