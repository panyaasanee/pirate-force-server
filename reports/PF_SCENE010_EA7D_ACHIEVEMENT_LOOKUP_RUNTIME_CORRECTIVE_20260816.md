# SCENE-010 — EA7D ACHIEVEMENT-registry lookup corrective

Date: 2026-08-16

## Claim

This corrective supersedes the earlier “numeric action-data” label. Exact static
population proof identifies `0x702A10` as the ACHIEVEMENT-registry lookup. The
historical raw JSONL path, filename and `numeric_lookup_result` event name are
retained unchanged as immutable evidence; that event name is semantically generic.

Exact static client proof and one checksum/code-guarded observe-only runtime trace
show that the ACHIEVEMENT registry is queried with key `0xEA7D` on both a
producer/control path and the inbound ActionVital acknowledgement path. All three
observed `0xEA7D` lookups returned null in this session.

The inbound null result skips one exact `n_LEVEL`-bit-7 branch while generic action
construction and queueing can still continue. It does not explain missing animation
or prove action metadata, combat or damage behavior. Why these action paths query
the achievement registry remains unknown.

## Static provenance

The exact numeric lookup is `0x702A10`, a `thiscall` over the ACHIEVEMENT registry
whose sole raw key is the u32 stack argument and whose result is the returned entry
pointer. The guarded probe observes only this boundary and records the caller,
key and return value without dereferencing the entry or writing memory, input or
packets. Singleton `0x4162A0` owns global registry object `0x102DAD8`.

Population function `0x705000` obtains `ACHIEVEMENT` and `ACHIEVEMENT_TIP` from
data manager `0x108CDD0` through `0x890EF0`. Rows come from the source-table vector
at `+0x64/+0x68`; `0x88FA20` selects a row, and `[row+0x14]` supplies its dword key.
An `0x84`-byte entry constructed by `0x703AF0` receives that key at `+0x04`.
`0x704E30` inserts the key into the ordered map at registry `+0x04`, and `0x703D10`
stores/refcounts the entry pointer in the map node.

Exact named entry fields include `+0x20=n_TYPE`, `+0x24=n_POINTS`,
`+0x28=n_LEVEL`, `+0x2C=n_REWARD_ITEM`, `+0x30=n_ITEMQUANTITY`,
`+0x34=f_REWARD_EXP`, `+0x38=f_REWARD_SP`, `+0x3C=f_REWARD_MONEY`,
`+0x40=n_REWARD_TOKEN`, `+0x44=n_REWARD_GREATTITLE`, and
`+0x48=n_BROADCASTING`; strings at `+0x4C/+0x68` come from the tip table. No
ScriptB load or stem-to-key binding occurs in this population path.

Producer/control function `0x44E890` calls the achievement lookup at `0x44E925`, returning to
`0x44E92A`. A null result follows its default-initialization lane; a non-null entry
with `n_LEVEL` bit 7 set takes a different lane. The function later contains
an exact `0xEA7D` branch and can call generic ActionVital producer `0x44D260`.
The two observed null lookups at this callsite do not prove two packets or explain
why the function invoked the lookup twice.

Inbound ActionVital handler `0x7516C0` calls the same lookup at `0x7517B0`, returning
to `0x7517B5`, using ActionVital field `+0x30` as the key. A null result still permits
generic constructor `0x47AB30` and actor queue path `0x4843F0`; it skips the later
`n_LEVEL`-bit-7 virtual-call branch. Static proof does not establish why an action
path consults achievement level or the semantic meaning of that branch.

Natural keys 278 and 279 returned non-null achievement entries at caller
`0x7555D2`. That callsite aggregates exact `n_ITEMQUANTITY` at entry `+0x30`; these
remain natural achievement controls with no promoted action, animation or combat
meaning.

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

Proven at grade A static plus grade C instrumented runtime: the exact ACHIEVEMENT-
registry population/lookup boundary, two producer/control lookups and one acknowledgement-
consumer lookup for `0xEA7D`, all returning null in this session. The consumer null
result skips the exact `n_LEVEL`-bit-7 branch while the generic action path remains
available. The prior action-data label and missing-animation explanation are retired.

Not proven: why action paths query the achievement registry, that no metadata for
`0xEA7D` exists elsewhere, any action/ScriptB binding, visible animation,
implementation execution, hit/miss, damage or HP mutation, range/cooldown,
FightAttr, CHitResult ordering or payload, AI, death, loot, skills, or authentic
player faction. Do not synthesize or insert an `0xEA7D` achievement entry and do not
send CHitResult, HP, UpdateAttr or FightAttr from this checkpoint.

The next safe boundary is read-only provenance for a named achievement
trigger/update consumer that explains these action-code-indexed lookups. It must not
mutate the registry or invent a response packet.
