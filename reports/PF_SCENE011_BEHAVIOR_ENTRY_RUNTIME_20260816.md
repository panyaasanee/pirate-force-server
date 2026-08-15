# SCENE-011 — Natural BEHAVIOR entry observation

Date: 2026-08-16

## Primary claim

One checksum/PE/code/ASLR-guarded observe-only run captured exact natural
non-null and null results from BEHAVIOR singleton `0x102DAD8` at lookup
`0x702A10`. Five non-null result events expose only source-proven entry fields and
the proven hit-keyframe vector bounds; four miss events prove null only at their
individual lookup instants. The probe wrote no client memory, input or packet.

This checkpoint is instrumentation evidence, not a gameplay response. No
CHitResult was observed or sent.

## Static boundary (grade A)

The exact manager chain remains `0x4162A0 -> 0x47BFC0 -> 0x491650`, table
`BEHAVIOR`, row `n_ID` stored at entry `+0x04`, with lookup `0x702A10`. The probe
filters entry ECX against the ASLR-adjusted address of singleton `0x102DAD8` before
recording either result or miss.

Recorded dwords retain only their source property names:

- `+0x2C n_AMOUNT_TARGET`
- `+0x30 n_RANGE`
- `+0x34 n_DAMAGE_AREA`
- `+0x38 n_PROFIT`
- `+0x3C n_THENDO`
- `+0x7C n_CLASS`

The object at `entry+0xE4` is a vector member constructed by `0x48C900` and fed by
the `s_HIT_KEYFRAME`/`s_HITBACK` parser `0x48F8F0`; begin/end are at
`+0xF0/+0xF4`, and `0x48D870` proves element stride `0x38`. The probe records only
object address, bounds and count. It does not dereference or interpret a vector
record.

Static caller `0x48D2C8` is the return from a `0x702A10` call in function
`0x48D270`; null returns immediately through that function's null lane, while a
non-null entry is tested at entry `+0x24` before later object construction. This
does not identify the function as attack, hit or damage behavior.

Static caller `0x7555D2` follows a loop that obtains a raw key from an iterated
object at `object+0x08`, calls `0x4162A0` then `0x702A10`, and, when non-null,
compares/loads source-named entry field `n_RANGE` at `+0x30`. The collection and
the meaning of those comparisons remain opaque.

## Accepted runtime trace (grade C)

Accepted artifact:
`GameClient/capture_behavior_entry/scene011_behavior_entry_miss_world_20260816_033300.jsonl`.
The exact local client loaded at base `0x00CC0000`; lookup runtime address was
`0x00FC2A10`, and BEHAVIOR manager runtime address was `0x018EDAD8`. The capture
contains one `probe_ready` followed by nine strictly increasing events on thread
16604, no `probe_error`; process exit was zero and stdout/stderr were empty.

- Sequence 1, key 97, caller live `0xD4D2C8` / static `0x48D2C8`: non-null entry;
  `n_AMOUNT_TARGET=0`, `n_RANGE=10`, `n_DAMAGE_AREA=0`, `n_PROFIT=0`,
  `n_THENDO=0`, `n_CLASS=0`, vector count 0.
- Sequences 2 and 6, key 60029 (`0xEA7D`), caller live `0xD0E92A` / static
  `0x44E92A`: null at those exact instants.
- Sequences 3 and 7, key 0, caller live `0x10155D2` / static `0x7555D2`: null at
  those exact instants.
- Sequences 4 and 8, key 278, caller static `0x7555D2`: the same non-null entry
  pointer, `n_AMOUNT_TARGET=1`, `n_RANGE=75`, `n_DAMAGE_AREA=200`, `n_PROFIT=0`,
  `n_THENDO=278`, `n_CLASS=0`, vector count 1.
- Sequences 5 and 9, key 279, caller static `0x7555D2`: the same non-null entry
  pointer across both observations, with the same recorded values as key 278 and
  vector count 1.

`n_DAMAGE_AREA=200` is only the exact source-named property value. It is not proof
of damage, HP mutation, radius units, target selection or any executed effect.

## Paired operational evidence

The paired server root is
`GameClient/capture_port_royal_fish_p60_ea7d_ack_20260816_032950`. During the
accepted probe window the client sent an ActionVital carrying `0xEA7D` and target
`0x203D`, but no TargetVital wire occurred in the run. The strict SCENE-007 gate
therefore sent no acknowledgement. This run does not test an inbound EA7D response
or CHitResult ordering. Heartbeats continued, server/guard stderr were empty, and
the database main/WAL/SHM guard returned `PASS_UNCHANGED`.

Two earlier attempts are superseded timing diagnostics, not acceptance inputs:

- `scene011_behavior_entry_port_royal_20260816_031900`: pre-miss-schema probe was
  ready but emitted no non-null entry and exited 1 under `--require-entry`.
- `scene011_behavior_entry_miss_port_royal_20260816_033000`: miss-capable probe was
  ready but expired before the world action, emitted no lookup event and exited 1
  under `--require-lookup`.

Their JSONL, stdout, stderr and exit sidecars are retained and hashed in the
manifest because they are mentioned here.

## Evidence ceiling and stop rule

Proven: exact natural BEHAVIOR lookup results at the recorded callers and instants;
exact source-named dwords for keys 97, 278 and 279; vector counts 0/1; repeated
instant-scoped null results for keys EA7D and 0; client/server health and unchanged
database state.

Not proven: permanent key absence; a ScriptB stem binding; the semantic role of
keys 97/278/279; attack animation; hit/miss; actual damage, HP or FightAttr; vector
record contents; CHitResult production, consumption or ordering; AI, death, loot,
skills or authentic faction.

Do not synthesize BEHAVIOR entries and do not send CHitResult/HP/UpdateAttr/
FightAttr from this checkpoint. The next evidence-first boundary must observe a
natural consumer of one captured non-null entry or a natural CHitResult correlated
to a data-bound key. Stop after one bounded run if neither occurs; do not infer a
packet from the source property values.
