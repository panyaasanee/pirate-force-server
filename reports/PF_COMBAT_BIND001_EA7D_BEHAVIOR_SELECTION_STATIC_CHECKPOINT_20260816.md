# COMBAT-BIND-001 — EA7D BEHAVIOR selection checkpoint

Date: 2026-08-16  
Classification: Grade A exact static proof composed with bounded Grade C
SCENE-011 observations; no runtime or packet experiment in this checkpoint

## Primary claim

The EA7D geometric gate selects a scalar from a natural BEHAVIOR candidate list.
In the accepted SCENE-011 order, key 278 supplies scalar 75 and equal-valued key
279 is skipped. Only scalar 75 survives downstream; neither candidate identity is
copied into inbound ActionVital, whose independent BEHAVIOR lookup key remains
the ActionVital `+0x30` value EA7D.

## Grade A static facts

- `0x44E98A` recognizes EA7D. The gated command path reaches
  `0x44EB1D -> 0x4758D0` and, on true, calls producer `0x44D260` at `0x44EB49`.
- The pre-gate lookup `0x44E91D -> 0x702A10` uses action code `EBX` itself.
- The EA7D gate begins with current-actor raw byte
  `[0x1032EC4]+0x348+0x18C`. `0x5DEBB0` bounds it and indexes fixed raw tables
  `0x1025494/0x1025498`; the two resulting opaque dwords pass through
  `0x46CFE0 -> 0x46C8A0` and are OR-combined. No named item or container lookup
  occurs in this chain.
- `0x755540` mode 0 resolves a candidate collection, reads each candidate key at
  pointed object `+0x08`, and looks it up through BEHAVIOR at
  `0x7555CD -> 0x702A10`. It retains the first non-null `n_RANGE` at `+0x30`;
  later values greater than or equal to the current value are skipped by
  `0x7555E4..0x7555EB`. It returns only the selected integer through x87 at
  `0x75562C`; the candidate key is not returned or copied downstream.
- `0x475A52/0x475A8F` adds that integer to another live scalar and uses the result
  in the strict squared-distance comparison. This does not preserve candidate
  identity.
- The inbound ActionVital path independently loads object `+0x30` at `0x7517A5`
  and supplies it to BEHAVIOR lookup `0x7517B0 -> 0x702A10`; return is
  `0x7517B5`.
- Relevant code spans are byte-identical in exact original and local binaries.

## Grade C composition

Accepted SCENE-011 observed candidate lookup order `0` (null), `278` (non-null),
`279` (non-null), with keys 278 and 279 both carrying raw `n_RANGE=75`. Combined
with the exact mode-0 logic, key 278 sets the retained 75 and equal key 279 is
skipped. The same run observed the separate EA7D pre-gate lookup as null. The
accepted ActionVital shape carries EA7D at `+0x30`.

## Bounded negative and nonclaims

Only scalar 75 survives the selector, so it cannot encode or bind candidate key
278 versus 279 to inbound ActionVital. Captured creation value 2200002 has zero
literal occurrences in either exact client image and no dataflow into this chain;
it is not proven equipped, owned, weapon-related or a BEHAVIOR key. No equipment,
weapon type, candidate semantics, attack success, hit, damage, HP, FightAttr or
persistence claim is established.

## Stop rule

Do not echo 278/279, add BEHAVIOR rows, alter ActionVital, synthesize CHitResult,
HP or FightAttr, or add hooks/packets on this lane. Resume only if an exact named
item/container source reaches the actor raw byte or candidate key and continues
through a preserved identity-bearing consumer boundary.
