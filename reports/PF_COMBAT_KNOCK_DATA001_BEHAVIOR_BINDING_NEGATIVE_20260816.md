# COMBAT-KNOCK-DATA-001 — BEHAVIOR binding negative

Date: 2026-08-16  
Classification: Grade A exact frozen-data and static-path audit, composed with
bounded Grade C structural observations; no runtime or packet experiment

## Primary claim

The guarded frozen BEHAVIOR table does not uniquely bind any named row to
`CKnockdownVital +0x20`. Rows 278/279 and rows whose source strings contain
`KNOCK` or non-empty `s_HITBACK` are catalog facts only. No exact producer or
dataflow copies any of those row IDs into the vital. Asset-name mining on this
lane is stopped.

## Artifact provenance

- The current packed client asset
  `C:\Users\Panya\Desktop\Pirate Force\GameClient\Data\B_CONSTDATA_TH.pc_`
  is 426,944 bytes with SHA-256
  `496B5C7B5A7F4C1AB5E343937CA7278B3DB5B4501250CAA7DA47F22DC2C9C3F8`.
  It is a separate artifact and was not parsed for this checkpoint.
- The exact expanded input is
  `backups/v103_one_item_backpack_20260814_103143/derived/v97_mapping_audit/B_CONSTDATA_TH.pc_.dec`,
  8,443,000 bytes, SHA-256
  `496DFB2EF2CF517482A7B426C9DD5EDF0278564FE11195B96F36DF90607F0D2D`.
- The v104 expanded copy at
  `backups/v104_item_operate_capture_20260814_111326/derived/v97_mapping_audit/B_CONSTDATA_TH.pc_.dec`
  has the same exact size and SHA-256.
- The read-only parser is
  `backups/v103_one_item_backpack_20260814_103143/derived/v97_mapping_audit/parse_pc_tables.py`,
  4,602 bytes, SHA-256
  `C5333381EB6319F22C75DE8D4100CB6D15B529C9D58606384BC8D1094FBD6AD6`.
  Its audit inventory
  `const_high_value_tables.txt` is 13,906 bytes, SHA-256
  `9350F1123500A5F2B144D46AA7F751F189989ACBBD60093226581CF9B012616B`.
  It places BEHAVIOR at `0x6A622..0x110B0C`, with 2,279 rows and 30 columns.

The packed and expanded files have different size/hash provenance and are not
interchangeable claims.

## Grade A facts

- BEHAVIOR row 278 contains raw source values `n_RANGE=75`, `n_CLASS=0`,
  `n_THENDO=278`, `n_AMOUNT_TARGET=1`, `n_DAMAGE_AREA=200`,
  `f_DAMAGE_PHYSICS=10`, `s_ANIMATION=_C_ATTACK_000;28`,
  `s_ANIMATION2=_C_ATTACK_000;28`, `s_HITRATE=HIT(100)`,
  `s_HIT_KEYFRAME=S_H_PHYSICS_PUNCH;0;12`, and empty `s_HITBACK`.
- Row 279 has the same listed raw numeric values and `n_THENDO=278`, but its
  source strings are `s_ANIMATION=_C_ATTACK_001;26`,
  `s_ANIMATION2=_C_ATTACK_001;26`, and
  `s_HIT_KEYFRAME=S_H_PHYSICS_PUNCH;0;16`; `s_HITBACK` is empty.
- Across all rows, 10 row IDs have a source string containing `KNOCK`:
  `71,72,307,308,309,310,311,317,7120,8014`. Separately, 106 rows have
  non-empty source column `s_HITBACK`. Zero row source strings contain
  `REACTION`.
- Concrete path `0x750700 -> 0x47CAD0 -> 0x48D270 -> 0x702A10` uses raw vital
  `+0x20` as the BEHAVIOR lookup key. Raw `+0x24` is stored at inner
  implementation `+0x50`; float `+0x34` is discarded by `0x47CAD0`.
  Neither `+0x24`, `+0x34`, nor receiver actor state selects a table row in this
  path.
- `0x48D270` consumes fields and the source-populated vector of the row selected
  by the already supplied key; it does not derive that key from row strings.
- Direct/static xrefs expose framework registration, codec/factory paths and the
  class-specific consumer, but no non-framework producer or writer assigning
  all CKnockdown fields. No exact row/key reference flows backward into vital
  `+0x20`.

## Grade C composition and inference ceiling

Accepted SCENE-011 observed natural non-null BEHAVIOR entries 278/279 with
`vector_count=1`. This is structural count provenance only: the probe did not
dereference or name vector records. The table's source column names and strings
can identify catalog candidates, but without a writer or original payload they
cannot establish a reaction, knockdown, animation, hit, damage, target or packet
meaning. An indirect or original-server producer remains possible despite the
bounded direct-writer negative.

## Nonclaims and stop rule

This checkpoint does not authorize a CKnockdown payload, any row ID, ordering,
animation, hit, damage, HP, FightAttr, UpdateAttr, target/performer semantics or
runtime probe/experiment. Rows 278/279 are not CKnockdown values merely because
they were natural BEHAVIOR entries, and rows containing `KNOCK`/`s_HITBACK` are
not selected candidates merely because of asset names.

Stop further asset-name mining. Resume only from a lawful original
server-to-client CKnockdown payload or an exact producer that assigns every vital
field and establishes its ordering. Then, and only then, compare the observed
`+0x20` key with the guarded BEHAVIOR table.
