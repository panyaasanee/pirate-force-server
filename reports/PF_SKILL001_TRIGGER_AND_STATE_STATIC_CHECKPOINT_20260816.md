# SKILL-001 — Trigger and state static checkpoint

Date: 2026-08-16  
Classification: Grade A exact static proof plus instrumentation readiness; no
runtime result

## Primary claim

The client registers a class named `TriggerCastSkillVital`, provides an exact
three-field codec, and has a bounded conditional construction/submission consumer.
This establishes a protocol observation boundary.
It does not prove that the current player owns, equips or successfully casts a
skill.

The proof was repeated against the exact original client
`C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
and local endpoint-patched client
`9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.

## Trigger protocol boundary

- Class registration at `0xBF1130` stores the registered ID in `0x108284C`;
  deterministic class-name hashing gives `0x5CD2`.
- The exact class vtable is `0xF3175C`.
- Codec `0x600A60` reads or writes, in order, object `+0x14 u16`, `+0x16 u8`
  and `+0x18 u32`. These names are deliberately raw offsets/types.
- Consumer `0x601810` first checks singleton `0x1032EC4`. When it is null, the
  consumer skips allocation, construction and submission. When it exists, the
  consumer allocates a 0x38-byte candidate, calls constructor `0x452FF0` only if
  allocation succeeded, and submits the resulting candidate (including null on
  allocation failure) only at exact edge `0x601880 -> 0x449110`. Every branch
  converges on boolean true at `0x601885`.
- Direct-call analysis finds only factory/default/prototype construction, virtual
  codec and virtual consumer paths. It found no exact local UI, hotkey or hotbar
  producer. This is bounded direct-call evidence and does not exclude an indirect
  generic-registry producer.

The committed `pf_skill_trigger_probe` is observe-only. It guards exact hashes,
PE fields, code bytes and the single accepted ASLR relocation, confines output to
`GameClient/capture_skill_trigger`, and correlates codec/consumer/submission events
by object, thread, invocation and live hook address. Focused tests passed 7/7; the
full verifier passed 115 tests plus deterministic release verification; independent
review passed after requiring host-side exact event-address validation. The probe
has not been run live, so there is no natural direction, caller or value result.

## Skill state boundary

`CSkillAttr` is separately registered at ID/hash `0x1661`. Its exact codec writes
a u16 count and repeated records `(u16,u16,u32)`. The first value is proven only
as the ordered record key; the other values remain opaque u16/u32 payloads.
Explicit count zero is valid, and aggregate code accepts the attr being absent.
Therefore the accepted StartGame omission remains valid and unchanged.

`CLearnSkillResultVital` mode zero clears and repopulates this container from three
parallel positional vectors. `CRevertSkilltVital` removes a record with the same
ordered key. These named-class consumers support state-management provenance, not
field meanings such as skill ID, level, rank or entitlement.

## Cooldown boundary

`CStartCooldownVital` is separately registered at ID/hash `0x4DDA`. Its exact codec
contains a u16 count followed by raw records `(s16,f32)`. Its consumer updates a
separate `CCooldownAttr` map. Static tracing found no exact dataflow from this key
to `CSkillAttr` or to any of the three TriggerCast fields; equal integer widths are
not a binding.

## Evidence ceiling and stop rule

This checkpoint proves static class, codec, container and consumer boundaries only.
It does not prove job/class mapping, skill ownership, learning entitlement, hotbar
placement, resource cost, cooldown duration/time units, successful cast, animation,
attack, hit, damage, HP change, persistence or reconnect behavior.

Do not add `CSkillAttr`, `CCooldownAttr` or `TriggerCastSkillVital` to StartGame and
do not synthesize any of these packets. Resume this lane only when an observe-only
natural codec/consumer occurrence fixes direction and raw values, or when an exact
named producer/table binding fixes the missing semantics.
