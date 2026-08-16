# COMBAT-KNOCK-001/BIND — CKnockdown static consumer checkpoint

Date: 2026-08-16  
Classification: Grade A exact static registration, codec and consumer proof;
bounded direct-writer negative; no runtime or packet experiment

## Primary claim

The class-specific `CKnockdownVital` consumer resolves one receiver actor and uses
raw object `+0x20` as a BEHAVIOR lookup key. A successful lookup constructs an
inner implementation and wraps it in an object with vtable `0xF0F7DC` and flags
`0x40000005`. Wrapper bit `0x40000000` selects the resolved actor's `+0x40`
queue lane; the queue call receives a separate argument `1`.
This proves an actor-scheduler boundary only. It does not prove a visible
knockdown, animation, hit or combat result.

## Grade A static facts

- `CKnockdownVital` is registered at `0xC0C1E0`; its deterministic class-name
  hash/ID is `0x3123`, stored at `0x108A2F0`. Its vtable is `0xF48A7C`, factory
  `0x74F540`, codec `0x74EBF0`, and class-specific consumer `0x750700`.
- The codec carries, in order, raw qword `+0x18`, u32 `+0x20`, u32 `+0x24`, a
  nested three-float structure at `+0x28/+0x2C/+0x30`, and float `+0x34`.
  These offsets have no promoted gameplay names.
- Consumer `0x750700` resolves the qword `+0x18` through `0x402A20 -> 0x446170`.
  The resulting object is only proven to be the receiver actor for this lane. A
  null actor or null actor implementation returns true without submission.
- The consumer forwards nested floats `+0x28/+0x2C` to `0x4845A0` and stores
  `+0x30` in the receiver implementation at `+0x18`. No field meaning is proven.
- `0x4162A0` returns the BEHAVIOR manager. Its vtable `0xF0F798` slot `+0x0C`
  resolves to concrete function `0x47CAD0`. The call receives receiver actor,
  float `+0x34`, u32 `+0x20`, and u32 `+0x24`.
- `0x47CAD0` discards the float `+0x34`. It passes `+0x20` to `0x48D270`, whose
  exact `0x48D2C3 -> 0x702A10` call uses it as the BEHAVIOR lookup key. Raw
  `+0x24` is stored at inner implementation `+0x50`; its meaning remains opaque.
- Null receiver input, null BEHAVIOR lookup, or failure of the actor-side object
  resolution inside `0x48D270` returns null.
- On success `0x47CAD0` allocates a `0x28`-byte wrapper through `0x442D50` at
  `0x47CB28`, initializes it through `0x486F90` at `0x47CB42`, then overwrites
  its vtable with `0xF0F7DC`. The wrapper has flags `0x40000005`, stores the
  inner implementation at `+0x20`, and stores
  the raw `+0x20` key at wrapper `+0x24`. Wrapper bit `0x40000000` makes
  `0x750761 -> 0x4843F0` select the receiver actor `+0x40` lane. The downstream
  `0x4A0C90` queue invocation receives a separate argument `1`.
- The relevant codec, consumer and concrete factory spans are byte-identical in
  the exact original and local client profiles.

## Bounded negative and nonclaims

Direct/static xrefs expose registration, generic pool/prototype construction,
factory/codec dispatch and the virtual consumer, but no non-framework producer or
writer that assigns all `CKnockdownVital` fields. This is a bounded direct-writer
negative, not proof that an original server producer does not exist.

No exact dataflow copies EA7D, natural BEHAVIOR keys 278/279, or CHitResult state
into `CKnockdownVital +0x20`. Inbound ActionVital independently looks up its own
`+0x30` value, exact EA7D in the accepted shape. No HP, FightAttr or UpdateAttr
access/mutation occurs in this consumer. The class name supplies role provenance
only; it does not authorize field semantics, visible animation, knockdown,
performer/target labels, ordering, payload construction or a packet experiment.

SCENE-013 remains only a bounded corpus-capability result and is not static
consumer exhaustion.

## Stop rule

Do not synthesize this vital or its fields. Resume only with a lawful original
server-to-client payload or an exact producer/dataflow that assigns every field
and establishes ordering. Any later runtime work must remain a separate milestone
with its own evidence claim.
