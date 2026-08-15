# SCENE-010 — EA7D BEHAVIOR-registry lookup corrective

Date: 2026-08-16

## Corrected claim

Exact static identity and population proof establishes that singleton
`0x102DAD8` and lookup `0x702A10` belong to the client `BEHAVIOR` registry. The
intervening ACHIEVEMENT interpretation is superseded: it followed unrelated
population function `0x705000`, whose manager is a distinct singleton at
`0x102DB68`.

Historical raw JSONL paths and generic event name `numeric_lookup_result` remain
unchanged. One checksum/code-guarded observe-only runtime trace recorded key
`0xEA7D` returning null twice on a producer/control path and once on the inbound
ActionVital acknowledgement path. Those null results are facts only at the three
captured instants.

## Exact static provenance (grade A)

- Lazy accessor `0x4162A0` passes global object `0x102DAD8` to constructor
  `0x47BFC0`.
- `0x47BFC0` preserves the same `this`, calls base `0x491CB0`, installs vtable
  `0xF0F798`, restores `this`, and calls population function `0x491650`.
- `0x491650` obtains UTF-16 table `BEHAVIOR` from data manager `0x108CDD0` through
  `0x890EF0`, iterates source vector `+0x64/+0x68`, selects rows with `0x88FA20`,
  reads `n_ID` with `0x891EE0`, constructs an `0x12C`-byte entry with `0x48C900`,
  and stores `n_ID` at entry `+0x04`.
- `0x702A10` is a `thiscall` over the ordered map at manager `+0x04`. Its sole raw
  u32 argument is the key; it returns the stored entry pointer or null.

Named row inputs include `s_CONDITION`, `n_AMOUNT_TARGET` (`+0x2C`), `n_RANGE`
(`+0x30`), `n_DAMAGE_AREA` (`+0x34`), `n_PROFIT` (`+0x38`), `n_THENDO`
(`+0x3C`) and `n_CLASS` (`+0x7C`). Exact parsers cover `s_ANIMATION`,
`s_FXS_CASTING`, `s_PHASING`, `s_ROTATE`, `s_HIT_KEYFRAME`, `s_HITBACK`,
`s_EMIT_KEYFRAME`, `s_CAST_POSTPROCESS` and `s_HIT_POSTPROCESS`.
`s_HIT_KEYFRAME`/`s_HITBACK` parser `0x48F8F0` accesses entry vector `+0xE4`;
its begin/end are `+0xF0/+0xF4`. Reaction factory `0x48D870` consumes that same
vector with exact `0x38`-byte record stride.

The unrelated ACHIEVEMENT chain is independently fixed: accessor `0x417380`
passes global `0x102DB68` to `0x416320`; that constructor calls `0x705620`,
installs vtable `0xF0A8B8`, then calls `0x705000`. Thus ACHIEVEMENT fields such as
`n_LEVEL` and `n_ITEMQUANTITY` belong only to that separate manager and do not
describe BEHAVIOR singleton `0x102DAD8`.

Producer/control function `0x44E890` calls `0x702A10` at `0x44E925`, returning to
`0x44E92A`. Inbound ActionVital handler `0x7516C0` calls it at `0x7517B0`,
returning to `0x7517B5`, with ActionVital field `+0x30` as key. Null does not
prevent generic constructor `0x47AB30` or actor queue `0x4843F0`.

CHitResult reaction factory `0x48D870` receives behavior ID from CHitResult
`+0x22` and selector from `+0x28`. It calls this same `0x702A10`; missing entry
takes fallback `0x48AE40`, whose CHitResult-supplied fallback argument is literal
zero. Composing that exact factory flow with an observed null predicts a null
implementation for the same key and loaded registry state. This is an A+C
compositional inference, not an observed CHitResult invocation.

## Runtime evidence (grade C)

The accepted probe attached to exact `GameClient.local.bin` at base `0x00CC0000`
and emitted one `probe_ready` plus 228 strictly sequenced
`numeric_lookup_result` events, no `probe_error`, exit zero, empty stdout/stderr.
For raw key 60029 (`0xEA7D`) on thread 23420:

- sequences 1 and 11 returned null from live caller `0xD0E92A`, static return
  `0x44E92A`;
- sequence 228 returned null from live caller `0x10117B5`, static return
  `0x7517B5`.

The paired server capture fixes hostile P60 TargetVital `0x203D` kind 1,
ActionVital request `0xEA7D`/target `0x203D`, and exact SCENE-007 ACK. The consumer
lookup occurred 18 ms after the ACK. Heartbeats continued, the client remained
responsive until controlled close, and database main/WAL/SHM returned
`PASS_UNCHANGED`.

Immutable accepted and diagnostic artifacts remain under historical
`GameClient/capture_action_data_binding/` names recorded in the manifest. Those
names are retired labels, not current semantic claims.

## Evidence ceiling and stop rule

Proven: exact BEHAVIOR registry identity/population/lookup, exact caller returns,
and three instant-scoped null observations for `0xEA7D`. The prior ACHIEVEMENT
correction is superseded.

Not proven: `0xEA7D` absence at every time or in every data set; an exact ScriptB
stem-to-`n_ID` binding; visible animation; CHitResult invocation or ordering;
selector/record provenance; hit, miss, damage, HP, FightAttr, AI, death, loot,
skills or authentic faction.

Do not synthesize a BEHAVIOR row and do not send CHitResult, HP, UpdateAttr or
FightAttr. The next safe boundary is observe-only capture of natural BEHAVIOR
population/lookup data and, if naturally present, correlation with a CHitResult
whose behavior ID, selector and record fields are all observed. Stop if no natural
CHitResult or non-null data-bound behavior lookup appears within one bounded run.
