# JOB-001 — CHARCREATE_CLASS static boundary

Date: 2026-08-16  
Classification: Grade A exact static table/codec proof plus a bounded
field-identification negative

## Primary claim

The client has an exact named `CHARCREATE_CLASS` registry for character-creation
presets. The current evidence does not identify any persistent job/class selector
in CreateActor, AvatarAttr, ActorAttr, Character List or StartGame.

Relevant code was checked against the exact original client
`C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
and endpoint-patched local client
`9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.
The frozen CONSTDATA input is 8,443,000 bytes with SHA-256
`496DFB2EF2CF517482A7B426C9DD5EDF0278564FE11195B96F36DF90607F0D2D`.

## Exact table boundary

- UTF-16 `CHARCREATE_CLASS` is at `0xF0C650`.
- The data manager at `0x108CDD0` resolves it through `0x890EF0`.
- Character-create UI path `0x4BD8EF` stores the table pointer at UI object
  `+0x1C4`; `0x4BD959` derives row count from the table pointer vector at
  `+0x64/+0x68`.
- The table contains five `n_ID` rows: `1`, `2`, `4`, `16` and `32`, plus 37
  other named columns for creation-preset icons, appearance, equipment and
  `s_SKILL_*` strings.
- Bounded client-image scanning found no standalone named `JOB` or `PROFESSION`
  registry. Other `CLASS` strings are not promoted because they belong to
  unrelated UI/content tables.

## Exact wire boundary

CreateActorDataEx codec `0x5DFF60` structurally carries object bytes `+0x18`,
`+0x19` and `+0x1A` as u8 values before later fields. Embedded AvatarAttr begins
at object `+0x60` and uses codec `0x464560`; its masked u32 range includes object
`+0x2C..+0x58` and later typed fields, all of which remain semantically opaque.

The exact original CreateActor `test01` capture has values `+0x18=0`, `+0x19=1`,
`+0x1A=1`. Its embedded AvatarAttr contains chest `2300026`, leggings `2300027`
and both weapon slots `2200002`. Those four equipment values numerically match
`CHARCREATE_CLASS` row 1 starter columns.

The numeric agreement supports the inference that the captured preset-derived
appearance/equipment came from row 1. It is not an exact dataflow proof and does
not identify a stored class selector. Most importantly, CreateActorDataEx
`+0x18=0` differs from matching preset key `1`, so that byte cannot be named class
from this evidence.

## Evidence ceiling and stop rule

No exact `CHARCREATE_CLASS.n_ID` setter or copy edge into a CreateActor, AvatarAttr
or ActorAttr field was recovered. No exact named-class lookup consumes a specific
field later in Character List, Select or StartGame. A separate field may preserve
the preset key, or the client may reconstruct a preset from appearance/equipment;
both remain hypotheses.

This checkpoint proves no job/class field, profession progression, skill
entitlement, class persistence or semantic meaning for opaque Avatar bytes.
`s_SKILL_*` strings are creation-preset data, not StartGame skill ownership.

Preserve all current Avatar bytes losslessly and keep them opaque. Do not
synthesize a class value. Resume only when an exact setter/copy chain connects a
named registry key to one wire offset and a corresponding List/StartGame consumer,
or when a natural observe-only trace is designed from such a proven setter.
