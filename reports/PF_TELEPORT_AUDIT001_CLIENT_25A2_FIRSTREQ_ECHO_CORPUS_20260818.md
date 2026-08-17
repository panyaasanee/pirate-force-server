# PF TELEPORT_AUDIT001 — Client-sent TeleportVital 0x25A2 is a fixed, target-less first-Req echo; no server change is warranted (2026-08-18)

**One claim.** In every captured GameClient session of the corpus (14/14 sessions
across 11 capture runs, rounds r17–r23, 2026-08-17), the client sends
`TeleportVital 0x25A2` version 4 **exactly once**, always as the **first vital of
its first `GSCN_RunTimeProtocolReq`** (`frame=4`), between 3 ms and 1.2 s after
the server's login TeleportVital. Its 11-byte payload is **byte-identical in all
14 sessions** and matches the server's outbound TeleportVital schema with the
target count set to 0 (no target object). The foundation's generic
`RUNTIME_RES_ACK_FIRST_REQ` already answers the bundle and no session stalls.
**Decision: audited, no hypothesis opened; no server change is warranted.**
Grade B: wire corpus + schema cross-reference; no client-observable claim, no
binary handler trace of the client's send site.

## Payload decode (client → server, nested in RunTimeProtocolReq v0 mask 0x02)

```
12 A2 25   u16  msg_id       0x25A2 TeleportVital
0B 04      u8   version      4
0B 02      u8   field A      2       (same value the server sends outbound)
0B 00      u8   target count 0       (server outbound sends 1 + one target object)
0B 00      u8   flag         0
0B 00      u8   flag         0
0F 00 00   u16  trailer      0
```

Cross-reference (server outbound, frozen v141 `make_login_teleport` /
`make_teleport_target`, serializer 0x5DF250): `0B 02 | 0B 01 | u16 SceneID,
u64 SceneSeq, u8, u8, vec3 | 0B 00 | 0B 00 | 0F 00 00`. The client echo is the
identical schema minus the target object. Reading it as "teleport
acknowledged/arrived" is plausible but **remains a nonclaim** — no counterfactual
session without a server teleport exists in the corpus.

## Corpus (read-only sweep, reproduce with `pf_bridge/replay/pf_teleport_audit.py`)

Two distinct first-Req bundles, both with `count=4` vitals; the 0x25A2 slice is
identical in both — the variants differ only in the *other* vitals:

| Bundle | PC len | Sessions | sha256 | Vitals in order |
|---|---|---|---|---|
| A | 190 B | 13 | `D8C610269F1E99DD48FD684BECC211308EFAE92BBD2DD7ECD0A385ADAA841C79` | TeleportVital 0x25A2 · AskForSystemGiftVital 0x8B93 · UpdateServerSettingVital 0x0F01 · TargetPosVital 0x2A90 |
| B | 95 B | 1 (r22_replay, post-movement-replay session) | `CA3BD8BE8810D5C3…` (see sweep output) | TeleportVital 0x25A2 · AskForSystemGiftVital 0x8B93 · OnLandVital 0x1EB4 · TargetPosVital 0x2A90 |

Timing (server `V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE` SENT → client
`frame=4` RECV, from each run's `GAME_LIVE.txt` lines 10–13): r17 1181 ms ·
r18_nologin 1182 ms · r18_parallel 1197 ms · r18_timing 8 ms · r19_reconnect
3 ms · r19_restartA 5 ms · r19_restartB 6 ms · r22_inject 7 ms · r22_replay
4 ms · r23_boot1 8 ms · r23_boot2 6 ms. Every `GAME_LIVE.txt` contains exactly
one client 0x25A2 line per session (dirs logging two sessions contain two).

## Why no hypothesis is opened (fail-closed rationale)

1. **Nothing stalls.** The bundle is already answered by the generic first-Req
   ack; heartbeats, movement, inventory, chat echo, and logout have all been
   proven downstream of this exchange in the same corpus.
2. **No reference exists.** `references/sources/` is empty — there is no
   original-server capture showing any dedicated response to the client 0x25A2.
   A designed response would be invented bytes, contradicting the no-invention
   discipline that HYP-PF-012/013/014 followed (their responses echoed or
   reused byte-proven material).
3. The 18:2x pre-approval covers gameplay functions that lack a handler and
   block gameplay completeness; this frame is neither unanswered (generic ack)
   nor blocking.

## Revisit triggers (falsifiable)

- An attended round observes a client stall, error dialog, or missing
  transition immediately after scene entry.
- A session shows a **second** 0x25A2 after a mid-session MARKER transport
  (observation folded into the big-round checklist; today's corpus never
  shows one, but no clean isolated post-transport observation exists).
- An original-server reference capture for this exchange appears.

## Neighbor observations recorded in passing (all nonclaims)

- **AskForSystemGiftVital 0x8B93** (name from the client-binary registry
  `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`; absent from the
  v141 python name table), v0, payload `0B 00 0B 00`, present in all 14
  sessions, second vital of the bundle. Same disposition as 0x25A2: generically
  acked, nothing stalls, no action. If a system-gift UI element ever appears
  stuck in an attended round, this is the frame to revisit.
- **TargetPosVital 0x2A90** in bundle A carries `(-9098.55, -2866.86, 186.0,
  heading 2.9944)` which does **not** equal the canonical persisted
  `character_positions` row `(-8094.61, -3207.83, 186.0, heading 2.4993)`
  (canonical DB `FA794D0B…4400`, read-only copy). In bundle B it carries the
  replayed session's landing position. The semantics of this field are
  unresolved; recorded as an open observation only.
- **UpdateServerSettingVital 0x0F01** (bundle A) and **OnLandVital 0x1EB4**
  (bundle B) decode cleanly under the v141 tag grammar; field meanings are not
  asserted.

## Evidence

- Sweep/decoder: `pf_bridge/replay/pf_teleport_audit.py` (read-only; prints
  both bundles, full decode, and per-file provenance).
- Per-session dumps: `pf_bridge/outbox/capture_r1*/capture_v141/GAME_*.txt`,
  `…/GAME_LIVE.txt` (11 runs, r17–r23) — read-only evidence, not copied.
- Canonical DB cross-check ran on a `/tmp` copy; the canonical file was not
  touched (sha re-verified `FA794D0B…4400`).
