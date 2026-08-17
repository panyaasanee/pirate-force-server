# PF-MOVE-AUTHORITY-001 — local player movement authority: current server is fully client-authoritative; the correction mechanism exists but is unexercised mid-movement

Date: 2026-08-18
Round: chief scheduled รอบ 58 (report-only, additive)
Coverage row: domain[2] movement/locomotion, `local_player_movement_authority` (currently `not_started`)
Grade claim: **static/code characterization** — no runtime hypothesis changed, no ledger/matrix/src edit this round.

## Question

Coverage note for `local_player_movement_authority` states: *"Reported positions are
accepted as given. No speed, distance, collision, terrain, or line-of-sight validation
exists, and no corrective reposition is ever sent. The original server's movement
authority model is uncaptured."* This round substantiates that note from the committed
artifacts and sharpens the remaining unknown to one bounded question.

## Findings

### 1. Wire ingress is client-reported absolute position (client → server)

`TargetPosVital` (`0x2A90`, `TARGET_POS_VITAL`) is the movement frame the client emits.
Its v0 body is fully decoded — `parse_target_pos_vital` / `parse_v141_refresh_target_pos`
in `current/pf_login_game_server_v141.py`:

- `x` f32 (tag `0x2A`), `y` f32, `z` f32, `heading` f32
- `moving` u8 (tag `0x0B`)
- `derived_mask` u8 (tag `0x0B`) — the strict refresh shape requires `derived_mask==0`
  and zero trailing bytes.

The frame carries an **absolute** position + heading chosen by the client. There is no
sequence number, tick, or client timestamp in the body — nothing the server would need to
reconstruct a movement trajectory for validation.

### 2. The current server accepts positions verbatim — no plausibility validation

On `TargetPosVital` the server (`v141`, ~line 4235) does exactly this: parse → reject only
non-finite floats and non-exact serializer shape → store `self.last_target_pos = (x,y,z,heading)`
→ use that position **only** as the anchor for the NPC nearest-set population refresh. There is:

- no comparison against the previous position,
- no speed / distance-per-tick / collision / terrain / line-of-sight check,
- no rejection of an implausible jump.

The persistence layer agrees. `store.save_position` (`src/pirateforce_foundation/store.py:263`)
validates only (a) scene identity within wire bounds, (b) all coordinates finite, and (c) an
**ownership guard** (the session must currently own the character). It is a single
`UPDATE character_positions ... WHERE character_id=? AND EXISTS(... session owns it ...)` —
an UPDATE-in-place of one row per character, not an append. Call sites are exactly two,
both in `lifecycle.py`: `checkpoint()` (mid-session) and `exit()` (save + close_session).

### 3. No server → client corrective reposition is ever produced

Sweep of `v141` for any outbound frame that repositions the **local** player found none.
Every position-bearing outbound frame targets **NPC/actor** identities (population refresh
"authoritative snapshot"), never the local player's own identity, in response to movement.
`TeleportVital` (`0x25A2`) exists but is a server-initiated transport, not a
movement-plausibility correction. `TeleportCheckVital` (`0x4477`) — a client → server frame
whose semantics are still undecoded — is logged with `semantics=unassigned no_response=1`:
the current server does not answer it.

### 4. Runtime corroboration (GT-005)

The one attended walk (`PF_GT005_...`) recorded **29 inbound `TargetPosVital`** and exactly
one client-initiated `TeleportVital`; the client's final walked position was written to
`character_positions` verbatim and survived a restart. No corrective frame was observed on
either end during the walk. This is direct runtime evidence that, in the current server, the
client's reported position is authoritative and unchallenged.

### 5. The authoritative-reposition mechanism EXISTS client-side — it is simply not used mid-movement

This is the key nuance for the "authority model" question. The client already has a proven
code path that accepts a **server-authoritative position for the local actor**:

- `StartGameRes` carries a **local** `MovementAttr` that positions the local player at scene
  entry — documented in `v141` (lines 15, 162, 196, 238) and **runtime-proven by V133**.
- The `MovementAttr` serializer (`v141` line 1209; static RE at `0x4671C0`) has a per-field
  derived mask where **bit `0x01` = position vec3 (`+0x28..+0x30`)**. The code comment records
  that a live position update can be pushed with mask `0x01` alone so "the client can merge a
  position delta without overwriting the existing locomotion/control fields."

So the mechanism to snap/correct the local player mid-session (bit-`0x01` `MovementAttr` aimed
at the local actor identity) is present and runtime-proven for actors. The current server
never aims it at the local player after scene entry. **Movement authority is therefore
architecturally available; it is a policy choice, not a missing capability, that the current
server is client-authoritative.**

### 6. What the authentic corpus can and cannot say

The decoded authentic corpus audit (`reports/capture_corpus_audit/scene013_...json`,
2621 decoded frames) shows `TargetPosVital` ×123 and `TeleportVital` ×7 — **all in
`client_to_server` sources**. Every decoded source in that corpus is client → server, so it
**cannot** exhibit a server → client movement correction, and its zero counts explicitly
"do not prove protocol" (its own nonclaim). This means the original server's *mid-movement*
use of the reposition mechanism remains **uncaptured** — neither shown nor ruled out by the
decoded corpus.

## Conclusion

- **Current server**: fully client-authoritative for local player movement. Positions accepted
  verbatim, no validation, no correction, UPDATE-in-place persistence with an ownership guard.
  (code-exact / GT-005 corroborated)
- **Client capability**: the server-authoritative local reposition path exists and is
  runtime-proven for scene entry (`StartGameRes` local `MovementAttr`) and for actors
  (`MovementAttr` mask `0x01` position push). The original server *could* have exercised
  movement authority through this exact path.
- **Remaining unknown (bounded)**: whether the original server ever pushed a `MovementAttr`
  bit-`0x01` position to the *local* player mid-movement (rubber-band / snap-back), and what
  `TeleportCheckVital` (`0x4477`) requests/answers. The decoded client→server corpus cannot
  settle either; a server→client capture or an attended provocation is required.

This moves `local_player_movement_authority` from a bare `not_started` to a characterized
`in_progress` (flip deferred to the next matrix edit per the round's report-only discipline).

## Next step / queued test

An attended provocation (queued as a UI test) can settle the bounded unknown cheaply: walk the
real client into a wall / off a cliff / an obviously illegal jump and observe whether the real
server ever emits a corrective `MovementAttr`/`TeleportVital` to the local player (visible
rubber-band on screen + a server→client position frame on the wire). Absence across several
provocations upgrades the "client-authoritative" characterization from the current server to
the original protocol; presence captures the correction golden and decodes the authority rule.

## Evidence (read-only; see companion .manifest for sizes + SHA-256)

- `current/pf_login_game_server_v141.py` — TargetPosVital parse, movement handler, MovementAttr
  serializer static-RE doc, TeleportCheck no_response
- `src/pirateforce_foundation/store.py` — `save_position` (validation surface + ownership guard)
- `src/pirateforce_foundation/lifecycle.py` — `checkpoint` / `exit` call sites
- `reports/PF_GT005_MOVEMENT_POSITION_PERSISTS_ACROSS_RESTART_RUNTIME_PASS_20260817.md` — runtime walk
- `reports/capture_corpus_audit/scene013_structural_combat_corpus_20260816.json` — authentic corpus direction/counts
- `GameClient\GameClient.local.bin` — binary underlying the cited static RE (`0x4671C0`, `0x400000` image base)
