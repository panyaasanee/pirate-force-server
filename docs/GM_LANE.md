# GM Lane -- GM / developer tools for faster attended testing

Owner order: PANYA-ORDER 2026-08-26 16:1x (+07:00), pf_bridge
`notes_to_chief/20260826_1630_PANYA-ORDER-open-Lane-GM-plus-attended-recon-GM-packets-already-in-client-registry.md`.

## What this lane is, in one sentence

GM tools exist to shorten the time a human tester spends reaching a
test-ready state -- not to prove any gameplay system works. Every test entry
that uses a GM shortcut must carry an explicit **nonclaim** line naming which
step it skipped (see "Nonclaim rule" below). "Warped to an island and saw
the island" is not a pass for that island's own scene-load feature.

## Write zone

- `src/pirateforce_foundation/gm/` -- all new modules for this lane
- `scenarios/gm_*.json`
- `tests/test_gm_*.py`
- `docs/GM_LANE.md` (this file)

`runtime.py`, `app.py`, and `current/pf_login_game_server_v141.py` belong to
chief. Any wiring into those files goes through a `CORE-REQUEST-GM-<nnn>`
letter in `pf_bridge/notes_to_chief/`, one letter per wiring point, naming
the module, the function to call, and the exact spot in runtime (login /
vital dispatch).

## Security invariant (does not change with any future decision)

- GM status is granted only to accounts listed in the server-side
  `gm_accounts` allowlist (`gm/accounts.py`). Default is the empty list --
  nobody is GM until an operator lists an account.
- The client has no message that requests GM status for itself. The static
  survey in the 1630 letter found no `/xxx` command strings and no
  client->server "become GM" vital anywhere in the client image. This lane's
  code never adds one.
- This holds even with `production_allowed=true`, because none of it is
  behind a flag: an unlisted account gets nothing different, ever.

## Wire facts used (pinned)

All three come from `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`
and `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` (span_sha256 pinned in the
docstring of each module that depends on it -- re-derive and compare before
trusting a claim here that a mismatch would invalidate):

| vital id | name | direction | layout status |
|---|---|---|---|
| 0x5A19 | `GM_UpdateGMStateVital` | server->client | **proven**: u8tag(0x0B) + u8tag(0x0B) + u32tag(0x14), span_sha256 `03b18673...033c661` |
| 0x51E9 | `GM_RunGMCommandVital` | client->server | **RE-088 PASS/DONE -- STRUCTURAL-LAYOUT-PINNED** (outer `0x00729E10` span_sha256 `541d82f5...c8554`, nested `0x00726C20` span_sha256 `aa3c7c8d...93559d`): one presence flag `u8tag(0x0B)`; when nonzero, exactly one nested body `u32tag(0x14) + u32tag(0x14) + u8tag(0x0B) + ~~UNTAGGED_WSTRING16LE_LEN32LE + UNTAGGED_WSTRING16LE_LEN32LE~~ **CORRECTED round `q6p0pb` (2026-09-02): each wide string is `tag 0x48 + uint32le byte count + UTF-16LE` = 5+N bytes**, per `PF_A2_STRING_WIRE_TAG_DELTA.tsv` (sha256 `e1f4f987...e208b3a2`) rows 6266/6267/6279/6280 -- same nested span sha256 as pinned here, tag instructions `0x0089A833`/`0x0089A89C` `push 0x48`. This is the SAME shape row 0x9F2C below already proved against real captured frames, which is what makes the coarse `UNTAGGED_*` label in `PF_SERIALIZER_FIELDS.tsv` the outdated one, not a second opinion. RE-088 closes the earlier "two runtime-selected sub-paths" question this doc used to carry: the presence flag gates one nested serializer call, not a sub-opcode choosing between two shapes, and RE-088 found no field it could prove is a separate sub-opcode. **Field meaning is still NOT proven** -- the two wide strings are not confirmed to be a command name and its argument text, and the live chat-input trigger condition is RE-091 (open). Decoder: `gm/command_wire.py`. |
| 0x8C77 | `GM_RunGMCommandResultVital` | server->client | **proven**: single u8tag(0x0B) @+0x14, span_sha256 `ad65d125...633e9`. Meaning of the byte not proven (RE-088 explicitly declines to call it success/error). Decoder: `gm/command_wire.py`. |
| 0x162E | `CheatVital` | both | ~~proven: single UNTAGGED_STRING8_LEN32LE @+0x14~~ **CORRECTED round `q6p0pb` (2026-09-02): tag `0x44` + `uint32le` byte count + payload = 5+N bytes @+0x14**, per `PF_A2_STRING_WIRE_TAG_DELTA.tsv` (sha256 `e1f4f987...e208b3a2`) rows 565/566, tag instructions `0x0089A6F1`/`0x0089A75C` `push 0x44`, same base span sha256 the module already pinned (reference only, not reused as GM wire). Codec: `gm/cheat_wire.py` (round `thhkup`, corrected `q6p0pb`) -- round-trip encode/decode, rejects a wrong tag and rejects the old 4+N shape, tested, NOT wired into `dispatch.py`/`runtime.py`; see that module's docstring for why the "not reused" note stays true. |
| 0x9F2C | `Channel_GMGlobalMessageVital` | server->client (Global-scope `Channel_*` family) | **already proven elsewhere in this repo -- do not re-derive or re-codec in this lane's zone.** `reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md` (byte-exact static, 69 static guards + `tests/test_chat_channel_family_static.py`, 15 passed) proves `Channel_GMGlobalMessageVital` shares serializer `0x65AD40` with four other channels (LocalTalk/Party/Guild/ActorBoardcast) byte-for-byte identically: `tag 0x48 + u32 byte-length + UTF-16LE` wstring codec, field order `speaker@+0x34` then `body@+0x18`. This is a **different, more specific wire shape** than `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`'s coarser `UNTAGGED_WSTRING16LE_LEN32LE` label for the same offsets implies (no leading tag byte) -- the report's claim is corroborated against real captured GT-006 frames (three independent byte-for-byte hash cross-checks against pins produced by an unrelated code path), which the TSV row alone is not. `src/pirateforce_foundation/channel_message_hypothesis.py` already implements a tested encoder/decoder for all five shared-serializer channels including this one (`CHANNEL_MESSAGE_FIELD_ORDER`, `SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"] = 0x9F2C`). **This lane tried to build its own codec for this message in a since-retracted round (see "Attempted and retracted" below) before finding this.** `gm/say_wire.py` (say-wire round, below) now bridges a parsed `say` `GmCommand` to that existing encoder by import -- no second codec. |
| 0x0E80 | `ForcePos` | direction NOT_OBSERVED (0 captured frames either way, `PF_FIELD_VALIDATION.tsv`) | **RE-090 PASS/DONE**: vec3 only, three `f32tag(0x2A)` (X/Y/Z), span_sha256 `7c6f6cb7...860e0d`. Vital id is not a table row in `VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (the client computes it at runtime from the name, it is not a stored constant); reproduced here from that file's own documented formula -- see "Vital id formula" below. Codec: `gm/teleport_wire.py`. |
| 0x1BA4 | `CWarpResult` | direction NOT_OBSERVED (0 captured frames either way) | **RE-090 PASS/DONE**: flat `qwordtag(0x32)` + vec3 (`f32tag(0x2A)` x3) + `u16tag(0x12)`, span_sha256 `5e3acf83...986c6db6a9`. The name `Result` is not evidence of direction. Codec: `gm/teleport_wire.py`. |
| 0x25A2 | `TeleportVital` | direction not confirmed, but NOT the same evidentiary state as the two rows above: 132 candidate frames per direction exist at status `A2_STATIC_OPEN` (candidate-matched, not parse-confirmed), unlike `ForcePos`/`CWarpResult`'s genuine zero | **RE-090 PASS/DONE**: `u8tag(0x0B)` field_0x18 -> presence-gated target object (stream order per RE-090's listing: `scene_id` u16tag(0x12), `scene_seq` qwordtag(0x32), then `field_0x10`/`field_0x11` u8 -- **not** ascending object-offset order, same pattern as the aux reorder below; `scene_id`/`scene_seq` are the same RE-077 crosswalk `player_wire.py`/`npc_wire.py` already use -- then vec3 f32tag(0x2A) x3) -> presence-gated auxiliary object (~~untagged wstring~~ **CORRECTED `q6p0pb`: `text` is at DEREF(+0x1C)+0x10 and carries tag `0x48` + `uint32le` byte count = 5+N bytes, per the same delta table rows 580/613**, then four more scalars, **wire order `+0x40` before `+0x38`** even though the object offset is lower -- RE-090 confirms this is real, not a transcription slip) -> `field_0x20` u8 -> `field_0x22` u16tag(0x0F). span_sha256 `fbe813db...df990487` (top), `ec9a5421...9a724df0b5ef` (target), `105bad91...6ccc049c93` (aux). Codec: `gm/teleport_wire.py`. The target field order is this lane's own reading of RE-090's prose listing. ~~a follow-up round should run it against the 132 `A2_STATIC_OPEN` candidate frames~~ 🔴 **SUPERSEDED / RED**: those frames HAVE been replayed and `PF_V5_FIELD_VALIDATION.md` ([MEASURED][CAPTURE], still red at V5) reports **R 190 mismatches, reason `STRING_TAG`**, at the field identity whose `DELTA` component is the dedup_key of delta row 613 -- i.e. at the aux-text tag correction this lane applied on 2026-09-02 -- and **W 188 mismatches, reason `TAG`, at `ORDER:4`** = `PF_SERIALIZER_FIELDS.tsv` row 570 = `TeleportTarget.scene_id`, with no delta component, i.e. base-schema-vs-capture. So the order is not merely unconfirmed, it is contradicted at one of its own fields by 188 real instances. `gm/teleport_wire.py` is therefore a reference codec **KNOWN to disagree with capture** and must not be promoted on its tests. A first written hypothesis (aux presence gate declared ungated in row 579) is in that module's docstring, `[PROPOSED]`. **Note:** the `132 / mismatch 0` figure in `external/PF_FIELD_VALIDATION.tsv` is the V1 aggregate and is stale for this row. |

### Vital id formula (ForcePos / CWarpResult)

`VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`'s own header states how the
client computes a message's wire id from its name at runtime:
`sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xFFFF`. That formula
reproduces the file's own `TeleportVital=0x25A2` and
`TeleportCheckVital=0x4477` rows exactly, so it is trusted (not treated as a
new guess) to compute `ForcePos=0x0E80` and `CWarpResult=0x1BA4`, which are
registered in `external/PF_PROTOCOL_REGISTRY.tsv` by name but are not rows
in that particular table. `[สมมติของสาย GM - รอ RE]`: this is this lane's own
inference from a documented formula, not a disassembled call site proving
the client computes these two exact values -- one step less certain than
the PROVEN byte layouts in this table.

### Correction (filed after `pf-adversary` review, same round)

The first draft of this file and of `gm/command_capture.py`/`gm/commands.py`
copied notes_to_chief `20260826_1630`'s claim that `GM_RunGMCommandVital` /
`GM_RunGMCommandResultVital` had no rows in `PF_SERIALIZER_FIELDS.tsv`. That
letter was written 2026-08-26 16:30 +07:00; the rows were actually added
earlier the same day by `pf_bridge` commit `5ab34dc` (2026-08-26 02:50 UTC =
09:50 +07:00). This round re-derived the table at HEAD instead of trusting
the citation, found the rows, and corrected every place that repeated the
stale claim -- this is exactly the "re-derive again before citing a current
number" rule `AGENTS.md` states and this round initially failed to apply.

## Modules delivered (round one)

- `gm/accounts.py` (GM-001) -- `is_gm_account` / `load_gm_accounts`, JSON
  config, default empty.
- `gm/state_wire.py` (GM-001) -- `make_gm_update_state_payload` /
  `make_gm_update_state_frame` for 0x5A19. The three field values are plain
  integer parameters, not named booleans: their meaning is unresolved,
  labelled `[สมมติของสาย GM - รอ RE]` in the module docstring, and wiring is
  requested via `CORE-REQUEST-006` (proposed; the shared cross-lane counter,
  not a lane-local number -- see `notes_to_chief` letter) to pin them
  against client handler `0x00729F00`.
- `gm/command_capture.py` (GM-002) -- `capture_raw_gm_command`, a raw
  hex-dump sink for 0x51E9. Does not parse or interpret even though a
  structural candidate layout is now known (see the wire-facts table above)
  -- the point is to have real bytes on disk, unique per capture (a
  same-second collision from the same account gets a numeric suffix, never
  a silent overwrite), so a later structural/semantic decoder has something
  real to check itself against.
- `gm/scene_catalog.py` (GM-004) -- scene id -> GM scene name, loaded from
  `gm/data/gm_scene_name_tip.tsv` (byte-identical copy of
  `pf_bridge/gamedata/tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv`, sha256 pinned
  and checked at import time). 330 rows. Confirms Port Royal=1, Prison Exile
  Island=2, Spice Paradise Island=3 from the order letter. Available for
  lane A to reuse for its own travel/scene work -- notified via
  `notes_to_chief`.
- `gm/commands.py` (GM-003 v1) -- `parse_gm_command` / `log_gm_command` for
  the six command grammars (`warp` `npc` `item` `lv` `spawn` `say`).
  **Parses and logs only; executes nothing.** Executing `warp`/`spawn` needs
  proven `TeleportVital`/`ForcePos`/mob-spawn wiring that does not exist yet;
  executing `npc`/`item`/`lv` needs write access to player/world state
  outside this lane's write zone. Each becomes real once its dependency
  lands, via its own `CORE-REQUEST-<nnn>` letter (shared cross-lane
  counter; see `pf_bridge/CHIEF_CONTINUATION.md`).

## Modules delivered (RE-088 follow-up round)

RE-088 (`notes_to_chief/20260826_1811_RE-088-RESULT-GM-COMMAND-WIRE-PINNED.md`)
raised `GM_RunGMCommandVital`/`GM_RunGMCommandResultVital` from a structural
candidate to PASS/DONE and, in the same result, closed the "two
runtime-selected sub-paths" open question this doc used to carry: there is
one nested body, gated by a presence flag, not a sub-opcode choice. Its own
`BUILD_IMPACT` line says this makes GM-002's raw capture eligible to become
a schema-aware decode and gives GM-003 a codec -- but repeats, in the same
breath, that execution and command naming both stay forbidden until
semantics (RE-091) or a real capture close that gap.

- `gm/command_wire.py` (new) -- `decode_gm_run_command_vital` /
  `decode_gm_run_command_result_vital`, a pure decoder for the RE-088 pinned
  byte shape. Field names stay positional (`field_0x10`, `field_0x14`,
  `field_0x18`, `string_0x1c`, `string_0x38`) per RE-088's own nonclaims --
  nothing here is renamed to "command", "argument", or "result_code".
  Decodes only; does not execute, dispatch, or read off a live socket.
  Raises `GmCommandWireError` (never a bare crash) on anything that does not
  match the pin, including trailing bytes after an otherwise-clean decode.
- `gm/command_capture.py` (updated) -- `capture_raw_gm_command` now also
  attempts a decode via `command_wire.py` and writes the result into the
  capture file's header (`presence=0`, the decoded fields, or a `FAILED`
  line naming what did not match), **in addition to** the untouched raw hex
  dump, which never goes away. A decode failure is caught inside the sink,
  not propagated -- a capture must never be lost because a client sent
  something outside the pinned shape; that is exactly the fact GM-002 exists
  to record. The two decoded strings are client-controlled bytes and go
  through the same `unicode_escape` header-injection guard already used for
  `account_name`.

## Modules delivered (npc-switch-catalog round)

- `gm/npc_switch_catalog.py` (GM-003 support) -- mob_id -> the client's own
  name string, for the 7 rows in `pf_bridge/gamedata/tables/CONSTDATA_TH__MOBS.tsv`
  that carry `n_GM_SWITCH=1` (the "NPC กิจกรรม 7 ตัว" the owner's 1630 order
  letter already found: 855, 871, 882, 897, 902, 8180, 8181). Loaded from
  `gm/data/gm_npc_switch.tsv`, an extracted 2-column copy (sha256 pinned and
  checked at import time, same pattern as `scene_catalog.py`). This is this
  lane's own committed-gamedata derivation, not a reuse of any lane-B module
  (none exists yet that exposes a general mob_id -> name lookup -- see the
  note below, still true).
- `gm/commands.py` -- new `describe_npc_target(command)`, the same
  non-blocking hint pattern as `describe_warp_target`: for a parsed `npc`
  command, returns the client's name if `mob_id` is one of the 7
  GM-switchable NPCs, else `None`. A `None` result is not a validity gate --
  `npc on|off` still parses and logs any mob_id; this only tells the log
  whether the client itself flagged that mob_id as GM-switchable.

## Modules delivered (RE-089/090/091 follow-up round)

RE-089, RE-090 and RE-091 (`notes_to_chief/20260827_0016_...`,
`notes_to_chief/20260826_2346_...`, `notes_to_chief/20260826_2322_...`) all
came back since the previous round; this round reads and folds all three in
before building further, per this lane's own "ค้นก่อนถอด" rule.

- `gm/state_wire.py` docstring corrected: RE-089 disproves the `bm_gm.tga`
  "GM chat-balloon icon" lead this docstring used to cite (it is the
  `FxNumberCache` green-minus damage-number glyph, unrelated to GM) and
  answers CORE-REQUEST-GM-001 as DONE/BOUNDED-NEGATIVE -- state propagation
  into `GMModule_Client` is pinned, but no render/widget/UI consumer is
  found, so the three payload fields **stay opaque integers**, unchanged
  from round one. Nothing in the module's behaviour changes, only the
  citation.
- `gm/teleport_wire.py` (new, GM-003 support) -- encode/decode for
  `ForcePos`, `CWarpResult`, `TeleportVital` per the RE-090 pinned byte
  shape (wire-facts table above). Positional field names for everything
  RE-090 does not resolve semantically, same convention as
  `gm/command_wire.py`; `scene_id`/`scene_seq` keep the names already
  established elsewhere in this codebase because RE-077 already crosswalked
  those two. This closes the "no wire codec for the warp dependency" gap
  `gm/commands.py`'s scope note has named since round one -- `warp`
  **still does not execute**, this only means the bytes it would need to
  send now have a real, tested builder instead of not existing at all.
  Direction (which side sends `ForcePos`/`CWarpResult`) is still
  NOT_OBSERVED, so the module provides both an encoder and a decoder for
  each message and does not assume a side.
- RE-091 (PASS/DONE) settles a question this doc did not previously carry
  explicitly: the real client's `0x51E9` comes from a **dedicated GM
  editor widget** (Enter key, non-empty text, gated on that widget being
  active), not from a prefix check inside the normal chat box -- normal
  chat uses the unrelated `Channel_*MessageVital` family. This project's
  own design of interpreting arbitrary chat text as a GM command (see
  `gm/commands.py`'s scope note: this module "takes a plain `str`" and does
  not depend on 0x51E9 at all) is therefore **this lane's own policy
  choice**, not a reconstruction of original client behaviour -- stated
  here so a future round or reader does not cite RE-091 as proof our chat
  parsing matches the original client's dedicated-editor path. It does not.

## Modules delivered (dispatch/authorization-gate round)

The previous round (`rounds/GM_20260827_0438_...md`) named the missing
piece explicitly: `warp` (and every other GM-003 command) still cannot
execute because no inbound dispatch of 0x51E9 has ever existed in
`runtime.py`, and the authorization-gate decision in front of it is "bigger
than a one-line CORE-REQUEST letter" -- proposed as its own round rather
than rushed. This round is that round.

- `gm/dispatch.py` (new) -- `handle_gm_run_command_vital(account_name,
  raw_payload)`, the single function `CORE-REQUEST-GM-010` asks chief to
  wire at the point `runtime.py` reads vital id 0x51E9 off the wire. It
  checks `gm/accounts.is_gm_account()` FIRST, before any capture/decode
  side effect, reusing the exact "refuse by name, not by crash" pattern
  `runtime.py`'s own CORE-REQUEST-006 login check already uses for a
  malformed `gm_accounts.json` (same `(ValueError, OSError)` catch, same
  `gm_account_lookup_failed_<ExceptionType>` reason string). Only when the
  sender is an authorized GM does it call
  `command_capture.capture_raw_gm_command` (GM-002's existing sink); an
  unauthorized or misconfigured call writes nothing to disk. It does not
  decode the two wide strings into a `gm/commands.py` `GmCommand` and does
  not log via `log_gm_command` -- that mapping is still unproven (RE-088's
  own nonclaim), so bridging it here would be a guess this lane's rules
  forbid. It does not execute anything and does not send
  `GM_RunGMCommandResultVital` (0x8C77) -- no send path exists in this
  lane's write zone and the result byte's meaning is unproven regardless.
- `tests/test_gm_command_dispatch.py` (new, 11 tests) -- proves the
  authorization gate specifically: a missing config, a non-GM account, and
  a malformed config all refuse and write nothing; an authorized GM's call
  writes exactly one real capture file per call, matching
  `command_capture.py`'s own format.

`pf-adversary` (this round) found that `command_capture.py`'s hex-dump sink
has no size cap of its own, and this module is what makes that sink
reachable from a live wire for the first time -- a many-megabyte
`GM_RunGMCommandVital` payload from an authorized-but-hostile or scripted
GM client would block the handling thread for tens of seconds and could
fill disk per call. `dispatch.py` closes this with
`MAX_RAW_PAYLOAD_LENGTH` (64 KiB, far larger than any real
`GM_RunGMCommandVital` RE-088 has proven the shape of): a GM account
sending an oversized payload gets `authorized=True` (it IS a GM account)
but `captured_path=None` and `refusal_reason=REFUSAL_PAYLOAD_TOO_LARGE` --
nothing is written to disk for that one call. The size check runs AFTER
the authorization check, so a non-GM sender's refusal reason stays
`REFUSAL_NOT_GM` regardless of payload size and never reveals the cap
exists.

The one thing this closes is the security gap the previous round flagged:
before this module, nothing in this package stopped any connected account
(GM or not -- RE-091 already proved the real client's own gate is a UI
widget, not a wire-level check) from making this lane write a capture file
to disk on demand, once wiring existed at all. This module is the gate that
must sit in front of any future wiring, not a new capability by itself --
warp/npc/item/lv/spawn/say still do not execute after this round, and no
account gets anything it could not already get from CORE-REQUEST-006's
existing login-time check.

## Modules delivered (warp-executor round)

- **new** `gm/warp_executor.py` -- `make_warp_force_pos_frame(legacy,
  vital_version, command, current_scene_id, z)`, the function
  `CORE-REQUEST-011` asks chief to wire at the point that would send a
  `warp` command's effect back to a GM connection. It bridges a parsed
  `warp` `GmCommand` (from `gm/commands.py`) into a real `ForcePos` frame
  (`gm/teleport_wire.py`, RE-090 PASS/DONE, zero unproven fields) -- but
  **only** the same-scene case: `ForcePos` carries no scene id field at
  all, so it cannot honor the scene-crossing half of what
  `warp <scene_id> x y` reads as. The caller must pass
  `current_scene_id` (the connection's real current scene; this module
  tracks no player state itself); if the command's own `scene_id` argument
  differs, or the command has no `x`/`y` at all (the scene-only
  `warp <scene_id>` form), the function raises `WarpExecutorError` instead
  of sending an in-scene hop for a command that asked to leave the scene --
  that would misrepresent what `ForcePos` actually did. `z` is a required
  parameter, not inferred, because the GM-003 grammar has no z argument.
  Cross-scene warp still needs `TeleportVital`, whose `target`/`aux`
  sub-objects carry several positional-only fields RE-090 leaves unproven
  (`field_0x10`, `field_0x11`, `field_0x18`, `field_0x20`, `field_0x22`,
  and most of `TeleportAux`) -- guessing values for those is exactly the
  invention this lane's nonclaim rule forbids, so this module refuses that
  case by name rather than attempting it.
- **new** `tests/test_gm_warp_executor.py` -- proves the same-scene frame
  matches the proven `ForcePos` codec byte-for-byte, and that every refusal
  path (non-warp command, scene-only form, differing `current_scene_id`)
  raises `WarpExecutorError` rather than returning a frame.
- **fixed** `gm/commands.py`'s module docstring, which still said executing
  `warp` "needs ... wiring that is not proven yet" -- stale since RE-090
  closed the `ForcePos` layout; corrected to point at `warp_executor.py`
  and state precisely what remains unbuilt (the scene-crossing case).

This module still does not send anything -- it returns frame bytes for a
caller to send. No account gets anything it could not already get before
this round; the visible effect of wiring `CORE-REQUEST-011` in is that a
GM connection already in the target scene can be repositioned within it.
Scene-crossing `warp`, `npc`, `item`, `lv`, and `spawn` still do not
execute after this round.

## Modules delivered (say-wire round)

- **new** `gm/say_wire.py` -- `make_say_broadcast_frame(legacy, command, *,
  speaker="")`, the function `CORE-REQUEST-012` asks chief to wire at
  whatever call site eventually produces a real `say` `GmCommand`. It
  bridges a parsed `say` command into a real `Channel_GMGlobalMessageVital`
  (0x9F2C) frame by importing `channel_message_hypothesis.py`'s already-proven
  `make_channel_message_response` -- the exact fix the retracted
  broadcast-wire round (below) named as the required next step, and the
  reason this round did not write a second wire codec. `speaker` defaults to
  `""`, the value every captured GT-006 frame on this shared serializer has
  carried; a caller with a real GM display name may pass one.
- **new** `tests/test_gm_say_wire.py` -- proves the built frame matches
  `make_channel_message_response`'s own output byte-for-byte, round-trips
  through `channel_message_hypothesis.decode_channel_message`, and that
  `GM_GLOBAL_CHANNEL_ID` is the same object as
  `SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"]` (no copy to
  drift). `pf-adversary` (this round) found two gaps against the
  "regardless of source" contract before this shipped: `gm/commands.py`'s
  480-char `MAX_SAY_MESSAGE_LENGTH` cap was enforced only inside
  `parse_gm_command`, so a hand-built `GmCommand` bypassed it entirely; and
  `command.args` was indexed with plain `len()`/`[0]`, leaking a bare
  `TypeError`/`KeyError`/`IndexError` instead of `SayWireError` for an
  `args` container of the wrong *shape* (`None`, a `set`, a `dict`), not
  just the wrong value. Both are fixed (the length cap is re-checked, and
  `len()`/indexing are wrapped) with 5 new regression tests.
- **known, deliberately not fixed this round**: `pf-adversary` confirmed
  `gm/warp_executor.py` has the identical args-shape gap (a `None`/`set`/
  `dict` `command.args` leaks a bare `TypeError` there too) -- it predates
  this round and is out of `say_wire.py`'s scope to fix. A follow-up round
  should apply the same `len()`/indexing guard there.

Like `warp_executor.py`, this module does not send anything -- it returns
frame bytes for a caller to send. `say` still does not execute after this
round: no account gets anything it could not already get before.

## Modules delivered (warp-executor args-shape follow-up round)

- **fixed** `gm/warp_executor.py`'s args-shape gap named as a known
  follow-up in the say-wire round above: `make_warp_force_pos_frame` now
  wraps `len(command.args)` and its three positional reads the same way
  `say_wire.py` already does, converting a shape-mismatched `args` (`None`,
  a `set`, a `dict`) into `WarpExecutorError` instead of a bare
  `TypeError`/`KeyError`.
- `pf-adversary` (this round) then found the `say_wire.py`-style three-type
  catch (`TypeError`/`KeyError`/`IndexError`) itself still leaves two gaps
  open, reproduced live: (a) a custom `__len__`/`__getitem__` raising
  anything outside those three types (e.g. `AttributeError`, `ValueError`)
  still leaked past `WarpExecutorError`, contradicting the module's own
  "every failure surfaces as `WarpExecutorError`" promise -- both guards now
  catch `Exception` broadly instead; (b) a `str`/`bytes` scalar of length 3
  (e.g. `"123"`) is not a crash at all -- it passes `len(args) == 3` and is
  positionally indexable, so it was silently read as a real
  `(scene_id, x, y)` tuple instead of being refused as the wrong container
  shape -- `args` is now rejected by `isinstance` before either guard runs.
  Both gaps also apply to `gm/say_wire.py`'s identical three-type catch;
  this round's write-zone fix only covers `warp_executor.py`, so
  `say_wire.py` carries the same two gaps as a known follow-up (see below).
- `tests/test_gm_warp_executor.py` -- 4 new tests: a `str` args scalar, a
  `bytes` args scalar, an `args` object whose `__len__` raises `ValueError`,
  and one whose `__getitem__` raises `AttributeError`. All four must raise
  `WarpExecutorError`, not the underlying bare exception.
- **known, deliberately not fixed this round**: `gm/say_wire.py` has the
  same two gaps this round found and fixed in `warp_executor.py` (narrow
  three-type catch instead of broad `Exception`; no `str`/`bytes` scalar
  guard on `args`, though `say_wire.py`'s own `arg_count != 1` check plus
  its `isinstance(body, str)` check on the extracted element happens to
  make the scalar case less exploitable there than in `warp_executor.py` --
  not independently re-verified this round). Out of this round's scope
  (`say_wire.py` was not touched); a follow-up round should apply the same
  broadened catch and scalar guard there.

## Modules delivered (say-wire args-shape follow-up round)

- **fixed, then re-fixed** `gm/say_wire.py`'s own copy of the args-shape
  gap named as a known follow-up above. First pass: `make_say_broadcast_frame`'s
  `len(args)`/`args[0]` guards were broadened to catch `Exception` instead
  of the narrow `TypeError`/`KeyError`/`IndexError` set, and `args` was
  rejected via `isinstance` if it was `str`/`bytes` -- the same blacklist
  shape `warp_executor.py`'s own follow-up round had applied to itself.
  `pf-adversary` broke that first pass the same day: an integer-keyed
  `dict` (e.g. `{0: "hello"}`) is exactly the "mapping" shape this
  document already names as one of the three canonical wrong shapes
  (`None`, a `set`, a `dict`), yet `len(d)` and `d[0]` both succeed
  normally for it -- no exception is ever raised, so neither the
  `str`/`bytes` guard nor the broad `except Exception` fires, and a
  hand-built `GmCommand` with such a dict silently built a real frame.
  The identical gap applies to `warp_executor.py`'s copy of the same
  blacklist (`{0: 1, 1: 2, 2: 3}`).
- **root cause and final fix**: a blacklist of individually-discovered
  wrong shapes is unbounded against a field typed `tuple[str, ...]`
  (`gm/commands.py`'s `GmCommand.args` annotation) with exactly one
  legitimate shape. Both `gm/say_wire.py` and `gm/warp_executor.py` now
  assert that shape directly (`if not isinstance(args, tuple): raise
  <ModuleError>(...)`) before any `len()`/indexing runs at all, closing
  the whole class of gap at once -- dict of any key type, `str`/`bytes`,
  `bytearray`, `memoryview`, a `list`, a custom object -- rather than
  continuing to chase individual shapes that happen not to raise.
- `pf-adversary` reviewed the allowlist fix itself (second pass, same
  round) and reported it found no tuple-subclass or tuple-like object
  that both passes `isinstance(args, tuple)` and misbehaves downstream.
  **That specific claim was wrong, and a third pf-adversary pass
  (same round) reproduced the counter-example live within a minute**: a
  tuple *subclass* overriding `__len__` or `__getitem__` to raise
  something other than this module's own error type
  (`class EvilTuple(tuple): def __len__(self): raise RuntimeError(...)`)
  passes `isinstance(args, tuple)` cleanly, and `GmCommand` (a plain
  frozen dataclass, `gm/commands.py`, no `__post_init__` validation)
  places no obstacle in front of a hand-built one -- exactly the
  "regardless of source" threat model this module's own docstring
  already claims to defend against. The two `WeirdLen`/`WeirdGetitem`
  regression tests carried forward from the first pass kept passing
  throughout, but for the wrong reason: those objects are plain objects,
  not tuples, so `isinstance` rejects them before their dunders are ever
  called -- the len()/indexing-exception path itself had gone untested
  since the allowlist landed. Recorded here rather than quietly
  corrected, per this lane's own rule against letting a convenient,
  unverified claim stand as fact.
- **root cause and final fix (third pass)**: `isinstance(args, tuple)`
  admits any subclass; `type(args) is tuple` does not. Both modules now
  check the exact type, not an `isinstance` match -- a real `tuple`
  (never a subclass) can never raise on `len()`/indexing, so there is no
  dunder left to lie through, closing this without needing any
  try/except around `len()`/indexing at all.
- `tests/test_gm_say_wire.py` (`SayWireArgsShapeFollowUpTests`) and
  `tests/test_gm_warp_executor.py` (`WarpExecutorArgsShapeTests`): each
  gained tests for an integer-keyed dict, a `list`, a `bytearray`
  (second pass) and a tuple subclass with a lying `__len__` and one with
  a lying `__getitem__` (third pass), alongside the `str`/`bytes` scalar
  and weird-`__len__`/`__getitem__` tests the first pass already added.

No behavior change on the happy path -- a real one-element `args` tuple
carrying a `str` (or a real three-element `args` tuple for `warp`)
produces a byte-identical frame to before. `say`/`warp` still do not
execute after this round: these modules only return frame bytes, they
send nothing, and no account gets anything it could not already get
before this round (`CORE-REQUEST-011`/`CORE-REQUEST-012` are not wired
into `runtime.py`).

## Modules delivered (GM-005 login-scene-override round)

Built the fast half of `notes_to_chief/20260827_1425_PANYA-ORDER-GM-warp-to-other-maps-two-paths.md`
("ทาง ก") -- the owner asked to see a non-default map without needing the GM
in-game editor widget (still gated on `RE-104`) or cross-scene
`TeleportVital` ("ทาง ข", still gated on `RE-090`'s unproven field semantics
and `CORE-REQUEST-011`'s same-scene-only wiring).

- `gm/login_scene_override.py`: `get_login_scene_override(account_name,
  gm_accounts_config_path=None, login_scene_config_path=None)` returns a
  scene_id only when the account is BOTH listed in `gm/accounts.py`'s
  `gm_accounts` allowlist AND has an entry in its own
  `config/gm_login_scene.json`-style config (env override
  `PF_GM_LOGIN_SCENE_CONFIG`, same pattern as `gm/accounts.py`'s
  `PF_GM_ACCOUNTS_CONFIG`) naming a scene_id present in
  `gm/scene_catalog.py`'s 330-row committed table. Checked fresh on every
  call, not cached -- revoking an account from `gm_accounts.json` removes
  its override on the very next call, no restart needed. ~~Neither file
  alone can grant anything: an override entry for a non-GM account is
  inert.~~ **SUPERSEDED, round `ccc9wj` (2026-08-28): no longer true as a
  description of the whole function.** A second, independent standalone
  path was added that grants an override with NO `gm_accounts.json`
  membership at all -- see "Modules delivered (round `ccc9wj`, GT-110
  standalone login-scene safety fix)" below for the current, accurate
  contract. This paragraph is left in place, struck through rather than
  deleted, as the historical record of what this round actually shipped.
- `tests/test_gm_login_scene.py`: default-empty, gating (GM+entry / GM-no-
  entry / non-GM-with-entry / unlisted), malformed config (non-object top
  level, non-dict `gm_login_scene`, non-int scene_id, `bool`-as-int,
  unknown scene_id), and a revocation-takes-effect-immediately test.
- `pf-adversary` review (this round) tried to make a non-GM account produce
  a non-`None` result (homoglyphs, NFC/NFD unicode, whitespace/case
  variants, a malformed entry for a *different* account) and could not; it
  did find that a non-object top-level JSON (a bare list/string/null) raised
  `AttributeError` instead of the documented `ValueError` -- both this
  module and `gm/accounts.py` shared the same gap (`data.get(...)` called
  without first checking `data` is a `dict`). Fixed in both files this
  round, with a regression test added to both `test_gm_login_scene.py` and
  `test_gm_accounts.py`.
- **Known, accepted blast radius** (flagged by `pf-adversary`, not fixed):
  `load_login_scene_overrides` validates the whole config file eagerly, so
  one malformed entry (e.g. an operator typo for `other_gm`) raises for
  every account's lookup, not just the mistyped one. This matches
  `gm/accounts.py`'s own existing behavior (`load_gm_accounts` already
  fails the same way for a malformed `gm_accounts.json`), so it is not a
  new inconsistency, but it is a real forward risk once a login call site
  exists: see `CORE-REQUEST-GM-015` for the explicit note to whoever wires
  the call point.
- **Not built this round** (chief's write zone, `runtime.py`): the two call
  points the owner's order asks for -- (1) at login, resolve
  ~~`get_login_scene_override(token)`~~ and send that scene_id instead of the
  default start scene when it is not `None`; (2) assemble that scene's
  census from `Data\Scene\Save\bgXXXX\bgXXXX.npc` placements (via
  `gamedata/pf_decode_lua_npc.py`, already used for `bg0001` by lane A/B)
  plus lane B's hostile roster where one exists for that scene (`bg0015`
  has one per the order). See `CORE-REQUEST-GM-015`.
  - **CORRECTION** (LANE-GM round `38c4tv`, after `pirate-force-server#236`
    merged 2026-08-28T23:39+07:00): the call point (1) describes is wired,
    and the call it makes is `consume_login_scene_override(self.token)` --
    which **replaced** the reader struck above rather than joining it
    (`CORE-REQUEST-GM-033` v2: two reads in one login means the second gets
    `None`). It answers with an outcome as well as a scene, and a
    `CONSUME_FAILED` outcome grants no scene at all.
    `get_login_scene_override` still exists and is still the right call for
    anything that wants to LOOK without spending.
  - **CORRECTION 2** (LANE-GM round `1fq5yf`, after `pirate-force-server#264`
    merged 2026-08-29T08:38:50Z): the call shape written above is now the
    BARE one, not the real one. The login site calls
    `consume_login_scene_override(self.token, scene_registry=scene_entry_registry)`,
    passing the registry snapshot `runtime.py` loaded once at boot, so the
    config is judged against what the process can actually place rather than
    against a fresh read of the file.
  - **PRINTED** (chief round `nbulzb`, `CORE-REQUEST-GM-037` wired): the
    `CONSUME_FAILED` outcome carries a `cause` and `runtime.py` prints it —
    the console line is now
    `GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED effect=login_at_own_row
    cause=<token>`, one token from the closed vocabulary below. An earlier
    paragraph here (LANE-GM round `1fq5yf`) said "NOT YET PRINTED" while
    only this lane's module carried the field;
    `tests/test_gm_login_scene_consume_cause.py::TheDocsAndTheConsoleAgree
    Tests` is the tripwire that forced this paragraph to change in the
    same round the print was wired, rather than rotting.

## Modules delivered (RE-105 vital-version-pin round)

`RE-105` closed the `[ASSUMED - awaiting RE]` gap `CORE-REQUEST-016` opened:
`gm/state_wire.py`'s `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` moves from
`None` to `0`, the exact value RE-105 traced through the client's generic
VitalData collection reader end to end. `runtime.py`'s call site (chief's
write zone, gated on this constant since `CORE-REQUEST-016`) needed no edit
-- the guard CORE-REQUEST-016 asked for exists precisely so this lane can
close the value inside its own write zone once RE pins it.

- `tests/test_gm_login_state_guard.py`: rewritten from "guard stays closed"
  to "guard is now open, at the exact byte RE-105 traced" -- a GM account's
  `GM_UPDATE_STATE_AFTER_LOGIN` action, driven through the real dispatcher,
  now asserts its `pc` bytes contain `12 19 5A 0B 00` (nested vital id
  `0x5A19` little-endian, tag `0x0B`, version `0`) and not `12 19 5A 0B 01`
  (the value GT-101 proved fatal), plus the outer envelope's separate
  protocol-version byte `08 04` is unchanged. A non-GM account stays
  unaffected. A third test patches the module constant back to `None` and
  proves the frame is withheld again -- the guard is a real conditional, not
  a permanent hardcode either direction.
- `tests/test_gm_dispatch.py`: its `CORE-REQUEST-006` dispatch test
  (`test_a_gm_account_gets_no_state_frame_while_the_version_guard_is_closed`)
  asserted the now-stale "no frame" behavior; renamed to
  `test_a_gm_account_gets_the_re105_pinned_state_frame` and updated to
  assert the frame IS present and the withheld-event is absent, matching the
  guard's new open state.
- Full `tests/test_gm_*.py` suite (206 tests) and the repo's broader
  `unittest discover` (3565 tests; the only failures are 18 pre-existing
  `ModuleNotFoundError: capstone` import errors in unrelated static-RE
  probes, not touched this round) both pass after this change.

nonclaim: this closes the wire-version byte only. `GM_UpdateGMStateVital`'s
three payload fields (`+0x14`/`+0x15`/`+0x18`) stay opaque integers, RE-089's
own open next step -- setting the version correctly does not mean the field
values this lane sends (`0, 0, 0`) mean anything, and does not by itself
prove any client-observable GM UI change. That still needs an attended
capture/observation session (`GT-101` rerun) this lane cannot run headless.

## Modules delivered (round `50x5xt`, pf-adversary follow-up)

A full-package `pf-adversary` pass over `gm/` (not tied to any single
change -- a standing-debt sweep, since GM-002's live wiring means this
package now handles real inbound bytes) found three issues, none of them a
non-GM account gaining anything -- the allowlist gate itself held under
every shape tried:

- **Fixed, HIGH -- `gm/dispatch.py`**: `handle_gm_run_command_vital` called
  `command_capture.capture_raw_gm_command` (a real `os.mkdir`/`os.open`/
  `os.write`) with no `try`/`except`. Since `CORE-REQUEST-010` wires this in
  "always on" with no surrounding guard in `runtime.py` either, an `OSError`
  from a full disk, a permission error, or `capture_root` colliding with an
  existing non-directory file would have propagated out of the handler and
  could have taken the connection-handling thread down for every player over
  ONE authorized GM command's capture write -- exactly the "refuse by name,
  not by crash" failure mode this module's own docstring already claimed to
  have closed (it had only closed it for the account-lookup call, not this
  one). Fixed by wrapping the call in `try`/`except OSError`, returning
  `GmDispatchOutcome(authorized=True, captured_path=None,
  refusal_reason="capture_write_failed_<ExceptionType>")` -- same shape as
  the existing `gm_account_lookup_failed_*`/`payload_too_large` refusals, so
  a caller already handling those handles this the same way with no new
  branch. New tests in `tests/test_gm_command_dispatch.py`: one forces a real
  `FileExistsError` by pointing `capture_root` at a path that already exists
  as a file, one mocks `capture_raw_gm_command` to raise a generic `OSError`
  directly.
- **Fixed, MEDIUM -- `gm/commands.py`**: `describe_warp_target`,
  `describe_npc_target`, and `log_gm_command` indexed or `list()`-ed
  `command.args` with no shape check -- the exact bug class
  `gm/warp_executor.py` and `gm/say_wire.py` already closed for their own
  `GmCommand` inputs (a blacklist defeated by an integer-keyed dict, then an
  `isinstance(args, tuple)` allowlist defeated by a tuple subclass lying
  through `__len__`/`__getitem__`), left open in this file because these
  three functions predate that fix and nobody re-swept this file when it
  landed. Concretely: a hand-built `GmCommand` with `args={0: "1", 1: "2",
  2: "3"}` used to make `log_gm_command` silently write `"args": [0, 1, 2]`
  (the dict's *keys*) into the forensic ndjson log instead of raising, and
  `args=None` raised a bare `TypeError` instead of a catchable
  module-specific error. Fixed with a shared `_require_args_tuple(args,
  min_length=N)` helper using the same `type(args) is not tuple` exact-type
  check (not `isinstance`) plus a length check, raising the new
  `GmCommandArgsError`, called at the top of all three functions. New tests
  in `tests/test_gm_commands.py` (`ArgsShapeGuardTests`) cover the dict, a
  `None`, a lying tuple subclass, and a too-short real tuple for each
  function, plus a regression test proving `log_gm_command` now records the
  real positional values, not dict keys.
- **Not fixed this round, MEDIUM, tracked below** -- no per-account rate
  limit on authorized capture writes. See "What is intentionally NOT built
  yet, and why" below for why this is deferred rather than rushed.

`tests/test_gm_*.py`: 215/215 (up from 189 -- 26 new tests, all from this
round). Repo-wide `unittest discover`: 3587 tests, 18 pre-existing
`capstone`-import errors only (same set as every prior round's baseline),
no new failures.

nonclaim: none of this changes what any command *does* -- `warp`/`say`
still only return frame bytes to a caller, nothing is sent to a socket, and
no field semantics changed. This round is pure robustness/correctness
inside this lane's own write zone; no wire fact, no RE citation, and no
`runtime.py` edit involved.

## Modules delivered (round `kzwdle`, rate-limit + collision-loop bound)

Closes the two items round `50x5xt` deferred (see the struck-through bullet
under "What is intentionally NOT built yet, and why" below).

- **`gm/dispatch.py`**: `handle_gm_run_command_vital` now enforces a
  sliding-window per-account rate limit before the payload-size check --
  `RATE_LIMIT_MAX_CALLS_PER_WINDOW = 20` calls per
  `RATE_LIMIT_WINDOW_SECONDS = 5.0`. A rate-limited call keeps
  `authorized=True` (the account really is GM) with `captured_path=None`
  and the new `refusal_reason=REFUSAL_RATE_LIMITED` -- same outcome shape
  as the existing oversized-payload and capture-write-failure refusals, so
  a caller already handling those needs no new branch. State
  (`_rate_limit_call_history`, one list of call timestamps per account) is
  process-global and lock-guarded; `reset_rate_limit_state_for_tests()`
  clears it for test isolation. The default is deliberately generous:
  `GAME_TEST_QUEUE.md`'s GT-103 capture-matrix procedure paces attended
  sends 3 seconds apart (at most ~2 per 5-second window), an order of
  magnitude under the cap, so ordinary attended use is never refused --
  this is a flood guard against a scripted client, not a per-command
  throttle on a human.
- **`gm/command_capture.py`**: the filename collision retry loop (flagged
  by the same round's verify-pass as a companion liveness gap, not an
  uncaught-exception risk on its own) is now bounded by
  `_MAX_FILENAME_COLLISION_ATTEMPTS = 1000`; exceeding it raises `OSError`
  instead of spinning, which `gm/dispatch.py`'s existing `except OSError`
  around this call already turns into a `capture_write_failed_*` refusal
  -- no new refusal reason needed for this half.
- **`pf-adversary` (this round, verify pass)** found and this round fixed
  a real ordering gap in the first draft of the rate limiter before it
  ever left draft: the clock read (`time.time()`) originally happened
  *before* acquiring `_rate_limit_lock`, so two threads for the same
  account could race the lock and record their timestamps out of the
  order they were read in -- reproduced live with real threads, no clock
  mocking. The prune loop's `while history and history[0] <= cutoff:
  history.pop(0)` silently assumed ascending insertion order; an
  out-of-order `append` could leave an individually-expired entry
  unpruned behind a newer one until that newer entry also aged out.
  Self-healing, never a bypass (the account was held at its cap *longer*
  than the window, never let through early) -- but a real deviation from
  the documented window, and reproducible by ordinary thread scheduling
  jitter, not just a clock anomaly. Fixed by construction, not
  convention: the clock is now read *inside* the same lock (removing the
  race for every production caller, none of which passes an explicit
  `now_ts`), and insertion uses `bisect.insort` instead of `append` (so
  the history list stays sorted even for an explicit, intentionally
  out-of-order `now_ts` from a test, or a wall clock that steps
  backward). `tests/test_gm_command_dispatch.py`'s
  `test_an_out_of_order_now_ts_is_still_pruned_correctly` reproduces the
  exact shape (a later timestamp recorded before an earlier one) and
  proves the fix holds without needing real threads.
- `tests/test_gm_command_dispatch.py`: 10 new tests -- calls up to the
  window max succeed, the call past it is refused without touching the
  capture root, the window slides (a call after it elapses succeeds
  again), rate limiting is scoped per account not global, a refused
  non-GM call never consumes a GM account's own budget, `reset_rate_
  limit_state_for_tests()` actually clears history, the shipped (not
  test-overridden) defaults survive a realistic same-second burst, and
  the out-of-order-timestamp regression test above.
  `tests/test_gm_run_command_dispatch_wiring.py` and
  `tests/test_gm_command_dispatch.py` both now reset rate-limit state in
  `setUp` for defensive test isolation (the state is process-global,
  shared even across test files in the same `unittest discover` run).
  `tests/test_gm_command_capture.py`: 2 new tests -- the collision loop
  gives up after its bound instead of spinning (mocked `os.open` always
  raising `FileExistsError`, patched bound of 3, exactly 4 attempts made),
  and a realistic 50-capture same-second burst is unaffected by the bound.

`tests/test_gm_*.py`: 225/225 (up from 215 -- 12 new tests: 10 dispatch +
2 capture; two existing test files gained a defensive `setUp` reset with
no new test methods). Repo-wide `unittest discover`: 3619 tests, 18
pre-existing `capstone`-import errors only (same baseline every prior
round reports), no new failures.

nonclaim: pure robustness/correctness inside this lane's own write zone --
no command behavior changed on the happy path (`warp`/`say`/`npc`/`item`/
`lv`/`spawn` still only parse/log/build frame bytes, nothing is sent to a
socket), no wire fact, no RE citation, and no `runtime.py` edit involved.
The rate limiter changes when an already-authorized GM's capture gets
written, never who is authorized -- a non-GM account still gets exactly
nothing, same as every prior round.

## Modules delivered (round `fmgvbx`, RE-113 trailing-mask fix)

- **`gm/state_wire.py`**: `make_gm_update_state_frame` now builds the
  `0x5A19` frame via the legacy bridge's plural `make_runtime_vitals()`
  helper (a single-item list) instead of the singular `make_runtime_vital()`
  helper. The singular helper does not append the trailing derived-class
  change-mask byte (`u8tag(0x0B, 0)`) that `GSCN_RunTimeProtocolRes` v4
  requires after its VitalData collection; `GT-107` (attended) measured the
  client throwing `ErrorData=28317` and closing the socket immediately after
  receiving exactly the frame the singular helper produces. `RE-113` traces
  this to the plural helper's own pre-existing code comment (citing this
  same error code) and to three independent prior incidents documented in
  `reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md` Sec.(c) --
  not a new disassembly finding, a pattern this codebase had already hit and
  fixed elsewhere that this lane's own frame builder had not picked up.
  Output shape is otherwise unchanged: same three fields, same tags, same
  `vital_version`; the only wire difference is one trailing `0x0B 0x00`.
- `tests/test_gm_state_wire.py`: `test_frame_carries_the_gm_update_state_vital_id`
  updated to compare against `make_runtime_vitals()` instead of the old
  `make_runtime_vital()`; new regression test
  `test_frame_carries_the_re113_trailing_change_mask_byte` asserts the built
  PC's last two bytes are the trailing change-mask tag, so a future
  regression back to the singular helper fails loudly here instead of
  waiting for another attended GT to notice.

`tests/test_gm_*.py`: 232/232 (up from 225 -- 6 new assertions in the one
new test plus the updated existing one; no other test file touched).
`tests/test_gm_login_state_guard.py`'s end-to-end login test is unaffected
by this change (it does not assert on the trailing bytes), but is a
separate, already-known casualty of `CORE-REQUEST-020` (below) once that
lands, not of this fix.

nonclaim: this closes the specific `ErrorData=28317` failure mode `RE-113`
traced -- it does not itself prove a real client accepts the corrected
frame (that needs an attended GT rerun), and it does not touch
`field_0x0b_second`'s value (still `0`, unproven-but-safe pending
`CORE-REQUEST-020`) or any other field semantics. Wire/DB evidence only,
no client-observable claim from this lane's own testing this round.

## Modules delivered (round `dnh0ai`, pf-adversary sweep of newer modules)

`CORE-REQUEST-011`/`012` stay blocked (the two-wide-string semantic gap in
`GM_RunGMCommandVital` still needs a live capture, `GAME_TEST_QUEUE.md`
GT-103 -- see "RE requests open" below, unchanged this round), so this
round's own write-zone work is a full `pf-adversary` pass over every `gm/`
module added since round `50x5xt`'s sweep (`say_wire.py`, `teleport_wire.py`,
`warp_executor.py`, `npc_switch_catalog.py`, `login_scene_override.py`) plus
a re-check of the whole package.

- **`gm/commands.py`**: `describe_warp_target`/`describe_npc_target` checked
  `command.args`'s *shape* via `_require_args_tuple` (the round `50x5xt` fix)
  but then called bare `int(args[0])`/`int(args[1])` with no
  `try`/`except` -- a shape-valid tuple with non-numeric content
  (`GmCommand("warp", ("abc",), "warp abc")`) crashed with an uncaught
  `ValueError` instead of this module's own `GmCommandArgsError`, directly
  contradicting the "regardless of source" contract `GmCommandArgsError`'s
  own docstring states. Not reachable from any live path today (`grep -rn
  "describe_warp_target|describe_npc_target" src/` -- called only from this
  module's own tests, not yet wired into `runtime.py`/`lane_hooks/`), but
  latent: the moment a future round bridges the still-unmapped `0x51E9` wide
  strings (RE-091) into a `GmCommand` that skips `parse_gm_command`, this
  was going to be exactly the crash it hit. Fixed with a new
  `_require_arg_int` helper (mirrors `_require_int`'s error message, raises
  `GmCommandArgsError` not `GmCommandParseError` -- the args-shape family,
  since this is the "regardless of source" path, not the parse-from-text
  path).
- No other finding: rate limiter, filename-collision loop, wire codec
  round-trips (`command_wire.py`, `teleport_wire.py`), fail-closed
  authorization (`accounts.py`/`dispatch.py`/`login_scene_override.py`), and
  the two committed data-table SHA pins (`scene_catalog.py`,
  `npc_switch_catalog.py`) were all specifically tried against and held.
- `tests/test_gm_commands.py`: 2 new tests in `ArgsShapeGuardTests` --
  `describe_warp_target`/`describe_npc_target` each reject a shape-valid,
  content-invalid tuple with `GmCommandArgsError`.

`tests/test_gm_*.py`: 234/234 (up from 232 -- the 2 new tests above).
Repo-wide `pytest tests/ --continue-on-collection-errors`: 3536 passed, 212
skipped, 17 pre-existing `capstone`-import collection errors only (same
baseline every prior round reports, confirmed unrelated by inspection --
`ModuleNotFoundError: No module named 'capstone'`, not a `gm/` import), no
new failures.

nonclaim: pure robustness fix inside this lane's own write zone -- the bug
was unreachable from any live path before this fix and still is after it
(no caller of `describe_warp_target`/`describe_npc_target` exists yet); no
wire fact, no RE citation, no `runtime.py` edit, no command's happy-path
behavior changed. This round sent no frame and ran no game test.

## Modules delivered (round `3a0tly`, literal byte-tail regression proof)

`CORE-REQUEST-011`/`012` stay blocked (unchanged since round `dnh0ai` / chief's
2026-08-27T22:00+07:00 reply), and GT-103 (the command-wire capture matrix)
stays `[PENDING]` on an attended runner. An attended-session nudge
(`pf_bridge/notes_to_chief/20260827_2305_KA1A-NUDGE-*.md`) pointed out this
lane had real write-zone work available anyway: both fixes needed for the
next login-state attended attempt (RE-113's trailing change-mask byte, round
`fmgvbx`; `CORE-REQUEST-020`'s `field_0x0b_second=1`, confirmed on main R198/
R199) had landed, but no test asserted the exact literal byte tail those two
fixes together are supposed to produce -- the two existing
`tests/test_gm_login_state_guard.py` tests both compare the dispatcher's
output against `state_wire.make_gm_update_state_frame`, the same function
`runtime.py`'s real call site uses, so a bug inside that shared function
could pass both sides identically and slip through.

- **`tests/test_gm_login_state_guard.py`**: one new test,
  `test_the_re113_plus_core_request_020_frame_matches_a_literal_hex_tail`.
  Drives a GM-account login through the real dispatcher (same harness as the
  file's other two tests) and asserts the frame's tail against a
  hand-written, byte-by-byte literal -- not computed from any function under
  test:
  ```
  12 19 5A  0B 00  0B 00  0B 01  14 00 00 00 00  0B 00
  ```
  (`u16tag(0x12, 0x5A19)` vital id LE; `u8tag(0x0B, 0)` RE-105's confirmed
  version; `field_0x0b_first=0`; `field_0x0b_second=1` per CORE-REQUEST-020;
  `u32tag(0x14, 0)` `field_0x14`; RE-113's trailing `u8tag(0x0B, 0)`
  change-mask byte). No production code changed -- this is a regression-proof
  addition only.
- `tests/test_gm_*.py`: 235/235 (up from 234). Repo-wide
  `pytest tests/ --continue-on-collection-errors`: 3586 passed, 212 skipped,
  17 pre-existing `capstone`-import collection errors only (same baseline
  every prior round reports), no new failures.
- `pf_bridge/GAME_TEST_QUEUE.md`: opened `GT-107-R3`, the attended session
  that fires this exact frame at a real client for the first time since the
  two fixes landed -- see `pf_bridge/rounds/GM_20260828_0022_*.md` for the
  full letter. `GT-107`'s own header corrected from a stale `[PENDING]` to
  reflect its actual negative result (error 28317, superseded by `GT-107-R3`).

nonclaim: headless-only round. No frame was fired at a real client. The
literal byte tail above is what the dispatcher assembles today, proven at the
Python level only -- whether a real client accepts it, and whether the
`BT_GM` button actually renders, are exactly the two questions `GT-107-R3`
exists to answer and this round does not claim either one.

## Attempted and retracted (broadcast-wire round)

This round tried to give `say` a wire codec for `Channel_GMGlobalMessageVital`
(0x9F2C), reading only `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`
(`UNTAGGED_WSTRING16LE_LEN32LE`, no tag byte) and `PF_FIELD_VALIDATION.tsv`
(one real R-direction frame). A `pf-adversary` pass (three rounds: initial
review, fix-verify, a final targeted check) eventually caught what the first
two passes did not: this repository's own `reports/
PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md` and
`src/pirateforce_foundation/channel_message_hypothesis.py` already prove a
**different, tag-prefixed** wire shape for this exact message (`tag 0x48 +
u32 byte-length + UTF-16LE`, not the untagged shape this round built) --
corroborated against real captured frames, not merely a static table row.
The draft codec this round wrote would have produced bytes the real client
almost certainly does not accept.

**Root cause: this round's "ค้นก่อนถอด" search never covered this
repository's own `reports/`, `docs/`, or sibling `src/` modules** -- only
`pf_bridge/external/` and `pf_bridge/gamedata/`, per the letter that opened
this lane. That letter's search scope is right for client-binary facts but
was wrongly treated as the *entire* search obligation; a working,
better-proven implementation was sitting in this same repository the whole
time. The draft module (`gm/broadcast_wire.py`) and its tests were deleted
rather than committed, once found to be wrong -- see the corrected wire-facts
table row above for what actually holds.

**For any future round**: `say`'s wire needs are already met by
`channel_message_hypothesis.py` (`SHARED_SERIALIZER_CHANNEL_IDS
["Channel_GMGlobalMessageVital"] = 0x9F2C`, field order `speaker`/`body`
proven). Bridge `gm/commands.py`'s parsed `say` `GmCommand` to that module's
existing encode function via import -- do not write a second codec in this
lane's zone. That module's own docstring notes its dispatch is currently
opt-in/`test_only: true` behind a scenario allowlist, not wired to any live
connection by default -- coordinate with whichever lane owns it (CHAT-ECHO/
CHAT-CHANNEL work, chief round 76) before importing, the same courtesy
GM-003's own "reuse via import, never copy" rule already asks for `world_
scene_travel.py`/`field_mob_tables.py`.

## What is intentionally NOT built yet, and why

- `state_wire` IS wired into the login path as of `CORE-REQUEST-006`
  (round R180, `runtime.py` ~line 4353): after a successful login, if
  `is_gm_account()` is true and `state_wire.
  GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` is not `None` (`CORE-REQUEST-016`'s
  guard), `make_gm_update_state_frame` is called with that constant as the
  version and the resulting frame is queued to that connection, no scenario
  flag. `is_gm_account()` failures are refused-by-name (login proceeds with
  no GM frame) so a config typo cannot take down the listener thread for
  every player -- see the comment at the call site.
  **UPDATED (round `kcm8ir`): the version is no longer an unproven
  placeholder.** This section used to say the call passed a hardcoded `1`
  tagged `[ASSUMED - awaiting RE]` -- `GT-101` (attended) proved that exact
  byte kills the session on a real client (modal `ErrorData=23065`), and
  `RE-105` (STATIC-ON-BRIDGE, DONE/PASS) then pinned the correct value as
  `0`. `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` is `0` now, not `None` and
  not `1` -- see "RE requests closed" item 5 and "Modules delivered (RE-105
  vital-version-pin round)" below for the full trail. Do not re-hardcode `1`
  here or at the call site; that is the byte GT-101 measured as fatal.
  The three payload fields (`0, 0, 0`) are a separate, still-open question:
  `RE-089 GM-STATE-VISUAL-001` came back **DONE/BOUNDED-NEGATIVE** (see
  wire-facts table): it pins the propagation path but finds no render/UI
  consumer, so it answers CORE-REQUEST-GM-001 without unblocking a semantic
  rename. What still needs to resolve real semantics is a capture/attended
  matrix (RE-089's own stated next step), not yet opened.
- No command *execution* path wired to a live connection (see
  `gm/commands.py` scope note above). `gm/teleport_wire.py` gives `warp` a
  real, tested byte builder for `ForcePos`/`CWarpResult`/`TeleportVital`,
  `gm/warp_executor.py` bridges the same-scene case into a ready `ForcePos`
  frame, `gm/say_wire.py` (this round) bridges `say` into a ready
  `Channel_GMGlobalMessageVital` frame, and `gm/dispatch.py` gives 0x51E9 an
  inbound authorization gate and a real capture sink. `CORE-REQUEST-010`
  (that last piece) **is wired and merged to `main`** as of chief round R190
  (`pirate-force-server@dfa61ac`, confirmed an ancestor of `main` this round
  via `git merge-base --is-ancestor`; `runtime.py`'s
  `GM_RUN_GM_COMMAND_VITAL_ID` branch, always on, no scenario flag) -- it
  counts and authorizes/refuses every inbound 0x51E9 frame and writes a
  capture file (`capture/gm_command_capture/`, see `gm/command_capture.py`)
  for authorized ones, but still does not decode the two wide strings into a
  `GmCommand` and sends no reply, so no command source exists yet that could
  drive `warp_executor.py`/`say_wire.py` from a real client. Because this
  path is now live on `main`, GM-002's attended capture matrix (real GM
  account, real client, real 0x51E9 frames landing in that capture
  directory) is runnable for the first time this round -- see
  `GAME_TEST_QUEUE.md` GT-103's GM-002 entry (filed this round). Sending
  anything
  *to* a socket still needs a runtime send path outside this lane's write
  zone, so execution stays not-built until `CORE-REQUEST-011` (same-scene
  warp) and `CORE-REQUEST-012` (say broadcast) -- both proposed, neither
  wired yet -- and a future `CORE-REQUEST-GM-<nnn>` (everything else) land.
  Even once wired, `CORE-REQUEST-011` only covers `warp` when the target
  scene_id matches the connection's current scene -- scene-crossing `warp`,
  `npc`, `item`, `lv`, and `spawn` all still need work beyond this round
  (spawn and cross-scene warp need RE the lane does not have yet;
  `npc`/`item`/`lv` need write access to player/world state in
  `runtime.py`). Separately, the wide-string field mapping in
  `GM_RunGMCommandVital` still needs to be proven enough to bridge real
  client input into `gm/commands.py`'s
  grammar -- `warp_executor.py` takes an already-parsed `GmCommand`
  regardless of source, same policy choice `gm/commands.py` itself makes.
- No general lane-A scene registry or lane-B mob roster reuse in
  `gm/commands.py`. Both lanes' current modules
  (`world_scene_travel.py`, `field_mob_tables.py`) are single-destination /
  single-scene, not general id->data lookups; importing them for a generic
  multi-scene `warp`/`spawn` command would misrepresent what they actually
  cover. `gm/scene_catalog.py` (this lane's own, from committed gamedata) is
  used only as a non-blocking name hint for `warp`, never as proof a warp
  target is reachable.
- ~~No per-account rate limit on authorized `0x51E9` capture writes~~ --
  **closed round `kzwdle`**, see "Modules delivered (round `kzwdle`,
  rate-limit + collision-loop bound)" below. `gm/dispatch.py` now enforces
  `RATE_LIMIT_MAX_CALLS_PER_WINDOW` per account per
  `RATE_LIMIT_WINDOW_SECONDS`, and `gm/command_capture.py`'s filename
  collision retry loop is bounded (`_MAX_FILENAME_COLLISION_ATTEMPTS`)
  instead of unbounded. No `CORE-REQUEST` was needed -- both fixes are
  fully inside this lane's own write zone.

## Nonclaim rule

Every PR and every attended test entry that uses a GM shortcut states, in
one line, which step the shortcut skipped, e.g.:

> nonclaim: reached the target scene via GM warp; this does not exercise or
> claim the player-driven travel/scene-load path.

## RE requests closed

1. `GM_RunGMCommandVital` (`0x00729E10`/`0x00726C20`): **CLOSED structurally
   by RE-088** (one presence flag, one nested body, no proven sub-opcode --
   see wire-facts table). `GM_RunGMCommandResultVital` (`0x00729790`): the
   single u8 result field at `+0x14` is proven positionally (RE-088).
2. `GM_UpdateGMStateVital` handler `0x00729F00`: **CLOSED
   DONE/BOUNDED-NEGATIVE by RE-089**. Byte/byte/u32 propagation into
   `GMModule_Client` is pinned; `bm_gm.tga` is disproven as a GM indicator
   (it is an unrelated damage-number glyph). No render/UI consumer found --
   field semantics stay unproven pending a capture/attended matrix, which
   RE-089 names as the next step but does not itself open.
3. `TeleportVital` / `ForcePos` / `CWarpResult` field layout: **CLOSED
   PASS/DONE by RE-090**, T0-T3 all closed including optional
   `TeleportCheckVital`. See wire-facts table; codec in
   `gm/teleport_wire.py`. Natural network direction for `ForcePos`/
   `CWarpResult` is not part of what RE-090 proves and stays open if it
   matters later.
4. Chat input -> 0x51E9 trigger condition: **CLOSED PASS/DONE by RE-091**.
   The real client's trigger is a dedicated GM editor widget (Enter, non-
   empty text), not a prefix check on normal chat; normal chat is a
   separate `Channel_*MessageVital` family with no prefix branch to
   0x51E9 anywhere in its 365-byte CFG. This project's own chat-text-as-
   GM-command design (`gm/commands.py`) is a policy choice this result does
   not validate or invalidate -- see "Modules delivered (RE-089/090/091
   follow-up round)" above.
5. `GM_UpdateGMStateVital` (`0x5A19`) wire version: **CLOSED DONE/PASS by
   RE-105**
   (`notes_to_chief/20260827_1613_RE-105-RESULT-VITAL-VERSION-ZERO-GENERIC-MISMATCH-PATH.md`).
   The generic VitalData collection reader (`[0x005F3E20,0x005F406D)`) does
   an exact-equality compare against `message+0x10`, and the `0x5A19`
   prototype's own bootstrap constructor stores that byte as `0` directly --
   not inferred from any other vital. `gm/state_wire.py`'s
   `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` is now pinned to `0` (was `None`
   since `CORE-REQUEST-016`); `runtime.py`'s call site is unchanged code
   (still gated on that constant), so this closes purely inside this lane's
   write zone -- no new `CORE-REQUEST` needed. See "Modules delivered
   (RE-105 vital-version-pin round)" below for the byte-level proof.
6. GM editor widget open/toggle trigger: **CLOSED PASS/DONE by RE-104**
   (`notes_to_chief/20260827_1518_RE-104-RESULT-BT-GM-MODULE-PLUS19-GATE.md`).
   The trigger is UI resource `BT_GM`, shown/enabled from connection query
   type `0x25` returning `GMModule_Client+0x19`; click re-checks the same
   gate, then opens dedicated panel `GMUI_BASIC` (`Radiobutton_Message` +
   `TextBox_Message`, Enter to send -- the producer RE-091 already proved).
   No screen coordinate or icon texture is claimed; this closes the *trigger
   mechanism* only. Static corpus gives no evidence either way on whether a
   non-GM account can see the `BT_GM` control -- that stays an open question
   for a real capture/attended matrix, same as `GM_UpdateGMStateVital`'s
   three field meanings below.
7. `GM_UpdateGMStateVital` (`0x5A19`) `GSCN_RunTimeProtocolRes` envelope,
   `ErrorData=28317`: **CLOSED PASS/DONE by RE-113** (round `fmgvbx`,
   `pf_bridge/CLIENT_RE_QUEUE.md`). Not a field-layout defect in the vital
   itself -- `gm/state_wire.py` built the frame via the legacy bridge's
   singular `make_runtime_vital()` helper, which omits a trailing
   derived-class change-mask byte (`u8tag(0x0B, 0)`) that
   `GSCN_RunTimeProtocolRes` v4 requires after its VitalData collection; the
   sibling `make_runtime_vitals()` helper appends it and already carries a
   comment citing this exact error code, independently corroborated three
   times in `reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md`
   Sec.(c). Fixed this round -- see "Modules delivered (round `fmgvbx`,
   RE-113 trailing-mask fix)" below. Residual bounded-negative: no single
   client-binary instruction address was found for the trailing-byte read
   itself (the proof rests on the legacy bridge's own code comment plus the
   committed report's wire/behavioral precedent, not a fresh disassembly of
   this exact continuation) -- does not block closure.

## RE requests open (owned by static RE lane, filed via chief)

None filed by this lane are open as of round `4djeqi`.

`RE-118` (round `y2nhzz`, `pf_bridge/CLIENT_RE_QUEUE.md`) is now **CLOSED
PASS/DONE** (round `4djeqi`,
`notes_to_chief/20260828_0411_RE-118-RESULT-CURRENT-UI-KEY-MUST-BE-NONEMPTY.md`):
the click chain from `BT_GM` uses only the existing `GMModule_Client+0x19`
gate (`+0x18`/`+0x1C` are read by an unrelated adapter, not this click path
-- do not tweak them). After that gate passes, dispatcher `0x00AA0710`
requires a non-null current-UI object whose vfunc `+0x04` returns a
non-empty UTF-16 key; when the key is empty, factory `0x007280D0` is never
reached and nothing is logged -- exactly the silent no-window/no-frame
outcome `GT-107-R3` observed. No new field on `0x5A19` needed. Static
cannot say whether the key was actually empty during that specific run, so
`GT-103` now carries an attended A/B step (click from an empty HUD vs. click
after opening a panel known to give a non-empty current-UI key,
`pf_bridge/GAME_TEST_QUEUE.md`) instead of staying blocked.

RE-088, RE-089, RE-090, RE-091, RE-104, RE-105, RE-113, and RE-118 are all
closed (see above) -- kept here so the next round does not have to
re-derive that from the closed list.

Remaining semantic gaps (what the
`GM_RunGMCommandVital` two wide strings and three scalars mean; what the
`GM_RunGMCommandResultVital` byte means; what `GM_UpdateGMStateVital`'s
three fields mean; what the `TeleportVital`/`CWarpResult` positional-only
fields mean; natural direction for `ForcePos`/`CWarpResult`) all need real
captured frames, not more static reading. `PF_FIELD_VALIDATION.tsv` is
NOT_OBSERVED (zero frames) for `ForcePos`/`CWarpResult` and for every other
message named above -- `TeleportVital` is the one exception, already noted
in the wire-facts table: 132 candidate frames per direction at
`A2_STATIC_OPEN` (candidate-matched, not parse-confirmed), so those bytes
exist to check field meaning and the `TeleportTarget` field-order caveat
against, they just have not been run through this codec yet. That check
(and everything else in this list) is attended-test / capture territory
(GM-002), not a new RE ticket, until this lane has a build that can
generate or observe one of these messages live.

## Modules delivered (round `w8t8vi`, one level deeper than the args-shape hardening)

`CORE-REQUEST-011`/`012` stay blocked (unchanged), and `GT-103`/`GT-107-R3`
stay `[PENDING]` on an attended runner -- nothing new to report on either.
This round instead ran the lane's own recurring `pf-adversary` sweep of
`gm/` and found a real gap in a bug class the lane's docstrings otherwise
describe as closed: every prior round hardened the `GmCommand.args`
*container* shape (`type(args) is not tuple`, broad `except Exception`), but
three call sites still only guarded the individual scalar *conversion* one
step deeper with `except (TypeError, ValueError)`, which a hand-built
element's `__int__`/`__float__` can raise past (an `AttributeError`, a
`KeyError`, anything else) -- exactly the same "hand this module a
`GmCommand` regardless of source" threat model, one field further in.

- **`gm/warp_executor.py`** `_require_int`/`_require_finite_float`: now
  catch `Exception` broadly, matching the container-shape guard already
  above them in the same module.
- **`gm/commands.py`** `_require_arg_int` (used by `describe_warp_target`/
  `describe_npc_target`): same fix, same reasoning.
- **`gm/commands.py`** `log_gm_command`: a shape-valid `args` tuple holding
  a JSON-non-serializable element used to create the log directory and open
  the file for append *before* `json.dumps` ran, so a rejected call still
  left an empty file/directory behind -- violating the sibling
  shape-rejection test's own "writes nothing on rejection" contract for
  this different failure mode. `json.dumps` now runs before any filesystem
  mutation; only a successfully serialized line reaches `mkdir`/`open`.
- `tests/test_gm_*.py`: 240/240 (up from 235, five new regression tests: two
  in `test_gm_warp_executor.py`, three in `test_gm_commands.py`). No
  production behavior changed for any input that was already valid -- these
  three call sites still return the same value for every input that used to
  succeed; only the exception type/no-write guarantee changed for inputs
  that were always supposed to be refused.

nonclaim: headless-only round, no code outside `gm/`/`tests/gm_*` touched,
no frame fired at a real client, no `runtime.py` edit. Full detail:
`pf_bridge/rounds/GM_20260828_0127_args-shape-hardening-one-level-deeper.md`.

## Modules delivered (round `ccc9wj`, GT-110 standalone login-scene safety fix)

Answers `notes_to_chief/20260827_2240_KA1A-NOTE-GT110-unsafe-until-0x5A19-payload-fixed-plus-M1P-jobs-staged.md`:
`GT-110` (attended test of the login-scene override) required
`gm_accounts.json` membership, which makes `is_gm_account()` true, which
makes `runtime.py` send `GM_UpdateGMStateVital` (`0x5A19`) on login -- the
frame that killed `GT-101`/`GT-107` two different ways, one fix (`RE-113`)
landed but **not yet attended-reverified** (`GT-107-R3` still `[PENDING]`).
Running `GT-110` the old way risked a third crash for a question the ticket
never needed to ask.

- `gm/login_scene_override.py`: `get_login_scene_override` now checks TWO
  independent paths, either sufficient alone, both fresh every call, never
  cached: (1) the existing GM-gated path, unchanged; (2) a new
  **standalone** path (`load_standalone_login_scene_overrides`, config key
  `standalone_login_scene`, default `config/gm_login_scene_standalone.json`,
  env override `PF_GM_LOGIN_SCENE_STANDALONE_CONFIG`) that never calls
  `is_gm_account()` and never touches `gm_accounts.json` -- an account
  listed there gets a login scene_id and NOTHING else; it cannot become
  `is_gm_account()==True` through this path, so `runtime.py`'s
  `CORE-REQUEST-016`-gated `GM_UpdateGMStateVital` block never fires for
  it. `[สมมติของสาย GM - รอ COO ยืนยัน]`: this changes the module's own
  previously-stated security contract ("neither file alone can grant
  anything") -- see the struck-through paragraph above and
  `notes_to_chief/20260828_0222_LANE-GM-ASK-COO-standalone-login-scene-override-path.md`.
  Not built by touching `runtime.py`: the existing `CORE-REQUEST-015` call
  site (~~`get_login_scene_override(self.token)`~~) already routes through this
  function, so the new path activates at the existing wiring point with no
  core-file edit.
  - **CORRECTION** (LANE-GM round `38c4tv`, after `pirate-force-server#236`
    merged): that call site now calls
    `consume_login_scene_override(self.token)`. The routing claim above
    still holds -- the consumer resolves the scene through
    `get_login_scene_override`, so both maps are still consulted in the same
    order at the same wiring point -- but the standalone half comes back
    under the `STANDALONE_NOT_CONSUMED` outcome, which the call site
    reports as `gm_login_scene_override_standalone_kept_<scene>` and does
    NOT spend (`COO-DECISION 20260829_0542`). That branch is walked through
    the real dispatcher by
    `tests/test_gm_login_scene_override_standalone_at_login.py`.
  - **CORRECTION 2** (LANE-GM round `1fq5yf`, after `pirate-force-server#264`
    merged): the call shape shown here is the bare one and is no longer what
    the login site does -- it passes `scene_registry=scene_entry_registry`.
    The routing claim is unaffected (both maps are still consulted in the
    same order at the same wiring point); what changes is WHICH READING of
    lane A's registry admits an entry, and therefore which entries survive
    to be routed at all.
- `tests/test_gm_login_scene.py`: +7 tests for the standalone path
  (missing-file, grant-with-zero-`gm_accounts.json`-membership,
  gated-path-still-wins-with-**differing** scene_ids so the precedence
  assertion is actually load-bearing, unlisted-gets-none, malformed config,
  unknown scene_id). The original version of the precedence test used the
  *same* scene_id for both paths -- `pf-adversary` (round `ccc9wj`) built a
  deliberately-broken reimplementation that checks the standalone path
  first and showed it still passed that test; fixed by giving the two paths
  different scene_ids so a precedence regression cannot ship green.
- `tests/test_gm_login_scene_override_wiring.py`: +3 tests through the REAL
  dispatcher (not just the module in isolation) -- a GM-gated account gets
  both the override AND a `GM_UPDATE_STATE_AFTER_LOGIN` action (contrast
  case); a standalone-only account gets the override with that action
  **absent** from `state.dispatch()`'s own return value (the core safety
  claim, proven end to end, not just read from the source); a
  standalone-listed account still returns `is_gm_account() == False`.
  `pf-adversary` (round `ccc9wj`) flagged that the original version of this
  round's change had no dispatcher-level proof of the safety claim at all --
  these three tests close that gap.
- `GAME_TEST_QUEUE.md`: `GT-110`'s server args, pre-boot grep checks, pass
  criteria (added: no `GM_UPDATE_STATE_AFTER_LOGIN` line anywhere in the
  session, or FAIL regardless of what the screen shows), teardown, and
  nonclaims all rewritten for the standalone path; the ticket no longer
  waits on `GT-107-R3`.
- `tests/test_gm_*.py`: 250/250 green(cloud sanity) (240 before this round +
  7 offline standalone-path tests + 3 dispatcher-level wiring tests), no
  regression.

nonclaim: headless-only round, no `runtime.py` edit, no frame fired at a
real client -- `GT-110` itself (now unblocked) is what proves this on a
real client. Full detail:
`pf_bridge/rounds/GM_20260828_0222_gt110-standalone-login-scene-safety-fix.md`.

## Modules delivered (round `4djeqi`, RE-118 closed, no code change)

`RE-118` (opened round `y2nhzz`, asking static RE to trace why clicking
`BT_GM` produces nothing) came back CLOSED PASS/DONE this round -- see "RE
requests open" above, now empty, for the mechanism. No `gm/` module needed
a change: the gap is a client-side UI dispatch precondition (a non-empty
current-UI key), not a server-sent field. `pf_bridge/GAME_TEST_QUEUE.md`
`GT-103` gained an attended A/B step (further split into 2a/2b after a
same-round `pf-adversary` fix -- see that file's own "Correction" note in
`pf_bridge/rounds/GM_20260828_0418_re118-closed-gt103-ab-procedure-added.md`)
in place of its `BLOCKED-ON RE-118` header; `GT-107-R3`'s own RESULT text
is untouched as of this round's final push, with a pointer paragraph
appended after it -- this round's first push briefly edited that section's
`nonclaim:` line in place before `pf-adversary` caught it and a follow-up
commit restored it verbatim.

nonclaim: headless-only round, no `runtime.py` edit, no frame fired at a
real client, no `gm/` code touched. Full detail:
`pf_bridge/rounds/GM_20260828_0418_re118-closed-gt103-ab-procedure-added.md`.

## Modules delivered (round `i76is0`, allowlist exact-type fix + capture-volume quota)

`CORE-REQUEST-011`/`012` stay blocked (unchanged), `GT-103`'s A/B procedure
and `GT-110` stay `[PENDING]` on an attended runner. This round's own
write-zone work is a fresh `pf-adversary` sweep of the whole `gm/` package
(the last full sweep was round `w8t8vi`; `ccc9wj` reviewed only the module
it touched) -- found two real gaps, fixed both, plus one stale doc
reference corrected.

- **Fixed, HIGH -- `gm/accounts.py`, `gm/login_scene_override.py`,
  `gm/dispatch.py`**: all three checked `isinstance(account_name, str)`
  before using `account_name` as a dict/frozenset key -- the exact bug
  shape this package spent five documented rounds hardening for
  `GmCommand.args` (`type(args) is not tuple`, never `isinstance`, because
  `isinstance` admits a subclass that can lie through its own dunders), but
  that lesson had never reached the one check this whole package's security
  invariant is gated on. A `str` subclass overriding `__eq__`/`__hash__` to
  always compare equal to, and hash the same as, a real listed account name
  passed the old check, then made `frozenset.__contains__`
  (`accounts.is_gm_account`) or `dict.get` (`login_scene_override`) report
  a match for an account name that was never actually listed -- reproduced
  live in all three call sites. `type(account_name) is not str` rejects any
  subclass outright, so the object reaching the containment/lookup test is
  always a real, final `str`. Not shown to be reachable from a raw network
  byte stream today (`lane_hooks/lane_gm_run_command.py` passes
  `session.token`, produced by the login deserializer as a plain built-in
  `str`), but a real violation of this package's own "regardless of
  source" threat model for any in-process caller -- another lane's code, a
  future refactor wrapping an identity value, or a test double.
- **Fixed, HIGH -- `gm/dispatch.py`**: `MAX_RAW_PAYLOAD_LENGTH` (round
  `50x5xt`) bounds one call; `RATE_LIMIT_MAX_CALLS_PER_WINDOW`/
  `RATE_LIMIT_WINDOW_SECONDS` (round `kzwdle`) bound burst rate -- neither
  bounded *sustained total volume*. A scripted, already-listed GM account
  sending max-size payloads at the sustained-legal rate (never tripping
  `REFUSAL_RATE_LIMITED`) could write roughly 4 files/second, several
  hundred KB each once `command_capture.py`'s hex dump expands the raw
  bytes, unbounded over time, in one flat directory -- entirely inside the
  range of traffic the rate limiter was deliberately built generous enough
  to never refuse. New `MAX_CAPTURED_BYTES_PER_ACCOUNT` (50 MiB, generous
  against any real `GT-103` capture-matrix session) caps estimated total
  captured bytes per account for the life of the process (same accepted
  process-global/resets-on-restart scoping as the rate limiter above,
  `reset_capture_quota_state_for_tests()` mirrors
  `reset_rate_limit_state_for_tests()`), charged against an estimate of
  the actual capture-file size (`_estimate_capture_file_bytes`: 5x the raw
  payload length plus a 1 KiB header margin, deliberately at or above the
  hex dump's real ~4.75x expansion so the charge never undercounts real
  disk usage) rather than the raw payload length itself. New refusal
  reason `REFUSAL_CAPTURE_QUOTA_EXCEEDED` follows the same shape as every
  other refusal in this module: `authorized` stays `True` (the account
  really is GM), only `captured_path`/`refusal_reason` say nothing was
  written for that call.
- **Corrected, doc-only -- this file**: the "dispatch/authorization-gate
  round" and "What is intentionally NOT built yet" sections above still
  described `CORE-REQUEST-010` as `runtime.py`'s own inline
  `GM_RUN_GM_COMMAND_VITAL_ID` branch calling `gm/dispatch.py` directly.
  The real call site moved to `lane_hooks/lane_gm_run_command.py`
  (`hook("vital_inbound_gm_run_command")`, `production_allowed = True`)
  when `lane_hooks` landed -- verified this round to still be wired
  correctly (same arguments, `session.token` then `payload`, exceptions
  caught fail-closed by `lane_hooks.fire`'s own broad `except Exception`,
  never bypassing the allowlist check), so this was a documentation-drift
  finding, not a functional bug. Left the historical section text in
  place and did not rewrite it line-by-line (the mechanism it describes --
  authorize-then-capture, no reply frame -- is still accurate); this
  paragraph is the correction, per this lane's own precedent for logging
  drift rather than quietly editing stale prose.
- `tests/test_gm_accounts.py`, `tests/test_gm_login_scene.py`,
  `tests/test_gm_command_dispatch.py`: 9 new tests -- a `str` subclass
  lying through `__eq__`/`__hash__` is rejected (not treated as a match)
  in all three call sites; the capture quota refuses once the estimated
  total exceeds the cap while staying `authorized=True` and writing
  nothing; the quota is scoped per account, not global; a refused non-GM
  call never consumes a GM account's own quota; `reset_capture_quota_
  state_for_tests()` actually clears usage; the shipped 50 MiB default
  survives a realistic handful of same-second calls.

`tests/test_gm_*.py`: 259/259 (up from 250 -- 9 new tests, no existing
test changed). Repo-wide `python3 -m unittest discover -s tests`: 3846
tests, 18 pre-existing `capstone`-import collection errors only (same
baseline every prior round reports), no new failures.

nonclaim: pure robustness/correctness inside this lane's own write zone --
no command behavior changed on the happy path for any real (non-subclass)
`str` account name or any capture under the new 50 MiB/account cap; no
wire fact, no RE citation, and no `runtime.py` edit involved (the doc
correction only updates which file this lane's own docs cite, not any
code). This round sent no frame and ran no game test. Full detail:
`pf_bridge/rounds/GM_20260828_0517_allowlist-exact-type-plus-capture-quota.md`.

## Modules delivered (round `whoaop`, capture-quota estimate fix)

Mailbox empty, no new RE ticket, `CORE-REQUEST-011`/`012` still blocked
(unchanged since chief's 22:00 reply on Aug 27) -- this round's own
`pf-adversary` re-sweep of the whole `gm/` package (rule F: no second
consecutive empty round) found one real, reproduced defect in the round-
`i76is0` capture-quota guard itself.

- **Fixed, MODERATE -- `gm/dispatch.py` `_estimate_capture_file_bytes`**:
  the round-`i76is0` formula (`raw_payload_length * 5 + 1024`) was derived
  only from `command_capture._hex_dump`'s ~4.75x expansion. It ignored that
  `command_capture._decode_section` (present since RE-088 closed) re-prints
  the SAME bytes a second time whenever the payload decodes as a nonzero-
  presence nested body: `string_0x1c`/`string_0x38` go through
  `_escape_for_header`, i.e. `text.encode("unicode_escape").decode
  ("ascii")`, which costs up to 6 ASCII bytes per UTF-16LE code unit (2 raw
  bytes) for any BMP codepoint outside ASCII/Latin-1 -- a 3x expansion on
  top of the same bytes' ~4.75x hex-dump cost, for any real non-Latin1 text
  a GM account could type (Thai included). Reproduced: a 65,534-byte
  payload built as a valid nested body with Thai-character wide strings
  charged an estimate of 328,694 bytes against an actual file write of
  508,235 bytes -- a 1.546x overrun, letting an already-authorized GM
  account exceed `MAX_CAPTURED_BYTES_PER_ACCOUNT` (50 MiB) by roughly 27.5
  MiB before `REFUSAL_CAPTURE_QUOTA_EXCEEDED` ever fired. The estimate's
  own comment claimed an invariant ("always meets or exceeds what
  `capture_raw_gm_command` actually writes") that was false for this input
  shape. New formula: `raw_payload_length * 8 + 2048` (hex dump 4.75x +
  decode-section worst case 3x = 7.75x, rounded up; flat term doubled to
  cover the header lines outside `raw_payload_length`) -- verified against
  the same worst-case reproduction (empirically, not just by the 7.75x
  derivation) before landing.
- Why the round-`i76is0` test suite never caught this: every quota test
  used `bytes(1000)` (all zero bytes, `presence=0`), which
  `_decode_section` renders as one fixed, content-independent line -- the
  code path that actually breaks the estimate (a decoded nested body with
  non-ASCII wide-string content) had no test at all. `grep` confirmed no
  existing test referenced `_estimate_capture_file_bytes`, `unicode_escape`,
  or non-ASCII payload content before this round.
- `tests/test_gm_command_dispatch.py`: one new test,
  `test_capture_quota_estimate_covers_non_ascii_decode_section_reprint`,
  builds the same worst-case Thai-heavy nested-body payload at
  `MAX_RAW_PAYLOAD_LENGTH`, runs it through the real
  `handle_gm_run_command_vital` -> `capture_raw_gm_command` path, and
  asserts the estimate is `>=` the actual file size written on disk (fails
  under the old formula, passes under the new one). The four existing
  quota tests that hardcoded the old formula's derived constant (`6024` for
  a 1000-byte payload) now compute it via
  `gm_dispatch._estimate_capture_file_bytes(1000)` instead, so they no
  longer silently drift out of sync with whatever the real formula is.

`tests/test_gm_*.py`: 260/260 (up from 259 -- 1 new test, 4 existing tests
updated to stop hardcoding the old formula's derived constant, no test
behavior narrowed).

nonclaim: pure accounting-correctness fix inside this lane's own write
zone -- no command behavior changed for any payload under the (now
correctly enforced) 50 MiB/account cap; no wire fact, no RE citation, and
no `runtime.py` edit involved. This round sent no frame and ran no game
test. Full detail: `pf_bridge/rounds/GM_20260828_0727_capture-quota-estimate-fix.md`.

## Modules delivered (round `vb3ktn`, capture-file permission fix + mailbox backfill)

Mailbox scan (correct `<filename>.md.CONSUMED.txt` standard, per
`20260828_0043_COO-DECISION-consumed-txt-naming-standard.md`, with the
legacy no-`.md` pattern checked as a fallback) found 5 letters addressed to
or opened by this lane with no stub in either location: `RE-088-RESULT`,
`RE-089-RESULT` (already consumed once by chief, but only at a
non-standard `notes_to_chief/consumed/` path this lane's own scan never
checks -- a stub-*location* gap, not a naming gap), and three of this
lane's own `ASK-COO` letters whose replies had already landed and were
already actionable (`pr131-pr72-undraft`, `two-consumed-txt-naming-
conventions`, `standalone-login-scene-override-path`). All 5 stubbed this
round at the correct top-level path; none needed new code action --
their content was already folded into this lane's code/docs by earlier
rounds. See `pf_bridge/rounds/GM_20260828_0824_mailbox-backfill-plus-capture-file-permission-fix.md`
for the full list.

`CORE-REQUEST-011`/`012` stay blocked (unchanged), `GT-103`/`GT-107-R3`/
`GT-110` all stay `[PENDING]`/attended-only. This round's own write-zone
work is a fresh `pf-adversary`-style pass over `gm/command_capture.py`
(the module handling real inbound bytes since `CORE-REQUEST-010` landed)
that found one real, reproduced gap no prior sweep of this file had
caught:

- **Fixed, MEDIUM -- `gm/command_capture.py`**: the capture-file write used
  raw `os.open(out_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)` with no
  explicit `mode` argument. Unlike the builtin `open()` this codebase uses
  everywhere else for file writes (`commands.py`'s `log_gm_command`,
  default mode `0o666` masked by umask, never an execute bit), `os.open`
  with no `mode` defaults to `0o777`. Reproduced live under this
  project's own default umask (`0o022`): the old call produced file mode
  `0o755` -- world-readable **and** world-executable -- for a file whose
  own module docstring already describes its contents as sensitive
  ("a decoded string comes straight from client-controlled bytes"): real
  account names and free-text a GM typed into the in-game command editor.
  Under a more permissive host umask (e.g. `0o000`) the same call would
  have produced a world-*writable* forensic file. Fixed with an explicit
  `mode=0o600` (owner read/write only, no execute for anyone) -- verified
  live to hold regardless of umask (0o600 has no group/other bits for any
  umask to need to clear; tested under a deliberately permissive `0o000`
  umask, not just this container's default). `grep`-confirmed this is the
  only `os.open` call site in `gm/`; every other file write in the package
  goes through `Path.open`/builtin `open`, already safe.
- `tests/test_gm_command_capture.py`: one new test,
  `test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask`,
  forces `umask(0o000)` for the duration of one capture call and asserts
  the resulting file mode is exactly `0o600` -- a test that would have
  failed under the pre-fix code (mode `0o777` under a `0o000` umask) and
  cannot pass by accident of this container's own umask.

`tests/test_gm_*.py`: 261/261 (up from 260 -- 1 new test, no existing test
changed or narrowed). Repo-wide `pytest tests/ --continue-on-collection-errors`:
3703 passed, 212 skipped, 5035 subtests passed, 17 pre-existing
`capstone`-import collection errors only (same baseline every prior round
reports, confirmed unrelated by inspection), no new failures.

nonclaim: pure file-permission hardening inside this lane's own write
zone -- no command behavior changed for any caller, no wire fact, no RE
citation, and no `runtime.py` edit involved. This round sent no frame and
ran no game test. Full detail:
`pf_bridge/rounds/GM_20260828_0824_mailbox-backfill-plus-capture-file-permission-fix.md`.

## Round `vb3ktn`'s own PR did not merge -- recovered and fixed this round

Round-lock check (this round, per ADDENDUM v2) found `pirate-force-server`
PR #185 (the companion PR for the round directly above) `state=closed`,
`merged=false` -- gate RED, closed by `.github/workflows/merge-claude-pr.yml`'s
reaper. **This lane's `pf_bridge` companion PR #285 merged fine**; only the
server-side PR failed, so `docs/GM_LANE.md`'s own "round `vb3ktn`" section
above describes a fix that was never actually on `main` until this round.

Root cause (from the failed run's own job log,
`https://github.com/panyaasanee/pirate-force-server/actions/runs/33132956815`):
`pytest_subset` failed on exactly the new regression test,
`test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask` --
`AssertionError: 438 != 384 : 0o666`. The assertion is POSIX-only: NTFS has
no POSIX permission-bit split, and CPython's `os.open()` on Windows only
ever inspects the `mode` argument for one bit (writable vs read-only) --
any owner/group/other split, including the `0o600` the fix passes, is
accepted and silently ignored. This project's real gate runs on
`windows-latest` on purpose (`.github/workflows/gate-windows.yml`'s own
docstring: it exists because the real deployment target is Panya's Windows
bridge), so the previous round's fix was correct in intent but its test
could never have passed the gate it was written against -- the previous
round verified it under this sandbox's own POSIX `pytest`, which cannot
surface a Windows-only divergence.

Fixed this round: cherry-picked the stranded commit
(`9bdc24b`, verbatim, from the kept branch `claude/upbeat-knuth-wipchl` --
nothing on it was lost, per the reaper's own comment) and made the
assertion `os.name`-conditional -- exact `0o600` on POSIX (unchanged
strength there), and on Windows only "the call succeeds and a real file
exists" (the strongest true statement available, since NTFS genuinely
cannot report what this fix asked for). No behavior in
`gm/command_capture.py` itself changed from the cherry-picked commit.

**Security-relevant finding, not swept under the rug**: this means the
`mode=0o600` argument provides real owner-only enforcement in every POSIX
CI/sandbox environment this project runs in, but **provides no enforcement
at all on the actual Windows production bridge** -- there,
`capture/gm_command_capture/*.txt` (real account names, free-text a GM
typed) is only as private as the containing directory's NTFS ACL, which a
plain-file `os.open()` call cannot set and which this lane's write zone has
no ACL API (`pywin32`/`icacls`) available to touch. Flagged to COO in
`pf_bridge/notes_to_chief/` this round (`ASK-COO`, not blocking -- this is
the same exposure the pre-fix code always had on Windows, not a new
regression) rather than either quietly weakening the test or claiming a
protection this platform cannot deliver.

`tests/test_gm_*.py`: 261/261 (unchanged count -- one test's assertion
strengthened/branched, none added or removed, none narrowed on the
platform where it already worked). Repo-wide
`pytest tests/ --continue-on-collection-errors`: 3706 passed, 212 skipped,
5035 subtests passed, 17 pre-existing `capstone`-import collection errors
only (same baseline every prior round reports; the higher `passed` count
vs the previous entry's `3703` is `main` having advanced with LANE-B's
RE-122 stat-fabrication-guard test in the meantime, unrelated to this
lane), no new failures.

nonclaim: recovery + a POSIX-vs-Windows portability fix inside this lane's
own write zone -- no `gm/` command behavior changed, no wire fact, no RE
citation, no `runtime.py` edit. This round sent no frame and ran no game
test. Full detail: `pf_bridge/rounds/GM_20260828_0920_round-lock-recovery-windows-gate-fix-plus-mailbox-backfill.md`.

## Round `usinho`: `log_gm_command` permission fix + shared `capture/` parent directory retightening

Round-lock check: both repos' most recent `[LANE-GM]` PRs (`pf_bridge#285`,
`pirate-force-server#188`) confirmed `merged=true` on `main` -- nothing to
recover. Mailbox: one item pending, `COO-DECISION-capture-file-windows-acl-
risk-accepted` (answers this lane's own prior `ASK-COO`) -- risk accepted
as proposed, no code action, stubbed.

A `pf-adversary` sweep of every file in this write zone (first sweep since
round `i76is0`) found `gm/commands.py`'s `log_gm_command` reintroduced the
exact permission-bug class round `vb3ktn` fixed for `gm/command_capture.py`:
its ndjson audit file (full `say`-message bodies and other GM-typed
free-text) was created via builtin `open("a")` with no explicit mode
(`0o666` masked by umask -- world-readable, world-writable under a
permissive umask), in a sibling file the `vb3ktn` fix never touched.
Fixed with the same `os.open(..., mode=0o600)` pattern.

The same sweep found both `log_gm_command`'s and `capture_raw_gm_command`'s
containing directories were created via `mkdir` with no explicit mode --
under a permissive umask the directory itself is world-writable even
though the files inside are `0o600`, letting another local user delete or
rename them without disclosure. First fix pass added `mode=0o700` to both
leaf `mkdir` calls; a follow-up `pf-adversary` verification pass on that
exact diff then found the fix was incomplete: `Path.mkdir(exist_ok=True)`
never chmods a directory that already exists, and `DEFAULT_LOG_PATH` and
`DEFAULT_CAPTURE_ROOT` share the literal parent `capture/` (`.gitignore`
documents it as never cleaned up) -- whichever function ran first on a
real host would lock that shared parent at whatever mode the umask in
effect at that one moment produced, forever. Fixed with an unconditional
`os.chmod(leaf_dir, 0o700)` after `mkdir` on every call, not just first
creation, plus two new tests that create the directory loose (`0o777`)
first to prove the retightening actually fires.

Same Windows caveat as round `vb3ktn`'s original fix applies to every mode
bit in this round's diff: NTFS ignores the owner/group/other split
entirely, so none of this provides real enforcement on the actual
production bridge -- only on every POSIX CI/sandbox this project runs in.
Not a new regression; not re-flagged to COO since it is the identical,
already-accepted risk the standing `20260828_0945_COO-DECISION` covers.

`tests/test_gm_*.py`: 266/266 (up from 261 -- 5 new tests, 0 removed, 0
narrowed). Repo-wide `pytest tests/ --continue-on-collection-errors`: 3717
passed, 212 skipped, 5035 subtests passed, 17 pre-existing `capstone`-import
collection errors only (same baseline every prior round reports), no new
failures. เขียว (local pytest, this session).

## ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `usinho`)

ไม่มีอะไรใหม่บนจอ -- headless-only ล้วน เป็นการอุดช่องโหว่สิทธิ์ไฟล์/โฟลเดอร์ในเขตเขียนของ
สายนี้เท่านั้น ไม่มีผลต่อพฤติกรรมคำสั่ง GM ใด ๆ ที่ผู้เทสเห็นบนจอ

nonclaim: security-hardening ล้วนในเขตเขียนของสายนี้เอง ไม่มีการยิงเฟรมใส่ client จริง
ไม่มีการรันเทสในเกม ไม่แตะ `runtime.py` ไม่เพิ่มบัญชีใดลง `gm_accounts.json`. Full
detail: `pf_bridge/rounds/GM_20260828_1035_log-permission-fix-plus-capture-dir-retighten.md`.

## Round `hs9m2r`: the GM button is dead -- take the chat box instead

> **CORRECTION (round `fo2lgh`, from RE-126 RESULT 2026-08-28T18:09+07:00).**
> The heading's *observation* stands: two attended rounds clicked `BT_GM` and
> the client stayed silent. The *explanation* this lane was carrying does not.
> RE-126 asked whether the rendered button and the control the handler
> registers are different objects, and the answer is **no, they are the same
> object** -- the binder writes the `BT_GM` lookup result to `this+0x48` at
> `0x0053B0CB`, and the same vtable's dispatcher (`0x00F21FA8+0x28`) compares
> `event.source` against that very field at `0x0053BCEF` before calling
> `0x0053B9B0` with the same `this`. A field/data-flow crosswalk, not a
> name-or-id coincidence. ~~So the button may simply not be wired to its
> handler.~~ It is wired. Why the click produces nothing is now an OPEN
> question about something later in the chain (connection context, the query
> gate, the current-UI object/key, or a create path) that RE-126 explicitly
> declined to fold into its identity objective. This lane is not chasing it:
> the chat door (`0xAC52`) makes it unnecessary, and RE-126's own closing
> warning is that the chat door is **not** an alternate entry into
> `GMUI_BASIC` and must never be cited as evidence that the UI path works.

Round-lock check: no open `[LANE-GM]` PR in either repo (`pf_bridge#301` was
open but is `[LANE-E]`, not this lane's lock -- untouched). Previous round's
PRs both confirmed `merged_at` non-null on `main` (`pirate-force-server#195`,
`pf_bridge#299`) -- nothing to recover. Mailbox: two items addressed to this
lane, both consumed this round (`20260828_1105_PANYA-ASK-LANE-GM-*`,
`20260828_1140_GT103AB-RESULT-NEGATIVE-*`).

Two attended rounds have now measured that the client's own GM door does not
open. GT-101-R3 (02:15 +07:00): the 41-byte `GM_UpdateGMStateVital` frame is
accepted and `BT_GM` becomes visible, but clicking it is silent. GT-103
steps 2a/2b (11:36 +07:00): clicked in four different UI states -- empty HUD,
map window held open, bag held open, bag closed again -- silent in every one.
Inbound frame census for the whole boot: `0x51E9` = 0, while `TargetPosVital`
x3 in the same window proves the client was alive and sending. That falsified
RE-118's practical "give the dispatcher a non-empty current-UI key first"
hypothesis; the remaining static question is now RE-126's.

RE-118's own follow-up list asked, as item (5), whether a cheaper entry to
`GMUI_BASIC` exists. It does, and it does not involve `GMUI_BASIC` at all:
the client already sends every line typed into the ORDINARY chat box to the
server as `Channel_LocalTalkMessageVital` (`0xAC52`), in a layout this
project measured three times over on 17-18 Aug. GT-006/GT-009 captured
payloads of three different lengths -- 34B/20B/46B for 12/5/18 characters,
i.e. `10 + 2N` every time, with the u32 length field (`0x18`/`0x0A`/`0x24` =
24/10/36) tracking the text in all three. The encoding itself (`tag 0x48`,
u32 LE byte length, strict UTF-16LE, no terminator) is the client's standard
wide-string serialization, already Grade A proven for CreateActorDataEx and
ActorAttr names. Payload = wstring#1 (speaker, empty client->server) +
wstring#2 (the typed text).

`gm/chat_command.py` reads it. A GM types `/warp 2` in the same chat box
every player uses; no GM window, no `BT_GM`, no `0x51E9`, nothing left to
discover about the client. `decode_local_talk_payload` fails closed on every
deviation from the measured shape (wrong tag, a length field past the end of
the buffer, an odd length, trailing bytes, anything not strictly decodable
UTF-16LE) rather than salvaging what it can -- a replacement character inside
a command argument would be an invented value. `handle_local_talk_chat`
checks the `gm_accounts` allowlist FIRST, before the payload is decoded at
all: the payload of an `0xAC52` frame is the literal sentence a player typed
to another player, so a non-GM's chat is never decoded, never
pattern-matched, never logged, and never carried back out of the module.
A GM's own non-command chatter is decoded (it has to be, to see there is no
sigil) but likewise never logged and never charged against the rate limit --
only a line starting with `/` that also parses becomes an audit record. An
unwritable audit log fails closed and the command is not handed onward.

`gm/dispatch.py` gains one thing: `rate_limit_allows()`, a public name for
the per-account limiter that was already there. Deliberately shared with the
0x51E9 path rather than duplicated -- what the RATE_LIMIT_* constants bound
is GM actions per account, not frames per door, and two counters would
quietly double the ceiling this lane advertises.

> 🔴 **UPDATED round `apk7ue` (R217) -- `CORE-REQUEST-GM-029` REPLACED the route this
> section describes.** `runtime.py` no longer fires the hook at `0xAC52`; it calls
> `gm/chat_command_action.make_gm_chat_command_action(...)` and appends the returned
> action. Consequences, measured: `lane_hooks/lane_gm_chat_command.py` is **registered
> and never fired** (WIRED v2 emission = 0 for that module, and its `production_allowed`
> flag no longer gates the GM chat door -- see the ASK to COO in
> `notes_to_chief/20260829_00xx_CHIEF-ASK-COO-*`); the console token is
> `LANE_GM_CHAT_ACTION` (not `LANE_HOOK_FIRED`) and prints **only after the allowlist
> passes**, so an ordinary player's chat line now produces NO console line at all
> (pf-adversary measured `stdout='' stderr=''`); events are `gm_chat_action_*`.
> `GT-127`'s gate-2 grep is stale until LANE-GM rewrites it. The paragraphs below are
> kept as the record of the GM-028 route -- read them in the past tense.

`lane_hooks/lane_gm_chat_command.py` registers for point
`vital_inbound_chat_local_talk`. That point was inert for one round and was
live for two: chief wired it in round `lo7e03` (R214, `CORE-REQUEST-GM-028`) as
the second `lane_hooks.fire()` site in `runtime.py`, at the `0xAC52` branch,
after every chat-keyed scenario lane, with no `return`, no `rx_frames` bump
and a `foundation.selected is not None` readiness guard.
`tests/test_gm_chat_command_dispatch_wiring.py` drives it headless on a
**flagless** boot and pins the three actions and the frame count a chat
frame produced before the branch existed, so the frame's own behaviour is
measured-unchanged rather than asserted.

Three things that file does NOT prove, measured by `pf-adversary` in the
same round and stated here so nobody repeats them as fact:

- **Scenario boots are not all untouched.** The 14 chat-keyed lanes return
  before this line, so those are byte-identical; a scenario boot keyed on
  some *other* vital reaches this line and does fire the hook.
- **Two surfaces change on any boot**: `self.events` gains one refusal per
  chat line for every ordinary player, and the console gains one
  `LANE_HOOK_FIRED` line per chat line. `fire()` was moved to stderr in
  the same PR so a tool's stdout artifact stays clean.
- **The GM door is silently absent under a chat-keyed scenario boot** (e.g.
  `--chat-input-hypothesis-scenario`): that lane claims the frame first and
  the hook never sees it. Indistinguishable, from the outside, from "not a
  GM".

`GT-127` is no longer blocked on wiring. It is still blocked on a tester at
the client **and** on the `GM_UpdateGMStateVital` (0x5A19) question recorded
above: putting the tester's account on the allowlist is what makes the
server send that frame on login, and `GT-107-R3` is still `[PENDING]`.

A hook-file mutation was found mid-round and is worth recording because of
what it exposed: line 53 appeared as `handle_local_talk_chat(payload,
session.tokn)` -- arguments swapped and the attribute misspelled. Because
`lane_hooks.fire()` swallows every exception a hook raises, that breakage
would have looked EXACTLY like the `[BLOCKED-ON-WIRING]` state this lane
already expects, so nobody would have found it. The two hook tests written
earlier that round passed against it unchanged: they proved only that a
callable was registered under the right point name and that
`production_allowed` was True. `HookBehaviourTests` (8 tests) now drives the
hook function itself with a fake session carrying only `token` and `events`,
with no `fire()` in between so nothing is swallowed -- verified to fail 8/8
against the broken line and pass once it was restored.

A `pf-adversary` sweep of the new code (the first attempt died mid-read on
an API rate limit -- that is not a pass, and the sweep was re-run to
completion) found six real defects; four are fixed in this round's diff and
two are recorded rather than "fixed". Fixed: (1) the ndjson audit log had no
volume cap at all -- this module is the first live caller of
`commands.log_gm_command`, so it inherited exactly the gap `dispatch.py` had
already closed on its own capture-file side, and the shared limiter is
deliberately generous enough (20 calls / 5 s) that a scripted GM account
appending ~600 bytes per call stays inside its accepted operating range
forever; now capped at `MAX_COMMAND_LOG_BYTES` (64 MiB), measured against
the file's real `st_size` rather than an in-process counter that would reset
to zero every boot and never bind. (2) `log_gm_command`'s `os.write` call
discarded its return value -- `write(2)` may write fewer bytes than asked
WITHOUT raising, which is precisely what a filling disk does, so the
`except OSError` fail-closed guarantee this module advertises did not hold:
the command was handed onward while the log held a truncated record that the
next append then glued itself onto; now a write loop, with zero progress
raising rather than spinning. (3) Unicode format characters (category Cf --
the bidi overrides above all) passed into the audit log verbatim, since
`json.dumps` escapes the C0 control range but nothing above it; a log line
that renders in a different order than it was typed defeats the one property
an audit log has, so command lines carrying any Cf character are now refused
(command lines only -- ordinary chat is never decoded for a non-GM and never
logged for a GM, so nothing constrains what players say, and a test pins that
ordinary Thai text is still accepted). (4) `handle_local_talk_chat` now
snapshots `bytes(payload)` once, before the size check, closing a
check-then-use window that is not live today (every caller passes immutable
bytes) but that nothing in the signature prevents. Recorded, not fixed: the
two doors' rate-limit consumption is not perfectly symmetric (0x51E9 spends a
slot before its size check, this path checks size first), which is written
into the code as a limitation with its reasoning rather than papered over --
reordering would charge a GM's ordinary conversation against the budget their
next real command needs; and the question of whether the `0xAC52` branch's
existing echo/broadcast lane would re-broadcast a GM's `/warp 2` to other
players once the fire point exists, which is `runtime.py`'s to answer and is
now a blocking condition on CORE-REQUEST-GM-028.

`tests/test_gm_chat_command.py`: 55 tests, 27 subtests, including the three
real captured payloads pinned as literal bytes (so this file goes red if the
reading of the frame ever drifts from what was actually measured), a non-GM
account driven through the exact command text that works for a GM, and one
test that fires the hook through `lane_hooks.fire()` with the exact keyword
names CORE-REQUEST-GM-028 asks chief to write -- because `fire()` swallows
every exception, a keyword mismatch at the future call site would otherwise
print the "lane is alive" token on every chat frame while the lane did
nothing, forever.
`tests/test_gm_*.py`: 321/321 (up from 266 -- 55 new, 0 removed, 0 narrowed).
Repo-wide `pytest tests/ --continue-on-collection-errors`: 3820 passed, 327
skipped, 5062 subtests passed, no new failures. เขียว (local pytest, this
session).

## ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `hs9m2r`)

**ยังไม่ได้ -- ตอบตรง ๆ** `GT-127` ติด `[BLOCKED-ON-WIRING]` รอสามบรรทัดของ chief จอยังไม่มีอะไรใหม่
สิ่งที่เปลี่ยนคือ**เส้นทางที่ต้องรอ**: เมื่อวานสาย GM รอ RE ตอบเรื่องปุ่มที่ไม่มีใครรู้ว่าจะเปิดได้ไหม
วันนี้รอ `CORE-REQUEST-GM-028` สามบรรทัดที่ทุกคนรู้ว่าเขียนยังไง โดยมีเทส 45 ตัวรออยู่ปลายทาง

nonclaim: ไม่มีคำสั่ง GM ใดมีผลในเกม (GM-003 v1 = parse + log, `"executed": false`) · เส้นทางแชท
**ยังไม่เคยทดสอบกับ client จริง** · ไม่อ้างอะไรเกี่ยวกับ `BT_GM`/`GMUI_BASIC`/`0x51E9` -- ประตูนั้นยังตาย
· ไม่อ้างว่าข้อความไทยผ่านเส้นทางนี้ได้ (sample ที่จับได้เป็น ASCII ทั้งหมด) · ไม่อ้างว่า wstring#1 คือช่อง
ชื่อผู้พูดจริง · รอบนี้ไม่ยิงเฟรมใส่ client จริง ไม่รันเทสในเกม ไม่แตะ `runtime.py`/`app.py` ไม่เพิ่มบัญชีใด
ลง `gm_accounts.json` · **GM nonclaim:** ทุกอย่างในรอบนี้เป็นเครื่องมือเพื่อไปให้ถึงสภาพที่จะเทส ไม่ใช่
หลักฐานว่าฟีเจอร์ใดทำงาน. Full detail:
`pf_bridge/rounds/GM_20260828_1712_chat-command-door.md`.

## Modules delivered (round `gr2q9j`, the half that can actually send bytes)

`src/pirateforce_foundation/gm/chat_command_action.py` (new).  One function,
`make_gm_chat_command_action(session, payload, legacy)`, returning a
`(label, pc, frame, delay_before)` action or `None`.

> **แก้ในรอบ `vvxkft` (ขีดฆ่า ไม่ลบ):** ประโยค "this round found that out
> before chief acted on it" ~~ผิด~~ — chief ต่อสาย GM-028 ลง main แล้ว
> (`runtime.py:4784`, PR #201 merge `d139f12`, จดหมาย
> `20260828_1845_CHIEF-REPLY-CORE-REQUEST-GM-028-chat-point-wired.md`) ก่อนที่ PR
> ของรอบ `gr2q9j` จะได้ merge — PR #200 ถูกปิดอัตโนมัติเพราะ gate แดง
> (Actions run 33168539342: !! U+1F534 ห้าตัวในคอมเมนต์ ไม่ผ่าน cp874 tripwire)
> จึงเป็น **เส้นทาง hook ที่ live ตอนนี้** และโมดูลใน section นี้ยัง dormant
> ไม่มีอะไรเรียกมัน · GM-029 จึงไม่ใช่ "เพิ่มจุดเรียก" อีกต่อไป แต่เป็น
> "**แทนที่** บรรทัด `fire()` ด้วยการเรียกที่คืน action ในคอมมิตเดียว"
> รายละเอียดในหัวข้อรอบ `vvxkft` ท้ายไฟล์

WHY IT EXISTS: `CORE-REQUEST-GM-028` (previous round) asked chief for a
`lane_hooks.fire()` point at the `0xAC52` chat branch.  That request could
never have moved a character on screen, and this round found that out before
chief acted on it.  `fire()` is fire-and-forget by its own documented
contract ("Never returns a value; hooks that need to hand something back to
runtime.py are not what this point shape is for"), and the only path bytes
take to a client in this server is the action list `dispatch()` RETURNS --
verified this round against `connection.py` (socket plumbing, no action
queue) and against `gm/dispatch.py`'s own docstring, which already said it:
"this lane has no send path outside a CORE-REQUEST wiring point".  So GM-028
would have unblocked `GT-127` (decided on the ndjson audit log, which is
what that entry honestly claims to decide) and nothing else, forever.
`CORE-REQUEST-GM-029` replaces it with one action-returning call site, the
same shape `gm_state_action` (CORE-REQUEST-006) already uses at
`runtime.py:5122`/`5331`.  !! Exactly one of the two may be wired: both at
the same branch would authorize every GM chat line twice, write two ndjson
rows for one typed line, and charge the rate limit twice.

`teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED = None` (new constant).
The vital version byte is NOT part of the RE-090 layout proof and cannot be
inferred from it.  RE-105 pinned the mechanism and the mechanism is
per-vital: the generic collection reader at `[0x005F3E20, 0x005F406D)` does
an exact-equality compare against `message+0x10`, and each vital's own
prototype constructor stores that byte by direct `mov`.  The two values this
project knows disagree -- `0x5A19` is 0 (RE-105), `SELECT_ACTOR_VITAL` is 10
(`pf_login_game_server_v141.py:2205, 2289`, proven by every successful login
this project has ever done) -- so there is no default to fall back on, and
GT-101 measured what a wrong guess does to a real client: modal error naming
the vital by id, connection halted, socket closed by the client itself.
`RE-129` asks for the one byte, by exactly RE-105's method.  Until it
answers, a valid `/warp` from a real GM is refused by name
(`gm_chat_warp_withheld_no_confirmed_force_pos_vital_version_re129_open`),
the same shape `runtime.py:5168`/`5173` already gates the login GM-state
frame with (line pins re-derived at HEAD in round `vvxkft`; chief's merged
hook block shifted everything after `runtime.py:4729` by ~60 lines).

ANSWERED THIS ROUND, from source, closing GM-028's own open blocker (b): a
GM's `/warp 2` cannot leak to other players as ordinary chat.  ~~Every
`CHAT_INPUT_VITAL_ID` branch in `runtime.py` (14 of them, lines 4591-4720) is
gated on `<name>_hypothesis_scenario is not None`, so on a flagless boot the
frame falls through to `super().dispatch(parsed)`~~

> **แก้รอบ `vvxkft` (pf-adversary จับได้ — ขีดฆ่า ไม่ลบ):** ประโยคที่ขีดฆ่าไว้ **ผิดสองข้อ**
> ที่ HEAD ปัจจุบัน (re-derive แล้ว): (1) สาขา `nested_id == CHAT_INPUT_VITAL_ID` มี **16**
> ไม่ใช่ 14 (2) และข้อที่สำคัญกว่า — **ไม่ใช่ทุกสาขาที่ gate ด้วย scenario** อีกต่อไป
> สาขาที่ chief เพิ่งเพิ่มตาม GM-028 (`runtime.py:4729-4732`) มีเงื่อนไขแค่
> `nested_id == CHAT_INPUT_VITAL_ID and self.foundation.selected is not None`
> พร้อมคอมเมนต์ `# CORE-REQUEST-GM-028 (LANE-GM). No scenario flag` ⇒ **บนบูตไร้แฟล็ก
> ที่เลือกตัวละครแล้ว เฟรมแชท "ไม่ได้" falls through อีกต่อไป** มันถึง `lane_hooks.fire`
> และเพิ่ม refusal event หนึ่งบรรทัดต่อหนึ่งบรรทัดแชทของผู้เล่นทุกคน (ตั้งใจ ไม่ใช่บั๊ก —
> เป็นเส้นทางที่ GM-028 ขอเอง และ event ไม่พก sentence ที่ผู้เล่นพิมพ์)
> ข้อสรุป "warp ของ GM ไม่รั่วไปหาผู้เล่นอื่น" **ยังจริงอยู่** แต่ยืนบนสองชั้นที่เหลือ
> (hook ไม่คืนค่าและไม่ส่งไบต์ · เซิร์ฟเวอร์ไม่มี broadcast machinery เลย) **ไม่ใช่**
> บนวิธีพิสูจน์ที่เขียนไว้ข้างบน ซึ่งซอร์สวันนี้บอกตรงข้าม

ส่วนที่เหลือของข้อพิสูจน์เดิมยัง re-derive ได้ตามเดิม: และ the legacy dispatcher
has no `0xAC52` branch at all (`grep -n "0xAC52\|44114\|CHAT_INPUT\|LocalTalk\|broadcast"`
on `current/pf_login_game_server_v141.py` = 0 rows; it is an if/elif chain
keyed by `nested_id`, so an unknown id produces no outbound bytes).  Second
layer: this server has no broadcast machinery at all -- `grep -rn "broadcast"`
across `src/pirateforce_foundation/*.py` returns three scenario/constant
names, one of them literally
`no_second_connection_no_broadcast_no_send_lock_no_population_py_change`,
consistent with `FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL.md`.  GM-028's
blocker (a) (keyword names) falls away entirely: GM-029 is a plain positional
call, not a `fire()` dispatch.

RECORDED, NOT FIXED (known debt, deliberately not this round's work):
`accounts.is_gm_account` opens and parses the allowlist JSON on every call,
so once GM-029 is wired the server reads that file once per chat line per
player.  This is not a regression this module introduces -- the landed
`0x51E9` site does the same, and GM-028 would have cost exactly as much --
and this server is strictly serial on one connection (FINDINGS_R18), so it is
not a problem today.  Caching it changes the meaning of "when does editing
the config take effect", which deserves its own decision rather than a
silent change here.

`tests/test_gm_chat_command_action.py`: 24 tests, 5 subtests.  Four groups:
the version gate is real (the shipped constant is asserted still `None`, and
a valid GM warp produces no action while it is); the path works once the byte
is known (patched-version tests assert the emitted bytes equal the pinned
composer's bytes, and that `z` comes from the connection rather than a
default -- an invented elevation drops the character through the floor);
permission (a non-GM typing the working command gets no action, no ndjson
row, nothing decoded, and a payload naming a GM account cannot promote the
sender); fail-closed (8 hostile session shapes -- no token, a `str` subclass
lying through `__eq__`, an `events.append` that raises, no `events` at all, a
composer that explodes, `handle_local_talk_chat` raising `MemoryError`, a
`GmCommand.args` tuple subclass lying through `__len__` -- every one must
return `None`, never raise, because the call site runs on the game-listener
thread shared by every player; plus one test that no exception MESSAGE and no
player-typed text ever reaches the event trail, which is both a leak and a
cp874 console hazard).
`pytest -k "gm or lane_hook"`: 365 passed, 4 skipped, 32 subtests.
Repo-wide `pytest tests/`: 3844 passed, 327 skipped, 5067 subtests, no new
failures.  เขียว (cloud sanity, this session -- not an Actions run, and not
the bridge full gate).

## ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `gr2q9j`)

**ยังไม่ได้ -- ตอบตรง ๆ เป็นรอบที่สองติดกัน** จอของเจ้าของยังไม่มีอะไรใหม่
สิ่งที่เปลี่ยนคือ **สิ่งที่ต้องรอ ถูกทำให้เล็กลงและชัดขึ้น**: เมื่อวานรอ "สามบรรทัดของ chief" ที่วันนี้รู้แล้วว่า
จะไม่ทำให้อะไรขยับได้เลย · วันนี้รอ **หนึ่งจุดเรียกของ chief (`CORE-REQUEST-GM-029`) + หนึ่งไบต์ของ RE
(`RE-129`)** ทั้งคู่มีวิธีทำที่พิสูจน์แล้ว และปลายทางคือ `GT-128` ซึ่งเป็นใบแรกของสายนี้ที่ตัดสินที่จอ
ไม่ใช่ที่ log

nonclaim: ไม่มีไบต์ `ForcePos` ออกสู่สายได้วันนี้ (ค่าคงที่เป็น `None` โมดูลปฏิเสธตัวเอง) · เส้นทาง
แชท→warp **ยังไม่เคยทดสอบกับ client จริง** · warp ข้ามฉากทำไม่ได้ (`ForcePos` ไม่มีช่อง scene id) ·
`/npc /item /lv /spawn /say` ยังไม่มี wire ทั้งห้าตัว · ไม่อ้างอะไรเกี่ยวกับ `BT_GM`/`GMUI_BASIC`/`0x51E9`
· ไม่แตะ `runtime.py`/`app.py` · ไม่เพิ่มบัญชีใดลง `gm_accounts.json` · **GM nonclaim:** ถ้า `GT-128`
PASS สิ่งที่พิสูจน์คือ "เราย้ายตัวละครไปจุดที่อยากเทสได้" ไม่ใช่ว่าการเดินทางในเกมทำงาน. Full detail:
`pf_bridge/rounds/GM_20260828_1831_chat-warp-send-half-plus-re129-force-pos-version.md`.

### pf-adversary, round `gr2q9j` -- NOT APPROVED on the first pass, 16 defects

Recorded in full rather than summarised as "reviewed", because four of them
were real and two were false greens in tests this lane wrote in the same
round.  Fixed before commit:

1. **The action label was a silent correctness bug.**  `runtime.py:3653-3660`
   (`_move_authority_note_server_moves`) reopens the move-authority grace
   window by testing `"TELEPORT" in action[0]` -- a cross-module contract
   expressed as a substring.  `LANE_GM_CHAT_WARP_FORCE_POS` did not contain
   it, so a 4243-unit GM warp would have been read as an impossible client
   jump, refused as over budget, and -- because the baseline only advances on
   admitted readings -- would have frozen the durable row for the rest of the
   session, persisting the pre-warp point at logout.  Renamed to
   `LANE_GM_CHAT_WARP_TELEPORT_FORCE_POS`, with two tests pinning both halves
   of the contract (the label carries it; `runtime.py` still keys on it).
2. **A double-wire would have been invisible.**  Measured: wiring both the
   `fire()` route and this one at the same branch produced TWO byte-identical
   ndjson rows for one typed line (same second-granularity timestamp, so
   indistinguishable from a GM typing twice), two rate-limit charges, and --
   because both routes used the same event strings -- two identical event
   lines.  `lane_gm_chat_command.py`'s events are now
   `gm_chat_hook_command_*`, distinct from this route's `gm_chat_command_*`,
   with a test asserting the two sets stay disjoint.  That cannot prevent a
   double-wire; it makes one legible instead of looking like normal traffic.
3. **False green: the `type(token) is not str` check was deletable** with all
   24 tests still passing -- the subclass test used a non-GM name, so
   `handle_local_talk_chat`'s own check raised, the outer catch swallowed it,
   and "returns None" stayed true either way.  Now asserts the specific
   `EVENT_BAD_SESSION_PREFIX` event; verified the mutation fails.
4. **False green: every event assertion was tautological** -- each compared
   the module's output against the module's own constant, so renaming any
   constant to `"zzz_"` kept the suite green.  Event names are an interface
   (GT graders, console greps), so they are now pinned as literals in
   `EventNameContractTests`, with an ASCII assertion on the event strings
   themselves (the label had one; the events did not).
5. Three `_current_position` guards had never executed under any test
   (`DeadGuardTests` now covers them); the production call shape chief will
   actually write -- three positional args, both paths resolved from CWD --
   ran zero times (`ProductionCallShapeTests` now covers it, and pins where
   the ndjson GT-127 is graded on actually lands); a wrong-typed `payload`
   landed in the `..._unexpected_TypeError` bucket that reads as "this module
   has a bug" rather than a named refusal (now `EVENT_BAD_PAYLOAD_PREFIX`).
6. Docstring overclaim corrected: "bytes reach the client on exactly one
   path" was false as stated -- the legacy file has four `sendall` sites --
   the true claim is that a LANE can only queue via the returned action list.

Recorded and deliberately NOT fixed this round, each with its reason written
into the module docstring: no coordinate range check (the fix is to reuse
lane A's `ground_extent` refusal by import, never to copy it here); the
uncached allowlist read per chat line per player (caching changes what "when
does a config edit take effect" means); `ForcePosBody`'s axis names, which
`PF_SERIALIZER_FIELDS.tsv` does not prove and this round makes load-bearing
(now RE-129's second question); and the one the reviewer was right to end on
-- **after a ForcePos leaves, who owns the character's position?**  The
module does not checkpoint, so the durable row keeps the pre-warp point, and
nothing reconciles it until a `TargetPos` that may never come.  That is now
`GT-128`'s third blocker and an ASK-COO letter: it must be answered BEFORE
RE-129 lets the constant change, not after.

Counts after the fixes, superseding the ones pinned in the `hs9m2r` section
above: ~~`tests/test_gm_chat_command_action.py` 34 tests / 25 subtests ·
`pytest -k "gm or lane_hook"` 375 passed, 4 skipped, 52 subtests~~ ·
**re-derived at HEAD ในรอบ `vvxkft` (pf-adversary ชี้ว่าตัวเลขชุดนี้ไม่ re-derive):**
`tests/test_gm_chat_command_action.py` = **43 passed, 25 subtests** ·
`pytest -k "gm or lane_hook"` = **395 passed, 4 skipped, 86 subtests** ·
repo-wide `pytest tests/` see the round file.  Mutation-checked, not merely
run: the version gate, the label substring, the identity check, the event
literals, the position guards and the exception-text leak each fail the suite
when removed.

## Modules delivered (round `vvxkft`, recovery of the gate-RED round + cp874 tripwire)

รอบนี้ไม่มีของใหม่ที่ผู้เล่นเห็น — เป็นรอบกู้ของ เพราะ PR ของรอบ `gr2q9j`
(`pirate-force-server#200`) **ไม่ได้ merge**: `.github/workflows/merge-claude-pr.yml`
ปิดให้อัตโนมัติเพราะ job `gate` แดง (Actions run 33168539342, commit `b262be7`)
branch `claude/sleepy-sagan-gr2q9j` ยังอยู่ครบตามที่ workflow บอก

**เหตุที่แดง มีสองข้อ ไม่ใช่ข้อเดียว** — ข้อแรกคือข้อที่ workflow รายงาน
ข้อที่สองรอบนี้เจอเองก่อน push:

1. **cp874 static tripwire (เหตุที่ทำให้ปิด PR จริง).** `U+1F534` (!!) ห้าตัว
   ในคอมเมนต์ — สี่ตัวใน `gm/chat_command_action.py` สามตัว/บรรทัด 36 56 66 131
   และหนึ่งตัวใน `lane_hooks/lane_gm_chat_command.py` บรรทัด 50 ตัวอักษรนี้
   **ไม่มี mapping ใน cp874** จึงไม่กลาย `?` แต่ยก `UnicodeEncodeError`
   กลางคำสั่ง `print()` บนคอนโซลสะพาน กติกา "โค้ดเป็น ASCII อังกฤษ" ของสายนี้ (อยู่ในใบตั้งสายบนสะพาน ไม่ได้อยู่ในรีโปนี้ —
   pf-adversary ชี้ว่าประโยคเดิมอ้างว่า "มีมาตั้งแต่ใบตั้งสาย" โดยไม่มีอะไรให้ผู้อ่านเปิดดูได้)
   มีอยู่แล้วตั้งแต่ใบตั้งสาย — รอบ `gr2q9j` ละเมิดเอง แล้วเสียทั้งรอบไปกับมัน
   แก้: เปลี่ยนเป็นมาร์กเกอร์ ASCII `!!`
2. **การเปลี่ยนชื่อ event ของเส้นทางที่ live อยู่ (ยังไม่เคยแดง เพราะ gate ตาย
   ที่ข้อ 1 ก่อน).** รอบ `gr2q9j` เปลี่ยนชื่อ event ของ hook จาก
   `gm_chat_command_*` เป็น `gm_chat_hook_command_*` เพื่อกันชนกับโมดูลใหม่
   แต่ระหว่างนั้น chief merge PR #201 ซึ่ง **หมุดชื่อเดิมไว้เป็น literal** ใน
   `tests/test_gm_chat_command_dispatch_wiring.py` บน main และด่าน headless ของ
   GT-127 grep ชื่อเดิม ⇒ cherry-pick ตรง ๆ จะแดงซ้ำที่เทสของ chief
   แก้: **เปลี่ยนชื่อฝั่ง dormant แทน** เส้นทางที่ live ไม่ถูกแตะแม้แต่ไบต์เดียว
   (`gm_chat_action_*` สำหรับโมดูลนี้ · `LANE_GM_CHAT_ACTION` เป็น console token)
   หลักคิดที่เขียนไว้ในโค้ดด้วย: เส้นทางที่ยังไม่มีใครเรียก เปลี่ยนชื่อฟรี
   เส้นทางที่ live ไม่ฟรี

`tests/test_gm_source_is_cp874_safe.py` (ใหม่) — ด่านที่ทำให้ข้อ 1 เกิดซ้ำไม่ได้
tripwire ตัวจริงรันเฉพาะบน Windows ใน Actions **หลัง** PR เปิดแล้ว ซึ่งตอนนั้น
ตัวปิด PR อัตโนมัติทำงานไปแล้ว ใบนี้ทำการทดสอบเดียวกัน (`str.encode("cp874")`
บนไฟล์ชุดเดียวกัน) ในชุดเทสที่สายนี้รันได้ **ก่อน** push
ขอบเขต = เขตเขียนของสายนี้เท่านั้น (`gm/**` + `lane_hooks/lane_gm_*.py`)
ไม่ใช่ทั้ง repo เพราะไฟล์ของสายอื่นแดงที่นี่ = ความล้มเหลวที่สายนี้แก้ไม่ได้
และจะสอนให้ทุกคนมองข้ามใบนี้ · ไม่ได้ทดสอบว่า "เป็น ASCII" — คอมเมนต์ไทย
encode cp874 ผ่านและได้รับอนุญาตตามกติกาบ้าน สิ่งที่ทดสอบคือสิ่งที่คอนโซลทำจริง
มีเทสกันลิสต์ไฟล์ว่างด้วย (ลูปบนศูนย์ไฟล์ = เขียวปลอม)

> 🔴 **กลับด้านแล้วตั้งแต่รอบ `apk7ue` (R217):** `CORE-REQUEST-GM-029` ถูกต่อสาย — เส้นทาง `fire()` (GM-028) **ถูกถอดออก** และ `chat_command_action.py` คือเส้นทางที่ live ย่อหน้าข้างล่างนี้เป็นบันทึกของสภาพ ณ รอบ `vvxkft` อ่านเป็นอดีต

**สถานะเส้นทางแชท หลังรอบนี้:** เส้นทาง `fire()` (GM-028) live บน main แล้ว
อ่านคำสั่ง GM จากกล่องแชทได้จริงและเขียน ndjson audit ได้ — แต่ **ส่งไบต์ไม่ได้**
ตามสัญญาของ `fire()` เอง · โมดูล `chat_command_action.py` (GM-029) recover แล้ว
แต่ dormant · `FORCE_POS_VITAL_VERSION_CONFIRMED` ยังเป็น `None` (RE-129 เปิดอยู่)
⇒ ต่อให้ chief wire GM-029 พรุ่งนี้ ก็ยังไม่มีไบต์ ForcePos ออกจนกว่า RE-129 ตอบ

nonclaim ของรอบ: **[ไม่อ้าง]** ว่ารอบนี้ทำให้ผู้เทสทำอะไรได้เพิ่ม — เป็นรอบกู้ของ
ล้วน ๆ · **[ไม่อ้าง]** ว่าเส้นทางแชท→warp ใช้กับ client จริงได้ (GT-127/GT-128)
· **GM nonclaim:** ทุกอย่างในสายนี้เป็นเครื่องมือไปให้ถึงสภาพที่จะเทส ไม่ใช่
หลักฐานว่าฟีเจอร์ใดทำงาน

### pf-adversary รอบ `vvxkft`: NOT APPROVED รอบแรก — 10 ข้อ, ห้าข้อเป็น blocking, แก้ทั้งหมดในใบนี้

ใบนี้เกือบเสียรอบเป็นครั้งที่สาม สิ่งที่ adversary จับได้และแก้แล้ว:

1. **[blocking] ตัว tripwire เองยังไม่ถูก `git add` และคอมมิตของ branch (`ac711e1` = cherry-pick ดิบ)
   ยังมี `U+1F534` ครบห้าตัว** — การแก้ทั้งหมดอยู่ใน worktree ที่ยังไม่ commit
   `git diff origin/main` เทียบ **worktree** จึงมองไม่เห็นเลย ⇒ push ตอนนั้น = โดนปิด PR
   ด้วยคอมเมนต์เดียวกับ #200 ไฟล์เดียวกัน บรรทัดเดียวกัน
2. **[blocking] tripwire อ่าน worktree ไม่ใช่สิ่งที่จะถูก push** — `rglob` บนดิสก์เขียวได้ทั้งที่ HEAD แดง
   ซึ่งเป็นคำถามที่ใบนี้มีไว้ตอบพอดี **แก้:** ตรวจ **ทั้งสองชั้น** — worktree (สิ่งที่ CI checkout)
   และเนื้อไฟล์ที่ `HEAD` ผ่าน `git show` (สิ่งที่จะถูก push) แดงถ้าชั้นใดชั้นหนึ่งแดง ·
   ชุดไฟล์มาจาก `git ls-files` ให้ตรงกับ gate (ไฟล์ scratch ที่ไม่ได้ track จึงไม่ทำให้แดงลวง)
   · พิสูจน์แล้วว่ามันแดงจริงบน `ac711e1` และเขียวหลังคอมมิตแก้
3. **[blocking] `CONSOLE_TOKEN` ไม่มีเทสแตะเลย** — ลบ `print` ทิ้งทั้งบรรทัด หรือเปลี่ยนชื่อ token
   เป็น `zzz_LANE_HOOK_FIRED` ก็ยังเขียว ทั้งที่มันคือหลักฐาน WIRED-v2 ของเส้นทางนี้
   (ใบเดียวกันนี้เขียนไว้เองว่ามีไว้ฆ่า tautology แบบนี้ แล้วหมุด 9 ค่า ลืมค่าที่ 10 พอดี)
   **แก้:** `ConsoleTokenTests` 6 เทส — literal, ASCII, ต่างจาก `LANE_HOOK_FIRED`, ยิงจริง,
   สตรีม, และผู้เล่นธรรมดาไม่ทำให้คอนโซลมีบรรทัด · mutation ทั้งสามแบบแดงแล้ว
4. **[blocking] `print()` ลง stdout ซ้ำบั๊กที่ `lane_hooks` จ่ายค่าไปแล้ว** —
   `lane_hooks/__init__.py:117-123` บันทึกไว้ว่า token ที่ลง stdout ทำให้
   `tools/pf_runtimeres_death_headless_replay.py --json` มีบรรทัดแปลกปนใน JSON artifact
   เพราะ control ของมัน dispatch เฟรมแชท และ fix คือ `file=sys.stderr` ·
   โมดูลนี้อยู่บนสาขา `0xAC52` เดียวกัน ⇒ รับ exposure เดียวกันทันทีที่ GM-029 ถูก wire
   **แก้:** `file=sys.stderr` + เทสที่หมุดสตรีม (mutation `stderr`->`stdout` แดง)
5. **[blocking] `test_the_live_hook_route_still_emits_...` ไม่ได้ทดสอบการ emit** —
   มันอ่าน `inspect.getsource()` แล้ว `assertIn` บน **ข้อความในไฟล์** ⇒ เปลี่ยนชื่อ event จริง
   แล้วทิ้งคอมเมนต์ `# was gm_chat_command_accepted_` ไว้ ก็ยังเขียวตลอดกาล (adversary ทำให้ดูแล้ว)
   **แก้:** ขับ hook จริงแล้วอ่าน `session.events` · mutation เดิมแดงแล้ว
6. **หมุดเลขบรรทัดของ `runtime.py` ค้างที่ค่าก่อน merge ของ chief ทุกตัว** (บล็อก hook ที่
   `4729-4787` ดันทุกอย่างหลังจากนั้นไป ~60 บรรทัด) — รอบนี้ re-derive `4784` ถูก แต่ลืมที่เหลือ
   แก้ครบ: `3654`/`3668` · `5181` · `5396` · `5168`/`5173` (`5595` เปลี่ยนเป็นอ้างโดยไม่ระบุเลข)
7. **ข้อสรุปความปลอดภัยที่วิธีพิสูจน์กลายเป็นเท็จ** — ดูบล็อกขีดฆ่าในหัวข้อรอบ `gr2q9j` ข้างบน
   (16 สาขาไม่ใช่ 14 · สาขาที่ chief เพิ่งเพิ่มไม่มี scenario gate) ข้อสรุปยังจริง วิธีพิสูจน์ไม่จริง
8. **ตัวเลขเทสใน section ก่อนหน้าไม่ re-derive** — แก้แล้ว (43 / 395 ข้างบน)
9. **คำพูดของ `gm/dispatch.py` ถูกตัดคำสุดท้าย "regardless" ทิ้ง** แล้วเอา caveat ที่พูดถึง vital
   ตัวเดียวมาใช้เป็นข้อเท็จจริงเชิงสถาปัตยกรรมของทั้งเลน — คืนคำและระบุขอบเขตแล้ว
10. `U+1F534` สามตัวใหม่ที่รอบนี้เพิ่งใส่ลง `GM_LANE.md` เอง หนึ่งในนั้นอยู่ในย่อหน้าที่กำลังเล่าว่า
    เอา `U+1F534` ออก (ไม่ทำให้ gate แดง เพราะ tripwire สแกนเฉพาะ `.py` — แต่เป็นอาการเดียวกัน)
    เอาออกหมดแล้วทั้งไฟล์

**คำถามที่ adversary ถามแล้วรอบนี้ตอบด้วยของ ไม่ใช่ด้วยประโยค:** อะไรบังคับกฎ "wire ได้จุดเดียว"?
เดิมคือ *ไม่มีอะไรเลย* — สอง namespace, เทส disjoint, console token ทั้งหมดทำให้ double-wire
**อ่านออก** และแต่ละอันเขียนไว้เองว่า "กันไม่ได้" กฎถูกถือไว้ด้วยประโยคในจดหมายขอ
และครั้งล่าสุดที่สายนี้ฝากกฎไว้กับการที่ chief อ่านจดหมาย chief ก็ส่งอีกครึ่งมาก่อน แล้วรอบนี้
ก็หมดไปกับการกู้ของ · **แก้: `OneOfTwoWiringTests`** อ่าน `runtime.py` จริงแล้วปฏิเสธสถานะที่มี
ทั้งสองจุดพร้อมกัน (และปฏิเสธสถานะที่ไม่มีเลยด้วย) — พิสูจน์ด้วย mutation ทั้งสองทิศ
เป็นสิ่งเดียวในรอบนี้ที่ **ทำ** แทนที่จะ **รายงาน**

## Round `fo2lgh`: RE-129 answered, and the switch stays off anyway

Round-lock check: no open `[LANE-GM]` PR in either repo at 22:16 +07:00
(`list_pull_requests state=open` on both -- both empty). Previous round's PRs
both `merged_at` non-null: `pirate-force-server#204` merged
2026-08-28T14:31:27Z, `pf_bridge#316` merged 14:32:39Z. Nothing to recover.

Mailbox, four items consumed (ADDENDUM v2 section B): `RE-126 RESULT`,
`RE-129 RESULT`, `COO-DECISION` on position ownership, and `CHIEF-REPLY` to
`CORE-REQUEST-GM-029`.

### The one thing that would have been wrong to do

RE-129 came back DONE/PASS at 20:09 +07:00 with the byte this lane had been
blocked on since 26 Aug: the `ForcePos` (`0x0E80`) vital version is **0**,
written as a literal by the prototype constructor (`xor ecx,ecx` then
`mov byte ptr [eax+0x10],cl` at `0x005E5186`) and compared by the generic
reader with exact equality at `0x005F3EFC` -- the same method RE-105 used for
`0x5A19`. `TeleportVital` is **4** (`mov byte ptr [esi+0x10],4` at
`0x005E5425`), which makes four measured values and still no default:
`0x5A19` -> 0, `ForcePos` -> 0, `SelectActor` -> 10, `TeleportVital` -> 4.

The obvious move was to set `FORCE_POS_VITAL_VERSION_CONFIRMED = 0` and let
`/warp` send. **This round did not do that, and no future round may, until a
precondition that has nothing to do with RE-129 is met on `main`.**

COO-DECISION 21:30 +07:00 answered this lane's own ASK-COO of 19:05 (who owns
a character's position after a GM warp) and ruled: the owner is the position
the **client confirmed**; the server must **never** write a position it did
not observe; the confirming event is the first `TargetPos` after the frame.
Then, verbatim, a hard lock: do not change that constant from `None` until
the confirmed write point is on `main` -- *even though RE-129 already
answered* -- and `GT-128`'s third precondition stays.

RE-129 independently made that caution concrete rather than theoretical: the
handler the client has **registered** for `ForcePos` is the complete body
`[0x00710440,0x00710445)` = `mov al,1; ret 4`. It reads no payload and writes
no position. A version-correct frame is necessary, not sufficient, and this
lane now has two independent reasons not to send one yet.

### What this round shipped

1. `gm/teleport_wire.py` -- the constant's comment block rewritten: the old
   reasoning kept under a `SUPERSEDED` marker (history is struck, not
   deleted), the new lock stated with its source, and the release sequence
   written down as the real sequence, in order (chief's write point on `main`,
   COO lifts the lock, *then* the constant, *then* the second test file named
   below). Two new names record RE-129's
   measurement without acting on it: `FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129
   = 0`, `TELEPORT_VITAL_VERSION_PROVEN_BY_RE129 = 4`.
2. `tests/test_gm_force_pos_version_lock.py` (new, 7 tests) -- **the lock is
   enforced, not described** -- but only after pf-adversary rewrote what
   "enforced" had to mean. The first version guarded a NAME; COO's order is
   about BYTES, and the adversary put four working senders through it with all
   five tests green (details in the adversary section below). The shipped
   version is AST-based and asks about frames:
   * the `runtime.py` write point must be a string constant **inside a call**
     (`print(...)`, `events.append(...)`) -- a `# TODO: GM_WARP_POSITION_CONFIRMED`
     comment saying the point does *not* exist satisfied the earlier substring check;
   * **no shipped module under `src/` may compose a ForcePos/Teleport frame
     with a literal version** -- the byte must come from the gated constant, so
     switching the constant off switches every sender off with it. The version
     byte is public now (RE-129, three letters, two source files); knowing it
     is not permission to send it;
   * the `*_PROVEN_BY_RE129` records may be written in their home file and read
     **nowhere in `src/`, that home file included** -- the adversary's second
     bypass was a sender added to `teleport_wire.py` itself, the one file the
     earlier check skipped;
   * no builder may default its `vital_version`, checked over **every function
     the two modules expose** rather than a hand-written list of four names.
   The file set is `git ls-files` **union a filesystem walk**, so a brand-new
   untracked module is covered before anyone remembers to `git add` it, and a
   missing git costs nothing instead of erroring.
   Only one direction is enforced: landing the write point does **not** force
   the constant on. Lifting the lock is COO's call, and a red inside chief's
   pull request for a lane he does not own is a red he cannot fix.
   All five bypasses now go red, and the honest release shape (a real `print`
   of the token) still passes; the four original mutations (flip the switch,
   mis-record the teleport value, default a builder's version, read a record
   elsewhere) go red and revert green.
   **[ไม่อ้าง]** ว่าด่านนี้กันการส่งได้ทุกทาง: เฟรมที่แพ็คเองด้วย `struct.pack` โดยไม่แตะ builder
   ทั้งสองตัวอยู่นอกสิ่งที่มันมองเห็น มันปิดทางที่วิศวกรจะเดินจริง ไม่ใช่ทุกทางที่มีอยู่
3. `gm/chat_command_action.py` -- the position-ownership section is no longer
   an open question. The ruling is written in as this module's contract, with
   the original question kept below it unedited, and one sentence that exists
   to stop a well-meaning future round: **this module's behaviour is already
   correct and must not be "fixed"** by adding a `foundation.checkpoint` call
   here. That is the one option COO struck out. The gap is in `runtime.py`,
   which is not this lane's zone.
4. `docs/GM_LANE.md` -- the `hs9m2r` heading corrected from RE-126 (above):
   the button *is* bound to its handler; only the silence is still a fact.

### Release day touches two test files, not one

`tests/test_gm_chat_command_action.py::VersionGateTests::test_the_shipped_constant_is_still_none_so_no_bytes_can_go_out`
asserts `assertIsNone` **unconditionally** and predates this round. Whoever
lifts the lock must edit it in the same commit or take three reds with no
explanation. pf-adversary found that the release sequence -- in
`teleport_wire.py`, in this file, and in CORE-REQUEST-GM-030 -- mentioned it
nowhere; all three now do.

### Deviation from COO's order, stated rather than hidden

COO ③ says to write the ruling into `gm/chat_command_action.py`'s header **in
place of the question** (`แทนคำถาม`). This round wrote the ruling at the top and
kept the question below it under "THE QUESTION AS IT WAS ASKED (kept, not
deleted)", following the house rule that history is struck, not deleted. That
is a deviation, not a reading of the order; it is recorded here and in this
round's letter so COO can overrule it in one line.

### Sent to chief

`CORE-REQUEST-GM-030` -- the confirmed-position write point COO ordered, one
letter for one point: on the first `TargetPos` after a GM warp, checkpoint the
observed position and print `GM_WARP_POSITION_CONFIRMED`. The token is a
literal in the test above, so the two sides cannot drift apart silently. COO's
deadline for the letter is 2026-08-29 09:00 +07:00; it went out tonight.

Also answered chief's two asks from his 21:43 reply: `#204` **is** merged
(his clone was at `cfb016c`, before the 21:31 merge), so
`gm/chat_command_action.py` is on `main` now and `GM-029` is unblocked; and
the signature on `main` is
`make_gm_chat_command_action(session, payload, legacy, *, config_path=None,
log_path=None) -> tuple[str, bytes, bytes, float] | None` -- the three
positional parameters and the 4-tuple-or-`None` return are exactly as the
ticket wrote them, the two keyword-only parameters are optional and exist for
tests.

### pf-adversary: NOT APPROVED on the first pass -- 17 findings, 5 of them fatal

The round's own headline claim ("the lock is enforced") was the thing that
failed hardest. Every bypass below was reproduced by the adversary, and every
fix was re-tested against it:

1. **[fatal] A comment satisfied the lock.** The check was
   `TOKEN in runtime.py.read_text()`. A one-line `# TODO(GM-030): ... NOT
   implemented yet` -- a comment saying the write point does not exist -- made
   the switch flippable with five green tests. **Fixed:** AST, and the token
   must be a string constant inside a call.
2. **[fatal] A literal `0` at any call site skipped the whole property.** The
   version byte is public now; a sender never has to mention the locked
   constant. COO's order is about bytes leaving the server, and the tests were
   about one name. **Fixed:** no shipped module under `src/` may pass a literal
   version to a ForcePos/Teleport builder.
3. **[fatal] The inertness check skipped `teleport_wire.py` itself** -- the
   adversary added a sender there using the record constant: green, and
   `pytest -k "gm or lane_hook"` returned the identical 400 this file was
   publishing as evidence. The metric could not tell a locked repo from a
   routed-around one. **Fixed:** the home file is scanned like every other; a
   record may be written there and read nowhere.
4. **[fatal] The file set missed where chief's wiring actually lands**
   (`runtime.py`, `lane_hooks/__init__.py`) and any brand-new file before
   `git add`. **Fixed:** all of `src/`, tracked union walked.
5. **[fatal] A stronger gate already existed and the release sequence never
   mentioned it** -- `VersionGateTests`' unconditional `assertIsNone`. On
   release day it must be edited or it reds for no stated reason. **Fixed:**
   named in three places (see above).
6. Stale `runtime.py:5107` pin re-typed into a new comment instead of
   re-derived (correct: `5168`/`5173`) -- fixed. 7. The CORE-REQUEST letter
   pinned `chat_command_action.py:206`, a line number this round's own diff
   created, while claiming to read `main` (`163` there) -- fixed to name the
   symbol. 8. `_tracked_lane_files` promised `None` when git is missing and
   raised `FileNotFoundError` instead, and its "no git" skip also swallowed
   the not-a-repo case under a wrong message -- fixed; the walk now covers
   both. 9. "greps every tracked lane source" and "any builder" were both
   larger than the code -- reworded to what it does. 10. "the third measured
   data point" over a list of four -- fixed. 11. The four version values
   flattened two evidence layers into one list (three from client
   constructors, `SelectActor -> 10` from the legacy **server** source) --
   separated. 12. The lane's assumption tag was forked into a third spelling
   (`[assumed by LANE-GM - awaiting RE]`), one of them replacing an existing
   canonical Thai tag, so a grep for either form missed both live assumptions
   -- canonical tag restored. 13. "Verbatim" over a rendering of a Thai letter
   -- reworded. 14. A shipped placeholder timestamp (`22:xx`) -- fixed.
   15. The deviation from COO ③ was undeclared -- declared (above).
   16. Missing nonclaim about what the lock cannot stop -- added.

**Checked and clean:** the adversary compared ASTs of both modified modules
against `origin/main` with docstrings stripped -- `chat_command_action.py` is
AST-identical, `teleport_wire.py` differs only by the two record assignments.
No behaviour change for an ordinary player or for the live `0xAC52` route. It
also independently confirmed `#204`'s merge sha and time, the signature
reported to chief, and that both RE letters and the COO ruling are rendered
accurately in this round's text.

**The question it left open, recorded because it is not fully answered:**
*what goes red for a `ForcePos` send that never mentions the constant at all?*
Fixes 2 and 3 close that for anything built through the two frame builders.
A frame hand-packed with `struct.pack` is still outside the net, and this file
now says so rather than implying otherwise.

### Tests

`pytest -k "gm or lane_hook"`: **402 passed, 4 skipped, 86 subtests** --
green(cloud sanity), not an Actions run and not the bridge's full gate.
`python -m compileall src tests` = 0.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `fo2lgh`)

เมื่อวานคำถาม "ถ้า RE-129 ตอบแล้วเปิดใช้ `/warp` ได้เลยไหม" ไม่มีคำตอบที่ผูกกับอะไรเลย --
มีแต่ประโยคในจดหมาย วันนี้ RE-129 **ตอบแล้ว** (version = 0) และผู้เทสได้ของสองอย่าง:
(1) คำตอบว่า **ยังไม่เปิด** พร้อมเหตุผลที่วัดได้ทั้งสองชั้น -- คำตัดสิน COO เรื่องเจ้าของตำแหน่ง
และ handler ของ client ที่เป็น `mov al,1; ret 4` อ่าน payload ไม่เลย
(2) เทสที่**บังคับ**คำตอบนั้น: ถ้ารอบไหนเผลอเปิดสวิตช์ก่อนจุดเขียนแบบยืนยันจะลง `main`
ชุดเทสแดงทันทีพร้อมข้อความที่บอกว่าขาดอะไร ⇒ `GT-128` จะไม่ถูกบูตในสภาพที่
client ยืนจุดใหม่แต่ DB จำจุดเก่า (aggro / ระยะเก็บของ / จุด logout ผิดตามทั้งชุด)

### nonclaims (round `fo2lgh`)

1. [ไม่อ้าง] ว่ารอบนี้ทำให้ `/warp` ส่งไบต์ได้ -- ตรงกันข้าม รอบนี้คือรอบที่**ยืนยันว่ายังไม่ส่ง**
   และเขียนด่านที่ทำให้เปิดเองไม่ได้
2. [ไม่อ้าง] ว่า version = 0 แปลว่า client จะขยับ -- RE-129 nonclaim 3 พูดตรงกันข้าม
   (handler ที่จดทะเบียนเป็น no-op) และเป็นข้อที่ `GT-128` เท่านั้นตัดสินได้
3. [ไม่อ้าง] ว่าชื่อแกน x/y/z ของ `ForcePosBody` ถูก -- RE-129 T2 ปิดเฉพาะ offset
   (`+0x14/+0x18/+0x1C`) และให้ bounded negative กับชื่อ [สมมติของสาย GM - รอ RE]
4. [ไม่อ้าง] ว่าปุ่ม `BT_GM` ใช้การได้ -- RE-126 พิสูจน์แค่ว่า binding ถูกตัว ไม่ได้อธิบายความเงียบ
5. [ไม่อ้าง] ว่าด่านของรอบนี้กันการส่ง `ForcePos` ได้ทุกทาง -- มันเห็นเฉพาะเฟรมที่ประกอบผ่าน builder
   ทั้งสองตัว เฟรมที่แพ็คเองด้วย `struct.pack` อยู่นอกตาข่าย และตัวตัดสินจริงยังเป็น
   `FORCE_POS_VITAL_VERSION_CONFIRMED` + วินัยของคนเขียน ไม่ใช่เทส
6. [ไม่อ้าง] ว่ารอบนี้ผ่าน pf-adversary ตั้งแต่รอบแรก -- **NOT APPROVED** 17 ข้อ ห้าข้อ fatal
   ของที่ push คือฉบับหลังแก้ครบและทดสอบกับ bypass ทั้งห้าแล้ว
7. **GM nonclaim:** ทุกอย่างในสายนี้เป็นเครื่องมือเพื่อไปให้ถึงสภาพที่จะเทส
   **ไม่ใช่**หลักฐานว่าฟีเจอร์ใดทำงาน หรือว่า milestone ใดผ่าน

## Round `w8hnu9`: `say` gets the action path `warp` cannot have yet

The lane spent three rounds on one command (`warp`) and ended each of them
with the same sentence: no bytes went out.  That was correct each time, but
it hid something this round went looking for -- **`warp` is not blocked on
one thing, it is blocked on three, and only one of them is about `say` at
all.**  Sorted:

| blocker | `warp` | `say` |
|---|---|---|
| a call site that RETURNS an action (`CORE-REQUEST-GM-029`) | yes | yes |
| this vital's own `vital_version` byte | answered (RE-129) | **open (RE-132, filed this round)** |
| COO's position-ownership lock + chief's confirmed write point (GM-030) | yes | **no -- a chat line moves nobody** |
| per-connection identity at the 0xAC52 branch (`runtime.py:4765-4774`) | yes | **yes -- added after pf-adversary, see below** |

So `say` is the shorter road to a screen, and this round built it.

**The fourth row is not a formality, and the first draft of this section did
not have it.** `runtime.py:4765-4774`, at the exact branch GM-029 would
convert, records that `self.token` is the process-wide `--token` CLI value and
NOT a per-connection authenticated login, and states that the question "has to
be answered before any executor is wired onto this point, not after"
(corroborated by `reports/PF_MULTIPLAYER_READINESS_AUDIT001_*_20260818.md`
I01-I04).  `warp` is triple-locked so it never arrives at that point first.
`say`, being the least locked, is exactly the command that would arrive there
first and cash the bug: with one shared token, the allowlist cannot tell two
humans apart, so an ordinary player's `/say` would be authorized if the shared
token is in `gm_accounts.json`.  Every allowlist test in this lane is
therefore a MODULE-layer fact, not a server-layer one.  Tagged as such in
`tests/test_gm_say_action.py`'s docstring and in `GT-133`.

### What shipped

1. **`gm/say_wire.py` -- two constants, no behaviour change.**
   `CHANNEL_CODEC_VITAL_VERSION = 0` names the byte the imported codec
   hardcodes (`channel_message_hypothesis.make_channel_message_response` ->
   `legacy.make_runtime_vitals([(channel_id, 0, payload)])`, written as
   `u8tag(0x0B, vital_version)` at
   `current/pf_login_game_server_v141.py:702-704`, re-derived at this commit).
   `GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED = None` is this lane's send gate
   for 0x9F2C, the same shape as `teleport_wire`'s.  The builder itself stays
   ungated on purpose -- it is a pure byte function its own tests exercise;
   the gate belongs where a socket is decided, which is the action module.
2. **`gm/chat_command_action.py` -- `_say_action`.**  An authorized `/say`
   now yields `(SAY_ACTION_LABEL, pc, frame, 0.0)` when the gate is open, and
   two DIFFERENT named refusals when it is not: `..._say_withheld_no_confirmed_
   gm_global_vital_version_re132_open` (RE-132 has not answered) and
   `..._say_refused_confirmed_version_is_not_the_codec_version` (RE-132
   answered with a byte the imported codec cannot emit).  Collapsing those two
   into one event would make release day look like "still waiting for RE"
   forever.
3. **`SAY_ACTION_LABEL = "LANE_GM_CHAT_SAY_GM_GLOBAL_MESSAGE"` -- and the
   absence of one word in it is load-bearing.**  `runtime.py:3654-3675`
   reopens the move-authority grace window for any queued action whose label
   contains `TELEPORT` (`if action and "TELEPORT" in action[0]`).  The warp
   label must carry it; this one must not.  A `say` label copied from the warp
   path out of symmetry would hand every GM a way to widen the anti-cheat
   window one chat line at a time, while the character never moved.  Pinned
   both directions against that call site's own source, not against a comment.
4. **`tests/test_gm_say_action.py` (new).**  The gate is shut and pinned shut;
   the path works when it is opened; the bytes are the imported codec's bytes;
   the refusal events never echo the GM's typed text; a non-GM gets nothing;
   `say` is no longer reported as "no wire path" and the other four still are.
5. **`GAME_TEST_QUEUE.md` `GT-128`: a grep the tester could never have hit.**
   Its wire-layer criterion said to look for `LANE_GM_CHAT_WARP_FORCE_POS`.
   The real constant has been `LANE_GM_CHAT_WARP_TELEPORT_FORCE_POS` since
   round `gr2q9j` -- not a substring of the other, so the grep fails on a
   working system and the tester writes FAIL.  Struck through, corrected,
   reason recorded in the entry.  Found while writing `GT-133` next to it.

### pf-adversary: NOT APPROVED on the first draft, 8 defects, fixed before push

The two that mattered most were both cases of this round failing at the thing
it was congratulating itself for:

* **D2 -- the new label and all three new event names had zero text pins.**
  Renaming `SAY_ACTION_LABEL` to anything left all 3941 tests green (measured,
  not argued): `SayLabelTests` pinned PROPERTIES (no TELEPORT, ASCII, not the
  warp label) and never the string, and `EventNameContractTests.EXPECTED` --
  a table that exists precisely because "compare the module against its own
  constant" is a tautology -- was never grown.  That is `GT-128`'s bug
  verbatim, shipped again in the same round that fixed `GT-128`.  Both labels
  and all three events are now pinned as text, plus a completeness assertion
  so the tables cannot silently fail to grow again.  Re-measured after the
  fix: renaming the label is red.
* **D3 -- the identity blocker above.**  The blocker table said two; there
  were three, and `runtime.py` itself says the missing one must be answered
  BEFORE an executor is wired onto that point.

The rest: **D1** this gate is lane-local, not repo-wide -- `runtime.py:2130`'s
channel-sweep scenario already composes and sends a real 0x9F2C frame carrying
the very byte RE-132 asks about, and `GT-016` (already queued, named in
`docs/HYPOTHESIS_LEDGER.json` and `docs/FUNCTIONAL_COVERAGE.json`) measures it
from the higher client-observable rung; **D4** "shortest path to a screen" was
a proposal wearing a measurement's clothes -- GMGlobal is not among the eight
per-channel style names in CHAT-CHANNEL-001's downcast chain, so RE-132 now
asks for that branch body too; **D5** the codec-mismatch event collided with
the `..._say_refused_` prefix whose contract is "exception type names only",
renamed; **D6** the TELEPORT rule is scenario-gated (`runtime.py:4518-4521`),
not global as the comment claimed, and the test that pinned it stayed green
with the call site deleted -- both fixed; **D7** "no durable row" -> "no DB
row" (an ndjson audit row IS written, and GT-133 counts exactly those);
**D8** `say_wire` caught only `ValueError` from a codec that raises
`RuntimeError` on all five drift checks, breaking its own "every failure
surfaces as `SayWireError`" promise.

What adversary tried and could NOT break, stated because each is a place this
round would have deserved a defect: eight mutations of `_say_action` (delete
either gate, put TELEPORT in the label, compose bytes locally, read the warp
constant instead) all go red; the two gates are genuinely independent; no
hostile session or payload shape escapes as an exception on the listener
thread; `CHANNEL_CODEC_VITAL_VERSION = 0` re-derives exactly as its comment
claims; and no pinned evidence anywhere in the repo covers 0x9F2C's envelope
byte -- both capture-derived cross-checks in `channel_message_hypothesis.py`
return early for any channel that is not LocalTalk (`:573`, `:588`).
**RE-132 is not theatre.**

### What did NOT change

No byte leaves the server.  Both gates are shut, for different reasons, and
neither can be opened by this lane alone.  `warp`'s constant is under
`COO-DECISION 20260828_2130` plus `tests/test_gm_force_pos_version_lock.py`;
`say`'s waits on `RE-132`, and if RE-132 answers with a byte that is not
`CHANNEL_CODEC_VITAL_VERSION`, the lane will NOT open the constant and will
NOT write a second codec in its own zone (that round was tried and retracted
on 2026-08-27) -- it will ask the owning lane for a version parameter.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `w8hnu9`)

เมื่อวาน คำสั่ง GM ทุกตัวรอสิ่งเดียวกันหมด และสิ่งนั้นคือกองที่ยาวที่สุด (ล็อกตำแหน่งของ COO
+ จุดเขียนของ chief + RE) ⇒ ผู้เทสไม่มีอะไรจะเรียงคิวเลยนอกจากรอทั้งกอง
วันนี้ผู้เทสมีใบที่ **ข้ามกองนั้นทั้งกอง**: `GT-133` (`/say`) เหลือด่านสามข้อ (จุดเรียกของ chief ·
หนึ่งไบต์จาก `RE-132` · คำถามตัวตนต่อ connection ที่ `runtime.py:4765-4774`)
~~สองข้อ~~ (นับผิดในฉบับแรก pf-adversary จับได้) และไม่แตะเรื่องตำแหน่งเลยแม้แต่นิดเดียว
⇒ ถ้า `RE-132` ตอบก่อน `GM-030` ลง main **คำสั่ง GM ใบแรกที่ตัดสินที่จอจะเป็น `/say` ไม่ใช่ `/warp`**
และผู้เทสได้ช่องทางที่เซิร์ฟเวอร์ใช้ "พูดกลับ" หาคนที่นั่งอยู่หน้าจอ ซึ่งสายนี้ยังไม่มีเลย
(`GM_RunGMCommandResultVital` ยังไม่รู้ layout) · และวันนี้ `GT-128` ก็ grep เจอ label ที่ถูกแล้ว

### nonclaims (round `w8hnu9`)

1. **[ไม่อ้าง]** ว่า `/say` ส่งไบต์ได้แล้ว -- ประตูปิดอยู่ และรอบนี้คือรอบที่**สร้างประตู**
2. [ไม่อ้าง] ว่า `0x9F2C` ใช้ `vital_version = 0` -- นั่นคือสิ่งที่ `RE-132` ถูกเปิดมาเพื่อวัด
   สิ่งที่พิสูจน์แล้วคือ **payload** ของห้า channel เหมือนกัน ไม่ใช่ไบต์ใน envelope
3. [ไม่อ้าง] ว่า `/say` เป็น broadcast -- action ไปที่ socket เดียว (ของ GM เอง)
4. [ไม่อ้าง] ว่ารอบนี้แตะ `runtime.py` -- ไม่แตะ · จุดเรียกยังเป็นของ chief (`CORE-REQUEST-GM-029`)
5. [ไม่อ้าง] ว่าประตูนี้กัน 0x9F2C ได้ทั้ง repo -- มันกัน **คำสั่ง GM** เท่านั้น
   `runtime.py:2130` (channel sweep scenario) ส่งเฟรม 0x9F2C ที่ถือไบต์เดียวกันนี้ออกสายได้อยู่แล้ว
   และไม่ได้อ่านค่าคงที่ของสายนี้เลย
6. [ไม่อ้าง] ว่า `/say` จะเห็นบนจอเมื่อ `RE-132` ตอบ -- GMGlobal **ไม่อยู่ใน**แปดชื่อ style
   ที่ CHAT-CHANNEL-001 นับได้จาก downcast chain ของ client และรายงานนั้นเขียนเองว่าไม่ claim การเรนเดอร์
7. [ไม่อ้าง] ว่าเทส allowlist ของสายนี้พิสูจน์เรื่องสิทธิ์ **ระดับเซิร์ฟเวอร์** -- เป็นข้อเท็จจริง
   ระดับ**โมดูล** ตราบใดที่ทุก connection ใช้ `--token` ตัวเดียวกัน
8. [ไม่อ้าง] ว่ารอบนี้ผ่าน pf-adversary ตั้งแต่ฉบับแรก -- **NOT APPROVED** 8 ข้อ แก้ครบก่อน push
9. **GM nonclaim:** ทุกอย่างในสายนี้เป็นเครื่องมือเพื่อไปให้ถึงสภาพที่จะเทส
   **ไม่ใช่**หลักฐานว่าฟีเจอร์ใดทำงาน หรือว่า milestone ใดผ่าน

---

## Round `z6gu2n`: the destination comes out of the lane, and RE-132 is spent

Two things happened between rounds, and they pull in opposite directions.

**Chief wired GM-030 and then filed its limit himself.**  `runtime.py` now
prints `GM_WARP_POSITION_CONFIRMED` when the first position report after a GM
warp causes a real durable write (PR #212, merged; re-run here on main with
`tests/test_gm_force_pos_version_lock.py` + `tests/test_gm_warp_position_
confirmed.py` = 20 passed, which is the check chief asked this lane to make
because his own clone predated the lane's lock file).  His appendix item 5
says what the token cannot say: the action tuple `(label, pc, frame, delay)`
carries no destination, so the token means "a row was written", never "the row
is the point the GM asked for" -- and the destination only exists inside this
lane.

**RE-132 came back, and it did not unblock what people expected.**  The byte
is `0` (client's own base constructor, `mov byte ptr [esi+0x10],al` at
`0x00657CC9`, reached from 0x9F2C's prototype at `0x0065BCD0`), equal to the
byte the codec already emits; and question 3 found the handler both vtables
bind (`0x0065C850`) is not a `mov al,1; ret 4` -- it routes, reads the body
wstring at `+0x18`, and calls a display sink.  That is two of the four
release-day items in `say_wire.py` gone.  The gate is still `None`, because
the remaining item is the one nothing static can touch: per-connection
identity at `runtime.py:4765-4774`.

### What shipped

1. **`gm/warp_target_record.py` (new).**  Parks one `WarpTarget` on the
   session an accepted warp was built for, and hands it back **once**.  On the
   session and not in a module-level map: the record must die with the
   connection and must never be readable from another one, and a map keyed by
   anything coarser than the session would hand connection A's target to
   connection B -- a second copy of the identity confusion this lane spends
   its rounds refusing to add to.  Also `distance_to_target` /
   `position_matches_target`, where every not-comparable case (another scene,
   a missing axis, NaN, Inf, an overflowing square measured live at 1e200) is
   `None`/False rather than a number that reads as "close".
2. **`gm/warp_executor.py` + `gm/teleport_wire.py` -- the target is the wire.**
   `make_warp_force_pos_frame_with_target` validates ONCE and the old
   `make_warp_force_pos_frame` delegates to it, so the recorded target and the
   frame bytes cannot disagree even for a hand-built `GmCommand` whose
   `__float__` returns a new number every call (pinned by a test that counts
   the reads).  The coordinates are read back out of the payload via
   `make_force_pos_frame_with_body`, so they are the binary32 values the
   client receives -- `11865.7` typed is `11865.6997...` on the wire, and a
   comparison against the typed value would charge that gap to the client at
   every coordinate in the tens of thousands.
3. **`gm/chat_command_action.py`.**  The target is parked after the frame is
   built and never before: the version gate shut, a cross-scene refusal, a
   non-GM, a `/say`, a GM with no selected character -- five paths that send
   no bytes, one test each.  (`_make_action` has more no-byte paths than
   that -- bad session, bad payload, an unwired command; these five are the
   ones a future edit could plausibly move the parking above.)  A session that
   cannot hold the record still gets its warp and gets
   `gm_chat_action_warp_target_not_recorded`, deliberately outside the
   refused-prefix family whose consumers read it as "nothing was sent".
4. **`gm/say_wire.py` -- RE-132 pinned, gate untouched.**
   `GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC = 0` plus the image SHA-256
   and three VAs, kept SEPARATE from the send gate because they answer
   different questions ("what byte?" vs "may we send?").  Collapsing them
   would make a lane blocked on identity look like a lane waiting for RE work
   that is already paid for.  A test pins that the send path never reads the
   static one.
5. **`tests/test_gm_force_pos_version_lock.py`.**  `VERSION_TAKING_BUILDERS`
   gained both new builder names.  This was not tidiness: the delegation moved
   the last shipped `make_force_pos_frame` call site, and the lock's own
   tripwire (`test_the_scan_actually_sees_the_calls_it_claims_to_check`) went
   red -- correctly -- because a literal version byte passed to the new name
   would have walked straight through COO's lock with every other test green.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `z6gu2n`)

เมื่อวาน: warp แล้วเห็นบรรทัด `GM_WARP_POSITION_CONFIRMED` ซึ่งบอกได้แค่ว่า "มีการเขียนแถวเกิดขึ้น"
วันนี้: ปลายทางของ warp ใบนั้นถูกเก็บไว้ให้เทียบได้แล้ว หนึ่งเฟรม หนึ่งตัวละคร หยิบได้ครั้งเดียว
พร้อมตัวเทียบที่ตอบ `None` แทนที่จะเดาเมื่อเทียบไม่ได้ ⇒ วันที่ `CORE-REQUEST-GM-031` ต่อสาย
ผู้เทสจะอ่านออกจากคอนโซลได้ว่า client "ขยับไปผิดที่" หรือ "ไม่ขยับเลย" ซึ่งวันนี้สองอย่างนี้หน้าตาเหมือนกัน

### nonclaims (round `z6gu2n`)

1. [ไม่อ้าง] ว่ามี byte ใดออกสายในรอบนี้ — `FORCE_POS_VITAL_VERSION_CONFIRMED` ยัง `None`
   (ล็อกของ COO) และ `GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` ยัง `None` ⇒ ทั้งสองเส้นยังหลับ
2. [ไม่อ้าง] ว่า RE-132 พิสูจน์ว่าข้อความ `/say` ขึ้นจอ — static render path เป็นชั้น client-binary
   ต่ำกว่า client-observable หนึ่งขั้น และใบผลเองเขียน nonclaim ข้อนี้ไว้ ต้อง `GT-016`/`GT-133`
3. [ไม่อ้าง] ว่า `WARP_TARGET_MATCH_TOLERANCE = 1.0` มาจากการวัด — [สมมติของสาย GM - รอ COO ยืนยัน]
   สิ่งที่พิสูจน์แล้วมีข้อเดียว: มันใหญ่กว่าความคลาด binary32 ที่พิกัดของเจ้าของราวสามอันดับ
4. [ไม่อ้าง] ว่าเทส allowlist ของรอบนี้พิสูจน์สิทธิ์ระดับเซิร์ฟเวอร์ — ระดับโมดูลเท่านั้น
   ตราบใดที่ `runtime.py:4765-4774` ยังใช้ `--token` ของโปรเซสร่วมกันทุก connection
5. เขียว(cloud sanity): สวีตเต็ม 4035 passed 327 skipped · gate ตัวจริงตัดสินบน Actions

### pf-adversary รอบ `z6gu2n`: NOT APPROVED รอบแรก — 10 ข้อ แก้ก่อน commit ทั้งหมด

The findings that changed the design, not just the wording:

1. **[fatal] The COO lock's own tripwire became self-satisfying.**  Making
   `make_warp_force_pos_frame` delegate meant both scanned builder names were
   called from inside their own defining modules, so adversary deleted the
   ONLY production ForcePos composition site
   (`chat_command_action.py`, replaced with `raise RuntimeError`) and
   `test_gm_force_pos_version_lock.py` stayed green: seven passed with nothing
   in the repo able to compose a ForcePos frame.  A tripwire a delegation can
   satisfy is not a tripwire.  Fixed by counting only CROSS-MODULE calls (a
   call from a file that does not define the builder) and asserting the real
   call site by name; re-run of the same mutant now fails, as it must.
2. **[fatal] `current_character_id` returned `None` for two different things**
   -- "no character selected" and "id unreadable" -- and `None == None`, so
   two connections that both failed to read an id matched each other and one
   GM's destination could be handed to another character.  Now
   `UNREADABLE_CHARACTER_ID`, a sentinel `take_warp_target_with_reason`
   REFUSES rather than compares.
3. **[fatal] `distance_to_target` raised the exception it guards.**
   `isinstance(x, int)` admits arbitrary precision and `float(10**400)` raises
   `OverflowError` one line above the `except OverflowError`.  Reproduced live;
   both conversions are guarded now.
4. **[fatal] `current_character_id` was unguarded on the dispatch path** and
   ran AFTER the frame existed, so a `selected.id` property that raises threw
   away a warp that was already built and blamed this module on the event
   trail.  It never raises now, and a test drives that through the real path.
5. **`runtime.py:4765-4774` had drifted** to damage dispatch; the identity text
   is at 4886-4896.  Every citation in this lane now names the anchor
   (`IDENTITY, STATED HONESTLY`), and a test greps `runtime.py` for it, so the
   load-bearing citation cannot rot silently again.
6. **The say_wire write-up overclaimed against its own text** -- "the reason it
   stays None is now exactly ONE item" while release-day item 0 names two and
   the screen is a third.  RE-132 removed the cheapest way (B) could fail (a
   handler that draws nothing); it did not satisfy (B).  Rewritten to count
   three.
7. Smaller, all fixed: `record_warp_target` returning True for a session that
   SWALLOWS the write (now reads back); consume-once broken when the clear
   fails (now refuses with `REASON_NOT_CLEARED`); `tolerance=inf` turning the
   comparison into `return True`; a "five paths, five tests" count that was
   four; the four `RE132_*` pins that nothing read (now pinned by a test); and
   `FakeSession`'s "three attributes and nothing else" docstring, which this
   round's own edit walked past -- replaced by `SessionSurfaceTests`, which
   measures every attribute name the module touches.

What adversary tried and could not break, which is the other half of the
deliverable: 35,343 random float64 triples through encode/decode with zero
round-trip mismatches and zero new refusals; the send gate (a mutant making
`_say_action` read the static pin is caught by two tests); a literal version
byte passed to either new builder name; the target-as-float64 mutant; removing
the character guard; and any cross-connection leak -- the module has no
module-level mutable state at all.

## Round `nz0qt2`: the audit log can finally tell a withheld command from a sent one

`COO-DECISION 20260829_0041` item 2 measured the hole, and it is a bad one for
a lane whose whole permission story is its audit trail: `handle_local_talk_chat`
writes its ndjson row BEFORE any version gate is read, so `/warp 2 100 200`
typed with the ForcePos gate shut (nothing on the wire) and the same line typed
on the day the gate opens (a real frame handed to `runtime.py`) produced rows
that differed only in their timestamp.  `GT-127` decides on that file.

`CORE-REQUEST-GM-032` split the fix in two zones and this round did the half
that is this lane's (items 1-2).  Item 3 -- the word `queued` -- is chief's and
is still open.

### What shipped

1. **A second audit row.**  One GM command now writes `issued` (unchanged in
   every field, so nothing that already reads the file breaks) and then
   `outcome`, tied by one `record_id`.  Appended, never an amend: this house
   does not rewrite history, and two rows carry the ORDER of events, which one
   mutated row cannot.
2. **One write point, on purpose.**  `_warp_action`/`_say_action` now return
   `(action, outcome)` and `_make_action` writes the row.  An audit appended at
   four different `return` statements grows a fifth `return` that forgets it.
3. **The vocabulary, and the one word held back.**  `withheld_<gate>` names the
   shut gate (so a reader goes straight to RE-129 or RE-132), `refused_<reason>`
   carries an exception TYPE name only, and `composed` is the strongest honest
   claim available here: the frame exists and was handed back.  Not `queued` --
   `actions = actions + [gm_action]` happens in a zone this lane cannot read.
   `tests/test_gm_command_audit_outcome.py::QueuedIsReservedTests` walks BOTH
   halves of the lane's zone (`gm/*.py` and `lane_hooks/lane_gm_*.py`, the
   probe-G lesson from round `xk4wmz`) and goes red if any file names the
   reserved word, so the day item 3 lands, someone has to delete a test that
   says why they may not -- it cannot be drifted into.

### Defects this round nearly shipped: two caught in self-review, four by adversary

1. **Fail-closed had to extend to the second row.**  `handle_local_talk_chat`
   already refuses to hand onward a command it could not record; a composed
   frame whose outcome row cannot be written is the same failure one row later,
   so it is withheld (`gm_chat_action_outcome_not_audited_action_withheld`)
   rather than sent with a trail that says only "a GM typed something".
2. **The parked warp target had to go with it.**  `_warp_action` parks the
   destination only AFTER the frame exists, precisely so "no bytes went out"
   and "a target is parked" can never disagree.  Withholding a composed action
   for an audit failure is a NEW route to exactly that disagreement, and a
   target left behind would let chief's confirmation token (CORE-REQUEST-GM-031)
   match the player's next ordinary step against a warp nobody sent -- the same
   class of false green that has `GT-128` blocked.  Cleared, with a paired test
   (cleared when withheld / not cleared when the warp really goes).

### What this round did NOT do

No gate was opened and no byte went out; `NoBytesWentOutTests` pins both
constants as `None` on the shipped tree, so every `composed` row in the suite
came from a patched gate.  `GT-016`'s 18-Aug evidence (the client really does
draw a `[GM]` line from a GMGlobal frame, byte `0`) was consumed this round and
deliberately did NOT open the say gate: chief's own letter says that boot ran
under two opt-in scenario files and never touched condition (A), per-connection
identity, which is the whole reason `COO-DECISION 20260829_0041` locked it.

### The other finding of the round, which is not about code

`pirate-force-server#218` -- chief's reconnection of the owner-approved
`production_allowed` kill switch, ordered by COO with a 12:00 deadline -- is
`state=closed merged=false`, and `module_production_allowed` greps 0 hit on
main `b79bb87`.  His letter at 01:03 said "PR #218, waiting to merge", which was
true when he wrote it.  `GT-127`'s HOLD depends on that switch, so the entry now
carries the measured status instead of "waiting on chief" forever, and the
finding went to him as its own letter so he can recover it under ADDENDUM v2
step A.  This lane touched neither his branch nor `runtime.py`.

### What pf-adversary broke, run on a separate worktree

Round `xk4wmz` recorded that the adversary had written probes into the round's
own tree and edited `runtime.py` (chief's zone).  This round it ran on a
`git worktree` copy carrying the round's patch, and the work tree was never
touched.  It reported damaging that copy mid-run, restoring it from the patch,
and discarding a polluted mutation batch to re-run the whole matrix -- which is
why the numbers below are worth believing.

Four findings that mattered, all fixed before merge:

1. **`queued` was writable today.** It wrote a function into
   `lane_hooks/lane_gm_chat_command.py` that passed `AUDIT_OUTCOMES[-1]`
   straight into the writer, and the reserved word landed in the ndjson file
   with all 519 GM tests green -- because an AST scan matches names and string
   literals, and a tuple index is neither.  **A source-shaped scan cannot make
   an output-shaped guarantee.**  Fixed where it belongs: `queued` is out of
   `AUDIT_OUTCOMES`, `is_known_outcome` returns False for it, and the writer
   raises with the reason.  The scan stays as the early warning; the writer is
   the door.
2. **Every assertion compared the row to the constant, never to the literal.**
   Mutating `OUTCOME_COMPOSED` to `"queued"` and then to `"sent"` left the
   whole suite green while the audit file said something false.  The file's own
   bytes are now pinned.
3. **`GT-127` had a SECOND pass-criteria block** -- the one literally headed
   `### pass criteria` -- still demanding "exactly 2 records" and the dead
   `gm_chat_command_*` event names.  A tester following it would have recorded
   FAIL on a healthy build: the same scar as job 1331, in the same ticket the
   previous round thought it had repaired.  Rewritten, with "if this disagrees
   with P1, P1 wins", plus two more stale spots it turned up (`GT-127`'s
   background block and `GT-133`'s row-count criterion, whose double-wire check
   is now "count distinct `record_id`s").
4. **The outcome row's `executed` field was unpinned** (a `True` mutant
   survived), and the file has a **third** state nobody had named: an `issued`
   row with no `outcome` row, reachable four ways.  Both closed --
   `HalfPairTests` pins the one thing a reader must be able to conclude from a
   half-pair, which is that **nothing was sent**.

It also measured that `_append_audit_record`'s inherited O_APPEND comment is
false -- O_APPEND makes each `write(2)` atomic, not a *sequence* of them, and
its probe produced two unparseable lines including a real command's `issued`
row.  The comment now says what the loop actually buys (detection, not
atomicity) and that this round doubled the window by doubling the writes per
command.

What it could not break, which is the other half of the deliverable: no path
returns an action without its outcome row (five mutants aimed at exactly that,
all red), the new fail-closed path creates no wider outage than the one the
issued row already had, and the file modes plus short-write handling that moved
into the shared helper are still killed by their own tests.

Suite after every fix: **4080 passed, 327 skipped** (cloud sanity).

## Round `gejldf`: `/warp` stops dead-ending, by taking the door that is already open

`/warp` had exactly one half.  `warp <scene_id> x y` INSIDE the scene the
connection is already in composes a `ForcePos` frame -- and that half is
frozen shut by COO order (`FORCE_POS_VITAL_VERSION_CONFIRMED = None`,
COO-DECISION 20260829_0041, liftable only by a new COO-DECISION).  Every
other form of `/warp` -- a different scene, or the bare `warp <scene_id>` --
was REFUSED, because `ForcePos` carries no scene id (RE-129) and
`TeleportVital`'s target/aux fields are unproven (RE-090), and this lane does
not guess bytes.

So a tester who typed `/warp 126` got a refusal and no way at all to see
scene 126, while a path that DOES cross scenes sat one config file away,
already wired into `runtime.py`'s login path and already tested: the
per-account login-scene override (GM-005, `CORE-REQUEST-016`), which
`login_scene_override.get_login_scene_override` re-reads FRESH ON EVERY
LOGIN.  This round connects the command the owner asked for to the mechanism
that works.

### What shipped

`gm/login_scene_stage.py` (new).  `stage_login_scene(account, scene_id)`
writes ONE entry into `config/gm_login_scene.json`; `restore_login_scene`
takes it back off.  `gm/chat_command_action.py` routes `/warp` to it for
every form except same-scene-with-coordinates, and audits the result with two
new words, `staged_login_scene` and `staged_login_scene_coords_ignored`
(`gm/commands.py`).  `gm/warp_executor.py` grew two public readers
(`warp_command_scene_id`, `warp_command_has_coordinates`) so the routing
decision and the frame builder validate a hand-built `GmCommand` through ONE
implementation, and `gm/login_scene_override.py` grew
`resolve_gm_login_scene_config_path` so the writer and the reader can never
resolve to two different files (`PF_GM_LOGIN_SCENE_CONFIG` is the case that
would otherwise look like it worked and change nothing).

### What it is not, said in the module and repeated here

It is NOT a warp.  No frame is composed, no byte goes on the wire, and
nothing at all happens until the GM logs out and back in.  `executed` stays
`false` in the audit row, because the gameplay command did not execute -- a
config entry was written, and the outcome word says exactly that.  `GT-141`
carries the same sentence as a nonclaim: seeing the island because a GM
staged the scene is not the sea route working.

### Why it cannot grant anything

* Only the GM-GATED map (`gm_login_scene`) is writable.  The STANDALONE map,
  which grants a login scene to an account with no `gm_accounts.json`
  membership at all, is unreachable from this writer -- checked behaviourally
  AND by reading the module's own source, since the last round's lesson was
  that a source-shaped scan cannot make an output-shaped guarantee (so the
  scan is the early warning; the absence of any import is the door).
* An entry is worth nothing on its own: `get_login_scene_override` re-checks
  `is_gm_account` at login time, so removing the account from the allowlist
  disarms a staged entry without touching this file.
* A refusal leaves the config byte-identical, including the case where an
  operator's file is already malformed: this module validates the whole file
  through the READER's own rules before writing and again after, and restores
  the original bytes if the read-back disagrees.  A config writer that
  "repairs" a file it did not understand is worse than one that refuses.

### The identity limit, named before anyone asks

[สมมติของสาย GM - รอ COO ยืนยัน]  `session.token` is the process-wide
`--token`, not a per-connection authenticated login, so on a listener whose
token is a listed GM account ANY connected player who types `/warp 126`
stages that account's next login scene.  Every command in this lane already
shares that gap; this is the first one whose effect OUTLIVES the chat line,
which is why it is in the module docstring, in the round letter, and in an
ASK-COO of its own rather than left to be discovered.  Blast radius: a listed
GM logs in somewhere else next time, recoverable by typing another `/warp` or
deleting the config.  No status, no command, no frame.

### The reorder, which is the one behaviour change nobody asked for

The version gate used to be the FIRST thing `_warp_action` read, so with the
gate shut every warp wrote `withheld_force_pos_vital_version`.  It is now
read only on the branch it actually governs.  A cross-scene warp never
touches it and no longer claims to have been withheld by a gate that had
nothing to do with why it did nothing.  Cost: with no current position, the
outcome is now `refused_warp_no_current_position` where it used to be the
version word -- more honest (this function cannot route without a scene), and
unreachable in production, where the call site requires a selected character.

### Tickets moved in the same round, not the next one

`GT-127`'s P1 told the tester `/warp 2` produces
`withheld_force_pos_vital_version`.  This round made that false, so this
round rewrote it -- PANYA-RULING 20260829_0127, the lane that changes the
fact fixes the entry in the same round as the code.  It also gained the
cleanup step the new behaviour needs: `/warp 2` now WRITES a file, and a
tester who leaves it there logs into Prison Exile forever after.  `GT-141` is
the new attended entry for the thing itself (stage, relog, see the island).

### Tests

`tests/test_gm_login_scene_stage.py` (new, 27 cases): grants-nothing,
writes-what-the-reader-reads, refusal-leaves-the-file-alone, hostile
arguments, restore.  `tests/test_gm_command_audit_outcome.py` gained
`StagedLoginSceneRowTests`, including the property that cost the design work:
a command whose `outcome` row cannot be written takes its staged entry BACK
OFF DISK, because unlike every other outcome in this vocabulary this one has
already changed durable state by the time the write point is reached -- and
an undo that fails is named (`gm_chat_action_outcome_stage_not_reverted`)
rather than silent.

Two test files also gained a throwaway config path in `setUp`: the first run
of the new routing created a real `config/gm_login_scene.json` under the
repo checkout, which is a test writing into the tree it is testing.

### The adversarial pass, run by hand after the subagent stalled

`pf-adversary` was launched on a separate `git worktree` carrying this
round's patch, the way round `nz0qt2` recorded it must be.  It produced 110
bytes of transcript and then stopped writing for four minutes with nothing
in the copy to show for it, so the round ran the pass itself rather than
either waiting or claiming a review that had not happened.  What that
means, stated rather than glossed: what follows is a self-review with the
same tools, not an independent one, and the next round should treat this
module as still owing an outside pass.

**Mutation matrix, 12 mutants, all DEAD** (run on the worktree copy, GM
test files only): the two new audit words mutated to `composed`, to
`queued`, and into each other; the routing predicate with its bare-form
clause dropped and then forced always-true; the undo call disabled; the
allowlist check, the catalog check, the bool-scene_id check and the
str-subclass check each removed; the JSON key switched to the standalone
one; and the restore-after-a-bad-read-back deleted.  Every one of them
turned at least one test red.

**Three probes, two of which found real defects** -- both fixed in this
round, both about walking over an operator rather than about a client:

1. **A symlinked config was replaced, not written through.**  `os.replace`
   renames onto the path it is given, and that path was the link: the link
   became a regular file, the file the operator actually maintains kept the
   old content, and the login path read the new one from then on.  Two
   configs, no error, nothing to notice.  Fixed by resolving the path
   first, which also keeps the temp file on the target's own filesystem --
   the thing that makes the rename atomic at all.
2. **A `chmod 400` config was overwritten and came back `0o600`.**
   `os.replace` needs the DIRECTORY's write bit, not the file's, so an
   operator saying "do not touch this" in the only way a file can say it
   was ignored.  Now `REASON_CONFIG_NOT_WRITABLE`, one `os.access` call.
3. **A failed rename leaves no temp file behind** -- probed because a
   stray `.gm_login_scene.XXXX` in `config/` is one more file an operator
   has to reason about.  Clean, and now pinned by a test.

### The adversary came back after the round had already been written, and it was right

The subagent had not stalled; it was working without writing to its
transcript, and it returned after this round's PR was already out of draft.
It brought one finding that falsified the headline claim above, and the
claim is corrected here rather than left standing with a correction
underneath it.

**~~330 scenes become typeable~~ -- FALSE.  Four do: 1, 2, 278, 997.**
This lane's writer asked the client's scene NAME table (`gm/scene_catalog.py`,
330 rows).  The login path resolves through lane A's
`scenarios/world_scene_registry_001.json`, which pins **five** destinations
and marks one of them `login_entry_allowed: false` (scene 17, after GT-106).
Two different tables, and nothing checked the second one before writing.

What that cost, measured end-to-end through the real dispatcher rather than
argued from the source: staging any of the other 326 named scenes wrote a
clean-looking entry and then made the account's **next login fail with no
reply** -- `WORLD_SCENE_ENTRY_REFUSED [scene_not_pinned]`, `return []`, the
client parked on "connecting".  It does not self-heal: the entry is re-read
on every login, and the only in-game fix is a chat line, which needs a login.
Recovery is an operator deleting the file on the server host.  The kill
switch does not help either -- it gates the chat call site, not the login
override read.  The lane had shipped a chat command that bricks a GM account
with probability 326/330, and had written "the worst it can do is put a
listed GM in a different scene" in three places.

Fixed the only way that is not a second copy of lane A's data:
`login_entry_is_pinned` asks `world_scene_travel.load_scene_registry()`
itself, fail-closed on unknown and on a registry it cannot read, and
`stageable_scene_ids()` publishes the answer so a ticket can print the list
instead of a tester discovering it by locking an account out.

The same pass also produced, all fixed here:

* **The new test module would not have IMPORTED on the Windows gate.**
  `os.geteuid()` in a `skipIf` decorator is evaluated at import and does not
  exist on Windows -- a collection error, not a skip, and a red gate closes
  the PR.  Every skip in that module is now a branch instead: each platform
  asserts what is true of it, and nothing is silently not-run.  (That also
  answers the second finding: the skips were undeclared in
  `docs/PYTEST_SKIP_PINS.json`, which the Windows gate's own census fails on
  and which is not this lane's file to edit.)
* **The privilege invariant had a detector, not a door.**  The source scan
  for the standalone map's names was defeated by splitting a string literal
  -- the same shape as last round's `AUDIT_OUTCOMES[-1]`, and the same
  lesson this lane wrote down and then did not apply.  The writer now
  refuses to write the standalone map's resolved file, whatever resolution
  produced it.  And `restore_login_scene`, whose comment claimed it "can
  only write a value that was already in this file", would in fact add any
  name at all; it now refuses a name that is neither listed nor already in
  the map.
* **The `issued` audit row still said "no gameplay effect applied"** in the
  file GT-127 and GT-141 are graded on, one row above an outcome that names
  a durable config write.  Rewritten to what that row can honestly say.
* **A successful undo left its own "staged" event standing.**  Retracted
  explicitly now (`gm_chat_action_outcome_stage_reverted`).

### The one thing this round did NOT fix, and who owns it

After a staged relogin the server's own `selected.position.scene_id` still
reads the character's stored scene, not the scene the override sent them to
(the override substitutes only the id fed to `resolve_entry`).  So `/warp`'s
routing predicate compares against a stale number: standing in scene 2 via a
staged login, `/warp 2 x y` stages again instead of taking the ForcePos
branch, and `/warp 1 x y` takes it.  Nothing is on the wire today, so nothing
is misdirected today -- but the day COO opens the version gate, that branch
would compose a ForcePos for the wrong scene, which is the exact
misrepresentation `warp_executor` refuses cross-scene warps to avoid.

That row is written in `runtime.py`'s login path, which is chief's zone:
`CORE-REQUEST-GM-033`.  Until it lands, `GT-141` tells the tester to log out
again rather than type a second `/warp` in the same session.

---

## Round `ank2vl` (2026-08-29 05:0x +07:00) -- a tripwire for the way `#224` died

This round set out to recover `#224` and fix the `os.geteuid()` line that
closed it.  **The recovery is not this round's**: the `gejldf` session did
the same work in parallel and landed it first, as `#232` (merge `b229269`),
and its `POSIX` / `ROOT` split is what is on `main`.  Where both rounds
touched a file, `main` won outright -- this round's own version of
`tests/test_gm_login_scene_stage.py` was discarded rather than merged, so
nothing here competes with what already landed.

What is left is the part `main` does not have: a guard against the failure
mode itself, rather than against the one line that caused it.

### The failure mode, kept on the record

```
tests\test_gm_login_scene_stage.py:295: in RefusalLeavesTheFileAloneTests
    @unittest.skipIf(os.geteuid() == 0, "root ignores directory write bits")
E   AttributeError: module 'os' has no attribute 'geteuid'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

(Actions run 33210364835, job `gate`.)  Two things worth keeping, neither
obvious from the line:

1. **A `skipIf` protects the test body, never its own argument.**  The
   condition runs while the class body runs -- at import -- so a POSIX-only
   call in a skip condition executes on Windows no matter how many
   `os.name` guards sit above it.  No ordering of decorators helps.
2. **A collection error is not one red test, it is the whole gate.**
   pytest aborted, so `pytest_subset` (exit 2) AND `skip_census` (exit 1)
   went red together -- the census saw 0 skips where nine modules pin 48
   between them and reported nine PIN DRIFTs unrelated to the cause.
   Chasing those first would have cost another round.

### `tests/test_gm_tests_collect_without_posix.py`

Imports **every** `tests/test_gm_*.py` for real, in a child process with the
POSIX-only names removed from `os` and the POSIX-only modules refusing to
import.  Not a grep: it reproduces the failure mode.  Measured both ways --
the file exactly as `#224` pushed it fails the probe with the gate's own
message, and every file on `main` today passes.

pf-adversary found three things worth naming:

- **The file was not `git add`ed.**  The gate checks out what git has, so the
  whole deliverable would have shipped as zero bytes.  There is now a test
  that goes red when a `tests/test_gm_*.py` exists on disk and git does not
  know it -- it caught itself.
- **The name list was hand-written and incomplete**: `os.setpriority`,
  `os.wait`, `signal.SIGKILL`, `socket.AF_UNIX`, `select.epoll` and
  `readline` all walked past the first version, two of them inside the very
  module it claimed to cover.  All six are pinned by their own bait tests
  now, the list reaches modules beyond `os`, and the docstring states that
  the lists are `[proposed]` with only `geteuid` measured.
- **`subprocess.run(text=True)` with no `encoding=`** puts the cp874 trap in
  the reporting path -- the place a tripwire can least afford it.  Both ends
  are explicit now.

A negative result kept rather than dropped: setting `os.name = "nt"` in the
child, so that import-time `if os.name == "nt":` branches would execute, is a
**false red on all 28 lane-GM modules** -- `pathlib.Path()` picks
`WindowsPath` off `os.name` at instantiation.  Not shipped; the docstring
says that half stays unwitnessed rather than implying coverage.

### nonclaim

1. **No GM capability changed this round, in any direction**, and
   **ไม่มีการใช้ GM ข้ามขั้นใดในรอบนี้**.  One new test file, nothing else.
2. **[withdrawn]** This round does not claim the `#224` recovery.  `#232`
   landed it; an earlier draft of this section claimed otherwise and was
   wrong.
3. เขียว(cloud sanity) only -- the lane suite is 567 passed / 0 skipped on
   `main`'s files plus this one.  Actions decides.

## Round `tp8mq6`: the condition that keeps `COO-DECISION 20260829_0542` true

`COO-DECISION 2026-08-29T05:42+07:00`
(`pf_bridge/notes_to_chief/20260829_0542_COO-DECISION-standalone-map-is-not-consumed.md`)
answered this lane's own ASK and upheld the lane's assumption: the STANDALONE
login-scene map (`config/gm_login_scene_standalone.json`) is **not** consumed
on login, while the GM-gated map (`config/gm_login_scene.json`) stays
single-use per `COO-DECISION 20260829_0441` item 2.

The confirmation is conditional, and the condition is the whole round:

> **Item 3.** If any path ever lets the client or a chat command write or
> modify the standalone file, this decision is **void immediately** and the
> standalone map becomes single-use, without asking again.
>
> **Item 4.** Lane GM writes the test that pins item 3 -- if somebody adds a
> write path later, the test must go RED. Due this round.

### Delivered

| file | what |
|---|---|
| `tests/test_gm_standalone_map_is_not_chat_writable.py` (new) | the item-4 tripwire |
| `src/pirateforce_foundation/gm/login_scene_consume.py` | docstring: assumption -> CONFIRMED, plus item 3 as a NONCLAIM |
| `src/pirateforce_foundation/gm/login_scene_override.py` | docstring: what 0542 did and did **not** confirm |
| `tests/test_gm_login_scene_consume.py` | `StandaloneMapTests` docstring: these do not flip (item 1) |

Nothing was inverted, per item 1 of the decision: `STANDALONE_NOT_CONSUMED`
is the same outcome it was and the two `StandaloneMapTests` cases stand as
they were.

**One behaviour DID change, and it was not in this round's plan**: the D3 fix
below. An earlier draft of this paragraph said `login_scene_consume.py` had
no code change at all -- true when written, false after `pf-adversary`, and
struck here rather than deleted. The change RESTORES the guarantee
`COO-DECISION 0441` item 2 ordered; it grants nothing new.

### How the tripwire is built, and why not as a scan

Two layers, with the weaker one labelled weak in the file itself:

1. **The door (primary).** Every name in `commands.COMMAND_NAMES` is driven
   end to end through the production entry point
   (`chat_command_action.make_gm_chat_command_action`) as a listed GM, with
   the standalone map pointed at a throwaway file that already holds an
   operator's line. Afterwards the file must be byte-identical, its directory
   must hold no new file, the reader must still return what the operator
   typed, and **no write-capable filesystem call made anywhere during the run
   may have named it** (`WriteWatch` wraps `builtins.open`, `io.open`,
   `os.open`, and `os.replace/rename/remove/unlink/truncate`).
2. **The scan (early warning only).** A source scan over the package for the
   map's two names, prose stripped, allowlisting only the reader. It is
   explicitly *not* the guard: `login_scene_stage._standalone_config_path`
   already records pf-adversary defeating a scan of this exact shape by
   splitting a string literal.

**The tripwire for tomorrow's command.** A test enumerating today's six
commands says nothing about the seventh, so the exercise table is compared
against `commands.COMMAND_NAMES` itself. Adding a command without adding a
line here fails the file -- the new command has to be walked past the door
before it ships.

### pf-adversary rebuilt this file, and the first version was not a guard

The tripwire was written, measured against two planted writes, and reported
as working. `pf-adversary` then walked a **nine-line** write straight past
it. Everything below is a defect it found and this round fixed; the entries
are kept because the shapes repeat.

| # | what it broke | how |
|---|---|---|
| **D1** | the door asked about **one resolved path** | the fixture binds the map via `STANDALONE_ENV_OVERRIDE`; production falls back to a **cwd-relative** `config/gm_login_scene_standalone.json` whenever that env var is unset -- the ordinary deployment. A `/lv` handler writing the production default left the real file in the checkout with **4299 tests passing**. |
| **D2** | only ONE of the two client doors was driven | item 3 says "the client **or** a chat command". `runtime.py`'s `0x51E9` branch fires `lane_hooks.fire("vital_inbound_gm_run_command", ...)` -> `lane_hooks/lane_gm_run_command.py` (`production_allowed = True`) -> `gm/dispatch`. A write planted there changed the map **from a client frame** with the suite green -- and needed no split literal, because the scan globbed `gm/` and `lane_hooks/` is not in it. |
| **D3** | the GM-gated map's **single-use** guarantee was already broken | `login_scene_consume` read the scene, then re-read the GM map; if another login's atomic claim landed between the two it concluded "then the STANDALONE map answered" and handed the single-use scene to the **loser** as well, labelled `standalone_not_consumed`, with no standalone file on disk. 4/4 under parallel load, 0/8 alone. |
| **D4** | "tomorrow's command" tripwire was satisfiable by `()` | the check compared KEYS; the per-line loops never execute on an empty tuple, so a new command shipped "walked past the door" without reaching it. |
| **D5** | the run could be silently emptied | with the shared rate limit lowered, 5 of 6 command names came back `refused_rate_limited` and every "did not write" assertion stayed green and meaningless. |
| **D6** | two recorder gaps | a `dir_fd`-relative `os.open` records a **bare relative name**, which never matched a realpath; a deferred (thread/timer) write outlives the watch. |
| **D7** | prose asserted more than the code did | "catches a write through ANY route", "watches the syscalls", and the Thai closing line all claimed the strong form. |
| **D8** | scan mechanics | the docstring strip ran **after** `#`-line removal, so any docstring containing a markdown heading survived into the scan; `glob("*.py")` never descended; the floor was a magic number. |

### What changed in response

- **Ask about the NAME.** `WriteWatch.named_basename()` flags any recorded
  write whose file name is `gm_login_scene_standalone.json`, however it was
  resolved -- which also closes D6's `dir_fd` route -- and every assertion
  additionally checks that the **production default path** did not appear.
- **Drive the client door too.** `TheOtherClientDoorTests` fires the real
  `vital_inbound_gm_run_command` hook (real hook, real dispatcher, real
  allowlist; only the capture root is pinned to a temp dir) with six hostile
  payloads, as a player and as a listed GM, and reads `runtime.py` to confirm
  the point it drives is the one the runtime actually fires.
- **Fix D3 in the module.** `_ask_the_standalone_map()` asks that map
  directly instead of inferring it by elimination; the loser of a claim now
  gets `NOTHING_STAGED` and the default scene. Pinned by
  `test_the_loser_of_a_claim_is_not_told_the_standalone_map_answered`, which
  forces the interleaving deterministically and **fails against the pre-fix
  code** rather than waiting for a loaded CI.
- **Un-empty the table and the run.** Every command name must have at least
  one line, and every name must appear as `gm_chat_action_accepted_<name>`
  in the session's events -- a refusal that empties the run is now red.
- **Scan**: docstring cut from the original source first, `**/*.py` plus
  `lane_hooks/lane_gm_*.py`, and the magic floor replaced by naming the
  modules that must be in scope.

### Measured: every plant listed here trips it (not: every plant does)

Each row was executed against the fixed file and then reverted.

| plant | result |
|---|---|
| `open(standalone, "w")` with the JSON key as a **split literal** | RED |
| **write-then-restore** (file ends byte-identical) | RED, recorder only |
| **D1**: production cwd-relative default, split literals | **RED, 8 tests** |
| **D2**: write inside `lane_gm_run_command.py`, client route | **RED, 3 tests** |
| **D4**: new `COMMAND_NAMES` entry with `()` | **RED, 3 tests** |
| **D5**: rate limit lowered to 3 | **RED, 11 failures** |
| **D6 route A**: `dir_fd`-relative `os.open` + `os.write` + restore | **caught by basename** (exact-path check still misses it, as designed) |

The non-GM case stayed green under the write plants, which is correct: a
player is refused before the payload is decoded, so that route never reached
them.

### nonclaim

1. **No GM capability changed this round, in any direction**, and
   **ไม่มีการใช้ GM ข้ามขั้นใดในรอบนี้**. One new test file, one behaviour
   fix inside `login_scene_consume`, and three docstrings.
2. **This does not claim the standalone map is safe.** It skips
   `gm_accounts.json` membership entirely, which is a *stronger* capability
   than anything the GM-gated map grants -- this lane said so in the ASK the
   COO answered, and the COO accepted that nonclaim. All that is claimed is
   the property item 3 rests on: nothing a client sends, and no chat line,
   can write that file. Its remaining protection is operator-at-the-machine
   access, nothing else.
3. **The door proves "no route that RAN", not "no route that exists".** It
   wraps five families of Python-level call -- module attributes, not
   syscalls -- plus the file, its directory and the production default path.
   A write deferred past the assertions (thread, timer, `atexit`) is a route
   it does not cover, and that is named here rather than left to be found.
4. **D3 was a live defect on `main`, not one this round introduced**, and it
   is fixed here because this round's docstrings assert the guarantee it
   broke. The single-use condition (`COO-DECISION 0441` item 2) was **not**
   held before this commit whenever two logins of one account overlapped --
   which `login_scene_consume`'s own identity note calls the ordinary case,
   since the lane shares one `session.token`.
5. **`GT-110` stays PARKED** -- untouched by this round. What changes for it
   is only that its repeatability is now a confirmed decision rather than
   this lane's assumption.
6. **[correction to an earlier round's figure]** The round `dnh0ai` section
   above says "the lane suite is 567 passed / 0 skipped". That was true when
   written; it is stale, not wrong-at-the-time, and is struck rather than
   edited. Today: lane GM **640 passed / 4 skipped**, whole repo **4377
   passed / 327 skipped / 0 failed**. Those 327 skips are not named, counted
   or capped anywhere this lane owns -- flagged, not claimed as handled.
7. เขียว(cloud sanity) only. Actions decides.

## ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `tp8mq6`)

ผู้เทสที่ตั้ง `gm_login_scene_standalone.json` ไว้เอง **เข้าฉากเดิมซ้ำได้ทุกครั้งที่รีทราย โดยไม่ต้องพิมพ์คอนฟิกใหม่**
และตอนนี้เป็นคำตัดสินที่ตรึงด้วยเทส ไม่ใช่พฤติกรรมที่บังเอิญเป็นอยู่

และของที่ใหญ่กว่านั้นซึ่งไม่ได้อยู่ในแผนของรอบนี้: **ผู้เทสสองคน (หรือสองหน้าต่าง) ที่ล็อกอินพร้อมกัน
จะไม่ได้ฉากที่ stage ไว้ทั้งคู่อีกแล้ว** — ก่อนคอมมิตนี้ ผู้แพ้ของการแย่งชิงได้ฉากนั้นไปด้วย
และแถวออดิตเขียนว่ามาจากแผนที่ standalone ที่ไม่มีไฟล์อยู่จริง

**บรรทัดที่ต้องแม่น** (ฉบับก่อนของบรรทัดนี้อ้างเกินจริงและ pf-adversary หักล้างแล้ว):
ถ้าใครเพิ่มทางเขียนไฟล์นั้น **ผ่านเส้นทางที่เทสนี้ขับ และในคอลที่มันเฝ้า** ชุดเทสแดงก่อนถึงมือผู้เทส
ทางที่เลื่อนการเขียนออกไปหลังเทสจบ ยังเป็นช่องที่เขียนกำกับไว้ ไม่ใช่ช่องที่ปิดแล้ว

### Follow-up in the same round: the fix for D2 was itself vacuous

`pf-adversary`'s second pass planted a write on the **authorized** half of
the `0x51E9` door (past the allowlist check, which is where a real GM feature
would live). `TheOtherClientDoorTests` -- the class added to close D2 --
stayed **green**.

Cause, measured rather than reasoned: `lane_gm_run_command` calls the
dispatcher with no config path, so the allowlist resolved to the checkout's
non-existent `config/gm_accounts.json`. Nobody is a GM there, so every
payload -- `GM_ONE` included -- came back
`gm_run_command_refused_not_gm_account`. The class's liveness check only
asked whether *some* `gm_run_command_*` event appeared, and a refusal
satisfies that. It covered the refusal branch and nothing else.

Fixed by pinning the allowlist through `accounts.ENV_OVERRIDE` -- the same
knob an operator uses, so the hook's own default resolution finds it -- and
by asserting that the authorized half was really walked
(`gm_run_command_authorized_capture` present, `..._refused_not_gm_account`
absent). The same plant now turns the class **RED**.

This is the D5 shape appearing inside the fix for D2, one round later: a
liveness check that accepts any event rather than the event that means the
code under test ran. Recorded because it will be tempting to write the loose
version again.

### Second adversary pass: twelve more, two of them bugs in the D3 fix itself

The reworked file went back to `pf-adversary`. It broke the tripwire three
more ways and found the D3 fix half-applied. Every row was executed against
the fix and reverted.

**In the module:**

| # | what | measured |
|---|---|---|
| F3 | the D3 fix reached **one loser branch, not both** | `claimed is None` -- the *more* likely loser under contention -- still returned `NOTHING_STAGED` without asking the standalone map, so an operator's standing entry was lost on every login that lost the claim: **420 of 420 losers** over 60 trials x 8 threads. This falsified this round's own Thai deliverable line about `GT-110` re-entering the same scene on every retry. |
| F4 | the fix **regressed the non-GM path** | a non-GM's scene can only have come from the standalone map, so the extra read was unlosable upside-free: a file mid-save inside the new window became `consume_failed`, a removed file became `nothing_staged`, where the old code returned the scene. That call site keeps the id it already holds. `CONSUME_FAILED` is wider than its name and now says so. |

**In the tripwire:**

| # | what | measured |
|---|---|---|
| F1 | **it never made the call `runtime.py` makes** | production calls `consume_login_scene_override(self.token)` with NO config paths; every test passed all three. A plant inside the reader guarded by `if config_path is None:` passed **21/21** while granting an unauthenticated login its own scene. One case now makes the bare call, paths supplied by env var as an operator supplies them. |
| F2 | **every branch behind a shut gate was unreachable**, and `/say` is one | a plant just past `_say_action`'s `if version is None:` return passed 21/21 -- and would fire the day RE-132 closes, which is when nobody is looking. The file already forced the ForcePos gate open for exactly this reason. |
| F7 | the production-path check **turned the file RED on a correct deployment** | with a legitimate operator file present and no plant anywhere: `FAILED (failures=9)`, accusing an inbound vital of creating a file the operator typed. The obvious fix -- delete the assertion -- would reopen D1 permanently. Snapshots in `setUp` now. |
| F6 | the scan's vocabulary was **two lowercase names** | the reader exports UPPERCASE constants, so an entirely idiomatic writer (`os.environ.get(STANDALONE_ENV_OVERRIDE) or STANDALONE_DEFAULT_CONFIG_PATH`) walked past with no split literal and no trick. |
| F6b | the reader-strip added the previous commit **was itself a hole** | the JSON key is a substring of the reader's name, so `"load_standalone_login_scene_overrides"[5:27]` was deleted along with it; a working `os.replace` write passed both source guards. The strip skips quoted occurrences now. |
| F8 | `WriteWatch` was **blind to bytes paths** | `realpath` returns bytes for a bytes argument and a bytes basename never equals a str one -- in the single check that exists to catch a third resolved path. `os.fsdecode`. |
| F5 | `assert_every_command_was_accepted` **does not prove reach** | the event fires before routing, and four of six names (`npc`, `item`, `lv`, `spawn`) have no handler at all. The docstring claimed reach; it now states the weaker thing it can prove. |
| F11 | a duplicated test method silently discarded one test | |

### The limit this round could not close, stated as a question

Every guard here asks *"did a write happen on a path a test drove?"* -- and
F1, F2 and F5 are the same answer three times: **the routes that matter most
are the ones no test can drive yet**, because they sit behind an unopened
version gate, behind a default only production resolves, or behind a handler
nobody has written. The equality check against `COMMAND_NAMES` sees command
*names*. It cannot see gates, handlers, or which arguments a caller omitted.

So "no route that RAN" shrinks every time this lane adds a gate, and the file
will keep reporting green about a smaller world unless someone notices. **What
rule decides, for each newly added GM branch, that it must be walked with its
gate forced open and its production path resolution live -- and who enforces
it?** This lane does not have that rule. It is carried here as an open
question, not as something the round solved.

### nonclaim (supersedes the list above where they disagree)

1. **This file does not prove item 3 holds.** It proves no route that RAN
   violated it. Three separate classes of unrun route were found in one
   review; there is no reason to think that list is complete.
2. **Three reviews, three times the guard was green about a smaller world
   than this lane claimed.** Not wrong facts -- a shrinking scope described
   as complete. Recorded because the correction is the finding.
3. `GT-110` stays PARKED; `GT-141` must not be graded with two overlapping
   logins until this round's PR merges (its head carries the reason).
4. เขียว(cloud sanity): whole repo **4377 passed / 327 skipped / 0 failed**,
   lane GM **640 passed / 4 skipped**. Actions decides.

## Modules delivered (round `qq0i9u`, config ADMISSION: the silent lockout)

### The defect, measured before it was fixed

Two config files in this lane point an account at a scene on login: the
GM-gated `config/gm_login_scene.json` (which a chat `/warp` writes) and the
standalone map (which only an operator writes). Until this round only the
WRITER asked whether the login path would accept the destination --
`stage_login_scene` has asked lane A's registry since round `0z3kjx`,
because staging a named-but-unpinned scene bricked the account. The READER
asked the client's 330-row scene NAME table and nothing else.

An entry that arrived through a text editor therefore skipped the check
entirely. Round `38c4tv` walked it through the real dispatcher with
`{"plain_tester": 17}` -- scene 17 is in the name catalog, so it loaded, and
is pinned `login_entry_allowed: false`, so `resolve_entry` refused it:

```
login #1: actions == []   events: standalone_kept_17, applied_17,
                          world_scene_entry_refused_no_reply
login #2: byte-for-byte identical
```

The refusal deliberately sends no reply so the client can retry -- and the
standalone map is deliberately never consumed (`COO-DECISION 20260829_0542`)
-- so the retry met the same wall. **Permanently, and silently**: no audit
row, no expiry, no in-game fix (the in-game fix needs a chat line, which
needs a login), and the file is in `.gitignore`, so only somebody with shell
access on the server host could undo it.

### What was built

| module | what it does |
|---|---|
| `gm/login_scene_admission.py` (new) | owns `login_entry_is_pinned` / `stageable_scene_ids`. Imports neither the reader nor the writer, so BOTH can use it -- `login_scene_stage` already imports `login_scene_override`, so the arrow only goes one way and the reader could not have imported the writer's copy. |
| `login_scene_override._load_scene_id_map` | refuses an inadmissible entry when the map is READ, for both files: prints `GM_LOGIN_SCENE_CONFIG_REFUSED` to stderr, then raises `ValueError`. |
| `login_scene_stage` | keeps the two names bound to the new module rather than owning a second copy. One implementation, asserted with `assertIs` in the tests, not described in a comment. |

**A second condition was added to the predicate.** `resolve_entry` -- the
call the login actually makes -- has FOUR refusal reasons: not pinned, id out
of range, `login_entry_allowed=False`, and pinned-with-no-spawn
(`REFUSED_NO_PINNED_SPAWN`, home excepted because home arrives on the
character's own row). The staging path modelled only the third. A spawnless
pinned destination would have been admitted and then refused at login --
the same lockout, one refusal reason along. No scene in the registry is
spawnless today, so this half is a guard against lane A pinning one
tomorrow, and the code says so rather than implying a fix.

### Why the raise does not take a login down

`consume_login_scene_override` already catches `(OSError, ValueError)` and
answers `CONSUME_FAILED`, which grants no scene. So a refused entry means:
the account logs in at its own stored row (scene 1), the console names the
file, the account, the scene and the admissible ids, and the operator's file
is not edited. **Fail-closed on the whole FILE, deliberately** -- a loader
that dropped the bad line and honoured the rest would be the same silence
this round is closing, one row down. Price, stated: one typo stops every
override in that file until it is fixed. Nobody is locked out of the game.

### The cross-check that makes this more than a second opinion

`tests/test_gm_login_scene_admission.py` walks lane A's registry scene by
scene and asks `resolve_entry` itself, in the shape `runtime.py`'s login
calls it, **in both directions**: every admitted scene must be accepted, and
every refused scene must be refused. A fifth refusal reason added upstream,
or a spawn removed from a pinned scene, turns this red here instead of
turning a tester's account into a locked door. The admissible set is also
pinned as the literal `(1, 2, 278, 997)`, so lane A pinning a fifth scene is
a decision somebody makes rather than a silent widening.

**What that cross-check could NOT reach, measured rather than assumed.** It
walks the scenes in today's registry, and none of them is spawnless, so the
spawn condition never executed on its False side: deleting it left the whole
lane suite green, 658 passed. Same for the home carve-out, and same for the
name-catalog filter in `stageable_scene_ids` -- and that last mutation
reached a pushed commit of this branch before a test existed that could see
it. `TheSpawnConditionTests` and `TheAdmissibleSetIsAlsoNamedTests` bend the
registry through lane A's own loader and ask both sides about the bent row,
which is the only way to execute those branches at all. Ten mutations, all
killed, on a 667-test baseline: 14 / 20 / 98 / 2 / 14 / 4 / 1 / 1 / 1 / 1.

### GATE-WALK (`COO-DECISION 20260829_0742`)

`runtime.py`'s `world_scene_entry_refused_no_reply` branch and the
restore-after-refusal handler inside it are no longer reachable from a
config file **on a process whose registry matches the disk**. The test that
walked them was not deleted: it reaches them at the seam that remains, with
an admissible scene, so the gate is walked open rather than disabled.
Mutation M13 (delete the handler from `runtime.py`) turns exactly that one
test red and nothing else, so the branch really executes.

~~the seam ... microseconds later~~ **That was wrong, and it matters.**
`runtime.py:527` loads the registry ONCE at boot and threads it into
`resolve_entry` at `runtime.py:5355`; admission re-reads the file on every
login. The gap is the uptime of the process, not microseconds -- see the
defect below.

### The claim this round could not keep (D1)

`pf-adversary` reproduced the original lockout **with this change in
place**: a process holding a boot snapshot that bars scene 278 while the
disk allows it admits the config entry, applies it, and `resolve_entry`
refuses -- no reply, no consumption, every retry identical, and
`GM_LOGIN_SCENE_CONFIG_REFUSED` never prints, so the new diagnostic points
away from the fault. Any post-boot edit that WIDENS the registry does it;
narrowing edits are safe (admission simply refuses, which is stricter than
the login needs).

So the honest claim is: **a config typo can no longer lock an account out
on a process whose registry matches the disk.** "No account can be locked
out by this lane's configs" is false and has been struck everywhere it was
written. `CORE-REQUEST-GM-034` asks chief for the one line at
`runtime.py:5308` that closes it; the lane will add the
`scene_registry=` parameter on its side, defaulting to today's behaviour,
with a test that stays red until that line lands.

### The diagnostic had to stop altering dispatch

`session.py` states the rule -- A DIAGNOSTIC MAY NEVER ALTER DISPATCH --
and the first version of this round's console line broke it. The bridge
console is `cp874`; an account name it cannot encode raised
`UnicodeEncodeError` out of the print, and `runtime_console._Mirror` writes
the console before the retained file, so the refusal was recorded nowhere
at all while the caller received the encoder's exception instead of this
lane's. Operator-controlled fields are folded ~~through `ascii()`~~ and the
whole print is wrapped: a closed or hostile stderr costs the line, never the
refusal.

> Two corrections from round `7gplcy`, struck rather than deleted.
>
> **The escape.** `ascii()` was the right idea in the wrong function -- it
> escapes as well as folds, which is what turned the gate red and closed
> `PR #249`. The fold goes through `console_safe()` now, which asks the
> stream what it can carry rather than assuming ASCII.
>
> **The attribution.** This paragraph reads as though the FOLD is what keeps
> the diagnostic from altering dispatch. It is not; the WRAP is, and it holds
> with no fold at all (measured, pf-adversary round `7gplcy`: with the fold
> removed the caller still receives this module's `ValueError`, never the
> encoder's). The fold buys something narrower and still worth buying -- that
> the line gets written, and written in a form an operator can read, paste
> and grep. Two mechanisms, two promises.
>
> See "Round 7gplcy" at the end of this file.

### Cross-lane coupling, declared rather than discovered later

Lane A's `scenarios/world_scene_registry_001.json` now decides what this
lane's configs may contain. Letter to lane A and chief:
`pf_bridge/notes_to_chief/20260829_0930_LANE-GM-STATUS-config-admission-follows-lane-A-registry.md`.

### nonclaim

1. Nothing here says a tester CAN reach any scene. It says the server will
   not accept an instruction to send them somewhere the login would refuse.
   Reaching a scene is `GT-141`'s to decide, on a screen.
2. **Never measured against a real client.** Every line of this round was
   measured through the dispatcher in the test suite.
3. ~~`[สมมติของสาย GM - รอ COO ยืนยัน]`~~ **RULED in round `7gplcy`**
   (`COO-DECISION 20260829_0941` approves option (a)) -- this was option (a) of the lane's own
   ASK-COO letter of 2026-08-29T09:06+07:00, which said the lane would walk
   it if no answer arrived by the next round. None did. It does not reverse
   `COO-DECISION 20260829_0542`: that ruled on whether an accepted entry is
   spent, this rules on whether it is accepted. The revert is this module
   plus two lines in the reader.
4. The spawn condition fixes nothing that is broken today.
5. **A reviewer's mutation reached a pushed commit of this branch** (`483db7c`,
   `stageable_scene_ids` missing its name-catalog filter) because a
   mutation run and a forced commit shared one working tree, and no test
   could tell. Recovered in the next commit, and the test that kills it now
   exists. Recorded because the process failure is the finding: never run a
   mutation pass on the tree you are about to commit, and remember that
   `git checkout -- <path>` restores the INDEX, not the work you just did.
6. **Not tested, declared by the adversary rather than by me**: that an
   ADMISSIBLE config value cannot break a login further downstream. It
   stopped short of driving scenes 278 and 997 end to end. Unknown, not
   safe.

## Round 7gplcy -- the round qq0i9u lost, and the gap that lost it

Round `qq0i9u` built everything above and **none of it reached `main`**.
`PR #249` was closed unmerged by `.github/workflows/merge-claude-pr.yml`
because the Windows gate was RED, and a red pull request left open would
hold the cloud round lock against every later round forever. The branch was
kept; this round recovers those two commits onto `main` as it stands today
and fixes what turned the gate red.

Approved in the meantime, so the assumption tag above is now a ruling:
`pf_bridge/notes_to_chief/20260829_0941_COO-DECISION-standalone-map-refuses-an-unreachable-scene-at-load.md`
walks option (a), keeps `COO-DECISION 0542` standing, and states the
combined rule as **hard to admit, unlimited to use** -- not *easy to admit,
then deleted quietly*. Its item 4 also settles what looked like a
limitation: today only scenes 1, 2, 278 and 997 are admissible, and that is
the correct value rather than something to widen. A door opens, the map
accepts it, automatically, with no second list to maintain.

### The defect: a fold that also escapes is not a fold

One test failed on the gate, `TheLoaderTests::test_the_console_token_names_
the_file_the_account_and_the_way_out`, on this line:

    self.assertIn(str(self.standalone_path), console)

The console token folds operator-controlled fields to ASCII so a `cp874`
console cannot turn a diagnostic into an exception (the section above).
That fold ran through `ascii()`, which folds AND escapes -- so on Windows
the line said `path='C:\\Users\\RUNNER~1\\...'` while the test, and the
operator, wanted `C:\Users\RUNNER~1\...`. The line named the file in a form
nobody could paste.

~~`console_safe()` now folds through `str.encode("ascii",
"backslashreplace")` instead: it folds exactly what `cp874` has no room for
and leaves every ASCII character, separators included, as it found them.~~

**Struck the same round, by pf-adversary, before it left draft. That second
sentence is false and the code it described repeated the defect it was
fixing** -- see "What pf-adversary broke" below. `console_safe()` folds
through the encoding of *the stream being written to*, and nothing wider.

### The finding is the blind spot, not the escape

`ascii()` was not a careless choice; it was measured, it fixed a real
defect, and the round that introduced it ran a full suite that reported
**0 failed**. It could not have reported anything else: on POSIX there are
no separators to double, so every assertion about that line passed here and
the only machine that could see the fault was the one that closes pull
requests.

So the fix is not "use `backslashreplace`". The fix is a test that
reproduces a Windows-shaped input **on the machine the round is written
on**: a backslash is a legal character in a POSIX filename, and
`TheLoaderTests::test_a_path_with_separators_in_it_is_named_verbatim`
writes a config at `dir\sub\standalone.json` and asks for the path back
verbatim. Reverting `console_safe` to `ascii()` turns it red here, in 0.16
seconds, instead of six minutes later on the gate.

~~`test_the_fold_survives_that_and_still_reaches_a_cp874_console` pins the
other half in the same place~~ -- it did not; it was named for the cp874
property and measured the ASCII-fold property. Replaced, below.

### What pf-adversary broke, before this left draft

**D3 -- the fix repeated the defect it was fixing, one field to the left.**
`str.encode("ascii", "backslashreplace")` does not fold "exactly what
`cp874` has no room for". It folds every non-ASCII character, and **`cp874`
is the Thai code page**: `"ทดสอบ".encode("cp874")` succeeds. On a
Thai-language project, an operator named `ทดสอบ` got a console line that did
not contain their account name and could not be grepped for it -- the
identical shape to `path='C:\\Users\\...'`, shipped by the round whose
whole thesis was *a fold that also escapes is not a fold*. Worse, this
round's own `assertNotIn("ทดสอบ", console)` would have made fixing it a red
test.

So the fold is no longer assumed. `console_safe(text, stream)` asks the
stream for its `encoding` and folds through that, falling back to ASCII when
the stream will not say (a `StringIO` has no `encoding` at all) -- narrowest
wins when we do not know. A Windows path keeps its separators, a Thai name
survives on a Thai code page, and `张三` still escapes.

That also sidesteps a question nobody has answered, rather than guessing at
it: **`runtime_console._Mirror` announces `utf-8` while `gate-windows.yml`
forces `cp874:strict`, and nobody has measured the real stream on the
owner's machine.** Asking the stream is correct in both worlds. Raised with
chief as `CORE-REQUEST-GM-035`.

**D1 -- the path half of the fold was pinned by nothing at all.** Deleting
`console_safe` from the *path* argument alone left the whole 4483-test suite
green, while the same deletion on the *account* argument went red in 0.16s.
Both of this round's new tests were about the path not being *escaped*, and
neither noticed it had stopped being *folded*. The live shape:
`PF_GM_LOGIN_SCENE_STANDALONE_CONFIG` under a home directory `cp874` cannot
carry -- the print raises, the wrap swallows it, and because
`runtime_console._Mirror` writes the console before the retained file the
refusal is recorded nowhere. The qq0i9u defect, returning through the other
field. `test_a_path_the_console_cannot_encode_is_folded_not_dropped` kills
it.

**D2 -- the test named for cp874 could not see cp874.** It used `ทดสอบ`,
which cp874 encodes natively, and its docstring claimed that dropping the
fold would raise `UnicodeEncodeError` out of the print. Both halves wrong:
that input does not raise, and for an input that genuinely cannot be encoded
the *wrap* (round `qq0i9u`) stops it raising out of the print anyway. An
evidence-layer swap -- a test named for one property, measuring another.
Replaced by the two above, and the dispatch claim re-attributed to the wrap
everywhere it was written.

**D4, D5 -- the strike over-struck and the ruling was not carried.** The
`ascii()` strike above took the true half of its sentence with the false
half; restored. And five places still carried
`[สมมติของสาย GM - รอ COO ยืนยัน]` after this round said the tag had become a
ruling; the three that are about *this* decision now say so. The two left
standing (`login_scene_override.load_standalone_login_scene_overrides` and
its module docstring) are about the standalone map's *existence without GM
listing*, which `COO-DECISION 0941` does not rule on. Still pending, still
tagged, deliberately.

| mutation | red here (was) |
|---|---|
| drop the fold on the **path** field | **1 (was 0 -- pf-adversary's survivor)** |
| drop the fold on the **account** field | 1 |
| fold at ASCII again, ignoring the stream | **1 (was 0)** |
| back to the `ascii()` escaping fold that closed `#249` | 2 |

Baseline 4484 passed, 327 skipped, 0 failed.

### nonclaim

1. This round wrote no new gameplay behaviour. It recovers a lost round and
   closes the gap that lost it; the claims of round `qq0i9u` above stand as
   written, including its struck sentence and `CORE-REQUEST-GM-034`.
2. **No GM step was skipped to produce any result here, because this round
   produces no gameplay result.** Nothing in it says a tester can reach a
   scene.
3. Never measured against a real client, or on Windows. The Windows failure
   is understood from the gate's own log for run `33229946448`; the fix is
   measured only through a POSIX reproduction of the same shape. The gate
   decides.
4. **[เสนอ ยังไม่วัด] and left standing deliberately.** `gate-windows.yml`
   sets `PYTHONIOENCODING: cp874:strict` job-wide, and
   `tests/test_gm_login_scene_admission.py` carries `张三`, `café`, `naïve…`
   as test inputs -- none of them cp874-mappable. If one of those subtests
   ever FAILS on Windows, pytest must print the subtest id to a strict cp874
   stdout, and whether its terminal writer's escape fallback survives that is
   unverified. They pass today (Actions run `33231419482`), so this is a
   hazard on the failure path only: a red run in this file could in principle
   come back as an INTERNALERROR with no `FAILED` line for the gate's own
   extractor to find. Raised rather than fixed -- the tests need those inputs,
   and `.github/` is chief's.
5. **The adversary's own untested claim, restated rather than absorbed:** it
   stopped short of driving an *admissible* config value end to end through
   scenes 278 and 997. Unknown, not safe.

---

## Round `7hfrt0` -- WHICH READING of lane A's registry a config entry is judged against

`CHIEF-REPLY` 2026-08-29T12:21+07:00 item 4 asked this lane to land a
`scene_registry=` keyword first, so chief's call site can pass `runtime.py`'s
boot snapshot into it.  Landed here, threaded through six files, default
`None` = the fresh file read every caller does today.

**THE PARAMETER DOES NOT ADD A READER OF THE REGISTRY -- IT REMOVES ONE.**
That is worth stating first because a new kwarg reads like the opposite.
`CORE-REQUEST-GM-034` reported a lane with three readings of one registry
free to disagree; chief's answer was to call `resolve_entry` itself at the
login site rather than write a private predicate.  This is the same answer
for the staging side: a caller that supplies its reading makes this lane
stop having one of its own.

### The two directions are not the same problem

| direction | who closes it | what it costs today |
|---|---|---|
| disk WIDER than the snapshot (file approves, process refuses) | chief's `resolve_entry` probe, on main via `#253` | ~~closed -- override refused by name, character logs in at its own row~~ see CORRECTION |
| disk NARROWER than the snapshot (registry edited to bar or drop a destination after boot) | ~~nothing yet~~ chief, on main via `#264` | ~~the whole-file load raises, `CONSUME_FAILED` -- EVERY account's override in that file stops working~~ closed for this direction: the load is judged against the snapshot the process holds |

- **CORRECTION** (LANE-GM round `1fq5yf`, 2026-08-29, from chief's own
  measurement in `CHIEF-REPLY` 2026-08-29T15:16+07:00 items 3 and 5/D2):
  wiring the snapshot into the consume call **moved** the WIDER case rather
  than leaving it where this table put it. It used to be caught downstream
  by the probe, which refused ONE entry BY NAME and printed
  `GM_LOGIN_SCENE_OVERRIDE_REFUSED`. Now the snapshot refuses the row at
  load time, the whole-file load refuses, and every account in that file
  gets `CONSUME_FAILED` together -- measured by chief through the real
  dispatcher with a two-account file `{good: 2, barred: 278}`, where the
  good account went down with the barred one, and pinned by their
  `test_one_refused_entry_takes_every_override_down_destroying_nothing`.
  - What did NOT get worse, and is why chief accepted the trade: the entry
    is never taken off disk, so nothing is destroyed, the login finishes at
    the character's own row, and there is no lockout.
  - What DID get worse: per-account resolution. One line the snapshot
    dislikes darkens every override in the file.
  - So the honest reading of row 1 today is "closed, at whole-file
    granularity" -- not "refused by name". The probe and restore remain as
    defence in depth for the case where admission and probe drift apart.
  - Chief has offered to relax the read side to per-line if this lane opens
    a ticket. **Not opened this round** and the reason is written down
    rather than left implied: this lane has no measurement of how often an
    operator's file holds more than one account, and asking for a rework of
    chief's read path on a guess is how the last two rounds' rework got
    paid for twice.

No gate at the call site can reach the second one: by the time the call site
sees anything, the load has already raised.  It has to be decided at the
load, which is where this parameter goes.

### `ConsumeResult.cause` — ~~the seven words~~ the closed vocabulary, and the axis they are cut on

Added round `1fq5yf` for `CORE-REQUEST-GM-037`; printed by `runtime.py`
since chief round `nbulzb` — see the PRINTED note above, and its tripwire
test.

🔴 **The heading said "seven" and the table below it has eight rows.** Chief
caught it in their reply of 2026-08-29T19:24+07:00 (item 2) and left it for
this lane; corrected in round `npo898` by **striking the number rather than
updating it**. Eight would be false in the round that adds a ninth, which is
D6 from round `6vhfgh` — this document stops carrying counts. The set that is
true today is `CONSUME_FAILED_CAUSES`, and the test that refuses a branch
outside it reads the *source*, not a number written here. The two "seven"s in
the paragraph below are about the discarded FIRST draft, which really did have
seven tokens; they stay.

The axis is **the remedy an operator would apply**, not which read failed.
The first draft cut it the other way and pf-adversary measured the result:
six of its seven tokens fired only if a config changed underneath a login
mid-flight, and the seventh answered *the same word* for both of the two
remedies chief said were different — including calling a perfectly readable
file `unreadable`, which is the normal case since `#264`.

| cause | what happened | remedy |
|---|---|---|
| `config_rejected` | the loader refused the file — malformed JSON, **or** valid JSON whose shape or scene id this lane rejects | edit the config file |
| `scene_not_admissible` | a row names a scene no reading of the registry admits (the ordinary hand-typed typo — e.g. 3 or 17, which *have* names) | edit the config file, to one of the admissible ids |
| `registry_stale_since_boot` | the row **is** admissible on disk today; only this process disagrees, because its snapshot predates the edit | **restart the server** |
| `gm_accounts_unreadable` | `gm_accounts.json` unreadable after the lookup passed | look at the accounts file |
| `gm_map_unreadable` | `gm_login_scene.json` unreadable | look at the override file |
| `standalone_map_unreadable` | the standalone map unreadable | look at the standalone file |
| `claim_raised` | the remover raised — entry's fate on disk **unknown** | check disk/permissions, then whether the entry is still there |
| `entry_survived_claim` | removal failed — entry **known** to still be there | delete the line by hand |

🔴 **Two corrections this table already carries, both from pf-adversary's second
pass, because the first version of it gave WRONG ADVICE:**

- `registry_refused_entry` sent *every* inadmissible row to "restart the
  server". But the row an operator actually hand-types — a scene with a real
  name that the login path does not admit — is refused by every reading of the
  registry, now and after any restart. The remedy was editing the file, which
  is the remedy the *other* token owned. The two remedies had stopped sharing
  a word without stopping being crossed. Split into `scene_not_admissible`
  (edit) and `registry_stale_since_boot` (restart), told apart by asking the
  disk whether it still admits the row.
- `config_unreadable` was renamed `config_rejected` because five of its six
  producers are **valid JSON with good bytes** (a string where a scene_id
  belongs, a scene id outside the catalog, a top-level list, a bool). Calling
  those "unreadable" was the same sin the first version committed, relocated.

The split that makes this worth printing is the first two rows. It is carried
by `login_scene_override.LoginSceneRefusedError`, a `ValueError` **subclass**
so that every existing caller's `except (OSError, ValueError)` behaves exactly
as before — the subclass only lets a caller that wants the distinction ask.

**Deliberately NOT split**, so it is not "restored" later: which *moment* a
read failed at (before vs after the claim). The standalone read has the same
two moments and got one token, so the axis was not even applied consistently,
and an operator does nothing different about the two. `claim_raised` vs
`entry_survived_claim` stays because that one *is* a remedy split.

Safety, since chief prints these on the owner's console: closed set, every
word a literal written before any client connected, no exception message ever
becomes a cause, `ConsumeResult` is immutable after construction, a `str`
subclass is refused by `type(...) is not str`, and every token is ASCII/cp874
with no space, `=`, or newline — so a forged second field or second console
line is not expressible. Four of those six exist because pf-adversary got
through the first version.

### What pf-adversary broke, and what changed because of it

The first version of this round was **not approved**.  Seven defects; the two
that changed the DESIGN rather than the code:

**D2 -- a snapshot-validated write poisons the file for every other account,
permanently.**  The measured version let a boot snapshot WIDEN a write.  The
entry lands in `config/gm_login_scene.json`, `_load_scene_id_map` then refuses
the WHOLE file (one bad line, every account's override dead), and no removal
path in this lane can clear it because `restore_login_scene` and
`claim_login_scene` both re-validate the whole file first.  A hand edit of a
gitignored config is the only way out.  It needed no exotic wiring: one server
RESTART re-reads the registry, and the fresh narrow reading meets the entry the
old wide one authorised.

The fix is a rule, not a patch: **THE FILE DECIDES WHAT MAY BE WRITTEN; A
SNAPSHOT MAY ONLY REFUSE ON TOP OF THAT.**  Reading may honour one process's
view, because a read writes nothing that outlives it.  Writing may not, because
THE ENTRY OUTLIVES THE PROCESS THAT WROTE IT.  That also answers the question
the adversary closed with -- "what happens to an entry whose authorising reading
no longer exists" -- by making such an entry unwritable in the first place.

**D1 -- the predicate never checked that the row it got was the row it asked
for.**  `registry[scene_id]` was trusted.  The most plausible wiring slip,
passing `scene_entry_registry.destinations` instead of `scene_entry_registry`,
is a TUPLE: subscriptable, so nothing raised, and `registry[14]` returned the
row at INDEX 14 (scene 278).  Scene 14 was admitted on scene 278's evidence,
`/warp 14` accepted, written, and refused by the login path -- the silent
lockout this module exists to close, reopened through the parameter meant to
help it.  A `MagicMock` admitted scenes 3, 17 and 999999 the same way.  Fixed
with `target.n_id != scene_id -> False`.

A duck-type shape gate was written alongside it and then **deleted**: removing
it again left every test green, because the identity check already refuses
every shape it did.  A second guard no test can tell apart from the first is a
claim with no evidence behind it.

Also fixed, all measured: **D3** the widened `except` clauses had changed the
DEFAULT path from "a bent lane-A row raises where a person sees it" to "no
scene is stageable" -- now `trusted` keeps the file path exactly as loud as it
was; **D4** eight of the threaded hops could be dropped with all 4599 tests
green (the whole standalone branch was green because the fixture wrote an
EMPTY map -- under the wrong JSON key, at that); **D5** the undo hop below;
**D7** two new tests were green for weaker reasons than their names, and the
"wrong objects" list had been chosen to pass rather than to probe -- the two
shapes that actually broke the guarantee were both absent from it.

### The defect this round nearly shipped, and it was in the UNDO

`restore_login_scene` was left without the parameter in the first draft.
`_write_entry` re-validates the WHOLE file before writing -- the reader's own
rules, deliberately, so a config with a typo comes back untouched.  So an
undo judged against a different reading from the write it is undoing
REFUSES: stage scene N under a snapshot that admits it, undo without the
snapshot, the load refuses N, `_write_entry` answers
`REASON_CONFIG_UNREADABLE`, and **the entry the call exists to remove stays
on disk**.  That is precisely the state `chat_command_action`'s withhold rule
("this house does not perform an effect it cannot record") exists to prevent,
reached through the undo that enforces it.

The rule now written into the source, because it is not obvious from any one
call site: **UNDO WITH THE SAME READING YOU STAGED WITH.**  It is why
`CORE-REQUEST-GM-036` asks for THREE call sites -- the third is chief's own
`_put_back_consumed_override`, which puts an entry back after the probe
refuses.

### Chief's merge-order warning, measured again in this lane's own house

Item 2 of that letter: a kwarg whose callee does not accept it raises
`TypeError`, which `runtime.py:5327` SWALLOWS into `login_scene_override =
None` plus an event -- the feature turns off silently.  Two test doubles in
this lane had exactly that shape:

* `test_gm_login_scene_consume.py`'s `lose_the_claim` -- the `TypeError` was
  eaten by `consume`'s own `except Exception`, and the test became "the claim
  was never contested".  It would have been GREEN but for one assertion that
  checks the race actually happened.
* `test_gm_login_scene_stage.py`'s `flaky` -- raised loudly, because the
  `except` around that call is narrower.

The one that swallows is the dangerous one.  Both fixed.

### What is NOT claimed

1. One layer only: wire/DB, headless.  **No client-observable evidence in
   this round at all.**
2. **No GM status was used to prove anything here.**  Nothing in this round
   is a milestone and nothing in it was reached by being a GM.
3. ~~The parameter has NO effect on a running server until `CORE-REQUEST-GM-036`
   lands: every caller in this repository passes `None`.~~
   - **CORRECTION** (LANE-GM round `1fq5yf`, 2026-08-29): struck because it
     stopped being true at a merge and nobody in this lane noticed --
     chief flagged it, along with six more labels of the same kind, in
     `CHIEF-REPLY` 2026-08-29T15:16+07:00 item 5 (D4). `CORE-REQUEST-GM-036`
     landed as `pirate-force-server` #264 (merged 2026-08-29T08:38:50Z) and
     `runtime.py` now passes its boot snapshot at all three call sites, so
     the parameter DOES have effect on a running server. What survives of
     the sentence: a caller that passes nothing still gets a fresh read.
4. Not measured against a real client; no scene named here is shown to be
   reachable by a person.
5. Green = **green(cloud sanity)** from `python -m pytest tests/`, not an
   Actions run.  The Windows gate closed round `7gplcy` outright once.
6. **The second adversary pass was this lane's own, not pf-adversary's.**  The
   twelve-mutation battery was re-run after every fix and all twelve are now
   killed, but nobody adversarial has looked at the FIXES.  D2's rule in
   particular is one round old and has had exactly one reviewer: the lane that
   wrote it.

## Round `9wy444` -- a mistyped GM command names its grammar, and says nothing else

**D8, closed on the operator's side, by the ruling that decided which side that is --
and NARROWER than the first attempt, because pf-adversary measured the first attempt
against the wired server instead of against a test.**

`pf-adversary` opened D8 against round `c48x1n`, this lane asked COO who the way out is
for (`notes_to_chief/20260829_1252_LANE-GM-ASK-COO-who-reads-the-way-out.md`), and
`COO-DECISION 20260829_1344` answered: path **(a)**, the console watcher. A reply that
reaches the tester at the game client needs the server->client channel locked behind
`/say`'s own gate (`COO-DECISION 20260829_0041`), and `CORE-REQUEST-GM-036` may not
start before that gate opens. So this round buys the operator a line and claims nothing
at all about the game screen.

### What was silent, measured through the real dispatcher

| typed | before | after |
|---|---|---|
| `/warp 9999` | `GM_CHAT_WARP_REFUSED ... stageable=(1, 2, 278, 997)` | unchanged |
| `/warp island` | NOTHING | `GM_CHAT_COMMAND_REFUSED account='...' reason=command_parse_error_GmCommandParseError usage='warp <scene_id> [x y]'` |
| `/warp`, `/warp 3 100`, `/warp 3 x y` | NOTHING | same usage line |
| `/nonsense`, `/` | NOTHING | the whole vocabulary, six usage sentences |

The refusal happens at the PARSE layer, upstream of every printer this lane owns --
which is why the way out added in `c48x1n` could not reach it.

### 🔴 The line carries NO CLIENT BYTES, and that is the design, not a detail

The first version printed `str(error)`, which quotes the offending token
(`got 'island'`). pf-adversary (D1) measured what that means where it runs:
`runtime.py:5140-5150` states plainly that `session.token` is the process-wide `--token`
CLI value, **not** a per-connection authenticated login -- every connection this listener
accepts shares one identity. On the only configuration where this feature ever fires
(that one token listed in `gm_accounts.json`), **any player typing `/warp <anything>` in
local chat would have had their sentence printed to the operator's console under the
operator's own GM account** -- and `decode_local_talk_payload` discards the wire's
`speaker` field, so the line could not even have told the truth about who typed it.
This lane's founding rule is that a non-GM's chat is never decoded, pattern-matched or
written anywhere by it.

So `usage_hint_for` returns one of exactly **seven fixed strings**: one of the six
`COMMAND_USAGE` sentences, or all six joined. Which of the seven is the only thing a
typed line can influence. That one change also closed three more of pf-adversary's
findings by construction rather than by patch:

* **D2** -- `runtime_console._Mirror` ANNOUNCES `utf-8` while the console FORCES
  `cp874:strict`, so `console_safe` folded nothing and `print` raised: `/warp ésland`
  produced **zero** lines on console *and* zero in the retained log, for exactly the
  inputs the feature was built for. Nothing unencodable is left in the line.
* **D7** -- strong-RTL letters and combining marks are category `Lo`/`Mn`, not `Cf`, so
  `has_format_characters` never saw them and `repr` left them raw: the parse-error path
  was echoing text carrying the very property the format-character path refuses to echo.
* **D6** -- a typed `GM_CHAT_WARP_REFUSED` could be quoted into the line.

### The rest of pf-adversary's report, and what was done with each

| # | finding | this round |
|---|---|---|
| D3 | `has_format_characters` ran BEFORE the rate limiter -- the one refusal that could print without spending a slot (**100 lines from 100 frames**, against 20 from 100 `/warp island`), and every line also lands in `server_console_live.err.txt` | **fixed**: moved behind the limiter; pinned with its control |
| D4 | the limiter runs before the parser, so a tester retyping at 5/s loses the way out after ~4 s -- at peak confusion | **not fixed, pinned as a known gap**: printing there is the flood D3 is about. The round's claim is scoped instead of widened |
| D5 | `REFUSAL_LOOKUP_FAILED_PREFIX` ("is my config broken") missing from a comment that read as exhaustive, and from the gate test | **fixed**: named in both, and its silence stated rather than papered over |
| D8 | a mutation echoing the refused text passed all 37 tests -- the bare `io.StringIO` console reports NO encoding, so `console_safe` ASCII-folded the bidi character the assertion looked for | **fixed**: `Utf8Console` announces `utf-8` like production; every "not in the console" assertion uses it |
| D9 | reversing `COMMAND_USAGE` left the WHOLE SUITE green; the comment claimed a pin that compares SETS | **fixed**: order pinned by a real test, false claim corrected |
| D10 | the width cap lived in the describer, so it was a property of that supplier, not of the line the printer writes | **fixed**: `MAX_CONSOLE_HINT_LENGTH` held at the printer |
| D11 | `GmCommandArgsError` arm of the `except` is dead -- `parse_gm_command` never raises it | **recorded, not removed**: it is a real catch for a real exception type; removing it would be a behaviour change outside D8's scope |

### The silence that stays, named so this is not read as more than it is

`not_gm` (never decoded), `not_a_command` (a GM talking to another player -- one console
line per sentence would bury the ones that mean something), oversized and undecodable
payloads (no human typing to blame).

**Still silent and NOT closed:** `rate_limited` (D4), `command_log_quota_exceeded`,
`command_log_write_failed_*`, `gm_account_lookup_failed_*` (D5). Each drops a
WELL-FORMED command, or a whole session, with no console line at all.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `9wy444`)

**คนเฝ้าคอนโซล** พิมพ์คำสั่ง GM ผิดแล้วรู้ว่าไวยากรณ์ที่ถูกคืออะไร แทนที่จะเห็นบรรทัดแชทหายไปเฉย ๆ
และแยก "พิมพ์ผิด" ออกจาก "เส้นทางตาย" ได้ ซึ่งก่อนรอบนี้แยกไม่ได้เลย
🔴 **สิ่งที่เขาไม่ได้และเคยเกือบได้: ตัวคำที่พิมพ์ผิด** -- ถอดออกโดยตั้งใจตาม D1 ข้างบน

**ผู้เทสหน้าจอเกม: ไม่ได้อะไรใหม่ และรอบนี้จะไม่แกล้งบอกว่าได้** บรรทัดนี้อยู่บน stderr ของเครื่องเซิร์ฟเวอร์
คนที่อ่านมันได้คือคนที่อยู่บนเครื่องนั้นและมี shell อยู่แล้ว ตาม `COO-DECISION 20260829_1344` ข้อ (ก)

## Round `6vhfgh` -- a SANCTIONED destination is not an ADMITTED one

`notes_to_chief/20260829_1603_CHIEF-DECISION-var2-test-path-scene126-registry-row-plus-gm-warp.md`
is addressed to lane A and to this lane. Item 1 asks lane A for a scene-126 registry row pinned
`login_entry_allowed: false`; item 2 asks this lane to "add 126 to the set `/warp` accepts".

**Measured on main this round, the two halves as written cannot both be true.** Not quoted from a
doc -- read off the files, and the greps are in the letter:

| fact | where |
|---|---|
| cross-scene `/warp` puts nothing on the wire; it stages the NEXT LOGIN scene | `gm/login_scene_stage.py` |
| `runtime.py` resolves that through `resolve_entry` with `via_login` DEFAULTED at both call sites | `runtime.py:5635` (silenced probe), `runtime.py:5706` (the call that places the character) |
| `via_login` true + `login_entry_allowed: false` = refused | `world_scene_entry.py:390`, `REFUSED_NOT_ALLOWED_AT_LOGIN` |
| the one lawful shape for a sanctioned non-login caller already exists | `columbus_quest_dispatch.py:464`, `via_login=False` |

So an admitted 126 writes a config entry the very next login throws away: one relog spent, nothing
reached, and the only explanation on the server host's stderr where the tester at the client cannot
read it. That is the same dead end `REASON_NO_LOGIN_ENTRY` was created to prevent, re-created one
layer up. **This lane does not own the login path's guard and will not route around it**, so the
predicate was NOT widened. `stageable_scene_ids()` is still `(1, 2, 278, 997)`.

### What shipped instead

| module | what changed |
|---|---|
| `gm/login_scene_admission.py` | `SANCTIONED_BARRED_SCENES` (a `MappingProxyType`, today one entry: `126 -> "CHIEF-DECISION 20260829_1603 item 2"`), `is_sanctioned_barred_scene`, `sanctioned_barred_provenance`, and `sanctioned_barred_blocker`, which measures WHICH half of the route is missing against lane A's registry on every call |
| `gm/login_scene_stage.py` | `REASON_SANCTIONED_NOT_YET_REACHABLE` (`scene_sanctioned_but_route_incomplete`), split out of `REASON_NO_LOGIN_ENTRY` and classified destination-shaped |
| `gm/chat_command_action.py` | the way-out line gains `blocker=` and `sanction=` for that reason only |
| `tests/test_gm_login_scene_sanctioned_barred.py` | new; the first class exists to prove the sanction grants NOTHING, and the last two pin the ORDER and the console line (a count is not written here on purpose -- pf-adversary D6 caught the first version's hardcoded one going stale inside the same round) |

**The blocker changes its own answer without an edit here.** Today
`sanctioned_barred_blocker(126)` returns `lane_a_registry_row_missing`, because
`scenarios/world_scene_registry_001.json` on main carries no `n_id` 126 (parsed this round: 1, 2,
3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 17, 130, 278, 997). The hour lane A's row lands it returns
`login_path_bars_it_needs_core_request_gm_038` instead -- a different remedy, named as one. Two
refusals that used to be one word.

### Why the split is worth a reason of its own

`scene_has_no_login_entry` answers "no". It does not answer "is this a merge I am waiting for, or a
request somebody has to chase" -- and those were indistinguishable for scene 126. Same refusal on
disk (nothing is written either way, pinned by
`TheStagePathSaysWhichRefusalItIsTests.test_the_refusal_writes_nothing_at_all`), different sentence
to a person.

### What is NOT claimed

The sanction map is not a grant, and the load-bearing test says so at the widest point:
`test_it_still_refuses_after_lane_a_lands_the_barred_row` builds lane A's registry WITH the 126 row
present and barred, and asserts the predicate, the stageable set, and `resolve_entry` itself all
still refuse. `TheSanctionIsAskedOnlyAfterThePinRefusesTests` pins the ORDER -- a sanctioned scene
the registry ADMITS still stages normally, so the map can never quietly become a deny-list.
`test_the_map_refuses_an_item_assignment` is a typo guard and is labelled as one: the
`MappingProxyType` stops an accidental item assignment from an importing module and nothing else,
it does not stop a rebind of the attribute, and there is no client-reachable path to either
(pf-adversary D8 refuted the first version's "closes the runtime-edit door" claim, and it is struck
rather than deleted: ~~`test_the_map_cannot_be_edited_through_the_module_attribute` closes the
runtime-edit door~~). Nobody has seen scene 126 on a screen; no claim here is client-observable.

### Two gaps this round did NOT close, named rather than left to be found

**The stale-boot-snapshot case is still one word (pf-adversary D7).** `stage_login_scene` asks the
disk first and the caller's snapshot second, and only the DISK branch can return the new reason. A
registry widened after boot (lane A merges, the process is not restarted) therefore refuses with
plain `scene_has_no_login_entry` and prints no `blocker=` -- in exactly the case where the two
readings disagree, which is the case the `scene_registry` parameter exists for. The remedy there is
"restart the process", which is not one of the five `BLOCKER_*` values, and a sixth that a
single-reading function cannot measure would be worse than the hole. It needs a function that
compares the two readings; this is not that function. Recorded in `CORE-REQUEST-GM-038`.

**If lane A lands the 126 row WITHOUT the key, 126 becomes stageable with no edit in this lane.**
`world_scene_travel.DEFAULT_LOGIN_ENTRY_ALLOWED` is `True`, so an absent `login_entry_allowed` reads
as allowed. That is lane A's call to make and this lane does not get a vote -- but it does get a
tripwire: `test_every_sanctioned_scene_is_one_the_predicate_refuses_today` goes RED on that merge,
because a sanction for an already-admissible scene is dead weight that reads like a grant. Read the
red as "delete the entry", not as "the merge is wrong".

**CORE-REQUEST-GM-038** (`notes_to_chief/20260829_1925_LANE-GM-CORE-REQUEST-GM-038-gm-warp-via-login-false.md`)
asks chief for the one runtime change that would make item 2 real, with three conditions that must
not leak -- the standalone map must never get the bypass (it grants a login scene to an account with
no `gm_accounts.json` membership), a character's own persisted row naming 126 must still be refused,
and no other scene may move. It also offers option B (lane A pins `login_entry_allowed: true`) and
says why this lane does not recommend it.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `6vhfgh`)

**คนเฝ้าคอนโซล** พิมพ์ `/warp 126` แล้วรู้ว่า **ครึ่งไหนของเส้นทางยังไม่มี** -- แถวทะเบียนของสาย A
ยังไม่ลง หรือ runtime ยังไม่ต่อสาย -- แทนที่จะเห็น `scene_has_no_login_entry` ก้อนเดียวเหมือนฉากที่
ไม่มีใครสั่งอะไรไว้เลย และรู้ว่าใบไหนเป็นคนปลดล็อก (`CORE-REQUEST-GM-038`) โดยไม่ต้องเปิดไฟล์จดหมาย

🔴 **ผู้เทสหน้าจอเกม: ไม่ได้อะไรใหม่ และรอบนี้จะไม่แกล้งบอกว่าได้** ยังไปฉาก 126 ไม่ได้ และรอบนี้
**เลือกที่จะไม่ให้ไป** แทนที่จะให้ `/warp 126` ตอบว่าสำเร็จแล้วเผารอบรีล็อกของเขาทิ้ง
บรรทัด `blocker=` อยู่บน stderr ของเครื่องเซิร์ฟเวอร์ ตาม `COO-DECISION 20260829_1344` ข้อ (ก)

## Round `npo898` -- "loud" had a consumer nobody had named, and it was a dead port

Consumes chief's reply of 2026-08-29T19:24+07:00 to `CORE-REQUEST-GM-037`
(`notes_to_chief/20260829_1924_CHIEF-REPLY-GM-037-wired-merged-plus-two-findings-back.md`),
both items.

### Item 1 -- where this lane's own "loud" was landing

The letter that asked chief to print `cause` also forbade a `getattr` default: a
`ConsumeResult` that lost the field must **raise**, not print a placeholder word.
Chief wired it exactly that way. pf-adversary then measured the other end of the
raise, and chief handed the measurement back for this lane to decide on:

| measured | where |
|---|---|
| the read is inside `except (ValueError, OSError, TypeError)` | `runtime.py`, the `CONSUME_FAILED` arm |
| a bare `AttributeError` is in neither that net nor the print guard | same block |
| an escape unwinds the **game listener thread**, and only that thread | `current/pf_login_game_server_v141.py`, `game_listener` — **re-measured in this round, not taken on trust**, and stated structurally rather than by line number (D9: this lane's own rule against pinning lines in a file it does not own): the only `except Exception` in the frame loop wraps decompress/parse, the `state.dispatch(parsed)` call is inside no `except` but the socket ones, the accept loop catches `socket.timeout` alone, and `game_listener` is started as a **daemon** thread while the login accept loop runs on the **main** thread. The last of those is what decides that the process survives its own dead port; the first version of this row cited the weakest of the three facts |
| the process keeps the **login** port | so a supervisor sees a healthy process and does not restart |
| the escape is **not** silent | Python's default `threading.excepthook` prints a full traceback -- file, line, field name -- to **stderr**. There is no excepthook override anywhere in this tree (`git grep excepthook`) |

So the failure mode this lane had asked for was: client connects, never enters,
supervisor says fine, and one traceback scrolls past on stderr while the port
stays dead forever.

🔴 **This paragraph said "console says nothing" and "the quietest failure the lane
can produce" until pf-adversary (D5, this round) measured the excepthook and
refuted it.** Struck rather than rewritten quietly, because the exaggeration was
load-bearing in the argument: the old failure was **louder in content** than what
replaces it. The defect is the **dead port** and a supervisor blind to it. That is
enough of a reason on its own -- a fix does not need a worse "before" than the one
that was actually there.

**The answer this round ships, and it needed no change in chief's file.**
`ConsumeResultMisuse` inherits **both** `AttributeError` and `TypeError`:

- `TypeError` puts it inside the net `runtime.py` **already** has, so the fault
  costs the **override** and never the thread. The events row then names it:
  `gm_login_scene_override_lookup_failed_ConsumeResultMisuse`.
- `AttributeError` keeps every `hasattr` / `getattr(x, n, default)` behaving as
  before -- `copy.deepcopy` probes `__deepcopy__` **on the instance** and relies
  on that swallow, which is the D8-R regression re-opened if the base is dropped.
- `__getattr__` covers the field that is not there (an unset slot -- `__new__`, or
  a subclass filling some of its slots), which `__setattr__` never could. Slot
  names are collected along the **MRO**: reading them off `ConsumeResult` alone
  (the first version) meant a subclass losing its own slot printed nothing at all
  (D12).
- **And it prints** -- because with the raise now *caught*, the console would
  otherwise get nothing:
  `GM_CONSUME_RESULT_LOST_FIELD field=<name> read=refused`, guarded,
  `flush=True` (D11: it replaces a stderr traceback, and stdout is block-buffered
  under a supervisor that pipes it), field names only (source literals), and
  **only** for a slot name so an ordinary `deepcopy` does not print a lane token.
  It says `read=refused` and **not** `effect=override_refused_login_at_own_row`
  (D4): the object cannot know what its caller will do, and the first version
  printed that effect word-for-word for a `hasattr` probe that refused nothing.
- `__repr__` renders a lost field as `<lost>` instead of raising (D10). A repr is
  most likely to be written *inside* an `except` handler, where a second raise is
  caught by nothing and takes the listener thread after all.

What did **not** change, because it is the contract, not the blast radius: the
attribute read stays outside the print guard, there is no `getattr` default at
the call site, and no placeholder `cause=` is ever printed for a lost field.

Who consumes it, finally answered: **the console line above, on a default boot,
plus a red suite for CI -- and the game port stays up.**

🔴 **Two claims this section made and pf-adversary refuted, corrected in place:**

- ~~"an events row for the operator"~~ / ~~"ที่ grep ได้"~~ — the events row
  `gm_login_scene_override_lookup_failed_ConsumeResultMisuse` is real, but on a
  **default boot there is nothing to grep** (D6): `app.py` builds an event
  exporter only under `--export-events`, and without it the row stays an
  in-memory list. The wiring test asserts `state.events`, which is a
  **test-process list** -- one layer, not the console/disk layer. The operator's
  default artifact is the console line, and only that.
- **What this does NOT close (D7):** the round changed **one class's bases**, not
  chief's net. Any other `AttributeError` raised inside that same `try` -- from
  `is_gm_account`, from the override loader, from a line written tomorrow --
  still unwinds the game listener exactly as before, and
  `test_a_result_that_lost_its_cause_raises_out_of_dispatch` still pins that
  escape for a foreign object. Closing it needs `AttributeError` in the net
  itself, which is chief's file: **`CORE-REQUEST-GM-039`**. pf-adversary tried 12
  malformed config shapes across the three files and could not reach the escape
  from config today -- it is a code-change risk, not a live one.
- ~~"Closing it needs ... which is chief's file"~~ — **CLOSED, round `znb56z`.**
  Chief wired it (`CHIEF-REPLY` 2026-08-29T23:20+07:00, letter
  `notes_to_chief/20260829_2320_CHIEF-REPLY-LANE-GM-039-wired-main-option.md`,
  landed as `pirate-force-server` #287): the login consume block's net is now
  `except (ValueError, OSError, TypeError, AttributeError)`, one point, no other
  net in the file touched. Chief took the **main** option and refused (a), (b)
  and (c). This lane's own test was **inverted** rather than deleted --
  `..._lands_in_the_net_by_name` now requires `dispatch` to return normally, an
  events row `gm_login_scene_override_lookup_failed_AttributeError`, the
  character on its own row, and **no `CONSUME_FAILED` line at all** (the
  "never print a word in place of the cause" promise is unchanged: the attribute
  read is still outside the print's guard and there is still no `getattr`
  default). Mutant measured by chief: removing `AttributeError` from the tuple
  turns that test RED rather than silently green. The price -- a wider net can
  swallow a real bug -- is accepted and is written into the comment at that
  point in `runtime.py`, together with this lane's `casue` measurement (a
  one-character typo goes red in 11 tests across 5 files), so a reader next year
  can see it was weighed rather than shrugged at.

### Item 2 -- the heading said seven, the table has eight

Corrected by striking the number rather than updating it (see the note under that
heading). A count in prose goes false in the round that adds a branch -- D6 from
round `6vhfgh`. The same stale seven in `login_scene_consume.py`'s constructor
comment ("at seven call sites") is struck the same way; the two "seven"s that
describe the discarded FIRST draft are accurate and stay.

🔴 **The first pass at this fixed the heading and left the thing that GENERATED
it** (pf-adversary D8): `gm/login_scene_consume.py` still carried the **seven-row**
"the split that ships" table, naming two tokens that no longer exist
(`config_unreadable`, `registry_refused_entry`) one screen above the constants
that refute them, and omitting `registry_stale_since_boot`. That table -- not the
heading -- is where chief's count came from. Corrected in the source, struck not
deleted. Same for a stale "returned from four sites" line in
`tests/test_gm_login_scene_consume_cause.py`, whose live count is an assertion
that AST-parses the source on every run rather than a number in prose.

### What pf-adversary broke, and what changed because of it

The first version of this round was **not approvable**. Three mutants survived the
**whole** suite (4951 passed, 0 failed), which is the shape of defect this lane
keeps paying for:

| # | what survived, measured | what this round did |
|---|---|---|
| D1 | four characters -- `else: return None` in `__getattr__` -- turned the hook into **the silent default the whole round forbids**, for any name outside `__slots__`. Every test lost only `cause`, which is inside the guard | `test_a_name_outside_the_slots_still_raises`: a plausible typo (`consume_cause`) must raise and print nothing. **Kill measured** |
| D2 | three mutants hardcoding `field=cause` (in the line, in the message, and by narrowing the guard to `name == "cause"`). `runtime.py` reads `scene_id` and `outcome` **before** `cause`, so those are the fields a real regression loses first -- the operator would grep `cause` while `cause` was intact | every test now runs over all three slots; the line and the message must name the field actually lost. **Kills measured** |
| D3 | appending `scene_id={...}` to the printed line stayed green: the fixture's `scene_id` was `None`, so the leak printed `scene_id=None`. The test named round `9wy444` D1 in its own comment and could not enforce it | fixtures carry a loud scene id (`90210`) and a real outcome; the line must contain neither. **Kill measured** |
| D4 | the token fired on a `hasattr` probe that refused nothing, saying `effect=override_refused_login_at_own_row` -- and this round's own suite printed it **6x per run** | the line says `read=refused` and claims no effect; every test captures stdout instead of leaking to it |
| D5 | "console says nothing" was **false** -- the daemon thread's traceback reaches stderr through Python's default excepthook | struck in three places (this section, the class docstring, the test module docstring), with the honest reason kept |
| D6 | "an events row the operator can grep" -- `app.py` exports events only under `--export-events` | corrected above; the console line is the default artifact |
| D7 | the hole is **narrowed to one class**, not closed | named above; `CORE-REQUEST-GM-039` opened for the net itself — ~~open~~ **closed round `znb56z`**, chief wired the net (#287); see the struck bullet above |
| D8 | the heading was struck and the **seven-row table that generated it** was left in the source | corrected in `gm/login_scene_consume.py`, struck not deleted |
| D9 | `:7440` pinned in a file this lane does not own, against its own rule, and the weakest of the three facts | restated structurally |
| D10 | `repr()` of a lost result **raised** -- and a repr is most likely written inside an `except` handler | `__repr__` renders `<lost>` via `object.__getattribute__`; a sibling read inside `__getattr__` would recurse forever, and the source now says so |
| D11 | the line went to unflushed stdout, replacing a stderr traceback | `flush=True` |
| D12 | a **subclass** losing its own slot -- the shape the hook's docstring names -- printed nothing | slots collected along the MRO. **Kill measured** |

What pf-adversary attacked and **could not** break: the premise of claim 1 (re-derived
from `runtime.py` and `v141` source), the ordinary copy/pickle path, the leak half of
the print (newline forgery through `__getattr__` is rejected by the slot guard before
the f-string, and no client-controlled path to `getattr` on this object exists), the
print guard, the three kills this round announced, and the hand-copied
`THE_RUNTIME_NET` -- narrowing chief's net, widening it to `except Exception`, and
swapping the bases underneath it each turned the wiring test red.

### What is NOT claimed

Nothing here is client-observable. No byte of any of this reaches a client and no
test says otherwise; the drills are in-repo regressions -- at HEAD a real
`ConsumeResult` cannot exist without a cause. This round did not touch the GM
account gate, did not widen any scene set, and gave GM status to nobody.
**It did not make the game listener safe from `AttributeError` in general** -- only
this class's raises moved inside chief's existing net (D7).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `npo898`)

**คนเฝ้าคอนโซล/ผู้ดูแลเซิร์ฟเวอร์:** ถ้าวันหนึ่งมีรีเกรสชันที่ทำให้ผลลัพธ์ของ consume เสียฟิลด์ไป
เมื่อวาน = พอร์ตเกมตายถาวรเงียบ ๆ ใต้โปรเซสที่ดูมีชีวิต (login ยังรับอยู่) ต้องเดาเอาเองว่าทำไม
ลูกค้าเข้าเกมไม่ได้ · วันนี้ = ล็อกอินนั้นเสียแค่ปลายทาง GM ที่วางไว้ ตัวละครยืนที่แถวของตัวเอง
**เซิร์ฟเวอร์ยังรับคนอื่นต่อ** และบนคอนโซลมีบรรทัดชื่อจริง
`GM_CONSUME_RESULT_LOST_FIELD field=<ฟิลด์ที่หาย> read=refused`
🔴 แก้คำอ้างเดิม (pf-adversary D5/D6): เมื่อวาน**ไม่ได้เงียบ** — มี traceback ลง stderr ก่อนพอร์ตตาย
สิ่งที่ได้เพิ่มจริงคือ **พอร์ตไม่ตาย** ไม่ใช่ "มีข้อความที่เมื่อวานไม่มี"
· และแถวเหตุการณ์ `gm_login_scene_override_lookup_failed_ConsumeResultMisuse`
**grep ไม่ได้บนบูตปกติ** (ต้อง `--export-events`) ⇒ ของที่ operator มีจริงคือบรรทัดคอนโซลบรรทัดเดียว

🔴 **ผู้เทสหน้าจอเกม: ไม่ได้อะไรใหม่รอบนี้** และรอบนี้จะไม่แกล้งบอกว่าได้

## Round `tvbiqc` -- an ACCEPTED command that sent nothing now says so

### The hole, measured through the real dispatcher before anything was written

| typed | events | what the CONSOLE said |
|---|---|---|
| `/warp 2 100 200` | `..._warp_withheld_no_confirmed_force_pos_vital_version_re129_open` | `LANE_GM_CHAT_ACTION warp route=action` and nothing else |
| `/say hello` | `..._say_withheld_...` | `LANE_GM_CHAT_ACTION say route=action` and nothing else |
| `/lv 10` `/item 1001 5` `/npc on 5` `/spawn 7` | `..._no_wire_path_<name>` | `LANE_GM_CHAT_ACTION <name> route=action` and nothing else |
| `/warp 9999` | `..._stage_refused_unknown_scene` | the admissible scene list (round `c48x1n`) |
| `/warp island` | `..._refused_command_parse_error_...` | the usage line (round `9wy444`) |

`route=action` is printed BEFORE any handler runs; it has always meant "this
route was reached" and nothing more.  So the six commands that put no byte on
the wire ended with a line that reads like success, while the two REFUSED
ones were fully explained.  A refused command was better served than an
accepted one -- and the worst-served of the six is `/warp <current scene> x
y`, the only command that can move a character on screen and the subject of
`GT-128`.

WHO PAYS: an attended tester types the warp, nothing moves, and the console
cannot separate "the version gate withheld the frame" (wiring fine, RE open)
from "the client ignored a frame we did send" (wiring fine, client's answer)
from "the route is dead" (wiring broken).  Two of those three are PASS-shaped
for the wiring and one is not, and the entry is graded from that console.

### What shipped

| file | change |
|---|---|
| `gm/chat_command_action.py` | fourth console token `GM_CHAT_NO_BYTES_SENT` for an accepted command that sent nothing and had no line of its own: the command name, the `outcome` word the ndjson row ACTUALLY carries, and `blocked_on='<what would unblock it>'` from the fixed `NO_BYTES_BLOCKERS` table.  Fifth token `GM_CHAT_STAGED_NEXT_LOGIN` for the cross-scene `/warp`, naming the staged scene, whether the typed coordinates were dropped, and the relog it needs.  `_Verdict` gained `line_printed`, `_print_warp_way_out` now reports whether its line actually reached the stream, and every console decision is made at ONE point, after the audit write |
| `tests/test_gm_chat_no_bytes_line.py` | new: the six silent commands each get exactly one line and the right blocker; the line never prints what was typed; no second line for `/warp 9999`, `/warp 126` or `/warp island`; a STAGED cross-scene warp stays silent; the audit-failure drop says so; a `None` or exploding stderr is named and costs no command |

No `runtime.py` change and no CORE-REQUEST: the whole fix is inside this
lane's own module, and chief's call site is untouched.

### Why a fourth token instead of reusing one

`LANE_GM_CHAT_ACTION` = the route was reached.  `GM_CHAT_WARP_REFUSED` = the
scene you named is not one login can enter (+ the list).
`GM_CHAT_COMMAND_REFUSED` = that is not a command this lane can read (+ the
usage).  `GM_CHAT_NO_BYTES_SENT` = we read you, we accepted it, and we
deliberately sent nothing (+ the blocker).  `GM_CHAT_STAGED_NEXT_LOGIN` = we
read you, we wrote your next-login scene, and here is what you do now
(+ whether your coordinates were dropped).  An operator greps one question at
a time.

### What these lines never carry, and why that is the property to guard

`session.token` on the wired server is the process-wide `--token`, not a
per-connection login, so a line that echoed what was typed would put any
player's sentence on the operator's console under the owner's own GM account
-- against this lane's founding rule.  Both fields are lane-authored: the
command NAME renders only if it is in `commands.COMMAND_NAMES` (`unnamed`
otherwise, which also stops a hand-built `GmCommand` from forging a second
line carrying another route's grep token), and the blocker sentence comes
from a fixed table, never from the command's arguments.  The staged line carries ONE field derived from what was typed -- the scene id, as an `int`, re-derived by the same helper the handler used and rendered `unknown` if it cannot be read.  That is the rung `GM_CHAT_WARP_REFUSED` has printed a typed `scene_id` on since round `c48x1n`, not a new one.

### Evidence

* green(local pytest, whole suite): 5147 passed, 327 skipped, 8941 subtests
  (~106s, `__pycache__` cleared first).  The pass/skip split is
  environment-dependent (5147+327 = 5474 collected either way).
* seventeen mutants measured killed, each run clean.  The first seven:
  dropping the `line_printed`
  hand-back (2 red -- doubled lines); the way-out printer returning `True`
  unconditionally (1 red -- a refusal it declines goes silent again);
  hardcoding one blocker sentence (2 red); rendering the command name
  unchecked (1 red); letting the staged outcomes into the gate (2 red -- a
  `/warp 278` that wrote a config entry called "sent nothing"); dropping
  `_one_line` from the account field (1 red -- newline forgery); removing the
  backstop call (11 red).
  Then the ten pf-adversary found surviving, re-run against the fixed
  version and now red: deleting the hint cap; dropping `console_safe` from
  the new line; `_print_warp_way_out` returning `True` from either failure
  return; deleting the new printer's own `no_stderr` note; announcing before
  the audit write; restricting the audit-drop line to the warp label; plus
  two regression mutants for the fixes themselves -- a silent staged warp
  (D3) and reading `why` off the verdict instead of the audit result (D1).

### What is NOT claimed

No byte reached a client because of this round, and no command that could not
be sent yesterday can be sent today.  The line goes to the SERVER HOST'S
stderr -- the operator rung `COO-DECISION 20260829_1344` path (a) named, not
a reply to the tester at the client, which is still blocked behind the same
identity and version locks as `/say`.  Nobody was given GM status, no scene
set changed, and no milestone is claimed from anything a GM shortcut reached.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `tvbiqc`)

**คนเฝ้าคอนโซล (รวมผู้เทสที่นั่งข้างเครื่องเซิร์ฟเวอร์ตอนรัน `GT-127`/`GT-128`/`GT-133`/`GT-141`):**
เมื่อวาน พิมพ์ `/warp 2 100 200` แล้วตัวไม่ขยับ คอนโซลพูดคำสุดท้ายว่า `warp route=action`
ซึ่งอ่านเหมือน "ส่งแล้ว" ⇒ ต้องเดาเองระหว่างเกตปิด / ไคลเอนต์ไม่สน / สายตาย
วันนี้ บรรทัดถัดมาบอกว่า **ไม่มีไบต์ออกไปเลย** พร้อมชื่อเกตและสิ่งที่จะปลดมัน
· และ `/warp <ฉากอื่น>` ซึ่งเมื่อวานเงียบเหมือนกันทั้งที่ **เขียนไฟล์จริง** วันนี้บอกว่าสตางค์ฉากไหนไว้
ต้องล็อกเอาต์-ล็อกอินใหม่ และ **พิกัดที่พิมพ์มาถูกทิ้ง** (ข้อสุดท้ายเมื่อวานไม่มีที่ไหนบอกเลย
นอกจากคำใน ndjson)
🔴 **ผู้เทสหน้าจอเกม: ไม่ได้อะไรใหม่รอบนี้** และรอบนี้จะไม่แกล้งบอกว่าได้

### What pf-adversary broke in this round's first version, and what changed

Twelve defects, ten surviving mutants, on a version whose own test file was
green.  The three that reshaped the round:

| # | what was measured | what the shipped version does |
|---|---|---|
| D1 | on an unwritable capture directory the line said `why=withheld_force_pos_vital_version` while the ndjson carried NO outcome row -- the console naming a word the operator cannot find, on the one boot where they are grepping both.  The line was printed BEFORE the audit write and keyed on the verdict | one announce point, AFTER the write: `why` is `verdict.audit_outcome` when the row landed and `audit_row_not_written` when it did not.  **Kill measured** |
| D2 | the branch that DID say `audit_row_not_written` sat behind `action is not None`, which cannot happen while both version gates are shut -- the reachable case printed the wrong word and the right word lived in unreachable code | the same single point covers both shapes; the audit-drop case no longer needs a composed frame to be heard |
| D3 | the staged cross-scene `/warp` -- the only `/warp` form that changes anything today -- printed NOTHING, so the hole this round claims to close stayed open for it, and `/warp 278 100 200` silently dropped the typed coordinates | `GM_CHAT_STAGED_NEXT_LOGIN`, with the scene, the coordinates verdict, and the relog.  A stage whose audit failed says `audit_row_not_written` instead, because the entry came back off disk.  **Kills measured** |

And the rest, each with the mutant that now fails: `no blocker recorded` on
five NAMED stage faults with knowable remedies, one of them a chmod (D4 --
the table now carries them and the contract test derives the list from
`login_scene_stage` instead of hand-copying it); `console_safe` droppable
from the new line with the whole suite green, which is round `qq0i9u`'s
incident shape (D5); a placement comment claiming a load-bearing reason for
what was then a no-op (D6); a docstring contradicted by its own second call
site in the same commit (D7); `_print_warp_way_out`'s new `bool` contract
unpinned in both failure returns (D8); a `None`-stderr test that passed
because an OLDER printer had already appended the same event for the same
session (D9); a client-driven console line whose volume doubled without
being named (D10 -- stated at the token, bounded by the rate limit); a
citation to a round file that does not exist and a "seven fixed sentences"
comment one commit after the second supplier arrived (D11); and an
audit-drop line restrictable to the warp label with everything still green
(D12).

What pf-adversary attacked and could NOT break: any path putting
client-typed bytes on the operator console (all four fields traced to closed
sets or the operator's own `--token`), any line forgery, any way for the new
line to alter dispatch (raise, withhold an outgoing action, write to stdout),
and any double line -- including the case it expected to find one,
`/warp 126`.

## Round `znb56z` -- the map that is SPENT may name a sanctioned scene; the other never may

`CORE-REQUEST-GM-038` landed both halves this round. Chief's half reached main
as `pirate-force-server` #281: `runtime.py` resolves a login with
`via_login=False` when, and only when, `override_consumed_scene is not None`
(the CONSUMED outcome) **and** `login_scene_admission.is_sanctioned_barred_scene`
answers for the destination. This lane's half is the admission that lets such an
entry reach that path at all -- until this round the reader refused it two
statements earlier and chief's bypass could not be reached from any real config
file.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `znb56z`)

**วันนี้ยังทำอะไรไม่ได้เพิ่ม และนั่นคือคำตอบที่วัดได้ ไม่ใช่คำแก้ตัว.** ตัวเลขที่วัดบน
main รอบนี้: `sanctioned_barred_blocker(126)` = `lane_a_registry_row_missing` --
แถวทะเบียนของสาย A (ครึ่งที่ 1 ของ `CHIEF-DECISION 20260829_1603`) ยังไม่ลง main
ดังนั้น `/warp 126` ยังปฏิเสธเหมือนเดิม

สิ่งที่เปลี่ยนจริงและผู้เทสเห็นได้: **คำที่พิมพ์ข้างการปฏิเสธเปลี่ยนเจ้าของ** จาก
"chief ยังไม่ต่อ `via_login=False`"
(`login_path_bars_it_needs_core_request_gm_038`) เป็น "สาย A ยังไม่ลงแถว"
(`lane_a_registry_row_missing`) -- คนละใบที่ต้องไปตาม คนละคนที่ต้องรอ และ
`sanctioned_barred_blocker` ถามทะเบียนสดทุกครั้ง จึงเปลี่ยนคำเองในวินาทีที่สาย A
merge โดยไม่ต้องแก้อะไรในเขตนี้

และในวินาทีนั้น -- **โดยไม่มี PR ของสายนี้คั่นอีกใบ** -- `/warp 126` จะผ่าน, entry
จะถูกเขียน, login ถัดไปจะถูกวางด้วย `via_login=False`, และใบคืน (put-back) จะรับ
entry เดิมกลับแทนที่จะทำลายทิ้ง ทั้งสี่ข้อพินไว้ใน
`tests/test_gm_login_scene_sanctioned_admission.py` ด้วยทะเบียนตัวแทน

**NONCLAIM:** ทุกเส้นทางข้างบนคือทางลัด GM ผู้เทสที่ไปถึงฉาก 126 ด้วยวิธีนี้
**ข้ามการเดินทางในเกมทั้งหมด** -- เห็นเกาะ ไม่ใช่ M2 ผ่าน และไม่ใช่หลักฐานว่า
เส้นทาง Columbus -> ทะเล -> เกาะ ทำงาน

### The rule, and why it is scoped rather than global

One predicate, `single_use_entry_is_admissible`: the plain
`login_entry_is_pinned`, **or** a sanctioned scene whose only remaining blocker
is `BLOCKER_LOGIN_PATH_BARS_IT` -- the one blocker chief's bypass actually
removes. Every other blocker still refuses, and that is not caution for its own
sake: `REFUSED_NO_PINNED_SPAWN` is a different refusal from
`REFUSED_NOT_ALLOWED_AT_LOGIN` and `via_login=False` does not touch it, so
admitting a spawnless sanctioned row would write an entry the login path
refuses for a reason nothing in this lane has bypassed.

**The widening is bound to the map that is SPENT on use, and that is the whole
safety argument.** Chief's bypass is gated on the CONSUMED outcome, which only
the GM-gated map (`gm_login_scene`) produces. The standalone map is deliberately
never consumed (`COO-DECISION 20260829_0542`), so it yields
`STANDALONE_NOT_CONSUMED`, the bypass stays False, and `resolve_entry` is asked
with `via_login=True`. A sanctioned scene admitted **there** would be refused at
login and refused identically on every retry -- the permanent silent lockout
this admission module was built to close, rebuilt by the fix for it. So
`_load_scene_id_map` takes `single_use` as a **required** keyword with no
default: a default is how a third map would inherit the wrong rule in silence.

What this does NOT widen, said plainly because the words are close enough to
confuse: not `login_entry_is_pinned`, not `stageable_scene_ids`, no GM status
for anybody, and no client-named destination. `/warp` still runs behind
`accounts.is_gm_account`, and the standalone map still grants a scene and
nothing else. It widens **which scene ids one already-authorised operator may
write into one already-gated file.**

### D5 -- chief's restore question, answered by construction

Chief's letter (2026-08-29T22:22+07:00) asked, from pf-adversary's D5: once the
consume side is widened, `restore_login_scene` still judges by plain admission,
so a granted sanctioned entry the snapshot then refuses would be **destroyed**
(`gm_login_scene_override_lost_to_refusal_126`) instead of handed back --
consume and restore running on two different rules for the same entry.

**This lane's answer: the undo believes the rule the write believed, because
there is only one rule to believe.** The widening lives in the READER
(`_load_scene_id_map` for the single-use key). `stage_login_scene` writes
through `_write_entry`, which re-validates the whole file through that same
reader; `restore_login_scene` is `_write_entry` with `allow_delete`. So consume,
stage and undo cannot disagree without someone deleting the shared reader --
a different and much harder mistake than forgetting to widen a second call
site. It is the same shape as the rule already written at
`restore_login_scene`: **undo with the same reading you staged with**, now also
**under the same predicate you staged under**.

Walked end to end rather than argued:
`test_the_undo_puts_a_sanctioned_entry_back_rather_than_losing_it` stages the
sanctioned scene, claims it (what a login's consume does), and puts it back
(what `_put_back_consumed_override` does when the probe refuses). A `False` from
that put-back **is** the destroyed-entry event, so the assertion is the defect
itself rather than a proxy for it.

### Two seams moved, and one added, because the reader now shares a predicate

- `chat_command_action` prints `single_use_stageable_scene_ids`: `/warp` writes
  the single-use map, so a way out computed under the other map's rule would
  omit exactly the destinations this command can reach -- telling a refused
  operator that a scene they may stage is not on the menu.
- `LoginSceneRefusedError` carries `single_use`, set by the reader that refused.
  `login_scene_consume._refusal_cause` asks "would the DISK have taken this row"
  to tell *edit the config* from *restart the server*; asked with the narrow
  rule about a single-use refusal it answers no for a reason that has nothing to
  do with the disk, and sends the operator to grep a file that is correct.
  Defaulted `False`, which can only ever under-state a remedy.
- `disk_admits_under_rule` is new and has exactly one caller. **Measured, not
  stylistic:** a diagnostic that shares a mockable name with the config reader
  cannot be broken in a test without also breaking the reader -- and
  `test_the_remedy_probe_can_never_cost_the_login` did exactly that this round,
  a `RuntimeError` escaping `consume_login_scene_override` through
  `_load_scene_id_map`. That test was then pinning the reader's behaviour under
  a name that says "probe". The seam gives it back the thing it meant to
  explode.

### One test class here is designed to go RED on lane A's merge

`TheSanctionAdmitsNothingOnMainTodayTests` asserts the blocker is
`lane_a_registry_row_missing` **today**. The hour lane A lands the row it goes
red -- deliberately: at that moment the sentence "the widening admits nothing
today" is false in this document, in `login_scene_admission`'s header, and in
the round letter simultaneously, and somebody has to come and say so rather
than leave three documents lying. It is the same mechanism
`test_every_sanctioned_scene_is_one_the_predicate_refuses_today` already uses
for the retirement of a sanction.

### What pf-adversary broke this round, and what changed because of it

The first version of this round was **not approvable**. The *safety argument*
held -- twelve refutation attempts, listed below, all failed -- but **six
independent mutations of this round's own new code left the whole lane suite
green (957 passed)**, which is the shape of defect this lane keeps paying for:
a claim with no test that can fail it.

| # | what survived, measured | what this round did |
|---|---|---|
| M5 | dropping `is_known_scene_id` from `single_use_stageable_scene_ids` -- **the same mutation `_admissible_ids`' own scar note says once reached a pushed commit of this file**. The new function copied the filter and the citation and not the test; no fixture could tell, because 126 IS named | `TheWayOutMayNotNameAnUnnamedSceneTests` patches the sanction map to an id the catalog does not name. **Kill measured** |
| M6/M7 | `disk_admits_under_rule` ignoring `single_use` in either direction | the old test asked only ids on which both rules agree, so no input could distinguish them. Replaced with the case that separates them (disk holds lane A's row): single-use admits, plain refuses. **Kills measured** |
| M8 | `_refusal_cause` hardcoding `single_use=False` | `test_the_remedy_word_follows_the_rule_that_refused` walks the real consume with a disk ahead of the snapshot: `registry_stale_since_boot` (restart) vs `scene_not_admissible` (edit a correct file). **Kill measured** |
| M14 | the config reader's `way_out` always narrow -- the chat path's equivalent is caught twice, the reader's had nothing | `test_the_readers_way_out_follows_the_readers_rule` reads the real refusal line off stderr. **Kill measured** |
| M16 | the two arms of `single_use_entry_is_admissible` reordered | **no test added, on purpose.** The mutation is green because the *claim* was false, not because the property was untested -- see D4 |

And four claims or gaps that were not mutations:

- **D4 -- a docstring asserting a reason that does not exist.** "THE ORDER IS
  NOT COSMETIC ... asked first so that a non-`int` raises `TypeError`": measured
  with the arms swapped, all four bad values raise the identical `TypeError`
  anyway, because `is_sanctioned_barred_scene` type-guards and control falls
  through. Struck. What *is* load-bearing turned out to be somewhere else, and
  is now written where it lives: `sanctioned_barred_blocker` checks the pinned
  spawn **before** the login bar, and a reader who "makes that consistent" with
  `_target_is_admissible`'s opposite order would admit a spawnless destination.
- **D5 -- "both arms are asked with the same reading" is only half true.** With
  a caller-supplied registry, yes. With the default `None` each arm loads the
  registry itself: two reads for a sanctioned id, three for the way out where
  the function beside it costs one. Half struck, with the reason it is a cost
  and not a correctness hole written down rather than assumed.
- **D6 -- this file held both halves of a contradiction in two passing tests.**
  The way out (one reading) can name a scene `stage_login_scene` (two readings)
  then refuses. Real, and **not introduced by the widening** --
  `stageable_scene_ids` has the identical shape and always has. Now asserted
  deliberately in one place, with its bound (between a lane A merge and the next
  restart) and the reason the cheap fix is refused: the way out is built inside
  the refusal's own `raise`, where an added read that can throw would swap the
  refusal a caller must handle for a registry error it does not.
- **D7 -- a latent raise the plain predicate would not make.** Not reachable
  today (`spawn` is a frozen-dataclass field), reachable the day it becomes a
  property, and the obvious one-line fix is **wrong**: swapping the blocker's
  order reopens the spawnless admission above. Recorded as open rather than
  half-fixed.
- **D8 -- fixed at the cause, not pinned.** The first attempt added the
  import-time skip to `docs/PYTEST_SKIP_PINS.json` and the repository's own
  guard refused it: `test_every_pinned_count_is_a_positive_integer`. That file
  carries skips that *actually happen*, and this one does not happen today --
  which is the honest answer to why it should not be pinned at all. So the
  import-time `SkipTest` is gone: `the_only_sanctioned_scene()` returns `None`
  and every class carries `@requires_a_sanctioned_scene`. Measured with the
  sanction map emptied, in a worktree: this module is **25 skipped, 0 failed**,
  and `test_gm_tests_collect_without_posix` is **no longer among the red**. The
  14 that stay red are in files from earlier rounds and are the retirement
  doctrine working as designed.
- **D9** the stand-in row now carries the arrival point the chief decision names
  `(3050, 232, 90)` instead of home's, and says out loud which fields are still
  home's and why none of them is read.

**Process defect, recorded because it is the more dangerous one.** The first
mutation sweep was run **in the live checkout**, reverting with
`git checkout -- .` between mutations. pf-adversary caught one of those
mutations mid-flight in `git diff` -- specifically M2, the standalone map on the
wide rule, i.e. verbatim the permanent-lockout regression this whole ticket
exists to prevent, sitting uncommitted in the tree one `git commit -a` from
shipping. Nothing shipped (every mutation reverted; `git status` clean at the
commit), but the exposure was real and the fix is free: the second sweep ran in
`git worktree add --detach`, and that is the rule from here.

### What pf-adversary attacked and could NOT break

Walked against `runtime.py` itself rather than against this lane's summary of
it: any path putting a sanctioned scene into a login that resolves
`via_login=True` (the standalone map, the character's own persisted row, the
two-map race, `get_login_scene_override`'s ordering, probe/real-call
disagreement, restore writing into the wrong map); any non-GM reach; any
client-named destination; `_refusal_cause` altering dispatch; and
`lane_a_row_on_disk` hiding a real refusal. The two mutations that matter most
-- standalone map on the wide rule (M2) and the reader's rule defaulting wide
(M1) -- were **red from the first sweep**, which is the part of this report
worth keeping.

## Round `h4v9wq` -- verify-only, no code change, and a shared tooling gotcha

Mailbox checked clean (nothing addressed to `LANE-GM` without a `.CONSUMED.txt`
stub already sitting next to it) and `GAME_TEST_QUEUE.md`'s GM-tagged entries
(`GT-101`, `GT-103` closed; `GT-127`, `GT-128` HOLD/BLOCKED, both entirely on
chief's side) leave nothing in this lane's write zone that is not already
blocked on a wiring point this lane does not own. `CORE-REQUEST-GM-040`
(escalated round `q9i00s`, 2026-08-30T08:35+07:00) is still unanswered but only
45 minutes old at the time of this check -- re-escalating that soon with no new
evidence would be manufacturing a cycle, so this round did not.

The one finding worth recording here because it is not specific to GM:
`list_pull_requests` (the REST list endpoint) returned `merged: false` for four
pull requests independently confirmed merged by other means (`main`'s own
commit log, and `pull_request_read(method="get")`'s `merged`/`merged_at`/
`merged_by` fields) -- `pirate-force-server#294`, `#289`, `pf_bridge#468`,
`#460`. The round-lock recovery step in the house protocol ("did my last
closed `[LANE-X]` PR actually merge?") must be answered with
`pull_request_read(method="get")` per PR, never with the `merged` field off a
list call -- see
`notes_to_chief/20260830_0920_LANE-GM-STATUS-mailbox-clear-plus-list-api-merged-field-gotcha.md`
for the full measurement and the escalation of the wording fix (out of this
lane's write zone; `AGENTS.md`/the round-lock protocol text is chief/COO's to
edit).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `h4v9wq`)

ไม่มี -- รอบนี้ไม่มีการเปลี่ยนพฤติกรรมโค้ดใด ๆ เป็นรอบตรวจสอบล้วน

**NONCLAIM:** ไม่มีการเปิด client ไม่มีการวัดกับไคลเอนต์จริง ทั้งหมดวัดจาก GitHub API และ
grep/read ซอร์สที่ commit แล้วบนทั้งสอง repo

## Round `dm8o4l` -- `queued` becomes writable, and the door that let it stays shut

`CORE-REQUEST-GM-040` is CLOSED. Both halves are on `main`.

**Chief's half (landed first, `pirate-force-server#299`, merged
2026-08-30T10:47Z).** `runtime.py`'s append site --
`if gm_action is not None: actions = actions + [gm_action]` -- now reads
`session._gm_action_queued_confirm`, a `(action, callback)` pair matched by
`is`, clears the slot, and fires the callback. Chief's own letter called it
"inert scaffolding": nothing in the tree set the attribute.

**This lane's half (this round).** `make_gm_chat_command_action` arms that
pair with the exact tuple it is about to return, and the callback writes the
`queued` row that `OUTCOME_QUEUED` has had reserved since
`CORE-REQUEST-GM-032` item 3.

### The shape of the door, and why it is not a flag

`OUTCOME_QUEUED`'s own comment predicted the change would be "one line in
`is_known_outcome`". **It deliberately was not, and that line did not
change.** Flipping the predicate -- or adding a
`confirmed=True` keyword to `log_gm_command_outcome` -- would have made the
word reachable by any caller holding the string, which is precisely the hole
`QueuedIsReservedTests` exists for: pf-adversary once got `queued` into the
ndjson through `AUDIT_OUTCOMES[-1]`, a tuple index no source scan can see.

Instead the word got its own writer, `commands.log_gm_command_queued`, which
takes **no `outcome` parameter at all** and hard-codes the constant. A
function with no outcome parameter cannot be reached by a VALUE; only by a
NAME -- which a reader sees and a scan can find. Consequences:

- `log_gm_command_outcome` still raises for `queued` by every spelling.
- `is_known_outcome('queued')` is still `False`; `AUDIT_OUTCOMES` still
  excludes it.
- Because the writer hard-codes the word, `chat_command_action.py` never
  names it -- so `QueuedIsReservedTests`' AST scan is still green AND still
  means what it says, on the very round the word became writable.
- **No test that guarded the old door was deleted or weakened to land this.**

### The hole this round's own adversary pass found in this round's own work

Moving the door moved what the scan can see. The AST scan forbids a lane file
from NAMING `queued`; after this change a lane file no longer has to -- it
only has to name a function. Before this round no lane file could write the
word at all; without a new pin any of them could, and the old guard would
have stayed green. Closed by
`test_gm_queued_confirm_arming.py::TheOldDoorIsStillShutTests::
test_only_the_confirmation_path_may_even_NAME_the_new_writer`, plus its
own "the scanner really sees something" companion.

### Three rows now, not two -- and one stale grading criterion

An appended command writes `issued` -> `outcome:composed` -> `outcome:queued`,
three lines sharing one `record_id`. Append-only, never an amend: the third
line extends the sequence, it does not rewrite the second.

**A reader of the ndjson must take the LAST outcome row for a `record_id`,
not "the" outcome row.**

- `GT-128`'s criterion already survives this: round `nz0qt2` rewrote it to
  **count distinct `record_id`s**, which is still exactly one per command.
- `GT-141`'s criterion is unaffected: a cross-scene `/warp` stages a login
  scene and returns NO action, so nothing is appended and no `queued` row is
  written -- its "two rows, second one `staged_login_scene`" still holds.
- 🔴 **`GT-127`'s wire/DB criterion is stale and this lane cannot fix it**
  (`GAME_TEST_QUEUE.md` is chief's file, `AGENTS.md` §7). It reads "ndjson has
  one row per command (**not two**)" -- which was already stale from
  `CORE-REQUEST-GM-032` (issued + outcome = two) before this round made it
  three. Reported to chief in this round's letter. Note this is latent, not
  live: `GT-127` grades the same-scene ForcePos path, whose version gate is
  still `None` (RE-129 unanswered), so nothing composes there today anyway.

### Failure shapes, each with its own name

Four, because "the `composed` row has no `queued` beside it" has four very
different causes and one event name would let a reader pick the wrong one:

| event | what happened |
|---|---|
| `gm_chat_action_queued_confirm_not_armed_<ExcType>` | the session refused the attribute (slots, a proxy). The command still went out. |
| `gm_chat_action_queued_confirm_overwrote_pending` | a pairing from an earlier frame was still unfired. Should be unreachable by construction; named because it means some earlier command's `queued` row went missing for THIS reason and not because an append failed. |
| `gm_chat_action_queued_confirm_write_failed_<ExcType>` | the append really happened and the row would not write. |
| `gm_chat_action_queued_confirm_fired_twice` | the callback was invoked twice. Chief's hook clears before calling, so this cannot come from him. Refused, because two `queued` rows read like two appends. |

**Nothing is withheld on a write failure**, and that asymmetry with
`_log_outcome` is deliberate: by the time the callback runs the action is
already in `runtime.py`'s action list. There is nothing left to take back, so
the honest report is "it went out and we could not record that".

**Arming follows the ACTION, not the composer.** It happens last, only for an
action really being returned -- a withheld, refused or unaudited command arms
nothing. Pinned three ways, because arming on composition instead would leave
a pairing that can never fire and would make the next real command report an
anomaly.

### What `queued` claims, and what it does not

One rung above `composed` -- the action tuple really reached `runtime.py`'s
action list. `executed` stays `false`. It is **not** a claim that bytes
reached a socket, that a client parsed them, or that anything moved in the
world; nothing inside this process can observe any of those. The three words
are a ladder whose top rung this lane cannot reach.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `dm8o4l`)

อ่านไฟล์ ndjson แล้วแยกออกได้ว่า คำสั่งที่ "ประกอบเฟรมได้" กับคำสั่งที่ "เฟรมเข้าคิว
ของ runtime จริง" ต่างกันตรงไหน -- เดิมสองสถานะนี้เขียนแถวเหมือนกันเป๊ะ

**NONCLAIM:** ไม่มีการเปิด client ไม่มีการวัดกับไคลเอนต์จริง ทั้งหมดเป็น code path
ที่วัดผ่าน dispatcher จริงแบบ headless (`QueuedRowLandsEndToEndTests`) และเทสออฟไลน์
· ประตู ForcePos ยังปิดอยู่ (`FORCE_POS_VITAL_VERSION_CONFIRMED is None`, RE-129)
⇒ รอบนี้ไม่ได้ทำให้ไบต์ใด ๆ ออกสู่ไคลเอนต์เพิ่มขึ้นแม้แต่ไบต์เดียว

### `spawn` closed bounded-negative, `npc` opened as `CORE-REQUEST-GM-041` (round `5btl0q`)

chief (round `nnlka4`, `notes_to_chief 20260830_1804`) confirmed by an independent source-wide grep
that no function in `src/` or `gm/` creates a new mob actor and inserts it into a running world -- the
project's only `def spawn*` is a coordinate finder (`world_scene_travel.py:657`), not an actor factory.
`gm/commands.py`'s module docstring is updated to state this as settled (bounded-negative), not
"RE-open" -- a future round must not reopen a CORE-REQUEST asking for a mob-spawn factory call site,
because there is no factory to call. Making `spawn` real needs a new engine feature, out of scope for a
CORE-REQUEST.

`npc on|off <mob_id>` is a different shape of problem: it toggles an NPC that already exists in the
game's own tables (`gm/npc_switch_catalog.py`'s 7 `n_GM_SWITCH=1` rows), not a new actor. `runtime.py`
already runs a re-encode/admission cycle for existing mobs via `mob_scene_recompose.recompose_frames`
(`:4342,4640,4650`) and `mob_scene_recompose.census_anchor` (`:7230,7498,7715,7924`) --
`CORE-REQUEST-GM-041` (`notes_to_chief 20260830_1817`) asks chief for a call site that lets `gm/`
trigger that same cycle for a GM-switchable `mob_id`, mirroring how `CORE-REQUEST-011` bridges `warp`.
Not built yet -- `npc` still only parses and logs, same as every other GM-003 command, until the call
site lands and an end-to-end test proves it.

**NONCLAIM:** no client opened, no live measurement, no code path added this round beyond a docstring
edit -- `npc`/`item`/`lv`/`spawn`/`warp`/`say` all behave identically to before this round.

### `npc` gets a real diagnostic answer instead of a static assumption (round `nbihci`)

`CORE-REQUEST-GM-041`'s read point (`gm_npc_toggle_recompose.npc_toggle_would_recompose`,
chief's module, round `bunu7v`) is now called from `gm/chat_command_action.py`'s no-wire-path
branch for `npc` only -- one diagnostic event
(`gm_chat_action_npc_recompose_diagnostic_{not_switchable,would_recompose_true,
would_recompose_false,bad_args_shape,unexpected_<ExcType>}`), never a change to `verdict`.
Runs AFTER `verdict` is bound (pf-adversary this round measured the first draft calling it one
line too early, before the binding -- fixed, and the call site's own comment now says so
correctly). Shape guard uses `type(args) is not tuple`, matching `commands.py`'s own
`_require_args_tuple` -- an `isinstance` check was proposed first and pf-adversary reproduced a
`tuple` subclass lying through `__len__`/`__getitem__` defeating it; a live test
(`test_a_lying_tuple_subclass_is_rejected_not_trusted`) pins the fix.

Opened `CORE-REQUEST-GM-042` (state store + write point + roster filter) for the follow-up that
would flip the diagnostic's answer from a measured `false` to a real per-mob check -- chief's own
letter invited this as a separate request, not part of GM-041's scope.

**NONCLAIM:** `npc on|off` still has zero effect in the game, exactly as before this round -- the
diagnostic only lets a console grep tell "would recompose" from "would not" today, both of which
mean nothing changes yet.

## Round `dao2gd` -- item_catalog's one bare KeyError, and the blank scene rows that were never pinned

Consumed chief's reply of 2026-08-30T21:00+07:00 to `CORE-REQUEST-GM-042`
(`notes_to_chief/20260830_2100_CHIEF-REPLY-CORE-REQUEST-GM-042-store-plus-write-point-deferred-
filter-wiring-too-risky-partial-read.md`) -- GM-042 stays OPEN, chief built neither the state
store nor the roster filter this round, and reading that letter unlocked nothing new on this
lane's own file territory (`gm/`) to build against. No code changed from it; see this round's own
`notes_to_chief` letter for the acknowledgement.

With no unblocked wiring step ready (`spawn` bounded-negative since `nnlka4`, `npc`/`item`/`lv`
still waiting on a runtime.py call site none of which a CORE-REQUEST can shortcut this round), this
round read `gm/item_catalog.py`, `gm/scene_catalog.py` and their test files end to end for edge-case
gaps left by GM-004 (scene catalog) and the GM-042 prep item catalog -- neither module had touched
runtime.py or another lane's file, and neither has an open RE/CORE-REQUEST blocking it. Found two:

**1. `item_catalog.item_max_stack` leaked a bare, unnamed `KeyError`.** Every other lookup this
module exposes (`item_name`, `is_known_item`) raises a `KeyError`/`ValueError` naming the id and
category that failed to resolve. `item_max_stack(99999999, category="misc")` instead raised
`KeyError('99999999')` -- the dict's own repr, with no mention of the category it was checked
against. A caller catching `KeyError` by type cannot tell that apart from an unrelated bug (a wrong
dict, a typo'd key) without reading this function's source. Fixed by wrapping the one dict lookup
(`gm/item_catalog.py:170-186`) in the same try/except-and-rename pattern `item_name` already uses;
no behavior change for a known id, confirmed by a test that reads the plain int back
(`tests/test_gm_item_catalog.py::test_item_max_stack_known_id_unaffected_by_the_error_message_fix`).
A second test pins that the message names the category actually QUERIED, not one the id happens to
resolve in elsewhere (id `1` is known in `quest` but not `consumable` --
`test_item_max_stack_unknown_id_message_names_the_category_it_was_checked_against`). `item_max_stack`
has no production caller yet (grepped; only test files call it, matching the module's own GM-042
prep docstring), so this is a contract cleanup with zero live-path risk, not a wiring change.

**2. Four scene ids the client's own table leaves nameless were untested.** `gm_scene_name_tip.tsv`
rows 13/137/138/141 carry an empty string in BOTH `s_SCENE_NAME` and `s_GM_SCENE_NAME` -- not a
parsing gap this module introduced, a fact of the committed client table (verified against the raw
tsv, not guessed). `scene_catalog.is_known_scene_id(13)` is `True` and `gm_scene_name(13)` returns
`""`, which was previously unexercised by any test -- the existing suite only pinned a real name
(id 1/2/3) and a truly-absent id (123456), leaving the third state (id present, name blank) to be
discovered by whoever next read `gm_scene_name(13) == ""` and had to guess whether that was a bug.
Pinned in `tests/test_gm_scene_catalog.py::test_blank_rows_in_the_clients_own_table_are_known_but_
empty_named` and, one layer up, in `commands.describe_warp_target` via
`tests/test_gm_commands.py::DescribeWarpTargetTests::test_a_scene_id_the_client_itself_left_
nameless_is_still_known_not_none` -- `describe_warp_target(warp 13)` returns `""`, not `None`, and
a caller must not read that empty string as "unknown scene, refuse the warp": the warp itself is
judged by `login_scene_admission`/`world_scene_travel`, never by this hint. No source or docstring
changed for either module; both are documentation-by-test of behavior that already existed.

### pf-adversary

The dedicated `pf-adversary` subagent tool was not reachable from this delegated session (no
`Agent`/`Task`-shaped tool was present in this round's tool set -- checked via tool search before
concluding this, not assumed). Ran the equivalent adversarial pass by hand instead of skipping it:
grepped every production and test caller of `item_max_stack` to confirm zero live-path callers exist
(only `tests/test_gm_item_catalog.py`, matching the module's own "GM-042 prep, not wired yet"
docstring, so the message-text change cannot break a runtime consumer); re-derived the four blank
scene ids straight from the committed tsv rather than trusting a memory of them; ran the full `gm_`
test slice (1052 passed, 0 failed) both before describing this round's findings and after applying
the fix, to rule out an unrelated regression riding along. Recorded here rather than silently
substituted, per this lane's own file-territory rule that a gap in process gets named, not folded
into "reviewed" language it did not earn this round.

### What is NOT claimed

Neither finding is wired to any client-observable behavior and neither touches `runtime.py`,
`app.py`, `pf_login_game_server_v141.py`, or another lane's `scenarios/*.json`. `item_max_stack` and
`describe_warp_target` are read by tests only today (GM-042/GM-004 prep) -- this round changed one
error message and added coverage, nothing a tester watching a live game session can see change.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `dao2gd`)

ไม่มี -- รอบนี้ไม่มีอะไรใหม่ให้ผู้เทสหน้าจอเกมเห็น การเปลี่ยนแปลงทั้งหมดอยู่ในข้อความ error ของฟังก์ชัน
เตรียมงาน (`item_catalog.item_max_stack`, ยังไม่ถูกเรียกจาก production path ใด ๆ) และเทสที่ pin
พฤติกรรมเดิมของ `scene_catalog`/`commands.describe_warp_target` ที่มีอยู่แล้วแต่ยังไม่เคยมีเทสคุม

**NONCLAIM:** ไม่มีการเปิด client ไม่มีการวัดกับไคลเอนต์จริง ไม่มีบรรทัดใดของ GM ไปถึงไวร์เพิ่มขึ้นจาก
รอบนี้ -- `warp`/`npc`/`item`/`lv`/`spawn`/`say` ทั้งหมดยังทำงานเหมือนเดิมทุกประการ รอบนี้เป็นการ
ทำความสะอาด error-contract และเทสล้วน ๆ ไม่มีการใช้ GM ข้ามขั้นตอนใดเลย เพราะไม่มีการทดสอบไคลเอนต์จริง

## รอบ `xq4vrn` -- 2026-08-30T23:45+07:00 -- GM-042 prep: `item` gets the same read-only diagnostic `npc` has

### หนึ่งบรรทัด

`gm/chat_command_action.py` ต้นรอบ (Addendum A) ยืนยันซ้ำว่ารอบก่อน (`2f9xji`) landed ครบ: `pf_bridge#535`
merged=true; `pirate-force-server#337` merged=false แต่ diff ของมันซ้ำซ้อนกับ chief's merged `#334`
ทุกจุด (ตรวจด้วย `pull_request_read get_files`/`get diff` ทั้งคู่ตรง ๆ ไม่เชื่อจดหมาย) -- ไม่ต้อง
cherry-pick อะไร ยืนยันซ้ำจาก `origin/main` เองว่า `test_gm_login_scene_sanctioned_barred.py` มี dedup
filter (`d.n_id != SANCTIONED`) ครบแล้วจริง แล้วจึงต่อยอด: `gm/item_catalog.py` (สร้างรอบ `opr2xd`, GM-042
prep) มีอยู่แล้วแต่ไม่เคยถูกเรียกจากที่ไหนใน `gm/` เลย -- รอบนี้เพิ่ม `_note_item_catalog_diagnostic`
mirror ของ `_note_npc_recompose_diagnostic` (CORE-REQUEST-GM-041's ของ `npc`) ทุกกระเบียดนิ้ว: same
`type(args) is not tuple` guard, same `noqa: BLE001` boundary, called จากจุดเดิมหลัง `verdict` ผูกค่า
แล้ว (จุดที่ pf-adversary รอบ `nbihci` เคยจับได้ว่าเรียกเร็วไปหนึ่งบรรทัด)

### ทำไมสามคำตอบ ไม่ใช่สองแบบ npc

`item_catalog.item_category(item_id)` คืน 0, 1 หรือมากกว่า 1 หมวด (module docstring: id ชนกันข้ามตาราง
misc/consumable/quest จริง วัดแล้ว) -- diagnostic รอบนี้จึงตอบสามแบบ: `unknown` (ไม่มีในตารางไหนเลย)
`known_<category>` (พบหมวดเดียว -- กรณีทั่วไป) `ambiguous_<n>` (พบ n หมวด, n=2 หรือ 3) วัดสดยืนยันตัวอย่าง
จริงแทนการเดาจาก docstring เดิม (docstring ยกตัวอย่าง id 1/6 ผิดคู่จากที่วัดได้จริงรอบนี้ -- id 1 ชนกัน
misc+quest ไม่ใช่ misc+consumable อย่างที่ตัวอย่างเดิมบอก; ไม่ได้แก้ docstring เพราะยังไม่ใช่จุดที่รอบนี้
แตะ แต่บันทึกไว้ตรงนี้ให้คนอ่านรอบหน้ารู้ว่าตัวอย่างในเอกสารต้นทางคลาดเคลื่อนจากตารางจริงเล็กน้อย)

### ทำไมยังไม่เปิด CORE-REQUEST หรือขยาย grammar

คำถาม "จะทำ `item <id> <n>` ยังไงกับ id ที่ชนกันข้ามหมวด" (ที่รอบ `opr2xd` บอกไว้ว่า "chief/Panya
เป็นคนตัดสิน ไม่ใช่ฝั่งนี้") **ยังไม่ตัดสิน** -- diagnostic รอบนี้แค่ทำให้คำถามนั้น**วัดได้จากคอนโซล**
ทุกครั้งที่พิมพ์ `/item <id> <n>` (ไม่ต้องเปิดไฟล์ ndjson) ไม่ใช่การตัดสินใจแทน ไม่แตะ grammar 2-argument
เดิมเลย (`COMMAND_USAGE["item"]` ไม่เปลี่ยน) เพราะการเพิ่ม argument ที่สามเป็นการเปลี่ยน interface ที่
operator เห็น ต้องรอ chief/Panya เคาะก่อนตามที่ระบุไว้แล้ว

### เทส (ยืนยันด้วย mutation-kill จริง ไม่ใช่แค่เขียนแล้วเขียว)

5 เทสใหม่ใน `tests/test_gm_chat_command_action.py`: known-single-category (id 11 -> `quest`),
unknown (id สมมติใหญ่เกินตาราง), ambiguous (id 1 -> 2 หมวด), exception-safety (`RuntimeError` ถูก mock
เข้าไปที่ `item_catalog.item_category` -> `unexpected_RuntimeError`, ไม่หลุดออกนอกฟังก์ชัน), lying-tuple
(`tuple` subclass โกหก `__len__`/`__getitem__` -> `bad_args_shape`, ไม่มี `known_`/`ambiguous_` event
ใด ๆ หลุดออกมา) -- ยืนยัน mutation-kill ของกรณี single-category ด้วยมือ (`pf-adversary` subagent ไม่มีให้
เรียกอีกครั้ง, สี่รอบติดต่อกันแล้วนับจาก `opr2xd`): แก้ `elif len(cats) == 1` เป็น `== 999` ชั่วคราว รัน
เทส เห็นแดงจริง (`known_quest` หาไม่เจอ, ได้ `ambiguous_1` แทน) แล้วคืนของเดิม รันเขียวอีกครั้งก่อนคอมมิต
(ระหว่างขั้นตอนนี้พลาดใช้ `git checkout --` ทับไฟล์ source ทั้งไฟล์โดยไม่ตั้งใจครั้งหนึ่ง -- เขียนซ้ำใหม่
ทั้งหมดจาก diff ที่จำได้ ตรวจด้วย `git diff`/pytest ซ้ำจนมั่นใจว่าเหมือนของเดิมทุกบรรทัดก่อนไปต่อ บันทึก
ไว้ตรงนี้เป็นบทเรียนกระบวนการ ไม่ใช่เพราะกระทบผลลัพธ์สุดท้าย)

`pytest tests/test_gm_chat_command_action.py -q`: **68 passed** (+5 จากเดิม), 64 subtests
`pytest tests/ -q` เต็ม: **5595 passed, 327 skipped, 9729 subtests passed**, 0 failed (base
`origin/main` ที่ 53b9a0b ต้นรอบ, cloud sanity)

### กล่องจดหมาย (Addendum B)

สองใบบริโภครอบนี้ (ทั้งคู่ addressed ถึงสาย GM, ไม่มี `.CONSUMED.txt` มาก่อน):
- `20260830_2048_COO-DECISION-warp-cross-scene-waits-for-gt106-r2.md`: ตัดสินไม่เปิด live teleport
  กลางเซสชันจนกว่า `GT-106-R2` (ของ chief, ยังไม่เห็นว่าเปิดในคิว ณ เวลาที่ตรวจรอบนี้) จะมีผล -- ตรวจ
  โค้ดจริง (grep `login_scene_stage.py`/`warp_executor.py`/`chat_command_action.py` หา
  `[สมมติของสาย GM - รอ COO ยืนยัน]` ที่เกี่ยวกับหัวข้อนี้โดยเฉพาะ): **ไม่พบป้ายให้ลบ** -- ทางเลือก 3
  (live teleport) ไม่เคยถูกเขียนเป็นโค้ดเลยสักบรรทัด อยู่แค่ระดับข้อเสนอในจดหมาย ป้ายที่จดหมายสั่งให้ลบ
  จึงไม่มีอยู่จริงให้ลบ -- พฤติกรรม stage-รอ-login-หน้าเดิมของ `warp_executor.py`/`login_scene_stage.py`
  ไม่เปลี่ยนแปลงเลยสักบรรทัด ตรงตามที่ COO สั่ง
- `20260830_2244_COO-DECISION-claim-before-work-rule-for-shared-tickets.md`: กติกา "ประกาศจองก่อนเริ่ม"
  สำหรับใบเปิดกว้างเกินหนึ่งสาย -- รับทราบ ไม่มีใบแบบนั้นเปิดอยู่ในกล่องจดหมายรอบนี้ให้ต้องจอง แต่บันทึก
  กติกาไว้ที่นี่เพื่อให้รอบหน้าเห็นก่อนหยิบใบเปิดกว้าง

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

ไม่มี -- `item <id> <n>` ยังคง parse+log เหมือนเดิมทุกประการ ไม่มีการแจกไอเทมจริง รอบนี้แค่เพิ่มบรรทัด
diagnostic บนคอนโซล/ndjson event ที่นักพัฒนา/ผู้ตรวจอ่านได้ ไม่ใช่สิ่งที่ผู้เล่นหรือผู้เทสในเกมเห็น

### nonclaim

ไม่มีการเปิด client ไม่มีการวัดกับไคลเอนต์จริง ไม่มีบรรทัดใดของ GM ไปถึงไวร์เพิ่มขึ้นจากรอบนี้ --
`warp`/`npc`/`item`/`lv`/`spawn`/`say` ทั้งหมดยังทำงานเหมือนเดิมทุกประการ ไม่แตะ
`runtime.py`/`app.py`/`pf_login_game_server_v141.py` และไม่แตะ `scenarios/world_*.json`/
`scenarios/combat_*.json` ของสายอื่นเลยตลอดรอบ วัดผลจาก `pytest`/`grep`/`git diff`/`pull_request_read`
ที่รันจริงเท่านั้น ไม่มีการใช้ GM ข้ามขั้นตอนใดเพราะไม่มีการทดสอบไคลเอนต์จริงในรอบนี้เลย

— สาย GM รอบ `xq4vrn`

## รอบ `aejgap` -- 2026-08-31T00:25+07:00 -- pf-adversary กลับมาใช้ได้: จับ off-by-one ใน docstring ของ `item_catalog.py`

### หนึ่งบรรทัด

ต้นรอบ (Addendum A) ยืนยัน `pf_bridge#541`/`pirate-force-server#342` (รอบ `xq4vrn`) ทั้งคู่ `merged: true`
บน main แล้ว ไม่มีอะไรต้องกู้ กล่องจดหมายไม่มีใบที่จ่าหน้าถึงสายนี้ค้างบริโภค (สามใบ cc ถึงสายนี้ในคืนนี้
เป็นเรื่องกติกา CLAIM ของสายอื่น ไม่มีข้อสั่งสายนี้) backlog ในเขต `gm/` ทั้งสามจุด (`GM-042` เต็ม, `GT-128`)
ยังบล็อกบน chief/COO เหมือนเดิม -- แต่รอบนี้ `pf-adversary` subagent **เรียกได้จริงเป็นครั้งแรกในรอบ
ติดต่อกันห้ารอบ** (`opr2xd`/`dao2gd`/`xq4vrn` ก่อนหน้าไม่มีให้เรียก) จึงใช้ตัวเลือก (ง) ของกฎข้อ F: ให้
มันตรวจ `gm/` ทั้งโมดูลหาหนี้สินทางเทคนิคที่ค้างจากการไม่มีมันมาสี่รอบ

### สิ่งที่พบ (ยืนยันซ้ำเองก่อนแก้ ไม่เชื่อผล subagent เปล่า ๆ)

`item_catalog.py` docstring ("IMPORTANT finding" ย่อหน้า) อ้างว่า "id 6 is 'Earth Element' (misc) but
'Fruit Wine Jar' (consumable)" -- ตรวจตรงกับ `gm/data/gm_item_misc.tsv`/`gm_item_consumable.tsv`/
`gm_item_quest.tsv` ที่ pin sha256 ไว้เอง (`awk -F'\t'` ตรงบนไฟล์ ไม่ใช่เชื่อ docstring): **id 6 ไม่มีอยู่
ในตาราง misc เลย** (id 6 มีแค่ใน consumable="Fruit Wine Jar" และ quest="Lucky Canine" -- เป็นคู่ชน
consumable/quest ไม่ใช่ misc/consumable ตามที่ docstring อ้าง) ส่วน "Earth Element" ตัวจริงอยู่ที่ **id 7**
ของตาราง misc -- และ id 7 เองก็ชนกับ consumable id 7 = "Fruit Wine Jar" พอดี (สามทาง จริง ๆ ยังชนกับ
quest id 7 = "Princess Sick Leave" ด้วย) สรุปคือผู้เขียนย่อหน้าเดิมพิมพ์เลข id ผิดหนึ่งตัว (เอาชื่อจริงของ
id 7 มาแปะไว้ใต้เลข 6) ไม่ใช่ชื่อไอเทมผิด -- ตัวอย่าง id 1 ในย่อหน้าเดียวกัน (misc="Adventure Key" /
quest="Sky Lantern") ตรวจแล้วถูกต้องอยู่แล้ว ไม่แตะ

ผลกระทบจริง: ไม่มีโค้ด production ทางใดอ่าน docstring นี้เป็นข้อมูล (`item_category()`/`item_name()`/
`is_known_item()`/`item_max_stack()` อ่านจากไฟล์ tsv ตรง ๆ ไม่เคยอ่านตัวเลขจาก docstring) แต่ย่อหน้านี้
เป็นจุดเดียวที่เตือนคนต่อไปที่จะ wire `item <id> <n>` ให้แจกไอเทมจริงว่า id ชนข้ามตารางได้ -- ถ้าใครเชื่อ
ตัวอย่าง id 6 แทนที่จะวัดสดตอนตัดสินใจ จะได้ทั้งหมวดผิดและชื่อไอเทมผิด ตรงกับสิ่งที่ย่อหน้านี้เขียนมาเพื่อ
ป้องกันพอดี -- `tests/test_gm_chat_command_action.py` (commit ก่อนหน้า) มีคอมเมนต์รับรู้ปัญหานี้แล้วแต่
เลี่ยงด้วยการวัดสดแทนที่จะแก้ docstring ตรง ๆ

### สิ่งที่แก้

1. `item_catalog.py` บรรทัด docstring: `id 6` → `id 7` (แก้ตัวเลขเดียว ชื่อไอเทมทั้งสองที่อ้างถูกอยู่แล้ว)
2. `tests/test_gm_item_catalog.py::test_module_docstrings_misc_consumable_example_id_matches_the_data`
   (ใหม่): pin ตัวอย่าง id 7 ของ docstring กับข้อมูลจริงในไฟล์ (`misc[7]=="Earth Element"`,
   `consumable[7]=="Fruit Wine Jar"`, ทั้งสองอยู่ใน `item_category(7)`, และ `6 not in misc`) ตอบคำถามที่
   `pf-adversary` ทิ้งไว้ตรง ๆ: "มีกลไกผูก docstring ตัวอย่างกับข้อมูลจริงไหม" -- ตอนนี้มีหนึ่งเทสที่ทำแบบ
   นั้น ถ้า data refresh รอบหน้าย้ายชื่อออกจาก id 7 เทสนี้แดงทันทีแทนที่จะปล่อยให้ docstring ค้างผิดอีกรอบ
   mutation-kill ยืนยันด้วยมือ: เปลี่ยนชื่อฟังก์ชัน `item_category` ชั่วคราวให้เรียกไม่ได้ เห็นเทสนี้ (และอีก
   6 เทสในไฟล์เดียวกัน) แดงจริงด้วย `NameError`, คืนของเดิม รันเขียวอีกครั้งก่อนคอมมิต

`pytest tests/test_gm_item_catalog.py -q`: **14 passed** (+1), 12 subtests
`pytest tests/test_gm_*.py -q`: **1054 passed** (+1), 469 subtests, 0 failed
`pytest tests/ -q` เต็ม: **5596 passed** (+1), 327 skipped, 9729 subtests passed, 0 failed (cloud sanity,
base `origin/main` ต้นรอบ)

### สิ่งที่ pf-adversary ตรวจแล้วไม่พบข้อบกพร่อง (บันทึกไว้กันขุดซ้ำ)

`chat_command_action.py`'s `_note_item_catalog_diagnostic` (ลำดับเรียก, shape guard, exception boundary),
`scene_catalog.py` blank-row handling, `dispatch.py` rate-limiter/capture-quota locking, `accounts.py`,
`npc_switch_catalog.py`, `login_scene_override.py`, `warp_executor.py`/`teleport_wire.py`/
`warp_target_record.py` round-trip encode/decode -- อ่านครบ ไม่พบข้อบกพร่องจริงที่ยืนยันได้ พบข้อสังเกต
อ่อนหนึ่งจุด (`chat_command.py`'s `_command_log_quota_allows` ไม่มี lock รอบ stat-then-append ต่างจาก
`_capture_quota_allows` ที่มี) แต่ผลกระทบเล็กมาก (ต่อ write ไม่เกิน ~650 ไบต์) ไม่ยืนยันเป็นบั๊กจริง บันทึก
ไว้เป็นจุดที่รอบหน้าอาจดูซ้ำ ไม่ใช่ finding

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

ไม่มี -- แก้ docstring และเพิ่มเทสเท่านั้น ไม่มีบรรทัดใดของ `item <id> <n>` หรือคำสั่ง GM อื่นเปลี่ยน
พฤติกรรม `item` ยัง parse+log เหมือนเดิมทุกประการ ไม่มีการแจกไอเทมจริง

### nonclaim

ไม่มีการเปิด client ไม่มีการวัดกับไคลเอนต์จริง ไม่มีบรรทัดใดของ GM ไปถึงไวร์เพิ่มขึ้นจากรอบนี้ --
`warp`/`npc`/`item`/`lv`/`spawn`/`say` ทั้งหมดยังทำงานเหมือนเดิมทุกประการ ไม่แตะ
`runtime.py`/`app.py`/`pf_login_game_server_v141.py` และไม่แตะ `scenarios/world_*.json`/
`scenarios/combat_*.json` ของสายอื่นเลย ไม่มีการใช้ GM ข้ามขั้นตอนใดเพราะไม่มีการทดสอบไคลเอนต์จริงในรอบนี้
เลย การแก้ครั้งนี้เป็นเอกสาร (docstring) + เทสล้วน ๆ ไม่แตะ logic ของ `item_category`/`item_name`/
`is_known_item`/`item_max_stack` แม้แต่บรรทัดเดียว

— สาย GM รอบ `aejgap`

## รอบ `gm17278` (2026-08-31T02:25+07:00) — BT_GM/GMUI_BASIC experiment fork (RE-164/GT-165)

### คำสั่ง

`notes_to_chief/20260831_0152_PANYA-ORDER-LANE-GM-make-the-BT_GM-button-and-GMUI_BASIC-window-actually-work.md`
(เจ้าของ, เขียนแทนโดยกะ1-A): ทำให้ปุ่ม `BT_GM` เปิดหน้าต่าง `GMUI_BASIC` ได้จริง เป็นงานหลักของสาย GM
รอบนี้ แทนงานรองอื่น -- `gm/attr_wire.py` (COO-DECISION 2026-08-31T01:46+07:00, six นาทีก่อนหน้า) ถูกเลื่อน
ออกไปรอบถัดไปตามข้อความของใบสั่งเองที่ว่า "แทนการวนกฎ F ทำงานรองไปเรื่อย ๆ"

### สิ่งที่รู้แล้วก่อนรอบนี้ (ห้ามขุดซ้ำ)

`RE-126` CLOSED: ปุ่ม `BT_GM` ผูกกับ object เดียวกับ dispatcher จริง (ไม่ใช่ผูกผิดตัว) -- ปิดท้ายด้วย
รายชื่อสี่ผู้ต้องสงสัยที่เหลือ (connection context / query-0x25 gate ตอนคลิก / current-UI object-key จริง
/ create path `0x007280D0`) แล้วปฏิเสธจะเดา `GT-103` A/B: NO-RESULT ที่มีค่า -- สี่สถานะ UI คลิกแล้วเงียบ
ทุกครั้ง หักล้างข้อเสนอเชิงปฏิบัติของ `RE-118` ("current-UI key ต้องไม่ว่าง")

### สิ่งที่สร้างรอบนี้

1. `src/pirateforce_foundation/gm/bt_gm_probe.py` (ใหม่) -- experiment fork ตามแบบ `PF_ADHOC_ATTR_PROBE`:
   - `iter_state_vital_bit_variants()`/`build_variant_frame()`/`build_variant_payload()`: 14 variant ของ
     เฟรม `GM_UpdateGMStateVital` (`0x5A19`) ทีละฟิลด์ -- ใช้ `gm/state_wire.py`'s proven builder ตรง ๆ
     ไม่เพิ่ม tag/offset ใหม่แม้แต่ตัวเดียว ครอบคลุมบิต 0-7 ของ `field_0x14` + ค่าสูงสุด `0xFFFFFFFF` +
     ทั้งสอง u8 field -- **ไม่ครอบคลุมบิต 8-31 ของ `field_0x14` รอบนี้โดยตั้งใจ** (ช่องว่างที่บันทึกไว้
     ชัดเจน ไม่ใช่ครบทุกกรณี รอบหน้าอาจขยาย)
   - `SUSPECT_STUBS` (3 รายการ, แท็ก `[สมมติของสาย GM - รอ RE]`): ผู้ต้องสงสัย connection-context /
     current-UI-object-key เก็บเป็นคำถาม+เหตุผลที่ยังต่อสายไม่ได้รอบนี้ -- ไม่มีการเดาความหมาย ผู้ต้อง
     สงสัย query-gate-value-at-click-time ก็เป็น stub เช่นกัน (เป็นคำถามเรื่อง**เวลา**ที่ client เช็คซ้ำ
     gate ไม่ใช่ค่าที่เฟรมนี้ตั้งได้) -- ผู้ต้องสงสัยตัวที่สี่ (factory ถูกเรียกไหม) ไม่ใช่ stub เพราะเป็น
     **ผล**ที่การคลิกทดสอบสังเกต ไม่ใช่ตัวแปรขาเข้า
2. `tests/test_gm_bt_gm_probe.py` (ใหม่, 22 เทส): ตรวจ frame/payload construction เท่านั้น (ความยาว 41/9
   ไบต์ตรงกับที่ใบสั่งเจ้าของเรียก "เฟรม 41 ไบต์ที่พินแล้ว", vital id คงที่, field range, variant id ไม่ซ้ำ,
   stub metadata) -- **ไม่มีเทสใดอ้างว่าหน้าต่างเปิด** ตามกฎ nonclaim ที่ตัวไฟล์ประกาศเอง
3. `pf_bridge/CLIENT_RE_QUEUE.md`: เปิด `RE-164` (ใบสอบสวนหลัก, tag `[NEEDS-ATTENDED-CAPTURE]`)
4. `pf_bridge/GAME_TEST_QUEUE.md`: เปิด `GT-165` (สเปกคลิกสำหรับกะ1-A ทีละ variant) -- **สถานะ BLOCKED**
   ดูข้อถัดไป
5. `pf_bridge/notes_to_chief/20260831_0225_LANE-GM-CORE-REQUEST-GM-043-...md`: ตรวจ `runtime.py:6424-6438`
   แล้วพบว่าจุดเรียก `make_gm_update_state_frame` ที่มีอยู่ตอนนี้ยิงค่าคงที่ `(0,1,0)` ครั้งเดียวตอน
   ล็อกอินของบัญชี GM เท่านั้น (`ALWAYS ON, no scenario flag` ตามคอมเมนต์จุดเรียกเอง) -- ไม่มีทางยิง
   variant อื่นระหว่าง session เดียวกันได้เลย `GT-165` จึง BLOCKED จนกว่าจุดเสียบใหม่ (เสนอสองทางเลือก:
   GM chat-command ใหม่ หรือ debug scenario flag) จะลงจาก chief

### pf-adversary รอบนี้

ตรวจ `bt_gm_probe.py`/เทสก่อน commit -- ดูหัวข้อ "pf-adversary" ด้านล่างสำหรับสิ่งที่พบ/แก้

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

ยังไม่มี -- รอบนี้สร้างแค่ตัวสร้างเฟรม/เทส/ใบคิว ยังไม่มีจุดเรียกที่ยิง variant ได้จริง (`CORE-REQUEST-GM-043`
รออยู่) `GT-165` เขียนสเปกไว้ล่วงหน้าแล้วแต่คลิกไม่ได้จนกว่าจุดเสียบจะลง

### nonclaim

**ไม่มีการอ้างว่า `GMUI_BASIC` เปิดหรือไม่เปิดจาก variant ใดเลยรอบนี้** -- ไม่มีการเปิด client ไม่มีการส่ง
เฟรมจริงไปยังไคลเอนต์จริง สาย GM ไม่มีจอ ไม่มีอิมเมจไคลเอนต์ การคลิกจริงเป็นของกะ1-A เท่านั้นตามกฎใบเดียว
ผู้ทำเดียว -- งานรอบนี้ทั้งหมดคือการ**สร้างเครื่องมือให้พร้อมสำหรับการคลิกทดสอบ** ไม่ใช่การพิสูจน์ว่าปุ่ม
ทำงาน ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py` (อ่านอย่างเดียวผ่าน `legacy_bridge` ตาม
ที่เทสเดิมทำอยู่แล้ว) และไม่แตะ `scenarios/world_*.json`/`scenarios/combat_*.json`

`pytest tests/test_gm_bt_gm_probe.py -q`: **22 passed**
`pytest tests/test_gm_*.py -q`: **1076 passed** (+22, tracked-file guard test นับรวม), 471 subtests, 0 failed
`pytest tests/ -q` เต็ม: **5626 passed** (+30), 327 skipped, 9733 subtests passed, 0 failed (cloud sanity,
base `origin/main` ต้นรอบ)
`python3 tools/verify_hypothesis_ledger.py` / `verify_functional_coverage.py`: ทั้งคู่ PASS ไม่มี drift

— สาย GM รอบ `gm17278`

## รอบ `jz4don` (2026-08-31T04:2x+07:00) — `/gmprobe <variant_id>` chat command (CORE-REQUEST-GM-043)

### คำสั่ง

`notes_to_chief/20260831_0357_CHIEF-REPLY-CORE-REQUEST-GM-043-decision-option-A-gmprobe-chat-command.md`:
chief ตัดสินทางเลือก A -- คำสั่งแชท `/gmprobe <variant_id>` ต่อสายผ่าน dispatch เดียวกับ `/warp`/`/say`
เรียก `bt_gm_probe.build_variant_frame` เพิ่มเทส dispatch wiring แบบเดียวกับ `WarpActionTests` -- ไม่ต้อง
แตะ `runtime.py` เพราะ `GM_UpdateGMStateVital` proven เต็มแล้ว (`RE-105`/`RE-089`)

### สิ่งที่สร้างรอบนี้

1. `gm/commands.py`: เพิ่ม `"gmprobe": "gmprobe <variant_id>"` ต่อท้าย `COMMAND_USAGE` (ลำดับ 7 คำสั่ง
   เดิม 6 ของเจ้าของยังเหมือนเดิม ต่อท้ายเท่านั้น -- pin โดย
   `test_gm_chat_command_parse_way_out.py::TheUsageHintItselfTests::
   test_the_vocabulary_order_is_pinned_because_a_human_reads_it`) + branch parse ใหม่ใน `parse_gm_command`
   -- รับ token เดียวเป็น `variant_id` (str ใด ๆ ที่มี 1 คำ) ไม่ตรวจกับตาราง `bt_gm_probe` ที่ชั้นนี้
   (แยกชั้นเหมือน `warp`'s `scene_catalog` hint -- ตรวจจริงที่ dispatch)
2. `gm/bt_gm_probe.py`: เพิ่ม `VARIANTS_BY_ID` (dict สร้างจาก `iter_state_vital_bit_variants()` ตัวเดียว
   กันสองตารางเพี้ยนออกจากกัน), `known_variant_ids()`, `variant_by_id()` -- คืน `None` สำหรับ id ที่ไม่รู้จัก
   ไม่เดาตัวใกล้เคียง
3. `gm/chat_command_action.py`: `GMPROBE_ACTION_LABEL` (ไม่มีคำว่า `TELEPORT` -- probe ไม่ขยับตัวละคร),
   `EVENT_GMPROBE_UNKNOWN_VARIANT`/`EVENT_GMPROBE_REFUSED_PREFIX`/`OUTCOME_GMPROBE_UNKNOWN_VARIANT`,
   ฟังก์ชัน `_gmprobe_action` (โมเดลตาม `_warp_action`/`_say_action`) ต่อเข้า `_make_action`'s dispatch
   -- **ไม่มี version gate** ต่างจาก `warp`/`say`: `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` ถูก RE-105
   พิน 0 ไว้ตรง ๆ ตั้งแต่ต้น ไม่ใช่ค่า `None`-รอพิสูจน์แบบ `FORCE_POS_VITAL_VERSION_CONFIRMED`/
   `GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` -- ไม่มีประตูให้ปิด
4. เทสใหม่: `GmprobeActionTests` (9 เคส) ใน `tests/test_gm_chat_command_action.py` -- variant รู้จักกลาย
   เป็น action จริง, variant ไม่รู้จักถูกปฏิเสธแบบมีชื่อ (ไม่เดา), ครบทั้ง 14 variant compose ได้โดยไม่ต้อง
   เปิดประตูใด, `args` shape ปลอมถูกปฏิเสธ (เหมือน `warp_executor`/`say_wire`), composer ที่ explode ถูก
   ตั้งชื่อไม่รั่วไหล, ไม่ต้องมีตำแหน่งผู้เล่น (ต่างจาก `/warp`), ไม่ park warp target ใด ๆ
5. อัปเดต pin tests สามจุดตามที่โค้ดเปลี่ยนแปลงจริงบังคับ: `TheUsageHintItselfTests` (ลำดับ vocabulary),
   `TheExerciseTableCoversTheWholeCommandSurfaceTests`'s `COMMAND_EXERCISES` (tripwire คำสั่งใหม่ต้องเดิน
   ผ่านประตู standalone-map-not-writable), `EventNameContractTests`'s `EXPECTED`/`EXPECTED_LABELS` (พิน
   ชื่อ constant ใหม่เป็น literal)

### pf-adversary รอบนี้

เรียก agent `pf-adversary` ไม่ได้ในสภาพแวดล้อมนี้ (ไม่มี Task/agent-launch tool ในชุดเครื่องมือของรอบนี้)
-- ตรวจทานเองอย่างเข้มแทนตามกติกา: ใช้ threat model เดียวกับ `warp_executor`/`say_wire` ทุกจุด
(`type(args) is not tuple`, ไม่ใช่ `isinstance`, กัน tuple subclass โกหก), จับ `Exception` กว้างรอบ
composer ไม่ให้หลุดไปกลางเธรดฟัง, ไม่ echo `variant_id` ที่ GM พิมพ์เข้า event/console เลย (ใช้ literal
คงที่สำหรับ unknown-variant แทน), ไม่แตะ label ที่มีคำว่า `TELEPORT`, และรันสวีตเต็มก่อน/หลังเปรียบเทียบ
ผลต่าง

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

ตอนนี้กะ1-A ยิง `bt_gm_probe`'s 14 variant ไหนก็ได้ระหว่าง session จริงด้วยการพิมพ์ `/gmprobe <variant_id>`
ในแชท GM แทนที่จะรอค่าคงที่เดียวที่ยิงครั้งเดียวตอนล็อกอิน -- `GT-164` (เดิมชื่อ `GT-165` ในรอบ `gm17278`
เปลี่ยนเลขตามอนุสัญญาโปรเจกต์ในรอบ `b3fgm6`) ไม่ BLOCKED อีกต่อไปด้วยเหตุผลเดิม เปิดให้เทสได้จริงรอบนี้

### nonclaim

**ไม่มีการอ้างว่า `GMUI_BASIC` เปิดหรือไม่เปิดจาก variant ใดเลย** -- การยิง `/gmprobe` ผ่านคำสั่งแชทไม่ใช่
หลักฐานว่าอะไรเรนเดอร์บนไคลเอนต์ ยังต้องรอ `GT-164` (attended click test) เป็นผู้ตอบ ไม่มีการเปิด client
ไม่มีการวัดกับไคลเอนต์จริงในรอบนี้ ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py` (ยังคง
dispatch call site เดิมของ chief ไม่เปลี่ยน) ไม่แตะ `scenarios/world_*.json`/`scenarios/combat_*.json`
ไม่ให้สถานะ GM กับบัญชีใดที่ไม่อยู่ใน `gm_accounts` ไม่มีการประกาศ milestone จากผลที่ได้ด้วย GM

`pytest tests/test_gm_*.py -q`: **1097 passed** (+21), 506 subtests, 4 skipped, 0 failed
`pytest tests/ -q` เต็ม: **5649 passed** (+23), 327 skipped, 9758 subtests passed, 0 failed
`python3 tools/verify_hypothesis_ledger.py`: PASS entries=47, ไม่มี drift
`python3 tools/verify_functional_coverage.py`: PASS domains=8, ไม่มี drift

— สาย GM รอบ `jz4don`

## รอบ `gm-20260831-0517` (2026-08-31T05:1x-05:5x+07:00) — verify-only + npc_switch_catalog.py 8180/8181 label (COO-DECISION 0245)

### ต้นรอบ

- ไม่มี PR `[LANE-GM]` เปิดค้างทั้งสอง repo ก่อนยึดล็อก — ยึดด้วย empty commit "round claim:
  gm-20260831-0517" แล้วเปิด draft PR ทันที (`pf_bridge#565`, `pirate-force-server#361`)
- PR `[LANE-GM]` ล่าสุดของแต่ละ repo (`pf_bridge#561`, `pirate-force-server#357`, รอบ `jz4don`):
  `pull_request_read(method=get)` ยืนยัน `merged=true` ทั้งคู่ — งานอยู่บน main จริง ไม่ต้องกู้คืน
- กล่องจดหมาย: ไล่ `notes_to_chief/` หาใบที่จ่าหน้าถึง LANE-GM หรือเปิดโดย LANE-GM ที่ยังไม่มี
  `.CONSUMED.txt` (ทั้งสองรูปแบบชื่อไฟล์ที่ใช้ในโปรเจกต์นี้) — **ไม่พบใบใหม่ที่ต้องบริโภครอบนี้** ใบล่าสุดที่
  แตะ LANE-GM ตรง (`0430_LANE-GM-STATUS`, `0245_COO-DECISION-gm042-owner-questions`) มี `.CONSUMED.txt`
  ครบแล้วทั้งคู่ (chief round `8skr91` backfill)

### สถานะ RE-164/GT-164 (เรื่องหลักของ `PANYA-ORDER 0152`)

ตรวจแล้วไม่มีอะไรให้ต่อสายเพิ่มรอบนี้: `GT-164` ปลด BLOCKED แล้วตั้งแต่รอบ `jz4don` (จุดเสียบ `/gmprobe
<variant_id>` อยู่บน main) รอเพียงกะ1-A คลิกจริงในเซสชัน attended — ไม่ใช่งานที่ทำได้ในสภาพแวดล้อมรีโมต
ไม่มีจอของรอบนี้ `RE-164` suspect 1/3/4 (connection context / current-UI object-key / create path
`0x007280D0`) ต้องใช้ disassembly ของไบนารีไคลเอนต์จริง (VA อ้างอิงเป็นของ client .exe) — เป็นงาน RE lane
ไม่ใช่ของ LANE-GM ตามกฎ "ถ้าเป็นงาน RE ไม่ใช่ของเรา เขียนใบขอแทนเดา" ใบ `RE-164` เปิดรออยู่แล้วจากรอบก่อน
ไม่ต้องเปิดซ้ำ

### สิ่งที่ทำรอบนี้ (เดียว, เล็ก, ปลอดภัย)

`gm/npc_switch_catalog.py`: เติมป้าย docstring สำหรับ `8180`/`8181` (Water Lantern x2) ตามที่
`COO-DECISION 20260831_0245` สั่งไว้ ("ครั้งต่อไปที่แตะไฟล์นี้ ให้ป้ายว่า catalog-only ยังไม่พบแถว
server-side") — ไม่มีการเปลี่ยน logic ใด ๆ ในไฟล์ เป็นการเพิ่ม docstring บรรทัดเดียวเท่านั้น

🔴 **พลาดแล้วแก้เอง**: ร่างแรกของ docstring ใส่ตัวอักษรจริงของ `s_NAME` (อักษรจีนดั้งเดิม ไม่ใช่ไทย) ลงในไฟล์
`.py` ตรง ๆ — รันสวีตพบว่า `test_gm_source_is_cp874_safe.py` fail จริง (ตัวอักษรนั้นไม่มี mapping ใน cp874)
แก้เป็นข้อความ ASCII ที่ชี้ไปที่ไฟล์ TSV แทนก่อน commit ไม่ได้ปล่อยโค้ดที่ทำให้ gate แดงหลุดออกไป

### pf-adversary รอบนี้

diff เดียวคือ docstring 12 บรรทัดใหม่ ไม่มีการเปลี่ยน logic/ฟังก์ชัน/ทางแยกใด ๆ — ไม่มี threat model ใหม่ให้
ตรวจ (ไม่ใช่การแก้คำผิดตามตัวอักษร แต่ก็ไม่มีความเสี่ยง logic ให้ pf-adversary จับ) รันสวีตเต็มก่อน/หลัง
ยืนยันจำนวนเทสไม่เปลี่ยน (`5661 passed` ทั้งสองครั้ง หลังนับรวมเทสที่ chief merge เพิ่มระหว่างรอบก่อนหน้า)

### เช็คสวีต

- `pytest tests/ -q` เต็ม: **5661 passed**, 323 skipped, 9758 subtests passed, 0 failed เขียว(cloud sanity)
- `python3 tools/verify_hypothesis_ledger.py`: PASS entries=47 ไม่มี drift
- `python3 tools/verify_functional_coverage.py`: PASS domains=8 ไม่มี drift (8 domain ยังเปิดเหมือนเดิม)

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบนี้ไม่มีจุดเสียบใหม่ที่ยิงได้จริง `GT-164` ยังรอกะ1-A คลิกจริงเหมือนเดิมทุกประการ (ปลด BLOCKED
ไปแล้วตั้งแต่รอบ `jz4don`) การเปลี่ยนแปลงรอบนี้คือ docstring/label เท่านั้น ไม่กระทบพฤติกรรมรันไทม์ใด ๆ

### nonclaim

1. ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่ได้เปิด client ไม่มีจอในสภาพแวดล้อมนี้
2. ไม่ได้ตัดสินหรือเดาคำตอบของ `RE-164` suspect ใดเลย — ยังคงเป็นใบเปิดรอ RE lane เหมือนเดิม
3. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/`scenarios/world_*.json`/
   `scenarios/combat_*.json` เลยรอบนี้ ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มีการประกาศ
   milestone จากผลที่ได้ด้วย GM
4. ป้าย 8180/8181 เป็น docstring เท่านั้น ไม่ได้เพิ่ม/ลด behavior ของ `is_gm_switchable_npc`/`npc_gm_name`
   ทั้งสอง id ยังถูกมองว่า "เป็นหนึ่งใน 7" เหมือนเดิมทุกประการ (แค่ไม่ให้ใครอ่านแล้วเข้าใจผิดว่ามีแถว
   server-side ยืนยันแล้ว)

### PR

- `pf_bridge#565` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle)
- `pirate-force-server#361` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle + wake-gate commit)

— สาย GM รอบ `gm-20260831-0517`

## รอบ `1q7nxu` (2026-08-31T08:2x+07:00) — RE-164 ปิดสองใน สี่ผู้ต้องสงสัยด้วย static synthesis

### สรุป

ไม่มีจอ ไม่มี client image ในสภาพแวดล้อมนี้เหมือนทุกรอบ — แต่พบว่า `RE-164` suspect ข้อ 2
(query-0x25 gate ถูกเรียกซ้ำตอนคลิกหรือไม่) และข้อ 4 (factory `0x007280D0` ถูกเรียกไหมหรือมี
early-return) **ตอบได้แล้ว** จากสองใบที่ commit อยู่ก่อน `RE-164` จะเปิดด้วยซ้ำ (`RE-104`, `RE-118`)
แค่ไม่มีใครเอามา cross-reference กับ `RE-164` ตอนเปิดใบ ไม่ใช่หลักฐานใหม่ เป็นช่องว่างของการสังเคราะห์
รายละเอียด/บรรทัดอ้างอิงเต็มอยู่ใน `pf_bridge/CLIENT_RE_QUEUE.md` RE-164 (แก้ tag เป็น
`[PARTIAL — 2/4 CLOSED STATIC, 2/4 NEEDS-ATTENDED-CAPTURE]`)

ข้อ 1 (connection context ตรง session ไหม) กับข้อ 3 (current-UI object-key เงื่อนไขจริง) ยังปิดไม่ได้
— ทั้งคู่ต้องไล่ disassembly ต่อจากจุดที่ `RE-118` หยุดไว้ (write-site ของ `[0x01032EC4]` / vfunc chain
ต่อจาก `[0x008946C0,0x008946EA)`) ไม่มีในอิมเมจของ clone นี้ ยังคง tag `[NEEDS-ATTENDED-CAPTURE]`

### ที่ทำรอบนี้

1. ยืนยัน round-lock ว่าง (ไม่มี PR `[LANE-GM]` เปิดค้างทั้งสอง repo) ก่อนเริ่ม
2. Addendum A: ตรวจ `pf_bridge#573`/`pirate-force-server#367` (รอบ `rob5s4` ก่อนหน้า) ด้วย
   `pull_request_read` โดยตรง — `merged=true` ทั้งคู่ (⚠️ `list_pull_requests` คืน `merged:false` ผิด
   สำหรับ PR เดียวกัน ตามที่ใบ `1936` เคยเตือนไว้ — ใช้ `pull_request_read` เท่านั้น) ไม่มีงานหาย
3. บริโภคจดหมาย `20260831_0723_KA1A-CORRECTION-*` (แก้คำวินิจฉัยของกะ1-A สองข้อ ไม่ต้องดำเนินการเพิ่ม
   `gm/attr_wire.py` ยัง shelve ตาม COO-DECISION 0350) — วาง stub + สำเนาไป `consumed/`
4. มอบหมาย `pf-static-re` agent ไล่สี่ผู้ต้องสงสัยของ `RE-164` จาก artifact ที่ commit แล้วเท่านั้น
   (ไม่แตะ client) พบว่าข้อ 2/4 มีคำตอบอยู่แล้วในใบเก่า แก้ `CLIENT_RE_QUEUE.md` ให้สะท้อนสถานะจริง
5. ไม่มีโค้ดเปลี่ยนในเขต `src/pirateforce_foundation/gm/` รอบนี้ — งานเป็นเอกสาร/คิวล้วน

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยน `GT-164` ยังรอกะ1-A คลิกจริงเหมือนเดิมทุกประการ
รอบนี้แค่ทำให้ `RE-164` มีสถานะที่ถูกต้อง (ครึ่งหนึ่งปิดแล้ว) แทนที่จะเขียนว่า "ยังไม่มีใครตอบสักข้อ"
ซึ่งผิดตั้งแต่ตอนเปิดใบ

### เขียว

`pytest tests/test_gm_*.py -q` (`pirate-force-server` HEAD ปัจจุบัน): 1085 passed, 500 subtests
เขียว(cloud sanity) — ไม่มี drift เพราะไม่มีการแก้ไฟล์ `src/`/`tests/`

### nonclaim

1. ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่ได้เปิด client ไม่มีจอในสภาพแวดล้อมนี้ — สอง suspect ที่
   ปิดคือการอ่าน artifact เก่าใหม่ ไม่ใช่หลักฐานใหม่จากไบนารี
2. ข้อ 1 กับ 3 ของ `RE-164` ยังไม่ปิด ห้ามอ้างว่า RE-164 ปิดครบ — เปิด CORE-REQUEST/ใบขอ RE runner แทนถ้า
   จะไล่ต่อทาง static (ต้องมี client image) หรือรอ attended capture
3. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/`scenarios/world_*.json`/
   `scenarios/combat_*.json` เลยรอบนี้ ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มีการประกาศ
   milestone จากผลที่ได้ด้วย GM
4. ไม่ได้แก้ `bt_gm_probe.py` หรือเทสใด ๆ รอบนี้ — เขตโค้ดของ `pirate-force-server` ไม่มีการเปลี่ยนแปลง

### PR

- `pf_bridge#578` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle)
- `pirate-force-server#370` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle + wake-gate commit;
  ไม่มีไฟล์ `src/` เปลี่ยนรอบนี้)

— สาย GM รอบ `1q7nxu`

## รอบ `szmgeh` (2026-08-31T09:2x+07:00) — GT-164 ปิดหัวใบ, field_0x0b_second codified เป็นสวิตช์การมองเห็น

### สรุป

กล่องจดหมายมีสองใบใหม่จ่าหน้า LANE-GM: (1) `KA1A-DELIVERY` ยืนยัน adhoc-probe reference materials
เข้า repo แล้ว (อ่านอย่างเดียว) และ `gm/attr_wire.py` ยัง shelve ตาม `COO-DECISION 0350` เหมือนเดิม --
ไม่มีการกระทำเพิ่ม (2) `GT164-RESULT` -- กะ1-A คลิก `BT_GM` จริงครบ 14/14 variant ของ `bt_gm_probe.py`:
ไม่มีตัวไหนเปิด `GMUI_BASIC` (bounded negative ปิด `RE-164` ข้อ 2 ทั้งชั้น static+attended) แต่พบผลข้างเคียง
ที่มีค่า: `field_0x0b_second` (รู้จักอยู่แล้วจาก `RE-089`/`RE-104`/`CORE-REQUEST-020` ว่าคุมการมองเห็นปุ่ม
ตอน login) ยืนยันด้วยตาเป็นครั้งแรกว่าคุมการมองเห็น**กลางเซสชัน**ด้วย ผ่าน `/gmprobe` 14/14 ไม่มีข้อยกเว้น
ไม่ต้อง relog

### ที่ทำรอบนี้

1. ยืนยัน round-lock ว่าง, reset สองสาขาลง origin/main สะอาด (ไม่มีงานค้างของตัวเอง), ยึดล็อกก่อนเริ่ม
2. บริโภคจดหมายทั้งสองใบ (`KA1A-DELIVERY` 0828, `GT164-RESULT` 0901) -- stub + สำเนาไป `consumed/`
3. `pf_bridge/CLIENT_RE_QUEUE.md` RE-164 -- เติมชั้น attended ใต้ข้อ 2 (ไม่ลบของเดิม), แก้ tag หัวใบ,
   แก้บรรทัด pass-criteria ที่ค้าง `BLOCKED` ให้ตรงความจริง, เพิ่ม nonclaim ข้อ 6, เพิ่ม link
4. `pf_bridge/GAME_TEST_QUEUE.md` GT-164 -- ปิดหัวใบเป็น RESULT, เก็บสถานะเดิมไว้อ่านประกอบ (ไม่ลบ)
5. `src/pirateforce_foundation/gm/bt_gm_probe.py` -- เพิ่ม `observed_button_visible()`,
   `guaranteed_visible_variant_ids()`, `guaranteed_hidden_variant_ids()` (pure predicate เหนือ generator
   เดิม ไม่มี field/เฟรมใหม่) พร้อม docstring อ้างอิง `GT-164`/`RE-089`/`RE-104`/`CORE-REQUEST-020` และ
   nonclaim ชัดว่า "มองเห็นได้" ไม่ใช่ "คลิกได้ผล" -- เพื่อให้ผู้เทสรอบต่อไปที่ไล่ `RE-164` ข้อ 1/3 เลือก
   variant ที่รู้แล้วว่าปุ่มโชว์แน่ ไม่ต้องเดา
6. `tests/test_gm_bt_gm_probe.py` -- เพิ่ม 12 เทสใหม่ (`ObservedButtonVisibilityTests`) ปักตารางการมองเห็น
   ตรงกับใบผลของ `GT-164` เป๊ะ (3 visible / 11 hidden ของ 14 variant)
7. pf-adversary self-review ก่อน commit (ไม่มี agent `pf-adversary` แยกในอิมเมจนี้ -- ตามที่รอบ
   `stale-stageable-count-refreshed` เคยบันทึกไว้แล้ว ทำเป็น self-review ตรวจทีละ hunk แทน): ตรวจ
   overclaim (ไม่มี -- ทุกคำอ้างอิงมีเลขบรรทัด/ที่มา), ตรวจ safety (ไม่แตะ account/permission logic ใด ๆ
   เป็น pure metadata เหนือ generator เดิม), ตรวจเขตเขียน (แค่ `gm/bt_gm_probe.py` +
   `tests/test_gm_bt_gm_probe.py`) -- ไม่พบจุดต้องแก้

### เขียว

`pytest tests/test_gm_bt_gm_probe.py -q`: 26 passed (14 เดิม + 12 ใหม่) · `pytest tests/test_gm_*.py -q`:
1089 passed, 500 subtests เขียว(cloud sanity, รันจริงในรอบนี้หลัง fetch origin/main)

### nonclaim

1. `GT-164` ปิดแล้วตอบเฉพาะข้อ 2 ของ `RE-164` เท่านั้น -- ข้อ 1/3/4 ไม่ถูกแตะเพิ่มรอบนี้ ข้อ 1/3 ยังเปิด
   รอ attended capture หรือ static RE เพิ่มที่ไม่มีในอิมเมจของ clone นี้
2. "ปุ่มมองเห็นได้" (`field_0x0b_second=1`) ไม่ใช่ "คลิกแล้วเปิดหน้าต่าง" -- สองเรื่องคนละชั้น พิสูจน์แล้ว
   ว่าแยกกัน (14/14 ที่มองเห็นได้ก็ยังคลิกไม่เปิด) `observed_button_visible` และเพื่อนบอกแค่การมองเห็น
   ไม่เคยอ้างเรื่องคลิก
3. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/`scenarios/world_*.json`/
   `scenarios/combat_*.json` เลยรอบนี้ ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มีการประกาศ
   milestone จากผลที่ได้ด้วย GM
4. warp ด้วย GM ไปเกาะแล้วเห็นเกาะ ไม่ใช่ M2 ผ่าน -- ไม่มีการอ้าง milestone ใด ๆ ในรอบนี้
5. ไม่มี client image/จอในสภาพแวดล้อมนี้เหมือนทุกรอบ -- โค้ดที่เพิ่มรอบนี้เป็นการ codify ผลที่กะ1-A
   สังเกตมาแล้ว ไม่ใช่การยิงเฟรมใหม่หรือสังเกตใหม่จากรอบนี้เอง

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

ผู้เทสที่ไล่ `RE-164` ข้อ 1/3 ต่อ (connection-context / current-UI object-key) สามารถเรียก
`bt_gm_probe.guaranteed_visible_variant_ids()` เพื่อเลือก variant ที่รู้แล้วว่าปุ่ม `BT_GM` จะโชว์แน่ก่อน
เริ่มไล่ suspect ถัดไป แทนที่จะต้องเดาหรือเจอปุ่มหายกลางเซสชันโดยไม่รู้สาเหตุเหมือนก่อนหน้านี้ (เมื่อวาน
ต้องดูเอาเองว่าปุ่มโชว์ไหม วันนี้มีตารางที่ยืนยันแล้วให้เลือกได้ตรง ๆ)

### PR

- `pf_bridge#581` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle)
- `pirate-force-server#373` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle + wake-gate commit)

— สาย GM รอบ `szmgeh`

## รอบ `oykcib` (2026-08-31T10:1x+07:00) — verify-only, backlog สี่ทางว่างเหมือนรอบ `szmgeh`

### สรุป

ตรวจกล่องจดหมาย + backlog สี่ทางสดใหม่ (ไม่เชื่อผลรอบก่อน): ไม่มีจดหมาย `ADDRESSEE: LANE-GM` ค้าง, ไม่มี
CORE-REQUEST/COO-DECISION ใหม่อ้างเลข `GM-0xx`, `GT-164` ปิดหัวใบแล้วไม่มีใบ GT อื่นของสาย GM ค้าง, ไม่มี
technical debt ใหม่ใน `gm/` (`grep TODO/FIXME/XXX/HACK` สดรอบนี้ = สองรายการเดิมที่ไม่ใช่ debt จริง)
`RE-164` ข้อ 1/3 ยังบล็อกด้วยเหตุผลเดียวกับที่ `COO-DECISION 20260831_0745` วินิจฉัยไปแล้วว่าเป็นบล็อกนอกเขต
(ต้องการ client binary image ระดับ VA หรือเซสชัน attended จริง) ตามคำสั่ง COO ("ไม่ต้องยื่นใบใหม่จนกว่า
สภาพเปลี่ยน") รอบนี้จึงไม่เปิด ASK-COO ซ้ำ เขียนใบ STATUS แทน

ไม่มีไฟล์ `src/`/`tests/`/`scenarios/` เปลี่ยนรอบนี้ทั้งสอง repo — รายละเอียดเต็มอยู่ที่ `pf_bridge`
`rounds/GM_20260831_1018_verify_only_backlog_still_empty_re164_external_blockers_unchanged.md`

### เขียว

`pytest tests/test_gm_*.py -q` (HEAD ปัจจุบัน, รันจริงรอบนี้): 1089 passed, 500 subtests เขียว(cloud
sanity) — ตัวเลขเดียวกับรอบ `szmgeh` ไม่มี drift

### nonclaim

ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่มีจอ/client image ในสภาพแวดล้อมนี้ `RE-164` ข้อ 1/3 ยังไม่ปิด
ไม่มีความคืบหน้าใหม่ (verify-only ตามเจตนา) ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
`scenarios/world_*.json`/`scenarios/combat_*.json` ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มี
การประกาศ milestone จากผลที่ได้ด้วย GM `gm/attr_wire.py` ยัง shelve ตาม `COO-DECISION 20260831_0350`
เหมือนเดิม

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบ verify-only ล้วน ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยนจากตอนจบรอบ `szmgeh`

### PR

- `pf_bridge#585` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle)
- `pirate-force-server#376` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle + wake-gate commit)

— สาย GM รอบ `oykcib`

## รอบ `qy8vln` (2026-08-31T11:18+07:00) — verify-only, backlog สี่ทางว่างเหมือนรอบ `oykcib`

### สรุป

ตรวจกล่องจดหมาย + backlog สี่ทางสดใหม่ (ไม่เชื่อผลรอบก่อน แม้ห่างกันแค่ ~1 ชั่วโมง): ไม่มีจดหมาย
`ADDRESSEE: LANE-GM` ค้าง (RE-088..091 มี `.CONSUMED.txt` ครบแล้ว), ไม่มี CORE-REQUEST/COO-DECISION ใหม่
อ้างเลข `GM-0xx` ที่ยังไม่บริโภค (3 ไฟล์ที่ grep เจอเป็น cc FYI ถึง COO/ATTENDED เนื้อหา `GM-042` consume
ไปแล้ว), `GT-164` ปิดหัวใบแล้วไม่มีใบ GT อื่นของสาย GM ค้าง, ไม่มี technical debt ใหม่ใน `gm/` (`grep
TODO/FIXME/XXX/HACK` สดรอบนี้ = สองรายการเดิมที่ไม่ใช่ debt จริง) `RE-164` ข้อ 1/3 ยังบล็อกด้วยเหตุผลเดียว
กับที่ `COO-DECISION 20260831_0745` วินิจฉัยไปแล้วว่าเป็นบล็อกนอกเขต (ต้องการ client binary image ระดับ VA
หรือเซสชัน attended จริง) ตามคำสั่ง COO ("ไม่ต้องยื่นใบใหม่จนกว่าสภาพเปลี่ยน") รอบนี้จึงไม่เปิด ASK-COO ซ้ำ
เขียนใบ STATUS แทน

ไม่มีไฟล์ `src/`/`tests/`/`scenarios/` เปลี่ยนรอบนี้ทั้งสอง repo — รายละเอียดเต็มอยู่ที่ `pf_bridge`
`rounds/GM_20260831_1118_verify_only_backlog_still_empty_matches_oykcib.md`

### เขียว

`pytest tests/test_gm_*.py -q` (HEAD ปัจจุบัน, รันจริงรอบนี้): 1089 passed, 500 subtests เขียว(cloud
sanity) — ตัวเลขเดียวกับรอบ `oykcib` ไม่มี drift

### nonclaim

ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่มีจอ/client image ในสภาพแวดล้อมนี้ `RE-164` ข้อ 1/3 ยังไม่ปิด
ไม่มีความคืบหน้าใหม่ (verify-only ตามเจตนา) ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
`scenarios/world_*.json`/`scenarios/combat_*.json` ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มี
การประกาศ milestone จากผลที่ได้ด้วย GM `gm/attr_wire.py` ยัง shelve ตาม `COO-DECISION 20260831_0350`
เหมือนเดิม

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบ verify-only ล้วน ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยนจากตอนจบรอบ `oykcib`

### PR

- `pf_bridge#588` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle)
- `pirate-force-server#378` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready + retitle + wake-gate commit)

— สาย GM รอบ `qy8vln`

## รอบ `x9wq3r` (2026-08-31T13:28+07:00) — verify-only ครั้งที่ 5 ติดกัน + ยืนยันซ้ำ MCP undraft

### สรุป

ตรวจกล่องจดหมาย + backlog สี่ทางสดใหม่ (ไม่เชื่อผลรอบก่อน): สภาพยังเหมือนรอบ `ep8v23` ทุกประการ — นี่คือ
รอบ verify-only ที่ 5 ติดกัน (`szmgeh`, `oykcib`, `qy8vln`, `ep8v23`, `x9wq3r`) นับตั้งแต่
`COO-DECISION 20260831_0745` วินิจฉัยว่า `RE-164` ข้อ 1/3 เป็นบล็อกนอกเขต (ต้องการ client binary image
ระดับ VA หรือ attended session จริง ไม่มีทั้งคู่ในสภาพแวดล้อมคลาวด์นี้) `GM-042`/`GT-128` ยังเป็นลูกบอลของ
chief ตามคำสั่ง COO ("ไม่ต้องยื่นใบใหม่จนกว่าสภาพเปลี่ยน") รอบนี้จึงไม่เปิด ASK-COO ซ้ำ

งานจริงของรอบนี้: อ่านกล่องจดหมายพบ `20260831_1242_KA1A-CORRECTION-*.md` ขอการยืนยันครั้งที่สองของวิธี
`update_pull_request(draft=false)` (MCP tool) — รอบนี้เรียกกับ `pf_bridge#598` และ `pirate-force-server#386`
แล้ว `pull_request_read get` ยืนยัน `draft:false` สดทั้งคู่ทันที ทั้งสองใบยัง merge ไม่สำเร็จภายในรอบนี้
(`mergeable_state: unstable` ตอน GET — CI ยังไม่จบ) นี่เป็นการยืนยันครั้งที่สองจากสายที่ไม่ใช่สาย A

ไม่มีไฟล์ `src/`/`tests/`/`scenarios/` เปลี่ยนรอบนี้ทั้งสอง repo — รายละเอียดเต็มอยู่ที่ `pf_bridge`
`rounds/GM_20260831_1328_verify_only_fifth_round_plus_mcp_undraft_second_confirmation.md`

### เขียว

`pytest tests/test_gm_*.py -q` (HEAD ปัจจุบัน, รันจริงรอบนี้): 1089 passed, 504 subtests เขียว(cloud
sanity) — ตัวเลขเดียวกับรอบ `ep8v23` ไม่มี drift

### nonclaim

ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่มีจอ/client image ในสภาพแวดล้อมนี้ `RE-164` ข้อ 1/3 ยังไม่ปิด
ไม่มีความคืบหน้าใหม่ (verify-only ตามเจตนา) ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
`scenarios/world_*.json`/`scenarios/combat_*.json` ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มี
การประกาศ milestone จากผลที่ได้ด้วย GM การยืนยัน MCP undraft รอบนี้เป็นตัวอย่างที่สองเท่านั้น ไม่ใช่การพิสูจน์
ว่าใช้ได้ 100% ของทุกกรณี

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบ verify-only ล้วน ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยนจากตอนจบรอบ `ep8v23`

### PR

- `pf_bridge#598` (draft ต้นรอบ ปลด draft ด้วย MCP `update_pull_request` ระหว่างรอบ ไม่ใช่ท้ายรอบ — ทดสอบ
  วิธีการเป็นเป้าหมายหลักของรอบ)
- `pirate-force-server#386` (เดียวกัน + wake-gate commit ท้ายรอบ)

— สาย GM รอบ `x9wq3r`

## รอบ `u2ulkl` (2026-08-31T14:25+07:00) — verify-only ครั้งที่ 6 ติดกัน + ใช้โปรโตคอลล็อกรอบฉบับล่าสุด

### สรุป

ตรวจกล่องจดหมาย + backlog สี่ทางสดใหม่: สภาพยังเหมือนรอบ `x9wq3r` ทุกประการ — `RE-164` ข้อ 1/3 ยังบล็อก
นอกเขต (client binary VA-level หรือ attended session, ไม่มีในสภาพแวดล้อมคลาวด์นี้), `GM-042` รอคำตัดสิน
ระดับเจ้าของสองข้อตาม `CHIEF-REPLY 20260831_0204`, `gm/attr_wire.py` shelved ยืนยันซ้ำโดย
`COO-DECISION 20260831_1244` (ไม่มีเงื่อนไขใหม่)

พบว่ากล่องจดหมายมีการแก้ไขซ้อนหลังใบ `20260831_1230_PANYA-ORDER-*` (เปลี่ยนตัวล็อกรอบเป็น marker):
`20260831_1242_KA1A-CORRECTION-*` ถอนข้อเสนอนั้นทั้งหมดเพราะพิสูจน์แล้วว่าเอเจนต์ปลด draft ได้จริงด้วย
GitHub MCP tool `update_pull_request(draft=false)` (`pirate-force-server#374`) รอบนี้จึงใช้โปรโตคอล
draft-flag + MCP-undraft (ของเดิม/ฉบับแก้) ไม่ใช่ marker-lock ของใบ 1230 ที่ถูกถอนไปก่อนมีใครใช้จริง —
รายละเอียดลำดับเวลาเต็มอยู่ใน round file

ประเมิน gap ที่เห็นใน `bt_gm_probe.py` (field_0x14 bit 8-31 ยังไม่ครอบ) แล้วตัดสินใจ **ไม่ทำ** — `GT-164`
วัดแล้วว่า field นี้ไม่มีผลต่อการมองเห็นปุ่มเลยตลอด 9 ค่าที่ทดสอบรวม boundary สูงสุด และใบผลเดียวกันเสนอ
ให้รอบถัดไปเปลี่ยนสิ่งที่แวดล้อมการคลิกแทนการเปลี่ยนค่าในเฟรม การขยาย sweep เพิ่มจะเป็น busywork ไม่ใช่
ทางออกจากบล็อกจริง เหตุผลเต็มบันทึกไว้ใน round file กันรอบหน้าต้องไล่ประเมินซ้ำ

ไม่มีไฟล์ `src/`/`tests/` เปลี่ยนรอบนี้ — รายละเอียดเต็มอยู่ที่ `pf_bridge`
`rounds/GM_20260831_1425_verify_only_6th_round_protocol_correction_applied.md`

### เขียว

`pytest tests/test_gm_*.py -q` (HEAD ปัจจุบัน, รันจริงรอบนี้): 1089 passed, 504 subtests เขียว(cloud
sanity) — ตัวเลขเดียวกับรอบ `x9wq3r` ไม่มี drift

### nonclaim

ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่มีจอ/client image ในสภาพแวดล้อมนี้ `RE-164` ข้อ 1/3 ยังไม่ปิด
ไม่มีความคืบหน้าใหม่ (verify-only ตามเจตนา) ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
`scenarios/world_*.json`/`scenarios/combat_*.json` ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มี
การประกาศ milestone จากผลที่ได้ด้วย GM การตัดสินใจไม่ขยาย field_0x14 bit-sweep เป็นการอ่านหลักฐานเดิม
เท่านั้น ไม่มีการยิงเฟรมยืนยันเพิ่ม ไม่อ้างว่าโปรโตคอลล็อกรอบที่ใช้รอบนี้เป็นทางที่เจ้าของยืนยันขั้นสุดท้าย
แล้ว (`CHIEF-ASK-PANYA 1256` เสนอถ้อยคำ prompt ไว้ ยังไม่เห็นใบยืนยันว่ากดรับ)

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบ verify-only ล้วน ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยนจากตอนจบรอบ `x9wq3r`

### PR

- `pf_bridge#602` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready ด้วย MCP `update_pull_request(draft=false)` +
  retitle)
- `pirate-force-server#389` (เดียวกัน + wake-gate commit ท้ายรอบ)

— สาย GM รอบ `u2ulkl`

## รอบ `xxsulh` (2026-08-31T15:23+07:00) — verify-only ครั้งที่ 7 ติดกัน

### สรุป

ตรวจกล่องจดหมาย + backlog สี่ทางสดใหม่: สภาพยังเหมือนรอบ `u2ulkl` ทุกประการ — `RE-164` ข้อ 1/3 ยังบล็อก
นอกเขต, `GM-042` รอคำตัดสินระดับเจ้าของสองข้อตาม `CHIEF-REPLY 20260831_0204`, `gm/attr_wire.py` shelved
ยืนยันซ้ำ ไม่มีเงื่อนไขใหม่

เจอใบสองฉบับของสาย E ใหม่กว่ารอบก่อน (`20260831_1435_KA1A-NOTE-*`, `20260831_1436_KA1A-ASK-COO-*` เรื่อง
GT-106-R2/warp cross-scene gate) ที่อ้างถึงบล็อกสามเรื่องของสาย GM เป็น nonclaim ของสาย E เอง — อ่านแล้ว
ยืนยันว่าไม่ใช่คำตัดสินใหม่ที่ปลดบล็อกสาย GM แต่อย่างใด

ไม่มีไฟล์ `src/`/`tests/` เปลี่ยนรอบนี้ — รายละเอียดเต็มอยู่ที่ `pf_bridge`
`rounds/GM_20260831_1523_verify_only_7th_round_no_new_conditions.md`

### เขียว

`pytest tests/test_gm_*.py -q` (origin/main สด HEAD `2d890aa1`, รันจริงรอบนี้): 1089 passed, 504 subtests
เขียว(cloud sanity) — ตัวเลขเดียวกับรอบ `u2ulkl` ไม่มี drift

### nonclaim

ไม่ได้ยิงเฟรมใด ๆ ใส่ client จริงรอบนี้ ไม่มีจอ/client image ในสภาพแวดล้อมนี้ `RE-164` ข้อ 1/3 ยังไม่ปิด
ไม่มีความคืบหน้าใหม่ (verify-only ตามเจตนา) ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
`scenarios/world_*.json`/`scenarios/combat_*.json` ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts` ไม่มี
การประกาศ milestone จากผลที่ได้ด้วย GM ใบสองฉบับของสาย E ที่อ้างถึงบล็อกสาย GM ไม่ถือเป็นเงื่อนไขใหม่
(ใบทั้งสองระบุ nonclaim ของตัวเองตรง ๆ ว่าไม่ปลดบล็อกสาย GM)

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** — รอบ verify-only ล้วน ไม่มีจุดเสียบใหม่ ไม่มี behavior เปลี่ยนจากตอนจบรอบ `u2ulkl`

### PR

- `pf_bridge#608` (draft ต้นรอบ ปิดท้ายรอบนี้เป็น ready ด้วย MCP `update_pull_request(draft=false)` +
  retitle)
- `pirate-force-server#393` (เดียวกัน + wake-gate commit ท้ายรอบ)

— สาย GM รอบ `xxsulh`

## รอบ `fftpji` (2026-08-31T16:40+07:00) — ปลดล็อก `/warp` ข้ามฉากยิง live teleport ตาม COO-DECISION 1441

### สรุป

กล่องจดหมายมีงานจริง: `20260831_1441_COO-DECISION-warp-cross-scene-opens-gt106r2-passed.md` (ตัดสินตรง)
กับ `20260831_1555_KA1A-TO-LANE-GM-*` (ใบเตือนว่ารอบ `xxsulh` ค้นไม่เจอเพราะขอบเขตการค้นผูกกับหัวข้อเดิม
สามอัน — `1441` เป็นหัวข้อที่สี่) `GT-106-R2` ผ่านจริง (`OBSERVER_CONFIRMED 2026-08-31T10:0x+07:00`, scene
17, X=834 Y=-598) และ COO เปิดทางเลือก 1: เปลี่ยน `/warp` ข้ามฉาก (ที่มีพิกัด) จาก stage-รอ-login-หน้า
ไปยิง `legacy.make_login_teleport` จริงกลางเซสชัน

**โค้ดที่เปลี่ยน** (ทั้งสามไฟล์อยู่ในเขตสาย GM ล้วน ไม่แตะ `runtime.py`/`app.py`/
`pf_login_game_server_v141.py` เลย — ตรวจเส้นทางส่งจริงก่อนเขียนโค้ดแล้วพบว่า `chat_command_action.py`
มีท่อส่ง `(label, pc, frame, delay)` -> `runtime.py`'s action list อยู่แล้วสำหรับทุกคำสั่ง GM จึงไม่ต้องขอ
CORE-REQUEST-GM-044 ใด ๆ):

1. `gm/warp_executor.py` — เพิ่ม `make_warp_teleport_frame_with_target` (คอมโพสเซอร์ใหม่ ยิงผ่าน
   `legacy.make_login_teleport(scene_id, population.SCENE_SEQUENCE, x, y, z)` ตัวเดียวกับที่
   `runtime.py` ใช้จริงอยู่แล้วสามจุด — Columbus dispatch, world-travel-gate crossing, scene-load path
   — ไม่แตะ field ที่ยังไม่พิสูจน์ของ `teleport_wire.py`'s general TeleportVital builder เลย) เพิ่ม
   `WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED = True` (ธงนโยบายที่อ้าง COO-DECISION 1441 ตรง ๆ
   ไม่ใช่ธงรอ RE เหมือน `FORCE_POS_VITAL_VERSION_CONFIRMED`) เกตด้วย `scene_catalog.is_known_scene_id`
   เท่านั้น (ไม่ใช้ `login_scene_admission` ซึ่งเป็นกฎของกลไก login คนละกลไก — วัดแล้วว่าฉาก 17 เอง
   `is_known_scene_id`=True แต่ `single_use_entry_is_admissible`=False ถ้าเกตผิดตารางจะปฏิเสธปลายทาง
   เดียวที่มีหลักฐานจริงของรอบนี้) อัปเดต docstring ของ `WarpTarget` ให้ระบุว่า `scene_id` หมายถึงฉาก
   ปัจจุบัน (ForcePos) หรือฉากปลายทาง (TeleportVital) แล้วแต่คอมโพสเซอร์ไหนสร้าง
2. `gm/chat_command_action.py` — `_warp_action` เพิ่มกิ่งที่สาม: ข้ามฉาก + มีพิกัด + ธงเปิด ->
   `_warp_teleport_action` (ฟังก์ชันใหม่ คืน action label ใหม่ `WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL =
   "LANE_GM_CHAT_WARP_CROSS_SCENE_TELEPORT_VITAL"` มีคำว่า TELEPORT ตามกฎ move-authority substring เดิม)
   ข้ามฉาก + ไม่มีพิกัด ยังคง stage เหมือนเดิมทุกประการ (ไม่มีกลไกไหนมีตำแหน่งให้ส่งสำหรับรูปแบบนี้)
   จุดพัก warp target (`record_warp_target`) และจุดล้าง target เมื่อ audit row เขียนไม่สำเร็จ ครอบทั้งสอง
   label แล้ว
3. `gm/login_scene_stage.py` — แก้ป้าย `[สมมติของสาย GM - รอ COO ยืนยัน]` ที่ "THE IDENTITY LIMIT" ตาม
   แบบ `login_scene_admission.py` (ขีดฆ่า + อ้าง COO-DECISION 1441) แตะเฉพาะป้ายนั้น เนื้อหาที่เหลือของ
   ย่อหน้าไม่เปลี่ยน (ช่องโหว่ identity เดิมยังเปิดอยู่ตามที่ใบนั้นยืนยัน)

**สิ่งที่ยังไม่เปลี่ยน (ตั้งใจ)**: `warp <scene_id>` ไม่มีพิกัดยัง stage เหมือนเดิม, `ForcePos` (same-scene)
ยังทำงานเหมือนเดิมทุกประการ, ไม่มีการเช็ค census/actor ของฉากปลายทาง (ช่องโหว่เดิมของ RE-162 ที่แม้แต่
Columbus dispatch เองก็ไม่ปิด), ไม่มีการเช็ค range พิกัด (ช่องโหว่เดิมที่ระบุไว้ใน `chat_command_action.py`
อยู่แล้วก่อนรอบนี้)

### pf-adversary

**Agent tool ไม่มีในสภาพแวดล้อมนี้จริง** — ตรวจด้วย `ToolSearch` หลายคำค้น (`Agent`, `Task`,
`pf-adversary`) และ `ListAgents` แล้วไม่พบเครื่องมือสำหรับ spawn subagent ชนิดนี้เลย ไม่ใช่การเลือกข้าม
ทำ **self-adversarial review แทน** อย่างจริงจังต่อ diff จริงของรอบนี้ (ไม่ใช่แค่ตรวจเอกสารเหมือนรอบ
verify-only ก่อนหน้า) พบและแก้ 1 ข้อ ก่อน commit:

- **line-number rot** — ร่างแรกของ docstring `warp_executor.py` อ้าง `runtime.py:5050`/`:7223`/
  `:6643`/`:6647` ตรง ๆ ขัดกับกฎที่ `chat_command_action.py` เขียนไว้เองแล้ว ("!! NO LINE NUMBERS FOR
  FILES THIS LANE DOES NOT OWN" — เคยรอบ 5107->5168/5173 ผิดสองครั้งในวันเดียว) แก้เป็นอ้าง anchor text
  ที่ grep เจอแทน (`_dispatch_columbus_quest3021`, `departure.confirmed_fields()`,
  `SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE`/`V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE`)
- เพิ่มเทสคู่ ASCII/TELEPORT-substring ให้ label ใหม่ (`ContractTests` ใน
  `test_gm_chat_command_action.py`) หลังตรวจว่ามีคู่ของ `WARP_ACTION_LABEL` อยู่แล้วแต่ label ใหม่ยังไม่
  มีคู่เดียวกัน
- ตรวจ routing order, WarpTarget cross-scene semantics ผ่าน `distance_to_target`'s scene-mismatch
  handling (ออกแบบมารองรับ cross-scene อยู่แล้วโดยไม่ต้องแก้ `warp_target_record.py`), และ two-read
  args threat model (เหมือนที่ ForcePos path มีอยู่แล้ว ไม่ใช่ช่องโหว่ใหม่) — ไม่พบข้อบกพร่องเพิ่ม

### เขียว

`python3 -m pytest tests/test_gm_*.py -q`: **1104 passed, 509 subtests** เขียว (จาก 1089/504 ก่อนรอบ —
เพิ่ม 15 เทสใหม่: 7 ใน `test_gm_warp_executor.py`, ที่เหลือใน `test_gm_chat_command_action.py`/
`test_gm_chat_no_bytes_line.py`/`test_gm_command_audit_outcome.py` ที่ต้องแก้ให้ตรงพฤติกรรมใหม่)

`python3 -m pytest tests/ -q` (ทั้ง repo): **5754 passed, 327 skipped, 10709 subtests** เขียว ไม่มี
ไฟล์อื่นนอกเขตพัง

### nonclaim

1. **ไม่อ้าง client-observable PASS ของ `/warp` เอง** — สภาพแวดล้อมนี้ไม่มี client เกม หลักฐานที่มีคือ
   proof เชิงเฟรม (headless): bytes ที่ `_warp_teleport_action` คืนตรงกับ `legacy.make_login_teleport`
   ทุกไบต์ และ label/ท่อส่งเดียวกับที่ ForcePos ใช้อยู่แล้ว — พิสูจน์ว่า bytes ออกไปถูกรูปถูกท่อ ไม่ใช่ว่า
   client เห็นอะไร
2. `GT-106-R2` พิสูจน์ฉาก 17 ผ่าน call site อื่น (`_dispatch_columbus_quest3021`, พิกัดคงที่) ไม่ใช่ผ่าน
   `/warp` — นี่เป็นครั้งแรกที่ `/warp` เองยิง live cross-scene ปลายทางทุกปลาย **รวมฉาก 17** ยังไม่เคยผ่าน
   การเทส attended จริงผ่านคำสั่งนี้เอง ตามกฎ G-OBS ทุกปลายทางใหม่ต้องเทส attended ก่อนประกาศ PASS
3. ไม่ปิดช่องว่าง census/actor ของฉากปลายทางที่ RE-162 พบ (ไม่มีเจ้าของ ไม่ใช่งานของ wire-builder)
4. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py` เลย ไม่ต้องเปิด CORE-REQUEST-GM-044
   (ตรวจแล้วว่าท่อส่งเดิมพอ)
5. ไม่ปลด `RE-164` ข้อ 1/3, `GM-042`, หรือ `attr_wire.py` — ยังติดเหตุผลเดิมทั้งสาม ไม่ใช่ขอบเขตรอบนี้
6. ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts.json` — allowlist check เดิมไม่เปลี่ยน

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

`/warp <scene_id> x y` ที่ตั้งชื่อฉากอื่น (ไม่ใช่ฉากปัจจุบัน) และฉากนั้นอยู่ใน `scene_catalog.py` จะยิง
`TeleportVital` จริงกลางเซสชันแทนการ stage รอ login หน้า — ยังไม่มีใครยืนยัน client-observable ว่าจอ
เปลี่ยนจริงผ่านคำสั่งนี้ (ดู nonclaim ข้อ 2) คิวเทส attended ใหม่อยู่ที่ `pf_bridge/GAME_TEST_QUEUE.md`

### PR

- `pf_bridge#613` (ล็อกรอบเดิม ปิดท้ายรอบนี้เป็น ready ด้วย MCP `update_pull_request` + retitle)
- `pirate-force-server#398` (เดียวกัน + wake-gate commit ท้ายรอบ)

— สาย GM รอบ `fftpji`

## Round `rawblk` -- `gm/attr_wire.py`: the composer + cache, and the raw-block-source question this module does NOT claim to have answered

`COO-DECISION 2026-08-31T16:50+07:00` (`pf_bridge/notes_to_chief/20260831_1650_COO-DECISION-attr-wire-
unlock-condition-revised-name-all-24-fields-replaced-with-lossless-preserve.md`) relaxed the shelved
`attr_wire.py` unlock condition from "name all 24 remaining fields" to "cover every NAMED field, preserve
every unnamed one losslessly", and asked this lane to "design and prove the raw-block-per-connection
mechanism ... before asking for a version-confirmation unlock" -- this round is that design-and-prove
step, not a live-send unlock.

### สิ่งที่สร้าง

- `src/pirateforce_foundation/gm/attr_wire.py` -- new module: the 55-row `FIELDS` table (12 BasicAttr +
  43 ActorAttr, re-derived in this lane's own zone from the owner's proven `reference_adhoc_probe`
  session -- 266 commands, 2h20m, one connection, no crash), `encode_field`/`encode_block`/
  `make_update_attr_frame` (pure composer, no send), `RawBlockCache` (per-connection memory, deliberately
  source-agnostic), and `build_named_field_update` (the one entry point a future chat command should
  call -- refuses unknown `x`, refuses `SENSITIVE_FIELDS` (x=30, an unadjudicated Codex-corpus semantic
  note names this offset as a password-hash-adjacent field), refuses every `known=False` field, and
  refuses outright if the cache was never seeded).
- `tests/test_gm_attr_wire.py` -- 46 tests: field-table shape/mask-bit integrity, byte-exact composer
  tests against a real loaded `legacy` module, `RawBlockCache` capture/merge/lossless-preserve behavior,
  every refusal path, and every individually known field round-tripping through the real composer.
- `UPDATE_ATTR_VITAL_VERSION_CONFIRMED: int | None = None` -- unchanged this round, same shape as
  `teleport_wire`/`say_wire`'s own gates.

### สิ่งที่ยังไม่ทำ, ตั้งใจ

- **No chat command dispatches into this module.** `/lv` still parses in `gm/commands.py` (owner-original
  command) but has no action function in `chat_command_action.py` -- wiring it is next round's job, once
  the question below has an answer, not this round's.
- **No DB persistence.** `COO-DECISION 0146` condition (b) (survive relog) is untouched -- `model.Character`
  still carries no level/hp/stat columns at all (checked again this round, same finding as the `0330`
  ASK-COO letter).
- **No live send.** The gate stays `None`.

### The open question this round surfaces, precisely (not solved, not guessed at)

The probe's own docstring claims "a sparse delta would zero what it omits" (static read of the client's
0x464F30 bulk-copy apply) -- if true, "preserve unknown fields losslessly" requires supplying their real
current value on EVERY send, not merely omitting them. Searched before writing code (ค้นก่อนถอด):
`model.Character` has nothing to read (identity/name/position/wire blobs only, no stats). `characters.
actor_wire` (`migrations/001_initial.sql`) IS a real per-character byte-preserved BLOB, but it is
`CreateActorDataEx` -- a different vital/codec from this module's `UpdateAttrVital` DBAttribute shape.
Whether its embedded sub-structure shares this table's tag/offset layout is an open, answerable, STATIC
question -- if yes, that BLOB is a ready-made raw-block source needing zero `runtime.py` changes; if no,
there is no source at all today, and a `lane_hooks` point would be asking for data that provably does not
exist yet (checked, and NOT opened this round for that reason). Routed to chief/RE:
`CORE-REQUEST-GM-044` (`pf_bridge/notes_to_chief/`).

### This round's provisional decision, tagged for COO

`[สมมติของสาย GM - รอ COO ยืนยัน]` Until the question above is answered, `build_named_field_update`
refuses to ever set a mask bit for any `known=False` field -- this bounds the module's claim to exactly
what COO's revised wording named ("every field with a confirmed name"), and does not resolve whether the
very first named-field send on a non-fresh character would still zero the unnamed fields once (documented
risk, named again in the CORE-REQUEST letter, a COO/owner call).

### pf-adversary

**Agent tool ไม่มีในสภาพแวดล้อมนี้จริง** -- ตรวจด้วย `ToolSearch` (คำค้น "Agent subagent spawn Task
pf-adversary" และ "select:ListAgents") แล้วไม่พบเครื่องมือสำหรับ spawn subagent ชนิดนี้เลย ตรงกับที่ทุก
รอบก่อนหน้าของสายนี้พบเหมือนกัน ทำ **self-adversarial review แทน** อย่างจริงจังต่อ diff จริง พบและแก้ 1
ข้อก่อน commit:

- **field 37 (`wstr_164_guild`) transcription error** -- ตารางต้นทาง (`reference_adhoc_probe/
  adhoc_attr_probe.py`) ติดป้ายแถวนี้ `[รู้]` (known) ชัดเจน แต่ร่างแรกของ `FIELDS` ในโมดูลนี้ใส่
  `known=False` ผิดพลาด (สับสนกับแถวข้างเคียงที่เป็น `[รู้บางส่วน]`) -- ตรวจซ้ำทุกแถวทั้ง 55 รายการเทียบ
  กับต้นฉบับทีละแถวแล้วพบมีจุดเดียว แก้เป็น `known=True` ตามต้นฉบับ

ตรวจเพิ่มเติมที่ไม่พบข้อบกพร่อง: ลำดับการเช็ค `SENSITIVE_FIELDS` มาก่อน `known` ใน
`build_named_field_update` (กันไม่ให้ future round เปิด `known=True` ให้ x=30 โดยไม่ได้ตั้งใจแล้วข้าม
การเช็ค sensitive), `RawBlockCache.merged_with` ไม่ mutate `self._values` (มีเทสยืนยันแยก), และ
`encode_block`'s paired-bit refusal ไม่มีทางถูกข้ามจาก `build_named_field_update` เพราะ x=39/40/41/42
ทั้งสี่เป็น `known=False` ทั้งหมด (เข้าไม่ถึง `encode_block` ผ่านทางเข้านี้เลย)

### เขียว

`cd pirate-force-server && python3 -m pytest tests/test_gm_*.py -q`: **1150 passed, 511 subtests** เขียว
(จาก 1104/509 ก่อนรอบ -- เพิ่ม 46 เทสใหม่ทั้งหมดใน `test_gm_attr_wire.py`, ศูนย์เทสเดิมถูกแก้)

`python3 -m pytest tests/ -q` (ทั้ง repo): **5803 passed, 327 skipped, 10713 subtests** เขียว (จาก
5754/327/10709 ก่อนรอบ -- ส่วนต่างตรงกับ 46 เทสใหม่ + ขยาย subtests เล็กน้อย ไม่มีไฟล์นอกเขตพัง)

### nonclaim

1. ไม่อ้างว่าปลดล็อกอะไร -- `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` ยังเป็น `None`, ไม่มีจุดเรียกใด (ไม่ใช่
   แค่เทสของโมดูลเอง) ที่ส่งไบต์จริงได้
2. ไม่อ้างว่าตอบคำถาม "omission = zero จริงไหม" ได้ -- เป็นแค่ static claim ของ probe เอง (v141 note
   0x464F30) ไม่เคยมีการวัด client-observable กับค่าที่ไม่ใช่ศูนย์มาก่อนจริง ๆ (ทุกเซสชัน probe เริ่มจาก
   ตัวละครสร้างใหม่)
3. ไม่อ้างว่า `characters.actor_wire` มี/ไม่มี sub-structure ตรงกับ `FIELDS` -- คำถามเปิด ส่งให้ RE ผ่าน
   `CORE-REQUEST-GM-044`
4. ไม่อ้างว่า x=30 คือรหัสผ่านแน่นอน -- อ้างจาก corpus ที่ยังมีไฟล์ `CONFLICTS`/`UNRESOLVED_BUCKETS` เปิด
   อยู่ (ยังไม่ adjudicate) แต่ปฏิเสธการเขียนอยู่ดีเพราะเป็นการเดาที่แพงถ้าผิด (fail-closed ฝั่งความ
   ปลอดภัย ไม่ใช่ฝั่งความสมบูรณ์)
5. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`, `scenarios/world_*.json`,
   `scenarios/combat_*.json`, หรือ canonical DB เลยสักไบต์
6. ไม่ให้สถานะ GM กับบัญชีที่ไม่อยู่ใน `gm_accounts.json` -- ไม่เกี่ยวข้องกับรอบนี้เลย ไม่มีจุดแตะ
   allowlist ในโมดูลนี้
7. ไม่ประกาศ milestone หรือ "attr_wire พร้อมใช้งาน" จากรอบนี้ -- นี่คือ groundwork หนึ่งขั้น ไม่ใช่ของที่
   เทสได้

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ยังไม่มีอะไรที่ผู้เทสทำได้ต่างไปจากเมื่อวาน** -- ไม่มีคำสั่งแชทใหม่ ไม่มีการส่งไบต์จริง รอบนี้เป็น
groundwork ล้วน (composer + cache + เทส) ตามที่ COO สั่งให้ "ออกแบบและพิสูจน์กลไกก่อน" ไม่ใช่รอบปลดล็อก

### PR

- `pf_bridge#617` (ล็อกรอบ)
- `pirate-force-server#401` (โมดูลนี้ + เทส + wake-gate commit ท้ายรอบ)

— สาย GM รอบ `rawblk`

## รอบ `1gia62` (2026-08-31T18:25+07:00) -- GM-044 ตอบลบ, เปิด ASK-COO นโยบาย + RE-172, ไม่มีการแก้ src รอบนี้

`CORE-REQUEST-GM-044` ตอบแล้ว: `characters.actor_wire` (`CreateActorDataEx`) เป็น `AvatarAttr` คนละคลาส
กับ `ActorAttr`/`BasicAttr` ที่ `gm/attr_wire.py::FIELDS` ใช้ (tag/width ต่างกันสามทาง, ตรวจข้าม 3 แหล่ง
อิสระ) -- ไม่มีแหล่ง "บล็อกดิบปัจจุบันจริง" ให้ `RawBlockCache` seed ได้วันนี้ ตามที่ round `rawblk`
ประกาศไว้ล่วงหน้าว่าจะทำถ้าคำตอบเป็นลบ: เปิด `pf_bridge/notes_to_chief/20260831_1825_LANE-GM-ASK-COO-
attr-wire-raw-block-source-policy-after-gm044-negative.md` (สามทาง: หาแหล่งดิบอื่น / ยอมรับความเสี่ยง
เคลียร์ฟิลด์ไม่รู้จัก / จำกัดถาวรเฉพาะฟิลด์มีชื่อ) และ `pf_bridge/CLIENT_RE_QUEUE.md` `RE-172` (ถามหา
แหล่งดิบอื่นก่อนเคาะนโยบาย ตามข้อเสนอของ chief เอง)

**ไม่มีการแก้ `attr_wire.py`/`chat_command_action.py`/โค้ดอื่นในเขต `gm/` รอบนี้.** `build_named_field_update`
ยัง fail-closed เหมือนรอบ `rawblk` ทิ้งไว้ (ไม่มี seed = ไม่มีอะไรส่งได้) -- ไม่ใช่ช่องโหว่ เป็นเพดานที่
ตั้งใจไว้แล้ว รอบนี้จึงไม่มีอะไรให้ผู้เทสทำต่างจากเมื่อวาน

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260831_1825_1gia62_gm044_negative_ask_coo_policy.md`
PR: `pf_bridge#621`, `pirate-force-server#404` (นี้)

## รอบ `2uud3t` (2026-08-31T20:28+07:00) -- mailbox หนึ่งใบ (COO-DECISION), แก้หัวใบ GT-172 ที่ล้าสมัย, ยังไม่มีอะไรใหม่ให้เทส

`COO-DECISION 2026-08-31T18:43+07:00` (`pf_bridge/notes_to_chief/20260831_1843_COO-DECISION-attr-wire-
stay-path0-re172-decide-1-vs-2-only-if-negative.md`) บริโภคแล้ว: อนุมัติทาง 0 (รอ `RE-172`), ยืนยัน
`gm/attr_wire.py`'s fail-closed ปัจจุบันถูกต้อง, สั่งไม่ให้เปิดใบใหม่จนกว่า `RE-172` มีผล -- ตรวจแล้ว
`RE-172` ยังเปิดอยู่จริง ไม่มีผลให้บริโภครอบนี้ ไม่มีการเปิดใบใหม่ ตรงตามคำสั่ง

ตรวจทุกโมดูลในเขตของสายนี้หางานแก้โค้ดที่ทำได้จริง: `attr_wire.py` บล็อกที่ `RE-172`, `say_wire.py`
ล็อกโดย `COO-DECISION 20260829_0041` (ต้อง COO-DECISION ใหม่เท่านั้นถึงพลิกได้), `item`/`npc`/`spawn`
ยัง `OUTCOME_NO_WIRE_PATH` โดยตั้งใจ (โครงสร้างไบต์ของ `0x51E9`/`0x8C77` พิสูจน์แล้วโดย `RE-088` แต่
ความหมายฟิลด์ยัง `NOT_OBSERVED` -- ต้องจับเฟรมจริงจาก attended session ซึ่ง cloud นี้ทำไม่ได้)
`warp`/`gmprobe`/`stage` wired และ live แล้วจากรอบก่อน ไม่มีอะไรต้องแก้เพิ่ม

**ไม่มีการแก้ `src/`/`tests/`/`scenarios/*.json` รอบนี้ในเรโปนี้.** งานจริงของรอบนี้ (แก้หัวใบคิว
`GT-172` ที่เปิดเงื่อนไข "READY เมื่อ PR ของรอบ `fftpji` merge" ไว้ ซึ่งตอนนี้เป็นจริงแล้ว, ยืนยันด้วย
`pull_request_read` ต่อใบทั้งสอง) อยู่ใน `pf_bridge` แทน

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260831_2028_2uud3t_gt172_header_fix_re172_still_open.md`
PR: `pf_bridge#628`, `pirate-force-server#410` (นี้)

## รอบ `a10g3c` (2026-08-31T21:24+07:00) -- verify-only รอบที่ 9 ติดกัน, ไม่มีอะไรใหม่ให้บริโภคหรือแก้

mailbox: ไม่มีใบ `ADDRESSEE: LANE-GM` ที่ยังไม่บริโภค (ทุกใบมี `.CONSUMED.txt` คู่แล้วจากรอบก่อน ๆ)
`CLIENT_RE_QUEUE.md` `RE-172` ยัง `[OPEN -- assigned สาย GM]` ตรวจสดแล้ว ไม่มีผลใหม่ -- ตาม
`COO-DECISION 1843` ยังห้ามเปิดใบใหม่จนกว่าจะมีผล หัวใบ `GT-*` ของสายนี้ทุกใบตรงจริงแล้ว ไม่มีอะไร
stale ต้องแก้ (`GT-172` READY จากรอบก่อน, `GT-164` ปิดแล้ว)

ตรวจทุกโมดูลในเขตของสายนี้อีกครั้งสด ๆ (ไม่เชื่อบันทึกรอบก่อน): `attr_wire.py` บล็อกที่ `RE-172` (COO
สั่งห้ามเปิดใบใหม่), `say_wire.py` ล็อกโดย `COO-DECISION 20260829_0041` (grep หาใบใหม่กว่านั้นแล้วไม่พบ),
`item`/`npc`/`spawn` ยัง capture territory จริง (`command_capture.py`+`lane_gm_run_command.py` wired
พร้อมรับเฟรมอยู่แล้ว รอ attended จับเฟรมจริงเท่านั้น) `grep TODO/FIXME/XXX/HACK` สดใน `gm/*.py` = สอง
รายการเดิมที่ไม่ใช่ debt จริง ไม่มีรายการใหม่

**ไม่มีการแก้ `src/`/`tests/`/`scenarios/*.json` รอบนี้.** รอบก่อน (`2uud3t`) ไม่ใช่รอบว่างเปล่า (แก้หัว
ใบ `GT-172` จริง) รอบนี้เป็นรอบว่างจริงรอบแรกหลังจากนั้น ไม่ผิดกฎ F แต่บันทึกไว้ชัด: ถ้ารอบถัดไปก็ว่าง
อีก ต้องหยิบงานตามกฎ (ก)(ข)(ค)(ง) จริงจังกว่านี้

เขียว: `python3 -m pytest tests/test_gm_*.py -q` -> **1150 passed, 523 subtests** เขียว(cloud sanity)
ไม่เปลี่ยนจากก่อนรอบ (ไม่มีไฟล์เปลี่ยน)

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260831_2124_a10g3c_verify_only_9th_round_re172_still_open.md`
PR: `pf_bridge#632`, `pirate-force-server#414` (นี้)

## Round `thhkup` (2026-08-31T23:2x+07:00) -- RE-172 closed bounded-negative (own ticket, answered from committed static evidence), plus a reference codec for `CheatVital`

Mailbox this round carried two new letters addressed `ADDRESSEE: LANE-GM`
(`notes_to_chief/20260831_2305_KA1A-TO-LANE-GM-*` and its selfcorrection
follow-up `20260831_2315_KA1A-SELFCORRECTION-*`): the attended tester
pointed out that `RE-172` (`CLIENT_RE_QUEUE.md:3277`) is assigned to this
lane itself ("ผู้เปิดใบเป็นผู้บริโภคผล -- สาย GM เปิดเอง บริโภคผลเอง") and
its own pass criteria says both questions are answerable from static source
already committed to this clone, no capture and no attended session needed.
Previous rounds (`qgmm2s` and earlier) had been treating it as blocked on a
"RE lane" that does not run as a cloud routine -- true, but irrelevant,
since the ticket was never routed to that lane in the first place.

**What this round did:** answered both of `RE-172`'s questions from source
already in this clone -- (1) no other named VitalData message (of 520 in
`pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`) resolves a call into
`ActorAttr`'s or `BasicAttr`'s own codec entry points, and even
`pf_bridge/notes_to_chief/reference_codex_attr/PF_ATTR_CLASS_CENSUS.tsv`
(Codex's own deepest class-level census) flags
`NO_REGISTERED_VTABLE_BOUNDARY_THROUGH_OWN_PLUS_0x34` for both classes --
unresolved even there, `UpdateAttrVital` included; (2) `model.py` (full
file) and all five `migrations/*.sql` files (full, not grepped) persist no
column shaped like any `attr_wire.py::FIELDS` row outside `actor_wire`.
Both negative -- closed `RE-172` as DONE/BOUNDED-NEGATIVE in
`pf_bridge/CLIENT_RE_QUEUE.md` (full trail:
`pf_bridge/notes_to_chief/20260831_2326_RE-172-RESULT-*`). Per
`COO-DECISION 20260831_1843`'s own advance instruction ("RE-172 negative =>
route straight to the owner, not COO deciding for this lane"), opened
`pf_bridge/notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-attr-wire-path1-vs-path2-after-re172-negative.md`
naming path 1 (accept the irreversible zero-unknown-fields risk) vs path 2
(name-only fields forever, possibly technically impossible) for the owner
to decide -- `attr_wire.py`'s fail-closed gate is untouched, every byte,
pending that answer.

**`gm/cheat_wire.py`** (new, this round): a structural round-trip codec for
`CheatVital` (0x162E) -- the untagged `uint32-LE`-length-prefixed narrow
string `PF_SERIALIZER_FIELDS.tsv` rows 565-566 prove byte-exact. Built per
this round's own rule-F menu (a known field layout not gated on RE-172 or
`say_wire`'s lock) as a reference codec only, the same role
`teleport_wire.py`'s `ForcePos`/`CWarpResult` held before `warp_executor.py`
bridged them -- nothing in this package imports it, and this round does not
propose wiring it into `dispatch.py`/`runtime.py`. It keeps the string as
raw `bytes`, never decoded, because the byte encoding (cp874/ascii/other)
is not proven anywhere in the cited rows. See the wire-facts table above
and the module's own docstring for the full citation. Tests:
`tests/test_gm_cheat_wire.py`, 14 cases (encode bounds, round-trip,
truncation/oversize/trailing-byte rejection, vital-id check against the
bridge registry).

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` -> **1164 passed, 529 subtests**
(was 1150/523 last round; +14 new `test_gm_cheat_wire.py` cases, no
regressions).

### nonclaim

1. `RE-172`'s negative answer is bounded to what is committed and
   searchable in this clone (520 named messages + the deepest available
   class census) -- it does not prove no such source exists anywhere in the
   real client, only that none was found here.
2. `gm/cheat_wire.py` does not claim `CheatVital` is related to this lane's
   actual GM command channel (`GM_RunGMCommandVital`, 0x51E9) -- the shared
   `+0x14` offset is coincidence of position in two unrelated structs, said
   explicitly in the module docstring.
3. No status/gate/policy change to `attr_wire.py`, `say_wire.py`,
   `dispatch.py`, or `runtime.py` this round.
4. Did not give GM status to any account outside `gm_accounts.json`; no
   milestone declared from this round's results.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้ (round `thhkup`)

**ไม่มีการเปลี่ยนแปลงที่ผู้เทสสัมผัสได้โดยตรง** -- `RE-172` ปิดเป็นข้อมูลนโยบายที่ส่งต่อให้เจ้าของ
ตัดสินใจ (path 1 vs path 2 สำหรับ `/lv`), และ `gm/cheat_wire.py` เป็น reference codec ที่ไม่ได้ต่อสาย
เข้าอะไรที่ผู้เทสเรียกได้ `GT-172` (READY จากรอบก่อน) ยังเป็นทางเดียวที่ผู้เทส attended ทำได้เพิ่มจาก
เมื่อวาน

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260831_2330_thhkup_re172_closed_plus_cheat_wire_codec.md`
PR: `pf_bridge#641`, `pirate-force-server#420` (merged)

## รอบ `dgyakk` (2026-09-01T00:18+07:00) -- verify-only, mailbox hygiene, no src change

Checked every channel fresh (mailbox / CORE-REQUEST-GM-0xx / GT queue read-only / own backlog): no
new `gm/` work available. `RE-164` items #1/#3 still need disassembly this clone doesn't have; the
carrier for that -- the RE runner -- was just reported idle 30h by
`pf_bridge/notes_to_chief/20260831_2325_KA1A-ROOTCAUSE-*` (a category-tag regression, chief's queue
territory, not this lane's to fix) so re-requesting it now would duplicate chief's own open item.
`attr_wire.py`/`/lv` stays shelved per `COO-DECISION 1244` plus `RE-172`'s negative result -- both
live paths wait on the owner's answer to `pf_bridge#20260831_2327_LANE-GM-TO-OWNER-*`, which that
letter itself says is not urgent (path 3, current fail-closed state, carries no new risk while
unanswered). Added the one missing `.CONSUMED.txt` stub for `COO-DECISION 1244` (already acted on
in rounds 1425/1523/1736, just never stubbed) -- mailbox hygiene only, no new decision made.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- verify-only round. `GT-172` (READY from an earlier round) is still the only thing an
attended tester can do beyond yesterday.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0018_dgyakk_verify_only_mailbox_hygiene_all_fronts_external.md`
PR: `pf_bridge#645`, `pirate-force-server#423` (this one)

## รอบ `bmedw1` (2026-09-01T01:22+07:00) -- consume COO-DECISION 0043, docstring-only, no unlock

Consumed `pf_bridge/notes_to_chief/20260901_0043_COO-DECISION-attr-wire-unlock-
criteria-replaced-shelve-stays-locked.md` (ADDRESSEE: LANE-GM, first letter this round
addressed to this lane by name). It ratifies a 3-point unlock definition -- (a) encoder
covers every named field, (b) unnamed fields preserved lossless, (c) a
version-confirmation constant gates the live send -- but does not itself audit this
module against the three. Checked directly: (a) and (c) hold at the code level; (b)
does NOT hold yet as an outcome -- no raw-block source exists to preserve unnamed
fields from, so the first named-field send would still zero them, which is exactly why
path 1 vs path 2 for `/lv` is still routed to the owner
(`pf_bridge/notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-*`, unanswered, not urgent per
that letter's own text). A first draft of this docstring update claimed the letter
"confirmed this module already satisfies all three" -- pf-adversary caught that this
overclaimed and self-contradicted the very next sentence about the open path 1/2
question; fixed before commit. No logic, no test, no gate touched --
`UPDATE_ATTR_VITAL_VERSION_CONFIRMED` stays `None`. Checked the other three channels
fresh (CORE-REQUEST-GM-0xx replies, GT queue read-only, own round backlog): nothing new
in any of them this round.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` -> **1164 passed, 537 subtests** (docstring-only
change, no regressions expected or found).

### nonclaim

1. Does not claim attr-wire is unlocked or that `/lv` can send live -- shelve stands,
   `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is still `None`.
2. Does not claim path 1 or path 2 was chosen -- that question stays with the owner.
3. Did not give GM status to any account outside `gm_accounts.json`; no milestone
   declared from this round's results; no `runtime.py`/`app.py`/
   `pf_login_game_server_v141.py`/canonical DB/`scenarios/world_*.json`/
   `scenarios/combat_*.json` touched.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- docstring/mailbox round only. `GT-172` (READY from an earlier round) is still
the only thing an attended tester can do beyond yesterday.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0122_bmedw1_consume_coo_0043_docstring_only.md`
PR: `pf_bridge#649`, `pirate-force-server#426` (this one)

## รอบ `kv02mn` (2026-09-01T02:16+07:00) -- verify-only, consumed COO-DECISION 0147, no unlock

Consumed `pf_bridge/notes_to_chief/20260901_0147_COO-DECISION-attr-wire-try-re172-first-
ack-sequencing.md` (ADDRESSEE: LANE-GM). It ratifies the sequencing this lane proposed
itself (try `RE-172` before deciding path 1 vs path 2) -- but by wall-clock time
`RE-172` had already closed bounded-negative in round `thhkup` (2026-08-31T23:26+07:00),
earlier than this letter was written (01:47). The sequencing COO acknowledged had
already happened before the letter arrived, so there is no new action to take from it.

Re-verified both open blockers are unchanged: (A) path 1 vs path 2 for `attr_wire.py`
is still with the owner (`pf_bridge/notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-*`,
unanswered) -- `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` stays `None`; (B) `RE-164` #1/#3
still needs disassembly not present in this clone's image, still waiting on chief's RE
runner (`pf_bridge/CLIENT_RE_QUEUE.md:2908` unchanged). Checked all four backlog
channels fresh (letters / CORE-REQUEST-GM-0xx / GT queue read-only / own round backlog):
nothing new. Cross-checked the full `gm/` directory (23 files) against every
GM-related row in `VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (`CheatVital`,
`CWebGMVital_GSGC`, `GM_RunGMCommandVital`, `GM_UpdateGMStateVital`,
`Activity_CheatCodeVital`, `GM_RunGMCommandResultVital`, `GM_ForbidToTalkResultVital`,
`Channel_GMGlobalMessageVital`) -- no unmapped row found.

No src/scenarios/tests change this round (mailbox stub + round notes only), so
pf-adversary was not invoked, matching the precedent set in round `dgyakk`.

### nonclaim

1. Does not claim attr-wire is unlocked or that path 1/2 was chosen -- still with the
   owner.
2. Does not claim `RE-164` #1/#3 is closed -- still waiting on chief's RE runner.
3. Did not give GM status to any account outside `gm_accounts.json`; no milestone
   declared from this round's results; no `runtime.py`/`app.py`/
   `pf_login_game_server_v141.py`/canonical DB/`scenarios/world_*.json`/
   `scenarios/combat_*.json` touched.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- verify-only round, mailbox consumption only. `GT-172` (READY from an earlier
round) is still the only thing an attended tester can do beyond yesterday.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0216_kv02mn_verify_only_10th_round_waiting_on_owner.md`
PR: `pf_bridge#653`, `pirate-force-server#429` (this one)

## รอบ `k0w291` (2026-09-01T03:18+07:00) -- GT-172 closed PASS, three new findings opened

Consumed `pf_bridge/notes_to_chief/20260901_0225_GT172-RESULT-PASS-*.md` (ADDRESSEE:
LANE-GM, attended tester). GT-172 PASSED at both layers: `/warp <scene> x y` in the
chat box moved a live client mid-session with no relog, confirmed on wire
(`LANE_GM_CHAT_WARP_CROSS_SCENE_TELEPORT_VITAL` -> `TeleportVital`, 4/4 fires
succeeded). Closed the GT-172 header in `pf_bridge/GAME_TEST_QUEUE.md` as PASS (this
lane's own queue entry).

Three observations from that test session were opened as their own letters, as the
result letter asked, rather than folded into a FAIL that GT-172 did not earn:

- **F-1** (`CORE-REQUEST-GM-045`): the console showed `WORLD_CENSUS ... scene=bg0001`
  (the origin scene) after a live warp to scene 278, with zero census lines for 278
  itself. Traced to source, not guessed: `gm/chat_command_action.py::_warp_teleport_
  action`'s own docstring states no new `runtime.py` call site was needed to land the
  live-teleport path, so it never touches the session state (`self.foundation.
  selected.position`, `self.last_target_pos`) that `runtime.py`'s `WORLD-CENSUS-001`
  block reads to decide which scene to census. Outside this lane's write zone
  (`runtime.py` is chief's) -- filed as a request, not fixed here.
- **F-2** (`CORE-REQUEST-GM-046`): a live cross-scene warp carries the origin scene's
  `z` unchanged, so the destination can leave the GM floating/stuck in geometry.
  `gm/warp_executor.py` deliberately never invents an elevation (its own docstring),
  and this lane has no per-scene spawn/ground data anywhere in `gm/` -- confirmed by
  grepping `gm/scene_catalog.py` (no spawn fields) and both `pf_bridge/external/
  00_SEARCH_HERE_FIRST.md` / `pf_bridge/gamedata/00_SEARCH_HERE_FIRST.md` for
  spawn/respawn terms (no hits, verified live before writing the letter, not asserted
  from memory). This is a data request, not a code-site request, and it lines up
  directly with the owner's new GM-A ask (`pf_bridge/notes_to_chief/
  20260901_0215_PANYA-ORDER-drop-milestones-*.md`).
- **F-3** (FINDING, no code request): a live warp does not update the scene staged
  for next login (`gm/login_scene_stage.py`) -- by design, the two mechanisms were
  always independent, but it is counter-intuitive and directly relevant to GM-A's
  design once a lane is assigned it.

This lane deliberately did NOT claim GM-A/GM-B from the owner's `20260901_0215`
letter this round, even though both are GM-prefixed: that letter asks chief to
announce lane assignments explicitly, and the most recent chief broadcast checked
(`FROM_CHIEF_R277`, 02:00) predates it, so no assignment exists yet -- claiming ahead
of that risks colliding with whichever lane chief actually names.

No `src/`/`scenarios/`/`tests/` change this round (letters, queue header, docs, round
notes only) -- pf-adversary not invoked, same precedent as rounds `dgyakk`/`bmedw1`/
`kv02mn`.

### nonclaim

1. Does not claim F-1/F-2 are fixed or even confirmed by chief -- both are open
   requests.
2. Does not claim GM-A/GM-B belong to this lane -- waiting on chief's assignment per
   letter `20260901_0215` item 6.1.
3. Did not give GM status to any account outside `gm_accounts.json`; no milestone
   declared (milestones already paused per letter `20260901_0215` item 2); no
   `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json` touched.
4. Did not delete any history -- new stubs only, originals copied to
   `pf_bridge/notes_to_chief/consumed/`.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

`GT-172` is now formally closed PASS in the queue (it was READY-but-unfired
yesterday). No new call site exists yet for an attended tester to exercise beyond
that until chief answers the three letters opened this round.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0318_k0w291_gt172_pass_three_findings_opened.md`
PR: `pf_bridge` (this repo's companion) -- numbers filled in once opened

## รอบ `jd4jqp` (2026-09-01T04:44+07:00) -- GM-A built (PR pending), P-3 RE-164 retagged, P-2 finding

`R278` formally assigned P-2/P-3/GM-A/GM-B to this lane. Consumed it plus the two CHIEF-REPLY
letters answering `CORE-REQUEST-GM-045`/`-046` from last round.

**GM-A built**: `gm/warp_executor.py` gained `warp_no_coords_live_target(scene_id)` and
`make_warp_teleport_frame_no_coords_with_target(legacy, scene_id)`; `gm/chat_command_action.py`
gained `_warp_teleport_action_no_coords` and a new action label
`WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL` (carries `TELEPORT`, per the move-authority
substring rule). A bare `/warp <scene_id>` naming a DIFFERENT scene now fires a live
`TeleportVital` at that scene's `world_scene_travel.spawn_position(world_scene_travel.
destination(scene_id))` -- the exact call pattern `R278`/`CHIEF-REPLY-GM-046` named -- instead of
only staging, whenever that scene's `has_authored_entry` (n_MARKER != 0) is true. Scenes with no
marker (17, 126, 278, 997) keep the old stage-only behaviour on purpose -- `GT-182`'s own
nonclaim 4 requires it, and scene 278 specifically has a pinned regression test
(`ProductionCallShapeTests::test_the_default_argument_call_stages_where_gt141_says_it_does`)
that would have broken under a looser "spawn is not None" gate. Full local suite green (6140
passed / 0 failed) after fixing 12 tests across five other `test_gm_*.py` files whose fixtures
used scene 2 (marker-backed) as their canonical "stages, does not send" example -- fixed by
patching `WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED = False` at exactly those call sites, the
same isolation the with-coordinates sibling's own kill-switch test already established, not by
narrowing GM-A's own scope. `pirate-force-server#438` (`CORE-REQUEST-GM-045`,
`_gm_warp_resync_selected_scene`) covers this new branch's census-scene-resync for free, verified
from source: that method keys on the `WarpTargetRecord` `_park_warp_target` parks, which both the
with- and without-coordinates branches call identically, not on any action-label string. `GT-182`
stays BLOCKED (headless only, PR not yet merged as of this round) -- see its own status note and
this round's STATUS letter for the full nonclaim.

**P-3**: `pf_bridge/CLIENT_RE_QUEUE.md`'s `RE-164` items 1/3 were tagged `NEEDS-ATTENDED-CAPTURE`,
which is the wrong route -- the ticket's own text says they need bridge-side disassembly
continuation, not a game click. Retagged to `STATIC-ON-BRIDGE` per the routing-tag rule chief
restored this cycle (`PROCESS_GATES.md` §18), so the RE runner idle 30h on the bridge can pick
them up. No content/nonclaim changed, header only.

**P-2**: searched broadly (`grep -rli` across `src/`) for any fontstyle/name-color computation --
found none in `gm/`; the only matches are `mob_aggro.py`/`mob_ai_control.py`/
`field_mob_ai_tables.py` (LANE-B's combat/mob-AI territory, which already carries an
idle/aggro/return/dead phase machine but no `runtime.py` call site yet). Filed as a finding, not
code, in this round's STATUS letter -- also found a new lead for the "dead=gray" gap chief named
(three more rows in `PF_ATTR_NAME_COLOR_SELECTOR.tsv` naming `fontstyle_id=63` under a condition
matching `PF_COMBAT_LIFECYCLE.tsv`'s dead-predicate vslot, but those rows' own nonclaim repeats
three times that fontstyle 63 is not proven equivalent to dead) -- routed to `RE-155` (LANE-A's
open ticket on this exact topic), not opened as a new ticket.

**GM-B**: `gm/attr_wire.py`'s fail-closed gate is unchanged and still locked -- `COO-DECISION
20260901_0147` still says "try RE-172 first, decide path 1 vs 2 only if negative"; RE-172 came
back negative and the follow-up letter asking for that decision is still unanswered by the owner.
The same policy that blocks `/lv` blocks `/speed`. No new code.

**pf-adversary**: this session's toolset carries no Agent/Task tool to spawn a subagent (searched
via `ToolSearch` before concluding absent) -- substituted a thorough self-adversarial review
before committing (12 points: login_scene_admission bypass parity with the already-COO-approved
with-coordinates sibling, double registry-load per call as a named inefficiency not a
correctness bug, no new global mutable state, audit logging reuses the already-tested shared
pipe) -- flagged `[สมมติของสาย GM - รอ COO ยืนยัน]` in this round's STATUS letter.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0444_jd4jqp_gm-a-live-warp-built-p3-retag-p2-finding.md`
PR: `pf_bridge` / `pirate-force-server` (numbers filled in once opened)

## รอบ `vsopwk` (2026-09-01T06:17+07:00) -- P-3: fifth hypothesis stub from Codex's GameMaster.dll finding; GM-A merged confirmed; GM-B/attr-wire still correctly blocked

Round-lock opened FIRST this round (draft PR in both repos, before any code) -- correcting the
protocol deviation the previous round (`jd4jqp`) logged against itself.

**Mailbox**: two letters addressed `LANE-GM` still lacked a `.CONSUMED.txt` at round start:
`20260901_0444_COO-DECISION-attr-wire-raw-block-proceed-path0-defer-1-vs-2.md` and the (already
chief-consumed, but not yet LANE-GM-consumed) trio `20260901_0254`/`0321`/`0344` CODEX-CORRECTION
letters on the `GameMaster.dll` GM-plugin loader. Both consumed this round -- see the STATUS
letter and the four `.CONSUMED.txt` append-notes for detail.

**GM-A**: confirmed merged (`pirate-force-server#440`, merged 2026-08-31T21:57:48Z / 04:57+07:00
Sep 1) -- `GT-182` is unblocked on this lane's side; the queue header itself is not this lane's
write zone, so no edit made there, only noted.

**P-3 -- new hypothesis stub, not a wire fix**: `20260901_0344_CODEX-CORRECTION-GM-EVIDENCE-
BOUNDARY.md` (authoritative, supersedes withdrawn drafts 0254/0321) found the client's
`GameMaster.dll` loader's direct-call slot `+0x04` is consumed as a GUI model basename
(`.\Data\GUI\Model\<key>.model`); the 534-file `.model` corpus has no `GMUI_BASIC.model` under
any case, but `GMUI.project` declares `GMUI_1`, whose own `.model` roots `GMUI_1` with child
`GMUI_BASIC`. Added `GM_PLUGIN_MODEL_KEY_SUSPECT` to `gm/bt_gm_probe.py`'s `SUSPECT_STUBS`
(now 4, up from 3) carrying this letter's own hedged wording verbatim (`L"GMUI_1"` is a
PROPOSED compatible binding, explicitly NOT a proven original-DLL return value) -- no wire
variant added, because this is a client-side resource-name question this lane's server code
never touches, not something a vital payload can vary. Searched `pf_bridge/external/` for the
three backing artifact files the letter names (`pf_rederive_gm_plugin_gate.py`,
`PF_GM_PLUGIN_GATE.tsv`, `PF_GM_PLUGIN_GATE.md`) -- ค้นแล้ว: ไม่เจอ (git-ignored/local-only per
the letter's own "Delivery blocker" section, not yet packaged for other clones). The stub is
built only from the letter's own prose, nothing pulled from those files. Test file
`tests/test_gm_bt_gm_probe.py` updated to match (28 tests, two new ones pin the hedged wording
so a future edit cannot silently drop it). Full suite เขียว(cloud sanity) -- `pytest tests/` =
6156 passed, 323 skipped, 0 failed; `tools/verify_hypothesis_ledger.py` PASS entries=47,
`tools/verify_functional_coverage.py` PASS domains=8, no drift versus last round.

**GM-B**: still correctly blocked. `RE-172` (already negative, prior round) plus the follow-up
owner-ask `20260831_2327` (unanswered) mean the path-1-vs-path-2 choice remains open; the newly
consumed `COO-DECISION 0444` turned out to answer an OLDER, now-superseded ask (`1825`, before
`RE-172` landed) and does not decide anything new -- noted, not re-litigated. This is an
irreversible-write-with-no-backup question (path 1 could zero live character fields with no
way to recover the pre-write value) -- category (b) of the "getting stuck" rule, correctly
left for the owner rather than guessed at by this lane. No code change to `gm/attr_wire.py`.

**pf-adversary**: no Agent/Task tool available this session either (re-checked via ToolSearch).
Self-adversarial review before commit: (1) checked no other module imports `SUSPECT_STUBS` or
the three named stub constants with a hardcoded count assumption -- grepped clean; (2) the new
stub is a frozen dataclass literal, no new mutable state, no new code path in any dispatch
function; (3) verified the stub's wording does not overclaim in either direction (neither
"GMUI_1 proven" nor "GMUI_BASIC proven not-original") by direct quote-check against the source
letter; (4) confirmed `write zone` compliance -- only `gm/bt_gm_probe.py` and
`tests/test_gm_bt_gm_probe.py` touched, no `runtime.py`/`app.py`/
`pf_login_game_server_v141.py`/canonical DB/`scenarios/world_*.json`/`scenarios/combat_*.json`.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- this round is a documentation/hypothesis-stub change plus mailbox hygiene, no new
wire behaviour, no new chat command, nothing an attended tester can exercise that they could
not exercise yesterday.

### nonclaim

1. `GM_PLUGIN_MODEL_KEY_SUSPECT` does not resolve, confirm, or refute any of RE-164's four
   original suspects -- it is a fifth, separate, upstream question, explicitly labelled as such
   in the module docstring.
2. Does not claim the three Codex artifact files are inaccessible forever -- only that this
   session's fresh clone does not have them, per the letter's own stated delivery blocker.
3. Did not give GM status to any account outside `gm_accounts.json`; no milestone declared
   (still paused); no `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`/`gm/attr_wire.py` touched.
4. Did not delete any history -- consumption notes appended to existing `.CONSUMED.txt` stubs,
   never overwritten; originals untouched.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0617_vsopwk_gmui1-hypothesis-stub-plus-mailbox.md`
PR: `pf_bridge` #673 / `pirate-force-server` #446

## Round `h6rsgl` (2026-09-01T09:2x+07:00) -- P-2 monster name color: static research, no proven "dead" fontstyle found, no code change

No source change in this repo this round. Companion PR to `pf_bridge#685`, which holds the full
writeup. Summary: per `PANYA-ORDER 20260901_0215` / chief's `FROM_CHIEF_R278` broadcast, P-2
(monster name-tag color: normal=orange, fighting=red, dead=gray, never pink) is assigned to
LANE-GM. Ran a static/headless research pass (`pf-static-re` subagent, no client image available
in this environment) over `PF_ATTR_NAME_COLOR_SELECTOR.tsv` and related committed tables.

Result: the table's `typed_CNetNPC` lane only has 2 proven fontstyle ids (61/62, fighting/not),
no third row for "dead." The closest candidate (`fontstyle_id=63`) comes from an
`untyped_dynamic_controller` row whose own `nonclaim` explicitly says "FontStyleID 63 is not
equivalent to dead" -- the CNetNPC-vtable call path for the underlying death predicate
(`0x0043BD70`) is not yet proven, only a shared cross-family predicate is. `RE-109` (closed) has
`BUILD_IMPACT: NONE` for this table -- hard-coding a color guess from any id in it would directly
violate that. So this lane did not write any color-selection code this round.

Proposed a narrow, static-only follow-up RE ticket (typed-downcast proof for the
`0x0043BD70` predicate through `CNetNPC`'s vtable, then RGB read for fontstyle 63 via
`UILabel_FontStyleID_parser_setter`) in a letter to chief -- reuses existing pins, does not
reopen `RE-067`/`RE-109`, does not touch `RE-155`'s own (unrelated, fighting-color) open scope.

pf-adversary (real spawned subagent, not self-review) caught a real self-contradiction in the
first draft of that letter -- it both said `RE-155` "is not about dead=gray" and then treated
`RE-155`'s attended-capture blocker as the only remaining path for the dead=gray gap, which
would have escalated a false dilemma to chief/COO. Fixed before commit: the proposed RE ticket
is purely static/IMAGE-layer and is unaffected by the owner's freeze on attended monster-hit
tests regardless of how that freeze question resolves for `RE-155` itself.

`GM-B` (`/speed`, `GT-183`): unchanged, still correctly blocked -- `gm/attr_wire.py`'s path-1-vs-
path-2 raw-block-source question is still routed to the owner (letter `2327`, unanswered as of
this round); not re-litigated, no new letter opened about it this round since nothing new arrived.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` = 1206 passed, 547 subtests passed เขียว(cloud sanity),
confirmed before and unaffected by this round (no code changed).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- research/letter round only, no wire change, no new chat command.

### nonclaim

1. Does not claim fontstyle 63 means "dead" -- the source table itself disclaims this.
2. Does not write any name-color code -- would violate `RE-109`'s `BUILD_IMPACT: NONE`.
3. Does not decide whether observation-only attended capture is exempt from the owner's
   monster-hit-ticket freeze -- routed to COO, tagged as this lane's own provisional read
   (currently: still forbidden) pending an answer.
4. Did not touch `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`/`gm/attr_wire.py`.
5. Did not give GM status to any account outside `gm_accounts.json`; no milestone declared.
6. Did not delete any history.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_0921_h6rsgl_p2-color-static-research-fontstyle63-gap.md`
PR: `pf_bridge` #685 / `pirate-force-server` #456

## Round `gm-20260901_1013` (2026-09-01T10:1x+07:00) -- rule F, GM_PLUGIN_MODEL_KEY_SUSPECT stub refreshed with newer Codex ABI facts, no wire change

Round-lock: no open `[LANE-GM]` PR in either repo at round start; previous round (`h6rsgl`,
`pf_bridge#685` / `pirate-force-server#456`) verified `merged:true` directly via
`pull_request_read(method=get)`, not `list_pull_requests`.

Mailbox: no unconsumed `ADDRESSEE: LANE-GM` letter found this round (fast-forwarding to
`origin/main` pulled in several already-consumed-by-others letters, including
`20260901_0934_CODEX-CHECKPOINT-GM-COLOR-DROP-SECOND.md`, already stubbed by chief round `632iyt`
with "no chief action this round; relevant lanes (GM, B) pick up their own pieces"). All three
priority fronts (P-2 color, GM-B `/speed`, P-3 GM button) are externally blocked this round:

- P-2: follow-up RE ticket proposed last round (`h6rsgl`) still awaits chief assigning it to the RE
  lane -- nothing new to do until that assignment lands.
- GM-B (`gm/attr_wire.py` path 1 vs path 2): still waiting on the owner's answer to
  `notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-attr-wire-path1-vs-path2-after-re172-negative.md`
  (unanswered as of this round). `GT-183` stays `BLOCKED-ON-WIRING`.
  `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB not touched, as declared.
- P-3 (GM button): the `0934` checkpoint adds an implementation-contract detail for
  `CreateGameMaster` itself (export name, vtable slot `+0x00` in addition to `+0x04`, calling
  convention/stack cleanup, MSVCR90 scalar-delete allocator compatibility) -- this is native
  `GameMaster.dll` authoring, a different question from `bt_gm_probe.py`'s existing
  `GM_PLUGIN_MODEL_KEY_SUSPECT` (`.model` basename resolution), and this Python server repo
  neither builds nor loads that DLL. Appended the new facts to that suspect stub's own docstring
  (additive only, no field/shape change, no new frame, no runtime effect) so a future native-side
  attempt does not have to re-derive them from the checkpoint letter. This is this round's only
  code change.

Empty-round-rule-F basis: no unconsumed `ADDRESSEE: LANE-GM` letter, no new `CORE-REQUEST-GM-0xx`
reply requiring code, no LANE-GM-owned `GAME_TEST_QUEUE.md` entry newly unblocked, and own last
round's backlog (P-2 RE assignment, GM-B owner answer) both still pending replies from other
parties -- per the mission's "don't stall" rule, took the one available in-bounds action (stub
refresh) rather than writing a pure status letter with zero `gm/` change.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` = **1206 passed, 547 subtests passed** เขียว(cloud
sanity), unchanged count before/after this round's docstring-only edit.

### pf-adversary

**ไม่ได้รันจริง** -- ไม่มีเครื่องมือ spawn subagent (`Agent`/`Task`, `subagent_type: pf-adversary`)
ในชุดเครื่องมือของ session นี้รอบนี้ (ตรวจด้วย `ToolSearch` แล้ว ไม่พบ) ทำ manual self-review แทน:
diff เป็นการเพิ่มข้อความ docstring ล้วน (ไม่มีโค้ด/logic/shape เปลี่ยน), อ้างอิงจดหมายที่มีอยู่จริงและ
ตรวจแล้วว่า chief consume ไปแล้ว, ไม่มี claim ใหม่เกินกว่าที่จดหมายต้นทางพูด, ไม่มีข้อขัดแย้งในตัวเอง
(ตรวจแบบเดียวกับที่ pf-adversary จับได้รอบ `h6rsgl`) -- **ต้องแจ้งเจ้าของ**: ถ้า session ในอนาคตก็ไม่มี
เครื่องมือนี้เช่นกัน อาจต้องทบทวนว่า pf-adversary ผูกกับ environment ไหน

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- docstring-only, ไม่มี wire ใหม่, ไม่มีคำสั่งแชทใหม่.

### nonclaim

1. ไม่อ้างว่า `GMUI_1` เป็นค่าจริงที่ original DLL คืน -- ยังเป็น proposed binding ตามจดหมายต้นทาง.
2. ไม่อ้างว่า slot `+0x00`/allocator facts ใหม่เปลี่ยนข้อสรุปของ suspect stub -- ยังไม่มี wire variant
   ให้เพิ่มเหมือนเดิม, เป็นการบันทึกไว้เผื่ออนาคตเท่านั้น.
3. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/`scenarios/world_*.json`/
   `scenarios/combat_*.json`/`gm/attr_wire.py` (ยัง shelved เหมือนเดิม).
4. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone.
5. ไม่ได้รัน pf-adversary จริง (เครื่องมือไม่มีใน session นี้) -- self-review แทน ตามที่ระบุข้างบน.
6. ไม่ลบประวัติเดิม.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_1013_gm-20260901_1013_rule-f-plugin-model-key-stub-refresh.md`
PR: `pf_bridge` #689 / `pirate-force-server` #460

## Round `p4cndg` -- 2026-09-01T11:19+07:00

No `gm/` code change. Corrected a misrouted letter (UI-A/UI-B belong to LANE-A per
`FROM_CHIEF_R278`, not LANE-GM), confirmed GM-B (`/speed`) ownership moved to the new LANE-DB
lane per `COO-DECISION 20260901_1059`, and sent LANE-DB an informational letter naming the two
independent refusal gates in `gm/attr_wire.py`'s `build_named_field_update` for field `x=7`
(`known=False`, separate from the cache-seed gate) so they do not have to re-derive it from the
source themselves. P-2's RE follow-up ticket (proposed round `h6rsgl`) is still waiting for chief
to assign an RE lane, second round running.

pf-adversary ran as a real spawned subagent this round (tool available, unlike round
`gm-20260901_1013`) and checked all three of this round's factual claims (UI-A ownership, the
`attr_wire.py` x=7 field status, the decision not to touch code) -- no defect found.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` = **1206 passed, 547 subtests passed** เขียว(cloud
sanity), unchanged (no code edit this round).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- letter/routing round only, no wire change, no new chat command.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_1119_p4cndg_ui-a-correction-p2-still-waiting-gm-b-to-lane-db.md`
PR: `pf_bridge` #695 / `pirate-force-server` #464

## Round `sched-20260901` -- 2026-09-01T12:25+07:00

`NOW.md` existed on `origin/main` this round (it did not exist at session start; it landed via
the Windows-bridge sync mid-round, per `PANYA-DECISION 20260901_1215`'s own finding that the
file was write-only until that fix). Read it as the first act after merging `origin/main`, per
its own file-first rule.

**GM-A -- confirmed still open, not claiming otherwise.** `PANYA-DECISION 20260901_1215` rejects
`GM-A` from `NOW.md`'s "รอ Panya ติ๊ก" list: her real acceptance test is a CHAIN of cross-scene
warps (GT-182 session 2: 5,6,7,8,9,10,11,14, back to 1 -- eight hops) each landing on a normal
NPC roster, not one warp. The census-latch fix that closes the root cause
(`KA1A-ROOTCAUSE 20260901_1035`, commit `67fe6fe`) is already on `main`, merged before this round
started -- this lane did not write it. What THIS round adds: `tests/test_gm_warp_position_
confirmed.py::GmWarpCensusLatchClearTests::test_a_long_chain_of_cross_scene_warps_clears_the_
latch_every_hop`, an 8-hop chain test modeling the owner's actual GT-182 sequence, since every
existing test in the module proved the latch clears on ONE cross-scene resync in isolation and
none simulated a SECOND hop after the previous scene's census had already re-armed the latch --
exactly the shape of gap that would let a "only holds for hop one" regression through unnoticed.
Manually confirmed with a temporary revert of the two `= False` lines in
`_gm_warp_resync_selected_scene` that the new test fails without the fix (`AssertionError: True
is not false`) and passes with it restored -- the test has teeth, not just green paint. This
closes a coverage gap; it does not make GM-A pass. Only Panya's own attended retest can do that
(`NOW.md`'s own rule: "เสร็จ" ติ๊กได้โดย Panya คนเดียว).

**P-2 (monster color) -- Codex checkpoint narrows the open question, doesn't close it.**
`CODEX_CHECKPOINT_20260901_1135_COLOR-DROP-GM-STATIC-UNLOCK.md` (landed on `main` this round,
same sync as `NOW.md`) proves the exact gap this lane's `h6rsgl`-round RE proposal asked for:
`fontstyle_id=63`'s death-branch predicate (`0x0043BD70`) is now closed as reachable through
`CNetNPC`'s own same-actor chain (manager registry -> tick/selector receiver -> `actor+0x254`
controller -> style store), not the untyped/unproved lane `RE-109` had flagged. `MCG-IMG-025..033`
moved to `PROVEN_EXACT` (conditional static path). Still open, per the checkpoint's own words:
runtime control-flow/distance/registry-retention gates and, critically, the actual RGB that
`fontstyle_id=63` renders as (still unconfirmed against 61/62's known control colors) -- the exact
follow-up this lane already proposed in `h6rsgl` (`UILabel_FontStyleID_parser_setter`,
`0x00AA488F`). No `gm/` code changes for P-2 this round: writing a color value now would still be
guessing the one fact that remains open. Sent an updated STATUS letter to chief narrowing the RE
ask to that one fact and flagging this is the third round waiting on an RE-lane assignment.

**P-3 (GM button) -- unchanged.** `NOW.md` and the Codex checkpoint both confirm the state this
lane already absorbed into the stub at round `gm-20260901_1013`: `PF_GM_PLUGIN_GATE.tsv` static
contract closed, but `GMUI_1`/panel/`GMUI_BASIC`/clean-shutdown still need DLL/build-output
evidence nobody has. Nothing new to act on.

**GM-B -- confirmed still with LANE-DB**, unchanged since `p4cndg`. `NOW.md` line "ยังไม่มีสายรับ"
matches (COO moved ownership, no lane has started work yet) -- not a contradiction of this lane's
own handoff.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` = **1229 passed, 547 subtests passed** เขียว(cloud
sanity) -- 1229 vs the previous round's 1228 baseline is exactly the one new chain test added
this round; nothing else moved.

### pf-adversary

**ไม่ได้รันจริง** -- ไม่มีเครื่องมือ spawn subagent (`Agent`/`Task`, `subagent_type: pf-adversary`)
ใน session นี้รอบนี้ (ตรวจด้วย `ToolSearch` แล้ว ไม่พบ, เหมือนรอบ `gm-20260901_1013`) ทำ manual
self-review แทน: (1) มิวเทชันเทส -- ปิด fix สองบรรทัดชั่วคราวใน `runtime.py` แล้วรัน test ใหม่ ล้ม
จริง (`AssertionError: True is not false`) เอากลับคืนแล้วรันทั้งชุดผ่าน 1229 ยืนยันว่าเทสจับบั๊กได้
จริงไม่ใช่ green ปลอม (2) ตรวจ docstring ของเทสใหม่ทุกบรรทัดเทียบกับโค้ด/จดหมายต้นทางจริง ไม่มี claim
เกินสิ่งที่วัดได้ (3) ตรวจว่าไม่ได้อ้างว่า GM-A ผ่านแล้ว -- เขียนชัดว่า "closes a coverage gap; it
does not make GM-A pass" (4) `git diff --stat` ยืนยันแตะแค่ไฟล์เทสไฟล์เดียว ไม่มีการแก้ `src/`

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี (บนจอ)** -- รอบนี้ไม่มีการแก้ wire/behavior ใด ๆ เป็นการเพิ่มเทสยืนยันของที่ merge แล้ว
เท่านั้น การพิสูจน์บนจอว่า GM-A ผ่านเกณฑ์จริงต้องรอ Panya เทสซ้ำเอง (ตามที่ `NOW.md`/`PANYA-DECISION
1215` สั่งไว้ตรง ๆ)

### nonclaim

1. ไม่อ้างว่า GM-A ผ่านแล้ว -- ยังรอ Panya เทสซ้ำ ตามที่ `PANYA-DECISION 20260901_1215` สั่งไว้ตรง ๆ
2. ไม่อ้างว่ารู้ RGB จริงของ `fontstyle_id=63` -- ยังไม่พิสูจน์ ตามที่ checkpoint เองเขียนไว้
3. ไม่เขียนโค้ดสีมอนสเตอร์ใด ๆ รอบนี้ -- จะเป็นการเดา ขัดกับ `RE-109` `BUILD_IMPACT: NONE`
4. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`/`gm/attr_wire.py`/`gm/chat_command.py`
5. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone
6. ไม่ใช้ GM เพื่อข้ามขั้นตอนใด ๆ รอบนี้ -- ไม่มีการ boot เกม/เซิร์ฟเวอร์เลย
7. ไม่ลบประวัติเดิมใด ๆ

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_1225_sched-20260901_census-latch-chain-test-p2-narrowed.md`
PR: `pf_bridge` #703 / `pirate-force-server` #468

## Round `r2jfjm` (2026-09-01T15:19+07:00) -- P-2 RGB question closed, second color path found (faction/pink), no code change

Consumed `notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md` (Codex static RE,
answering the RE-191 ticket this lane opened round `h6rsgl`). Result: exact RGBA proven via
DATA+IMAGE cross-reference for `fontstyle_id` 61/62/63:

| FontStyleID | FontColor RGBA | คำบรรยาย |
|---:|---|---|
| 61 | (255,100,100,255) | แดง/แดงอมชมพู (fighting) |
| 62 | (255,159,113,255) | ส้ม/แซลมอน (normal) |
| 63 | (179,179,179,255) | เทา (candidate: dead) |

This matches the owner's stated rule (normal=orange, fighting=red, dead=gray, never pink) and
none of the three IDs is pink -- closes the exact question `COO-DECISION 20260901_1241` ordered
answered. **Does not close P-2 as a whole**: the RE-191 letter itself says this proves the DATA
palette and the conditional static IMAGE path only, not that any live actor reaches
`fontstyle_id=63` for "dead" specifically, and warns against hardcoding a style ID -- the client
selects it from identity/relationship/death path.

**New this round (no prior GM round cross-referenced this):** searched outside this lane's write
zone (read-only) and found `src/pirateforce_foundation/npc_hostile_hypothesis.py:11-30`
(GT-032, attended PASS, not this lane's module) documents a **second, separate** color mechanism
-- a faction/relation comparator (`0x4A1D50`, BasicAttr bit `0x0400` at `+0x68`) that a real
client has rendered as **"pink/red name"** for one measured faction pairing (player faction 1 vs
NPC faction 6). That result is the literal thing the owner's P-2 rule forbids. Filed
`CORE-REQUEST-GM-048` to chief asking which mechanism (FontStyleID selector vs faction
comparator) P-2 should bind to, and for a faction-pairing block-list if it's the latter, before
any lane writes color code against either path.

### เขียว

`python3 -m pytest tests/test_gm_*.py -q` = **1229 passed, 547 subtests passed** เขียว(cloud
sanity) -- unchanged from the previous round's baseline; no `gm/` source touched this round.

### pf-adversary

**ไม่เรียก** -- ไม่มีการแก้ `src/`/`scenarios/`/`tests/` รอบนี้ (เฉพาะจดหมาย/round notes/docs)
ตามบรรทัดฐานรอบ `dgyakk`/`bmedw1`/`kv02mn`/`t2qkn3`

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี** -- รอบนี้เป็นการบริโภคจดหมาย + ค้นข้ามเขต (อ่านอย่างเดียว) + เปิดใบขอเท่านั้น ไม่มีการแก้
wire/behavior ใด ๆ

### nonclaim

1. ไม่อ้างว่า faction comparator กับ FontStyleID selector เป็นกลไกเดียวกัน -- ตั้งข้อสังเกตให้ chief
   ตัดสิน
2. ไม่อ้างว่า RE-191 ปิด P-2 ทั้งใบ -- ปิดเฉพาะคำถาม RGB
3. ไม่แตะ `npc_hostile_hypothesis.py`/`runtime.py`/`app.py`/`pf_login_game_server_v141.py`/
   canonical DB/`scenarios/world_*.json`/`scenarios/combat_*.json` -- อ่านอย่างเดียว นอกเขตเขียน
4. ไม่เขียนโค้ดสีมอนสเตอร์ใด ๆ รอบนี้ -- ยังไม่รู้ว่าเป็นกลไกไหน เขียนตอนนี้ = การเดา
5. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone
6. ไม่ลบประวัติเดิมใด ๆ

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_1519_r2jfjm_p2-rgb-closed-faction-pink-crossref.md`
PR: `pf_bridge` #723 / `pirate-force-server` #483

## Round `zkqaq1` (2026-09-01T16:29+07:00) -- pf-adversary finds and fixes a withheld-warp-clear gap in this lane's own zone

Consumed chief's reply on `CORE-REQUEST-GM-048`: P-2 targets the FontStyleID selector
(`0x00443F50` chain), not the faction/relation comparator. `RE-195` is open to answer whether the
two mechanisms are the same function; no color code yet either way. P-2/P-3 both unchanged from
prior rounds, still externally blocked (RE-195 open; RE-164 items 1/3 need disassembly this clone
does not have).

Ran `pf-adversary` (Agent tool available this round) against the merged warp wire
(`warp_executor.py`, `teleport_wire.py`). Found a real bug, this time inside this lane's own write
zone rather than `runtime.py`: `chat_command_action.py:1256-1259`'s withhold-clear tuple (which
clears a parked warp target when the audit-log write for a composed warp fails) listed only
`WARP_ACTION_LABEL` and `WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL` -- missing
`WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL`, which GM-A added later without updating this
set (confirmed via `git log`, commit `cdf5d7b`). A withheld bare `/warp <scene_id>` whose audit
write raised `OSError` left `gm_last_warp_target` parked despite no bytes reaching the client,
violating the invariant the surrounding comment states directly. Not an observed on-screen defect
today (the runtime's confirm-token gate only reads labels actually present in the dispatch
`actions` list, so the stale target was never read this way yet) -- a landmine, not a regression
a tester would have hit.

Fixed this round: added the missing label to the tuple and rewrote the stale two-label comment.
Added two regression tests in `tests/test_gm_command_audit_outcome.py` covering both cross-scene
shapes. Mutation-tested: reverted the fix, confirmed the new no-coords test fails
(`AssertionError: WarpTargetRecord(...) is not None`), restored the fix, confirmed all tests pass.

### เขียว

`python3 -m pytest tests/ -q` = **6350 passed, 327 skipped, 13717 subtests passed, 0 failed**
เขียว(cloud sanity) -- prior baseline was 6156 (other lanes' merges account for the rest; this
round adds exactly 2 new tests). `tools/verify_hypothesis_ledger.py` PASS entries=48,
`tools/verify_functional_coverage.py` PASS domains=8 -- no drift.

### pf-adversary

Ran for real via the Agent tool (not self-review) against `warp_executor.py`/`teleport_wire.py`
plus their test files. One real bug found and fixed (above). Six other areas checked (auth gate,
scene validation, kill-switch regression test, `warp_executor.*`'s input hardening,
`teleport_wire.py`'s wire codec round-trip, the `FORCE_POS_VITAL_VERSION_CONFIRMED` release) with
no issues found -- recorded so nobody re-digs them.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี (บนจอ)** -- this closes an invariant gap that was never observed as a visible defect; no
new wire, no new chat command for an attended tester to try.

### nonclaim

1. ไม่อ้างว่าบั๊กนี้เคยทำให้ตำแหน่งเพี้ยนบนจอจริง -- landmine ปิดก่อน ไม่ใช่ observed defect
2. ไม่อ้างว่า `RE-195` ตอบแล้ว -- ยังเปิดอยู่
3. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`
4. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone
5. ไม่ลบประวัติเดิมใด ๆ
6. ไม่ใช้ GM เพื่อข้ามขั้นตอนใด ๆ รอบนี้ -- ไม่มีการ boot เกม/เซิร์ฟเวอร์เลย

รายละเอียดเต็ม:
`pf_bridge/rounds/GM_20260901_1629_zkqaq1_adversary-finds-fixes-withheld-warp-clear-bug.md`
PR: `pf_bridge` #729 / `pirate-force-server` #488

## Round `nqba17` (2026-09-01T17:28+07:00) -- `/speed` sparse x=7 chat command parser + composer, GM-B first half

Consumed COO-ORDER `20260901_1641` (GM-B, Panya's live session override 2026-09-01T16:39+07:00:
"ส่งให้พอใช้งานได้ก่อน อย่ารอ RE") and the CODEX color-handoff addendum (`CODEX_URGENT_20260901_1646`,
P-2 -- no code change, still routed through chief/COO's normal queue per that letter's own words;
P-2 status unchanged from last round, still waiting on `RE-195`).

Added `speed <value>` to `gm/commands.py`'s grammar (parses/audits through the existing
`gm/chat_command.py` pipeline unchanged -- `/speed 5.0` now authorizes, decodes, parses and logs
exactly like `/lv 10` does today). Built `gm/speed_wire.py::compose_sparse_speed_update`: a SPARSE
`UpdateAttrVital` (0x309A) composer that sets ONLY the BasicAttr mask bit for field x=7 (offset
+0x54, f32 -- `attr_wire.FIELDS[6]`, still `known=False` there and left that way), never any of the
other 54 fields, and never through `attr_wire.build_named_field_update` (which would refuse x=7 on
its `known` gate) or `RawBlockCache` (a sparse send has nothing to merge). LANE-DB's independent
reply (`notes_to_chief/20260901_1201`) cross-references the client-side codex table
(`reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv:53`) naming the same bit/offset/tag/kind row
`FightAttr_run_speed_formula_input`, `PROVEN_EXACT` on both structural and semantic status -- two
independently-derived sources agree, which is why this door is named "speed" rather than left
`basic_f32_54`, though neither source is a client-observable measurement.

NOT wired into `gm/chat_command_action.py` this round: `speed` falls into the existing no-wire-path
branch, same as `npc`/`item`/`lv`/`spawn` today -- parsed and audited, no action composed. Two
reasons, both load-bearing and neither lifted by COO-ORDER `1641` (which approved WHICH fields the
sparse door touches, not the send safety gate below): (1)
`attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is still `None` -- `UpdateAttrVital`'s vital_version
byte has never been measured against a real client, sparse or full, and `GT-101` already showed
what an unproven version does (modal error, connection halted); (2) no call site in this lane's
zone can read a connection's `identity_lo`/`identity_hi` today. Opened `CORE-REQUEST-GM-049` to
chief naming both blockers and the exact call this lane asks `runtime.py` to make once they clear.

### เขียว

`python3 -m pytest tests/ -q` = all green (baseline 6350 + this round's 14 new tests in
`tests/test_gm_speed_wire.py`, plus grammar cases added to `tests/test_gm_commands.py` and one
exercise-table row in `tests/test_gm_standalone_map_is_not_chat_writable.py`). Two suite-wide
contract tests caught real omissions during this round and were fixed before commit: the pinned
`COMMAND_USAGE` order tuple in `tests/test_gm_chat_command_parse_way_out.py` (a literal tuple, not
derived from the source table) needed `speed` appended, and the standalone-map exercise table
needed a `speed` row for the "every parsed command has an exercise" check.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี (บนจอ)** -- `/speed <value>` now parses and audits (an attended tester can see the
`issued` row in the ndjson log and the `gm_chat_action_no_wire_path_speed` event), but no bytes
reach any client yet. That half needs `CORE-REQUEST-GM-049`'s two blockers cleared first.

### nonclaim

1. ไม่อ้างว่า x=7 คือ speed ที่พิสูจน์บนจอจริงแล้ว -- การอ้างอิงข้ามแหล่ง (probe table + codex) เห็น
   ตรงกันเท่านั้น [สมมติของสาย GM - รอ RE-193/GT ผลจริง]
2. ไม่อ้างว่า `attr_wire.FIELDS[6].known` ถูกแก้เป็น `True` -- ยังเป็น `False`, มีเทสยืนยัน
3. ไม่อ้างว่า `/speed` ส่งอะไรออกไปได้วันนี้ -- อยู่ใน no-wire-path branch เดียวกับ `npc`/`item`/
   `lv`/`spawn`
4. ไม่อ้างว่า P-2 (สีมอนสเตอร์) ขยับ -- consumed เท่านั้น ไม่มีโค้ดสีเขียนรอบนี้
5. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`
6. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone
7. ไม่ลบประวัติเดิมใด ๆ

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260901_1728_nqba17_speed-sparse-x7-chat-command-parser.md`
PR: `pf_bridge` #735 / `pirate-force-server` #493

## Round `egee8l` (2026-09-01T20:28+07:00) -- first real `pf-adversary` pass on `gm/`, one doc fix, two cross-lane letters

Two verify-only rounds in a row (`csux59`, `9x4k1q`) had left LANE-GM's write zone genuinely empty
(GM-A waiting on Panya's `GT-192`, GM-B's remaining half waiting on chief's `runtime.py` wiring per
`COO-DECISION 20260901_1847`, P-3 waiting on RE-104's continuation) -- rule F's "not a second empty
round in a row" forces picking one of (a)/(b)/(c)/(d) this round. Picked (d): this session is the
first one in this project's ~300 rounds to actually have the `Agent`/`pf-adversary` subagent tool
available (every prior round recorded its absence and substituted a manual self-review) -- ran it
for a full adversarial read of `gm/` (not a TODO/FIXME grep) rather than reporting empty again.

The agent live-tested invariant 1 (GM only for `gm_accounts` members) with a real attack: a `str`
subclass forging `__eq__`/`__hash__` to match a listed account, fed into `accounts.is_gm_account`.
Confirmed `frozenset.__contains__` itself is exploitable this way in isolation, but
`is_gm_account`'s `type(x) is not str` guard (not `isinstance`) rejects the subclass before the
`in` test ever runs -- the invariant holds under an actual exploit attempt, not just by reading the
guard and trusting it. Full `tests/` suite green in an isolated `git worktree` before any change
(1262 passed / 554 subtests / 0 failed on the `gm/`-scoped run cited by the agent; this round's own
post-fix run below is the full suite).

Three findings, all resolved or routed this round:

1. `GM_WARP_POSITION_CONFIRMED` fires on "position row changed," not "reached the commanded
   target." Re-checked against the codebase's own answer: the stronger, target-comparing pair
   (`GM_WARP_POSITION_TARGET_MATCH`/`..._MISMATCH`, `runtime.py:3899-3914`, driven by
   `warp_target_record.position_matches_target`) already exists and nothing in this lane's docs or
   tests relies on the weaker token alone as proof a warp worked. Not a new defect -- closed by
   re-verifying the mitigation, no code change.
2. `/warp` has no coordinate-magnitude bound (`_require_finite_float` only rejects NaN/Inf). Already
   named in this file's own docstring (`chat_command_action.py:231-238`, "ALSO OPEN") as fixable by
   importing a check from LANE-A's `world_scene_entry.py` rather than copying its logic -- not done
   because no public function exists yet to import. Opened
   `notes_to_chief/20260901_2028_LANE-GM-TO-LANE-A-warp-coordinate-bound-needs-a-public-ground-check.md`
   asking LANE-A for one; LANE-GM will wire the check itself once it exists. Not fixed this round
   (cross-lane, low severity: GM-authenticated-only, self-affecting, and the version gate already
   blocks any `/warp` byte from reaching a client today regardless).
3. `attr_wire.FIELDS`'s ActorAttr mask-bit sequence jumps from `1 << 30` to `1 << 32`, skipping bit
   31 -- looked like a possible transcription slip in a 55-row table this project treats as a
   probe-measured, independently-rewritten transcription. Re-read the original source
   (`pf_bridge/drafts/CHUNK2_Q1_ACTORATTR_MASK_FINDINGS.md:12`) rather than re-guessing from the
   table alone: `[PROVEN]` states the mask is genuinely 64 bits wide but only 41 of those bits are
   ever bound to a field, and bit 31 (`0x80000000`) is one of the 23 that are not. Not a bug --
   added a 7-line comment in `attr_wire.py` between the x=45/x=46 rows citing the source so a future
   reader (or another adversarial pass) does not re-open the same question from scratch.

A fourth item surfaced that is a genuinely new, previously-untracked question rather than a
resolved finding: every authorization check in `gm/` reads `session.token`, which this lane's own
docs already state plainly is a process-wide `--token` set once at server boot, not a
per-connection identity (`chat_command_action.py`'s "IDENTITY, STATED HONESTLY" block). No letter,
CORE-REQUEST, COO-DECISION, or test anywhere had asked what happens to audit rows, parked warp
targets, and staged login-scene entries written under that shared identity once per-connection
identity eventually lands (which `CORE-REQUEST-GM-049` already has chief moving toward, for an
unrelated reason -- reading `identity_lo`/`identity_hi` to compose outbound frames, not migrating
inbound history). Opened
`notes_to_chief/20260901_2028_LANE-GM-ASK-COO-shared-process-identity-leaves-audit-migration-unowned.md`
with this lane's best-effort position (no retroactive migration by guessing which account a shared-
identity-era row belonged to; treat old rows as bound to wall-clock time, not to an account) tagged
`[สมมติของสาย GM - รอ COO ยืนยัน]`, and kept moving rather than blocking on an answer.

### เขียว

`python3 -m pytest tests/ -q` (cloud sanity) = 6402 passed, 327 skipped, 13732 subtests passed, 0
failed -- run after the one-comment `attr_wire.py` change, confirming zero behavioral diff (the
edit adds a comment between two existing tuple rows; nothing in `FIELDS`, `BY_X`, or `BY_NAME`
changed).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี (บนจอ)** -- one explanatory comment plus two cross-lane/COO letters this round; no new wire,
no new chat command, no server or game client boot.

### nonclaim

1. ไม่อ้างว่าพบช่องโหว่ authorization ที่โจมตีได้จริงวันนี้ -- invariant 1-3 ยืนจริงภายใต้การโจมตีจริงที่
   ทดลอง (`str` subclass forgery); คำถามเรื่อง shared-identity migration เป็นคำถามสำหรับอนาคต ไม่ใช่
   ช่องโหว่ปัจจุบัน
2. ไม่อ้างว่าแก้ `/warp` coordinate bound แล้ว -- เปิดใบขอ API จาก LANE-A เท่านั้น ยังไม่มีเช็คขอบเขตจริง
3. ไม่อ้างว่า `attr_wire.FIELDS` เคยผิด -- ตารางถูกอยู่แล้ว มีแค่คอมเมนต์อธิบายเพิ่ม
4. ไม่ใช้ GM เพื่อข้ามขั้นตอนใด ๆ รอบนี้ -- ไม่มีการ boot เกม/เซิร์ฟเวอร์เลย
5. ไม่ให้สถานะ GM กับบัญชีนอก `gm_accounts.json`, ไม่ประกาศ milestone
6. ไม่แตะ `runtime.py`/`app.py`/`pf_login_game_server_v141.py`/canonical DB/`scenarios/world_*.json`/
   `scenarios/combat_*.json`
7. ไม่ลบประวัติเดิมใด ๆ

รายละเอียดเต็ม:
`pf_bridge/rounds/GM_20260901_2028_egee8l_first-real-adversarial-pass-plus-two-letters.md`
PR: `pf_bridge` #751 / `pirate-force-server` #506

## Round `ku3jz6` (2026-09-01T21:32+07:00) -- RE-164 item #3 closed static, item #1 write-site found, GameMaster.dll flagged for P-3

No code change in this repo this round -- the work is entirely `pf_bridge` static-RE and mailbox
(`CLIENT_RE_QUEUE.md` RE-164 update + a result letter). Logged here per this file's own convention of
recording every LANE-GM round, not because anything under `src/pirateforce_foundation/gm/` changed.

`RE-164`'s two still-open sub-questions (item #1: write-site of global `[0x01032EC4]`; item #3:
current-UI object-key crosswalk past the predicate RE-118 stopped at) had been labeled
STATIC-ON-BRIDGE since round `1q7nxu` -- needs live disassembly this cloud session does not have.
Called the `pf-static-re` agent (available for the second time in this project's history, after round
`egee8l`) to search committed artifacts again before accepting that label for another round. It found
`notes_to_chief/reference_codex_attr/PF_GM_PLUGIN_GATE.tsv`/`.md` in `pf_bridge`, synced into that repo
at 19:54+07 today (commit `a0909b1`) -- after an earlier round (`20260901_0626`) had checked for these
exact three files and found them absent. Every citation the agent made was independently re-verified
by reading the actual files (`grep`/`sed`), not trusted from the agent's report alone.

Item #3 closes statically: the full chain (`GameMaster.dll` load -> fallback object on failure ->
click reads a vtable slot that returns `NULL` in the fallback case -> the same empty-key predicate
RE-118 stopped at -> factory requires an exact key match -> `GMUI_BASIC` is a child/tab lookup *after*
panel creation, not the value the slot must return) is proven IMAGE fact end to end, all rows
`PROVEN_EXACT`/`PROVEN_EXACT_CONDITIONAL` with VA + sha256 evidence spans. Item #1 gets a genuine new
write-site (`0x0044CB7D`, end of the `CMyActor` constructor, corroborated independently in two other
committed tables from unrelated investigations) but not full closure -- it identifies the global as
the local-player-actor singleton rather than a session object, but no clear/dtor site was found, so
the cardinality-across-relogin question this ticket actually asked stays open and genuinely
STATIC-ON-BRIDGE.

The more important part of this round is not a static fact at all: `PF_GM_PLUGIN_GATE.md` itself
carries an "UNPINNED OPERATIONAL INVENTORY -- NOT IMAGE/DATA EVIDENCE" line stating the bridge
machine's inventory did not find `GameMaster.dll` next to the client at generation time. If still
true, that is a complete, mechanical explanation for the "button visible, click does nothing" symptom
this lane has chased since `RE-104` (six days) -- every gate `RE-104`/`RE-118`/`RE-126`/`RE-164`#2/#4
already proved correct sits *downstream* of a plugin that never loaded. This is flagged to chief/COO/
the owner as something requiring an actual look at the client install; this lane has no client image
and cannot confirm it itself.

### pf-adversary

Not called this round -- no code or new-hypothesis content, only cross-referenced static facts each
independently re-verified by hand against the committed files. `AGENTS.md`'s "call pf-adversary before
every commit when the Agent tool is available" rule is about content changes; recording that fact
plainly here rather than silently skipping it.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

**ไม่มี (บนจอ)** -- static-RE and mailbox only; no wire, no chat command, no server or client boot.
What changed is that P-3 now has one concrete, checkable root-cause hypothesis (is `GameMaster.dll`
present next to the client) instead of an open-ended "still waiting on RE."

### nonclaim

1. Does not claim `GameMaster.dll` is actually missing from the current test environment -- the
   source artifact itself flags its inventory as possibly stale, not IMAGE/DATA evidence.
2. Does not claim `GMUI_1` is the value the original DLL actually returned -- it is the artifact's own
   `[RECONSTRUCTED POLICY -- PROPOSED]`.
3. Does not claim `RE-164` is fully closed -- item #1's cardinality/clear-site question is still open
   and genuinely needs on-bridge disassembly.
4. Does not claim the panel will open once the DLL question is resolved -- a new `GT-164` variant must
   confirm the client-observable layer.
5. No GM shortcut used to skip any step this round -- no game/server boot at all.
6. No GM status granted outside `gm_accounts.json`, no milestone declared.
7. Did not touch `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`/canonical DB/
   `scenarios/world_*.json`/`scenarios/combat_*.json`.
8. No prior history deleted -- `CLIENT_RE_QUEUE.md` edits strike through outdated text instead of
   removing it.

รายละเอียดเต็ม:
`pf_bridge/rounds/GM_20260901_2132_ku3jz6_re164-item3-closed-plus-gamemasterdll-flag.md`
PR: `pf_bridge` #756 / `pirate-force-server` #510

## Round `hw6dix` (2026-09-02T01:29+07:00) -- `/speed` writes the row: DB first, wire second (GM-B, `GT-193` condition (b))

### What changed

`_speed_action` in `gm/chat_command_action.py` went from "compose a wire frame only, touch no DB
row" to **DB FIRST, WIRE SECOND**. It now calls LANE-DB's existing
`store.write_typed_attributes_and_compose_sparse(character_id, {"speed_walk": value})` and composes
the frame from THAT call's read-back, not from the text the GM typed.

The premise of last round's letter to LANE-DB (asking them for an `identity_lo`/`identity_hi`-keyed
overload) was wrong and is withdrawn: `model.Character` has always carried `id` as its first field,
and `session.foundation.selected` IS that `Character` -- the same read site `_selected_speed_identity`
already used. The translation is one line and it belongs in this lane, not in theirs. New read site:
`_selected_speed_character_id` (positive `int` only; `bool` excluded by `type(...) is not int`, and
`0`/`-1` refused because a rowid starts at 1, so those are a leaked sentinel).

Two more pieces worth naming:

* `_speed_store` is now **the one read site** for `session.foundation.lifecycle.store`, shared by the
  run-copy-DB gate and by the write. Before this round the gate read the chain itself; leaving it
  that way would have allowed the gate and the write to mean two different objects, which is a gate
  in name only.
* `SPEED_TYPED_COLUMN = persistence_typed_attrs.column_for(speed_wire.SPEED_FIELD_X)` -- resolved at
  IMPORT time through LANE-DB's own table, never the literal `"speed_walk"` typed twice. If x=7 ever
  loses its column this lane fails loudly at boot instead of refusing silently in front of a tester.

Four new no-frame outcomes, all TYPE-name-only in the audit row (an exception message can embed the
GM's typed text): `no_store`, `no_character_id`, `persist_refused_<ExcType>`,
`persist_readback_unusable`. Pinned in `tests/test_gm_chat_command_action.py`'s event-name contract
table, which enforces completeness, not just correctness.

### The gate that matters

🔴 The run-copy-DB gate (`_speed_db_is_canonical`) used to guard only a SEND. It now guards a
**WRITE**, and it is the only thing standing between this lane and the project rule "never touch the
canonical DB". It fires first and fails closed: a store path that cannot be read counts as canonical
and refuses. `test_the_canonical_db_gate_fires_before_any_write` asserts `store.calls == []`, and
`test_a_shut_version_gate_writes_nothing_either` asserts the same for the version gate -- withheld
means no frame AND no row.

It is still a FILENAME HEURISTIC, exactly as its own docstring has always said. This round made it
load-bearing for more; it did not make it more accurate.

### Why this is `GT-193` condition (b)

`GT-193` (chief's entry, `PENDING interface`) waits on both (a) LANE-DB's sparse x=7 write path on
`main` -- closed `20260901_2213` -- and (b) LANE-GM's `/speed` wiring that CALLS that function.
Before this round step 6 of the entry ("Re-query the same persisted attribute row ... Diff
field-by-field") would have produced an empty diff every time, and the entry would have graded a
frame rather than a memory. The head is chief's to flip; letter
`20260902_0129_LANE-GM-STATUS-speed-writes-the-row-gt193-condition-b-closed.md` asks for it.

### Tests

`SpeedPersistenceTests` (fake store) proves the order, the one-column write, the read-back-not-typed-
text rule (the double reports 9.5 while the GM typed 5.0, and the test asserts both that the frame is
9.5's and that it is NOT 5.0's), no-frame-on-store-refusal, and that neither gate lets a write
through. `PersistenceIntegrationTests` runs the same command against a **real `SQLiteStore` on a real
temp file** and reads the value back through a SECOND store opened on the same path -- the closest a
headless test gets to "the GM logs in again tomorrow" -- plus the f32 rounding agreement for `400.1`
and a refused `1e40` leaving the prior row untouched. It carries its own fd guard on the temp
directory, because a leaked sqlite handle is what killed PR #495 on the Windows gate (`WinError 32`),
a failure Linux never shows.

### เขียว

`python3 -m pytest tests/ -q` = 6622 passed, 327 skipped, 13796 subtests -- เขียว(cloud sanity).
`tests/test_gm_*.py` = 1307 passed, 590 subtests -- เขียว(cloud sanity).

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

พิมพ์ `/speed 800` แล้วขั้นที่ 6 ของ `GT-193` มีอะไรให้ diff จริง -- คอลัมน์ `speed_walk` ใน run-copy DB
เปลี่ยน และเลขบนจอเป็นเลขเดียวกับที่แถวถือ เมื่อวานคำสั่งเดียวกันสร้างเฟรมแล้วลืมทันที

### nonclaim

1. Does not claim `GT-193` passed -- no client is in this round's evidence at all. Only the entry's
   opening condition (b) closed.
2. Does not claim GM-B is done. `NOW.md`'s own rule: code on `main` is not "เสร็จ"; only Panya ticks.
3. The DB-first ORDERING is still `[สมมติของสาย GM - รอ COO ยืนยัน]`
   (`20260902_0017_LANE-GM-ASK-COO-speed-db-first-ordering-change.md`, unanswered). It is live code
   now rather than a proposal; if COO rules the other way the change is one function and
   `SpeedPersistenceTests` goes red.
4. Does not claim the run-copy-DB gate is a cryptographic guarantee -- it is a filename heuristic.
5. Does not claim x=7 is speed proven on screen. `RE-194` runs in parallel and is not a blocker.
6. Did not touch `runtime.py` / `app.py` / `current/pf_login_game_server_v141.py` / canonical DB /
   `scenarios/world_*.json` / `scenarios/combat_*.json` / any LANE-DB file (their method is CALLED,
   not edited).
7. No GM status outside `gm_accounts.json`, no client self-elevation, no milestone declared.
8. GM shortcut used: `/speed` is a GM command; a speed value obtained through it is not evidence that
   a normal player's movement/attribute path works. It is a way to reach a testable state.
9. No prior history deleted -- the docstring line that became false (`"writes no DB row"`) is struck
   through, not removed.

รายละเอียดเต็ม: `pf_bridge/rounds/GM_20260902_0129_hw6dix_speed-persistence-wired-db-first.md`
PR: `pf_bridge` #777 / `pirate-force-server` #523

### pf-adversary (round `hw6dix`, second pass) -- NOT APPROVED, six defects, all six fixed before the draft came off

The subagent ran 20 minutes of real mutation testing in a separate worktree, sha256-compared its
copies against the committed blobs (so it measured the shipped code, not a stale patch), and returned
**Not approved**. Every finding was fixed in a follow-up commit on the same branch, before the PR left
draft. None was deferred.

* **D1 -- `/speed` had durable state and no `undo`.** `_make_action`'s own rule is "AN EFFECT THAT IS
  ALREADY ON DISK HAS TO COME BACK OFF IT" when the outcome row cannot be written. Reproduced: an
  `OSError` on the outcome append left the column at 777.0 while the console printed *"anything it had
  in hand was dropped with it"* -- false. Fixed with `_speed_undo`, which reads the prior value BEFORE
  the write and restores it through `write_typed_attributes` (never the compose variant -- an undo a
  wire-side gate can refuse is not an undo), carried by every verdict from the write down. A column
  that was NULL before cannot be restored (`write_typed_attributes` refuses `None` by design) and
  reports `not_reverted` rather than lying. Control: removing the undo turns 4 tests red, including
  one against a real `SQLiteStore`.
* **D2 -- one word for two opposite durable states.** `refused_speed_<ExcType>` meant both "parse
  failed, nothing stored" and "write committed, composer then failed", and the console printed
  `no blocker recorded` for the dangerous one. Fixed with its own
  `refused_speed_persist_compose_<ExcType>` and a prefix-matched blocker sentence
  (`COMMITTED_ROW_BLOCKER_PREFIXES`) that says the row IS committed. The two pre-existing tests whose
  meaning had silently changed are struck through with the reason and replaced.
* **D3 -- 🔴 the canonical-DB gate authorized a WRITE to the canonical file.** The exact `==` was
  case-sensitive, and `app.py:660` keeps the operator's `--db` string verbatim. Measured as allowing
  `PirateForce.sqlite3`, `PIRATEFORCE.SQLITE3`, a trailing space, a trailing dot, `::$DATA`, and the
  8.3 short name -- all the same file on Windows. Fixed by normalizing (stream suffix, trailing dots
  and spaces, casefold), refusing any `~` short name outright (a string cannot resolve one), and
  adding `os.path.samefile` against a sibling `pirateforce.sqlite3`, which sees through case, 8.3,
  hard links and junctions. Fail-closed on every error. Controls: the old `==` turns 7 tests red;
  dropping `samefile` as well turns 8 red, including a real hard link on a real file.
* **D4 -- the ordering test could not see ordering.** Inserting a compose call ABOVE the write left
  all 134 tests green. Replaced with a test that wraps the composer and records how many rows the
  store had written each time it ran; a compose before the write shows up as a `0`. The same mutation
  is now red.
* **D5 -- `SPEED_TYPED_COLUMN`'s stated purpose had no control.** Hardcoding the literal survived
  everything, because the guard compared the constant against itself -- and so did a first fix that
  compared it against `column_for(7)`, which agrees today. Replaced with an AST guard that reads the
  source and requires the binding to be a `column_for(...)` call, not a constant. `FakeStore` no
  longer copies the literal it forbids. The docstring's "loud boot failure in this lane" is corrected:
  `runtime.py:40` imports this module at module level, so it is the whole server refusing to start --
  a deliberate trade, now stated as one.
* **D6 -- three of the four new refusals are unreachable in production.** `no_store`,
  `no_character_id` and `persist_readback_unusable` cannot occur against a real `SQLiteStore`; only
  `persist_refused_TypedAttrError` can, and the integration test reaches it. The class docstring now
  says which is which instead of implying all four are proven against production shapes.

Also fixed from its two non-defect flags: `unittest.main()` sat mid-file above three classes, so
`python3 tests/test_gm_speed_action.py` ran 29 of 59 tests and printed OK (pytest, and therefore the
gate, was never fooled) -- moved to the end. And its worktree measured `6562 passed / 387 skipped`
against this clone's `6638 / 327`: same total, 60 tests moved passed→skipped, none red, almost
certainly the client-image/capture-corpus modules a sandbox lacks. Recorded rather than smoothed over;
naming those 60 is next round's backlog.

### The design question it said was unanswered, answered here

**When the row is on disk and the frame is not, who owns the divergence?** Two cases, not one:

1. **The audit row could not be written** -> revert. The house rule is "no effect this lane could not
   record", and D1's undo is what makes it true. A NULL-before column cannot be restored and reports
   `not_reverted` instead of claiming success.
2. **The composer or the store failed after the commit** -> keep the row. The DB is the durable truth
   and the value IS that character's speed; the client sees it at next login. But it must be
   distinguishable in the trail, which is what D2's own outcome word and console sentence are for.

**How a tester grading `GT-193` step 6 reads it:** a changed row with an unchanged screen, together
with `refused_speed_persist_compose_*` or `refused_speed_persist_*` on the console, is NOT a FAIL of
the entry -- it is the designed state; record it as a separate observation. The same divergence with
NO such token is something nobody has measured; open a new entry for it. Case 2 is
`[สมมติของสาย GM - รอ COO ยืนยัน]`; case 1 is the existing house rule.

### เขียว (after the six fixes)

`python3 -m pytest tests/ -q` = 6638 passed, 327 skipped, 13805 subtests -- เขียว(cloud sanity).
The 6622/327 pinned earlier in this round's first entry was the pre-fix run; the difference is this
round's own new tests, not a test that had been red.

## Round `c637o1` (2026-09-02T02:5x+07:00) -- the refusal line names the row, and three more refusals stopped vanishing

`COO-DECISION 2026-09-02T01:47+07:00` confirmed DB-before-wire for `/speed` (so that ordering is no
longer `[สมมติของสาย GM]`) and attached a condition: a refusal may not be SILENT. It asks for two
things per refusal -- an immediate chat line the GM reads at the client, and one server-side log line
carrying IDENTITY and the reason. This round delivered the second, widened it after `pf-adversary`
measured it half-done, and asked COO about the first. **`pf-adversary` returned NOT APPROVED on the
first draft with six defects; all six are fixed below, in the same branch, before draft was lifted.**

### What changed in `gm/chat_command_action.py`

1. **`_identity_fields`** -- one builder for `character_id=<rowid|none> identity=<lo>:<hi>|none`, used
   by both printers that carry them. `account=` is not identity: `session.token` is the process-wide
   `--token`, one string shared by every connection.
2. **`GM_CHAT_DROPPED_BEFORE_DISPATCH`** -- a THIRD console token, and `_print_server_drop_way_out`
   behind it, for a well-formed command from an allowlisted GM that the SERVER dropped before
   dispatch: rate limiter, audit-log quota, unwritable audit log. Its reason set lives in
   `chat_command.SERVER_SIDE_DROP_REFUSALS`, beside the constants, exactly as
   `TYPED_COMMAND_REFUSAL_PREFIXES` does for the typo half.
3. **`WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT`** -- a second why-word for the audit failure, chosen when
   the undo ran and did NOT revert.

### The six defects, and the control that proves each fix

* **D1 -- "every refusal reaches this line" was false; 5 of 25 were silent.** Measured through the
  real route: 25 rapid `/speed 400` printed 20 route lines and **nothing at all** for the five the
  rate limiter dropped -- neither `GM_CHAT_NO_BYTES_SENT` (no handler ran) nor
  `GM_CHAT_COMMAND_REFUSED` (not a typing mistake). From an attended chair that is
  indistinguishable from "the route was never wired", which is the state COO named as forbidden.
  Fixed by item 2 above. Control: removing the call kills 3 tests. **Still silent, deliberately, and
  now said in the source rather than a round file: a non-GM's chat, a GM's ordinary conversation, an
  unreadable allowlist, a malformed frame** -- all decided above the `is_gm` check. So "no GM command
  vanishes quietly any more" is STILL FALSE; what is true is that no command from an allowlisted GM
  that parsed (or was command-shaped and throttled) vanishes quietly.
* **D2 -- 2 of 9 new tests were green with the whole feature deleted.** The guard named for the
  account-token mutant was defeated by `identity='GM_ONE'` -- one quote character -- and the
  "cannot forge a second line" test attempted no forgery. Fixed: assertions now extract the FIELD
  VALUE and compare it, a real forgery goes through the only door these fields have (a `.selected`
  whose `id`/`identity_lo` are text), and a new `test_two_rows_in_one_process_get_two_different_lines`
  kills the hardcode and stale-cache mutants that previously survived 199 of 200 tests.
* **D3 -- "the only proven server->client text route is `say_wire`" was refuted by this repo's own
  ledger.** `docs/FUNCTIONAL_COVERAGE.json`'s `chat_input_echo_hypothesis` is `runtime_pass` on
  attended GT-009: the real client RENDERED echoed text over `0xAC52`, through the same shared
  serializer `say_wire` imports, while `0x9F2C` has never been seen on a screen. Corrected in the
  docstring (struck, not deleted) and in the letter, which now puts FOUR options to COO -- the fourth
  being `PROMOTE-153`, the open chief-owned ticket for landing chat echo on a default boot. Neither
  route is usable from this zone today, so the conclusion did not change; the reason did.
* **D4 -- new harm: the line named a row and lied about it.** A first-ever `/speed` on a NULL
  `speed_walk` commits 400.0, loses the audit write, runs an undo that has nothing to restore, and
  printed `blocked_on='...anything it had in hand was dropped with it'` -- next to `character_id=`
  naming the row that was still at 400.0. Fixed by item 3. Control: collapsing the two words back
  into one turns `test_an_unrevertable_row_is_reported_as_still_in_place` red.
* **D5 -- the fields are per-CHARACTER, not per-connection.** `store.select_character` has no
  exclusivity check, every connection shares the process `--token`, and `identity_hi` is `0` for
  every character this server creates. The claim is now "WHICH ROW", not "WHO", in the code, the
  tests and the letter -- and the round file no longer cites a multi-connection `GT-193` run this
  strictly-serial server cannot host.
* **D6 -- the line's own contract file had zero coverage.** `tests/test_gm_chat_no_bytes_line.py`
  gained `TheIdentityFieldsOnEveryCommandTests` and `TheServerSideDropLineTests`; its `FakeSelected`
  now carries identity fields, so the six other commands that share this line are pinned too.
* **D7 (suspicion, not a live defect) -- the two fields were the only ones bypassing
  `console_safe`/`_one_line`.** Now sanitised like every other field, with the reason stated: being
  the only unsanitised fields is a discipline hole, not a proof of safety.

### Mutation controls, re-measured after the fixes

| mutant | tests killed (before -> after) |
|---|---|
| delete both identity fields | 5 -> **18** |
| account token in their place (quoted) | **0** -> **18** |
| both fields hardcoded to the suite's own values | 1 -> **12** |
| `identity=` lo/hi swapped | 4 -> **14** |
| never print the server-drop line | n/a -> **3** |
| D4 collapsed back to one why-word | n/a -> **1** |

### Measured, not assumed: where the three states separate

* **typo** -- `/speed not-a-number`, `inf`, `nan`, `1e400` are refused by `parse_gm_command` UPSTREAM
  of `_speed_action` and print `GM_CHAT_COMMAND_REFUSED ... usage='speed <value>'`. Consequence:
  `_speed_action`'s own `refused_speed_<ExcType>` branch is NOT reachable through the real route, and
  is defence in depth against a hand-built `GmCommand`.
* **server drop** -- `GM_CHAT_DROPPED_BEFORE_DISPATCH ... why=rate_limited character_id=.. identity=..`
* **DB refused** -- `GM_CHAT_NO_BYTES_SENT ... why=refused_speed_persist_* character_id=.. identity=..`
* **frame sent** -- `LANE_GM_CHAT_ACTION speed route=action`, and no refusal line at all.

### เขียว

`python3 -m pytest tests/ -q` = **6663 passed, 327 skipped, 13821 subtests** -- เขียว(cloud sanity).
`tools_bridge/pf_gate_preflight.py --repo <server>` = **PREFLIGHT PASS** (cp874 + no new skips), per
`COO-DECISION 20260902_0148` item 2.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

Two things. Grep one console line and know WHICH character row a refused `/speed` was about --
yesterday every refusal line said `account='GM_ONE'`, the process-wide `--token`, identical on every
line. And see a line at all when the rate limiter eats a command: yesterday `/speed` typed too fast
produced total silence, which reads exactly like dead wiring.

### nonclaim

1. Nothing here is client-observable. This is the server host's stderr. A GM at a real client still
   sees nothing when `/speed` refuses -- that is the half the letter to COO is about.
2. Does not claim `GT-193` passes or that GM-B closes. No client is in this round's evidence.
3. Does not claim silence is eliminated -- four refusal classes above the `is_gm` check stay silent
   on purpose, and the source says so.
4. Does not flip either text-route gate and does not build a second composition route.
5. The identity fields name a ROW, not a person and not a connection.
6. GM shortcut used: `/speed` is a GM command; a readable refusal line is not evidence that the
   ordinary player attribute path works.

## Round `ibxaf0` (2026-09-02T04:2x+07:00) -- GM-A measured one layer below the latch: a census really ships on every hop

### What this round did NOT touch, and why that is the headline

`COO-DECISION 20260902_0346` (item "ใครทำอะไรต่อ") tells this lane, in as many words, not to touch
`gm/say_wire.py` or `gm/chat_command_action.py` for the on-screen half of `/speed` this round -- chief
holds both files under `COO-DECISION 0345`. So this round changed **no source file at all**, in this
lane's zone or anywhere else. It added one test file and two letters.

### The gap that was actually open

`NOW.md` records the owner's own criterion for GM-A: warp across SEVERAL maps in a row and find the
NPCs on EVERY map. `tests/test_gm_warp_position_confirmed.py`'s KA1A class pins the fix that makes
that possible (each cross-scene hop clears the once-per-login census latch) but stops there: it
asserts flags and event tokens and never dispatches another frame afterwards, and its chain hops to
`departure_scene + 1 .. + 7`, scene ids produced by arithmetic rather than taken from the registry.
Between "latch cleared" and "a frame with bodies in it" sit five more gates, every one of which fails
closed and silently: the arrival anchor (`runtime.py:7945-7967`), a registered composer
(`:8184-8194`), the composer's own `login_entry_allowed` admission (declined arm at `:8339`),
composition itself (`:8326`), and scene 1's walk-before-census disjunct.

### Measured, headless, on the real dispatcher, flagless boot

`tests/test_gm_warp_chain_census_shipped.py`, 10 tests. Twelve consecutive cross-scene warps in ONE
login (eleven registry scenes plus one revisit -- the chain is read from the composer registry, not
written down, and guarded against shrinking below eight), each followed by one ordinary runtime poll:

| destination | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 14 | 130 | 3 again |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| actors on the arrival census | 62 | 109 | 87 | 66 | 56 | 69 | 57 | 94 | 51 | 81 | 41 | 62 |

Then the whole reachable world, asked of the production gate rather than listed: bare `/warp <scene>`
reaches exactly 13 scene ids today (`1, 2, 3-11, 14, 130`), and **12 of the 13 ship an arrival census
with a non-zero actor count**, scene 2 included (97, from the runtime's own bg0002 arm, which a chain
built from the lane registry alone would never have touched). Scene 1 is the one exception and is
asserted AS an exception.

And the way a tester actually plays: land, walk, then type the next `/warp`. That leaves the
departure map's coordinates in `last_target_pos`, which the arrival census reads before it falls back
to the destination's spawn -- so the walking chain asserts BOTH the queued buffer and the stamped
`census_anchor_record` belong to the destination and its own spawn. That is GT-172's F-1 arriving
through a different door.

### pf-adversary: NOT APPROVED on the first pass, ten defects, all ten answered before un-drafting

The subagent ran mutation experiments in its own worktree and came back with the finding that mattered
most: **the first version of this file asserted labels, not bytes**. A census label's actor count is an
integer the LANE hands the runtime -- `runtime.py:8270-8272` coerces it and the runtime's own comment
there calls it untrusted -- so two mutants that ARE the bug being hunted stayed green:

* blank `lane_pc`/`lane_frame` at `:8270-8271` -> every hop ships `..._SCENE7_INITIAL_56` with an empty
  buffer behind it. That is the empty map GT-182 reported, and the first version said 9 passed;
* cache hop one's bytes and replay them for every later hop -> scene 130's arrival ships scene 3's dock
  NPCs under scene 130's label. Also 9 passed.

Every assertion now goes through the queued buffer: the count is read back off the wire with
`world_population_handoff.wire_count_of`, and the buffer is compared byte for byte against a census
composed independently for that scene at that scene's own spawn.

Two more findings were corrections to what this lane had WRITTEN, not to the code:

* the walking-chain docstring claimed a stale anchor "puts the bodies where the player is not". The
  subagent measured it: same actor count, same buffer length, same multiset of bytes -- only the ORDER
  actors are listed in changes, which `runtime.py:8237-8248` says in as many words. The claim is now
  the narrow one it can support, and the sentence that overstated it is gone rather than softened;
* the "whole reachable world" test visited scene 1 FIRST, and the session boots in scene 1 -- so the
  warp was a same-scene no-op that returned before the resync ran (`runtime.py:5660`). Scene 1's
  silence was being "proved" by a session that had never warped anywhere. It is visited LAST now,
  arrived at from another map, with `gm_warp_selected_scene_resynced_1` asserted so it cannot go
  vacuous again. The published "12 of the 13" was re-measured after that fix, not carried over.

The rest: once-per-scene latching is asserted (a second poll must ship nothing), scene 2's own label
spelling is pinned (renaming it to the home census's spelling is the "dock NPCs into Prison Exile
Island" mix-up), `world_census_refused` gets its own test, and every helper that reads the registry has
a minimum-size guard so a shrunken registry cannot leave a test asserting nothing.

### Mutation control (separate worktree, deleted; live tree clean)

Measured on the 10-test file that is being merged, not on the draft the subagent reviewed:

| mutant | before this pass | after |
|---|---|---|
| neither latch field cleared on a hop (the pre-`67fe6fe` behaviour) | 5 red | **6 red** |
| only `world_census_sent = False` removed | 5 red | **5 red** |
| only `world_census_refused = False` removed | **0 red** | **1 red** |
| `last_target_pos = None` removed (stale anchor) | 1 red | **1 red** |
| `lane_pc`/`lane_frame` blanked: label says 56, wire is empty | **0 red** | **5 red** |
| hop one's bytes replayed for every later hop | **0 red** | **4 red** |
| composed around the previous map's anchor, stamp still correct | **0 red** | **4 red** |
| the lane census never latches `world_census_sent` | **0 red** | **1 red** |
| scene 2's label renamed to the home census's spelling | **0 red** | **1 red** |

The `last_target_pos` row is still the whole reason the walking-chain test exists: every other test in
this file warps from a standing start, so none of them can see a stale anchor.

### The two asterisks GT-192 needs before the owner runs it (letter to COO, `0425`)

1. A warp BACK to scene 1 mid-session stays empty until the character moves one step. That disjunct
   is held shut ON PURPOSE (`KA1A-AMENDMENT 20260901_1120`) and this lane did not touch it -- but the
   owner's criterion says "every map", so without one line in the ticket she will read a deliberate
   gate as GM-A failing again and burn an attended round. Pinned as its own test, which goes red the
   day the disjunct opens.
2. The ticket should name a closed list of maps to warp to. Outside those 13 ids a bare `/warp` is
   REFUSED by name, not silently empty -- but a tester picking numbers off the 330-scene catalog
   cannot know that from the ticket as written.

Both are chief's to apply: `GT-192`'s head is his ticket, not this lane's.

### ผู้เทสจะทำอะไรได้ที่เมื่อวานทำไม่ได้

Read one test run and know, before booting a client, which maps a chained `/warp` session will show
NPCs on and which one will not. Yesterday the only answer to "does hop eight work?" was the attended
round itself.

### nonclaim

1. **Wire layer only.** Census actions are composed and queued; no client is in this round's
   evidence. Nothing here may be read as "the NPCs were seen".
2. Does not claim GM-A passes, does not close it, does not announce a milestone. Only Panya ticks.
3. GM shortcut used: `/warp` is a GM command, used to reach each map. Reaching a map with GM is not
   evidence that ordinary travel to it works.
4. Does not claim scene 1's silence is a defect -- it is a gate this project chose, recorded here so
   nobody claims "every map" without the asterisk.
5. No source file changed this round: `runtime.py`, `app.py`, `pf_login_game_server_v141.py`, the
   canonical DB, `scenarios/world_*.json`, `scenarios/combat_*.json`, LANE-DB's files and other
   lanes' queue headers are all untouched, and so are `gm/say_wire.py` and
   `gm/chat_command_action.py` (chief holds those this round).
6. No history deleted.

## Round `lmqf69` (2026-09-02T05:2x+07:00) -- P-3: the four look-alike failures become four different verdicts, before the game boots

### The gap this round closed

P-3 has produced exactly one observation since RE-104 opened on 2026-08-27: the GM button is visible
and the click is silent. RE-164 finished the job of listing what can produce that one observation,
and the list is the problem -- four unrelated failures are indistinguishable from the player's chair:
`GameMaster.dll` absent [GM-IMG-001]; present but the export decorated so `GetProcAddress` returns
NULL [GM-IMG-001/002]; loaded and resolvable but slot `+0x04` hands back an empty key so the
dispatcher returns before the factory [GM-IMG-003/006]; or everything above fine and the gate is
somewhere else entirely [RE-104, RE-118, RE-126].

`patches/gm_plugin/build_vs2008.bat` already checks the export name and the CRT imports -- of a
FRESH BUILD, on a machine with `dumpbin`, by reading dumpbin's human text with `findstr` word
boundaries. It cannot look at the DLL that is actually **installed** beside the client (build copy
and installed copy are two files, and only one of them is the one the game loads), it cannot run
without the VC toolchain, and it cannot run in this repository's test suite.

### What landed

`src/pirateforce_foundation/gm/plugin_image_check.py` -- a stdlib-only PE32 reader that parses the
export directory, the import descriptor table and the resource directory itself, so
`_CreateGameMaster`, `CreateGameMaster@0` and `?CreateGameMaster@@YAPAXXZ` are told apart from
`CreateGameMaster` by structure, not by regex. One verdict per file: `missing` / `no_such_dir` /
`unreadable` / `not_pe` / `wrong_machine` / `not_a_dll` / `no_exports` / `export_decorated` /
`export_forwarded` / `export_missing` / `manifest_missing` / `image_ok`, each with a sha256 and a
one-line reason, as grep-able cp874-safe console tokens (`GM_PLUGIN_IMAGE ...`). EVERY blocking
problem is printed, not only the first: one attended session cannot afford to discover them one
rebuild at a time. It also compares the built copy against the installed copy and **fails** (exit 1)
when they differ, because a rebuild whose flag never reached the compiler produces byte-identical
output and the tester then re-tests yesterday's binary.

CLI, one line on the bridge before the game boots (there is no installed package -- `PYTHONPATH=src`
is required, and paths with spaces must be quoted):

    PYTHONPATH=src python -m pirateforce_foundation.gm.plugin_image_check \
        --dll  <path>/GameMaster.dll --client-dir "<client install>"

`tests/test_gm_plugin_image_check.py` -- 44 tests on synthetic PE32 images assembled field by field
(this clone has no client image, no DLL, no VC toolchain; a test that needed a real DLL could only
skip here, which this lane has already lost a round to).

### pf-adversary rejected revision 1, and the reason is the interesting part

Twelve defects on this module alone. Five mattered:

1. **The suite could not fail.** Six independent parser mutations -- `span = raw_size`,
   `span = virtual_size`, `sections[:1]`, deleting the ordinal-only guard, deleting the
   `NumberOfRvaAndSizes` bound, deleting the no-import-directory early return -- all passed 30/30,
   because every fixture had ONE section, `VirtualSize == SizeOfRawData`, and 16 data directories.
   The fixture builder now emits three sections with the export directory in the SECOND one, one
   section whose VirtualSize is smaller than its raw size and one whose VirtualSize is larger, and
   the directory count (with the optional-header size that follows from it) is a parameter. Measured
   after the fix: 9 mutants tried, 9 killed.
2. **A mistyped path manufactured the finding.** `C:\Pirate Force\Client` unquoted on cmd.exe
   arrives as `C:\Pirate`, and revision 1 answered that with "the RE-164 operational note is
   confirmed for this machine". A directory that does not exist now has its own verdict
   (`no_such_dir`) whose text says it means nothing about the client install.
3. **The tool died mid-report on the bridge console.** Export names were decoded with
   `errors="replace"`; U+FFFD has no cp874 mapping, so a corrupt or packed DLL raised
   `UnicodeEncodeError` inside `print()` after two lines -- no verdict, no sha256. Now
   `errors="backslashreplace"`, with a test that plants a high byte in an export name.
4. **`crt_missing` was a red light for a DLL that works.** Revision 2 of the plug-in allocates from
   the CLIENT's CRT (it walks the client's import table), so a `/MT` build is not wrong. Demoted to
   an advisory.
5. **`image_ok` covered two ways to fail anyway.** A forwarded export is byte-identical to a real one
   in the name table (now read through `AddressOfNameOrdinals` + `AddressOfFunctions` and reported as
   `export_forwarded`), and a `/MD` build with no embedded RT_MANIFEST is refused by the side-by-side
   loader with 14001 -- the plug-in README's own triage row -- which `build_vs2008.bat` cannot catch
   because it never calls `mt.exe`. Now `manifest_missing`.

Cross-validated against real MSVC-built PE images found on this machine (32-bit and 64-bit
launchers): machine, PE32/PE32+, DLL flag, section walk with mixed VirtualSize/SizeOfRawData, import
names and RT_MANIFEST all read correctly. **The repo has no real PE fixture** -- the export-directory
path is exercised by synthetic bytes only. That is a real gap and the round file records it.

### Evidence tier -- the line that must travel with every quote of this module

`image_ok` means "none of the file-level failure modes this module can see is present in these
bytes". It is NOT evidence that the GM window opens. The client-observable half of P-3 still needs a
person at the screen, and still needs the GT ticket asked for in
`notes_to_chief/20260901_2225_LANE-GM-DELIVERY-*`.

The claim "GameMaster.dll is missing from the owner's install" remains, per RE-164 and this lane's
own 21:32 letter, an UNPINNED OPERATIONAL observation. This module does not settle it; it gives
whoever stands in front of that install a one-line way to settle it, with a sha256 attached.

### The other seven findings are in the plug-in source, and two are HIGH

`pf-adversary` also re-reviewed `patches/gm_plugin/GameMaster.cpp` (the review this lane promised
last round). `DllMain` still resolves the wstring constructor with
`GetModuleHandleW(L"msvcp90.dll")` -- the exact side-by-side base-name ambiguity `FindClientCrt()`
was written to remove, and worse in consequence (a `_Container_proxy` allocated on one MSVCP90
instance's heap and freed by the other). And `PF_GM_SLOT0_TOUCH_PLUS4` defaults to writing a
guessed-size subobject into client-owned memory, while its documented escape hatch (`=0`) produces
exactly the state the source itself calls "strictly worse than the dead button we already have".
Both are unfixed here: `patches/` is not this lane's declared write zone and this clone has no
Windows SDK to compile-check a change. Letter to chief carries the findings and the patch shape.

## Round `ha492g` (2026-09-02T06:2x+07:00) -- the `/speed` refusals, verified from the bytes by this lane, then hardened by pf-adversary against its own first draft

### Why a second test file for something already tested

COO-DECISION `20260902_0346` gave this lane one instruction for the first round after chief's notice
PR reached `main`: confirm that ALL NINE refusal paths of letter `0311` ship `SPEED DENIED` --
"เทสของคุณเอง ไม่รับคำพูดใคร" (your own test, taking nobody's word for it). chief's
`tests/test_gm_speed_denied_notice.py` is a good file and this is not a review of it; the order was
to verify the claim from a DIFFERENT footing, because a proof that shares the claim's assumptions
cannot contradict it.

Chief's PR is on `main`: merge `d2d61ff`, code commit `35f1eeb`, `main` tip `98d2767` at the start of
this round.

### What landed

`tests/test_gm_speed_denied_nine_paths.py` -- 23 tests, 24 subtests, no source change anywhere.

Three things make it an independent check rather than a copy:

1. **Its own byte parser.** `_decode_local_talk_notice` writes the layout out as literals -- channel
   id at `pc[16:18]` little-endian, the nested vital's `u8tag(0x0B, version)` at `pc[18:20]`, payload
   at `pc[20:-2]`, each string a `0x48` tag + a 4-byte little-endian BYTE length + UTF-16LE -- and
   imports nothing from `channel_message_hypothesis`. A day where the project's encoder and its own
   decoder drift TOGETHER is the one failure an encode/decode round-trip cannot see, and it is red
   here. Both fields outside the payload are read from the bytes: the channel id (the assertion
   pf-adversary's channel-swap mutant walked straight through in round `aa9ajr` when it was made
   against the constant the test passed in) and the vital_version byte RE-132 pinned and GT-101
   measured as fatal to a real client.
2. **The paths are proven distinct.** Every path runs through the real
   `make_gm_chat_command_action` with the real `legacy`, and is identified by the word it wrote to
   the audit ndjson ON DISK, not by `session.events` in memory. The words are then asserted to be
   nine DIFFERENT words, matched against letter `0311`'s list AND re-derived from the module's own
   `OUTCOME_*` constants (the letter lives in `pf_bridge`, which is not this repository).
3. **The parser is shown to be a parser.** Bodies of 1, 10, 12 and 40 characters, composed through
   `legacy.make_runtime_vitals` from a payload the test file encodes itself, decode back exactly --
   so the offsets are not constants tuned to one 12-character frame.

Two guards chief's file does not carry, plus what a refusal costs:

* `test_every_path_prints_both_console_lines` -- `GM_CHAT_NO_BYTES_SENT` (half (b) of COO-DECISION
  `0147`, the line this lane warned in letter `0419` would disappear) AND `GM_CHAT_NOTICE_SENT`
  (`GT-193` step 9's own token) on ALL NINE paths, not the one a regression test happened to pick.
* `NoRefusalMayGoOutSilentTests` -- an `ast` pass over BOTH places a `/speed` verdict is built:
  every `return` in `_speed_action` (a bare `return` and a `raise` included) and the dispatcher
  branch that calls it, whose sibling `else` already builds a `_Verdict(None, ...)` of its own.
* `WhatARefusalStillCostsTests` -- paths 8 and 9 say DENIED while the row already holds the new
  value. Pinned, not fixed: it predates the notice and is a property of when `_speed_undo` fires.

### pf-adversary found four HIGH defects in the first draft of this file

Run against the draft (15 tests), every finding reproduced as a mutant. All four are fixed above and
re-killed in a throwaway `git worktree`, never in the live tree:

| finding | what stayed green in the draft | fix |
|---|---|---|
| D1 | the canonical-DB gate moved BELOW the write: screen DENIED, ndjson `withheld_speed_canonical_db`, and 400.0 in the canonical row | every pre-write path asserts the store was never called |
| D2 | a stray `state/pirateforce.sqlite3` in the process CWD -- `app.py`'s own default -- collapsed EIGHT drivers onto path 1, per-path tests still green | store paths are absolute, inside the test's own temp dir |
| D3 | a tenth refusal written as a bare `return`: no notice, no audit row, no console line | the AST guard rejects a valueless `return` and any `raise` |
| D4 | a tenth refusal built in the DISPATCHER branch, one `def` above what the guard read | the dispatcher branch is asserted to be one call and nothing else |
| D5 (med) | `vital_version` flipped to 1 -- outside the payload, so no round-trip sees it | the parser reads `pc[18:20]` and asserts the tag and the version |
| D6 (med) | renaming the drivers made the console test pass with ZERO subtests | `drivers()` derives 1..9 and raises on any other numbering |
| D8 (low) | `NINE_PATHS` cited a letter that is not in this repo | every word re-derived from `OUTCOME_*` constants |
| D9 (low) | `GT-193`'s own `GM_CHAT_NOTICE_SENT` token was never asserted | asserted on every path |

### Measured: the mutants that had to die (all in a `git worktree`, live tree untouched)

| mutant | result |
|---|---|
| `SPEED_DENIED_NOTICE_TEXT` -> `"SPEED DENIE"` (11 chars) | 23 red |
| composer switched to `GM_GLOBAL_CHANNEL_ID` (`0x9F2C`, the LOCKED channel) | 22 red |
| `vital_version` 0 -> 1 in the shared codec | 22 red |
| path 5 back to `return _Verdict(None, ...)` (silent) | 7 red |
| canonical-DB gate moved below the write (D1) | 1 red |
| bare `return` as a tenth path inside `_speed_action` (D3) | 1 red |
| `raise` inside `_speed_action` | 1 red |
| a silent verdict in the dispatcher's speed branch (D4) | 1 red |
| the nine drivers renamed (D6) | 4 red |
| stray `state/pirateforce.sqlite3` in the CWD (D2) | 23 GREEN -- the point: the file no longer depends on it |

### What this does NOT say

Every byte here is composed in-process and asserted in-process. **Nobody has seen `SPEED DENIED` on
a screen.** `GT-193` step 9 is the only thing that can say that. What is asserted is the action this
module RETURNS; `runtime.py`'s send site is one layer above and is not exercised.

**Eight of the nine are reachable from a chat line; the ninth is not.** `commands._require_number`
and `speed_wire.parse_speed_value` apply the same `float()` + `math.isfinite` rule, so no typed value
can pass the grammar and fail the composer: path 4 is a backstop reached here only under
`mock.patch`. And the refusal a GM will actually meet -- `/speed fast` -- is refused ABOVE all nine
at `parse_gm_command` and is **still silent on screen** (chief asked COO in `0545`).

**The nine are nine returns of one function, not every refusal of the command.** The dispatcher guard
closes the one other site that exists today; a refusal invented at a third site is still outside what
any test in either file can see. That question went to COO in this round's letter.

## Round `q6p0pb` (2026-09-02T08:5x+07:00) -- the string tag byte three of this lane's codecs never wrote, and the capture red that was hiding behind it

Consuming ka1-B's letter `notes_to_chief/20260901_2215_KA1B-TO-LANE-GM-third-untagged-string-module-plus-attr-wire-corrections.md`.

**What changed.** `gm/cheat_wire.py`, `gm/command_wire.py` and `gm/teleport_wire.py` all wrote and read
`uint32le byte_count + payload` for their string fields. The client's own string helpers push a **type tag
byte first**, so the real shape is `tag(1) + uint32le byte_count(4) + payload(N)` = **5+N bytes, not 4+N**:
`0x44` for the narrow helper (`0x0089A6D0` W / `0x0089A740` R) and `0x48` for the wide one
(`0x0089A810` W / `0x0089A880` R). Both directions of all three modules now write and require the tag, and
reject the old 4+N shape rather than decoding it.

**Evidence, checked against the source before acting, not taken from the letter.**
`pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv`
sha256 `e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2`, rows 565/566 (CheatVital),
580/613 (TeleportVital aux text, and it also names that field's offset: `DEREF(+0x1C)+0x10`),
6266/6267/6279/6280 (GM_RunGMCommandVital's two strings). Every row's `base_span_sha256` is byte-identical
to the span each module already pinned in its own docstring -- **which is a reason to look for an outside
tiebreaker, not a reason to trust the delta on its own**: it is the same IMAGE lineage re-reading the same
helper bytes, exactly the argument this lane accepted in the other direction for `attr_wire`'s x30.

The tiebreaker exists and is in this repository: `channel_message_hypothesis.py` has carried
`CHANNEL_WSTRING_TAG = 0x48` / `CHANNEL_WSTRING_HEADER_SIZE = 5` against the **same helper VAs** since
2026-08-18, corroborated against real captured GT-006 frames; and `current/pf_login_game_server_v141.py:21-24`
records a **live client rejecting a frame** (`ErrorData=0x2A7A`) because that helper's string went out with
`0x44` where `0x48` was required. 🔴 That corroboration is for the WIDE tag. The narrow `0x44` in
`cheat_wire.py` has the delta rows and the helper disassembly and nothing else -- no captured frame in this
project has ever carried a `0x44` string a client accepted. It is the least-supported of the three.

**Nothing player-visible moves.** `make_teleport_aux_payload`/`make_teleport_vital_frame` have no production
callers (the live cross-scene warp is `warp_executor.py` -> `legacy.make_login_teleport`, whose payload sets
aux presence = 0), `CheatVital` is not wired into `dispatch.py`/`runtime.py` at all, and the `0x51E9` path
only decodes captured bytes and already keeps the raw bytes when the decode raises.

**🔴 The red this uncovered, which is the important part of the round.**
`PF_V5_FIELD_VALIDATION.md` ([MEASURED][CAPTURE]) has TeleportVital **R: 190 mismatches, reason
`STRING_TAG`**, at the field identity whose `DELTA` component is the dedup_key of **delta row 613 -- the very
field this round corrected** -- and **W: 188 mismatches, reason `TAG`, at `ORDER:4`** =
`PF_SERIALIZER_FIELDS.tsv` row 570 = `TeleportTarget.scene_id`, with no delta component at all. Still red at
V5. A first draft of this round's docstrings wrote that the 190/188 result "predates the tag correction and
says nothing about field order"; **that was false in both halves** and pf-adversary caught it before commit.
The correction is still applied, for the reasons above, but `gm/teleport_wire.py` is now labelled a reference
codec **KNOWN to disagree with capture**, with the first written hypothesis for why (the static plan declares
the aux sub-object ungated at row 579 while the real message gates it, so the validator hunts a `0x48` where
an absent object begins) marked `[PROPOSED]` in the module. Letter opened to chief this round to route it.

**Tests.** `test_gm_cheat_wire.py` / `test_gm_command_wire.py` / `test_gm_teleport_wire.py` /
`test_gm_command_capture.py` / `test_gm_command_dispatch.py` updated. pf-adversary's second finding was that
eight guards went **silently vacuous** when the shape changed -- they pinned byte offsets that are now the tag
byte, so they asserted on the tag check and never reached the branch each was named after, including
`cheat_wire`'s own `MAX_STRING_LENGTH` DoS cap and the capture-quota regression guard round `whoaop` added.
All pins moved, three tests added (missing-tag rejection in two modules, a real even-length truncation case),
and two now assert on the message text so the same disarming cannot happen silently again.

**Two gates in this repo caught this round's own mistakes, and both are worth naming.**
`test_tree_is_cp874_safe.py` / `test_gm_source_is_cp874_safe.py` rejected the `U+1F534` marker character
this round put in two of the modules -- their failure message names the pull request that was closed
automatically the last time a non-cp874 byte reached the Windows gate, so the marker is `!!` now.
`test_gm_say_gate_lock.py::test_only_say_wire_may_call_the_shared_channel_codec` then rejected the
corroboration paragraph itself: no module in this package may so much as **name** the shared channel codec,
because naming leads to calling and calling walks around `say_wire`'s gate. The corroboration is still cited,
by pointing at row `0x9F2C` of this document instead.

**nonclaim.** The tag byte's own semantics (domain, signedness, sentinels) are NOT proven -- `PF_HANDOFF_V1.md`
8.5 gives proven meanings only for `0x2A`/`0x12`. This round reproduces a byte; it does not claim to know what
that byte encodes. `GM_RunGMCommandVital` remains `NOT_OBSERVED` (0 captured frames), so nothing here is
confirmed by a real frame of that message. No GM status was granted to any account and no milestone moved.

## Round `0aij4z` (2026-09-02T15:2x+07:00) -- the GT-192 preflight, and the seam that lies about scene 2

`gm/warp_chain_preflight.py` (new) + `tests/test_gm_warp_chain_preflight.py` (new). No existing
file in either repository is touched, no production code path changes, nothing is wired into
`runtime.py`.

### What it is for

`GT-192` is GM-A's acceptance entry: a GM types `/warp <scene>` across the owner's closed list
(`2-11`, `14`, `130`, closing with `1`, per `COO-DECISION 20260902_0544`) inside ONE login and
must see a normal NPC population on every map. An attended round is the most expensive resource
this project has, and until this round a tester who saw an empty map had no way to tell three
different things apart:

1. the census-latch bug the entry exists to catch -- a real FAIL;
2. **scene 1**, which is empty ON ARRIVAL BY DESIGN and fills one step later
   (`KA1A-AMENDMENT 20260901_1120` holds the walk-before-census disjunct shut on purpose);
3. **scene 2**, whose roster does not come from a `lane_hooks` composer at all.

The tool prints one ASCII line per scene before she boots, so an empty map is graded against a
stated prediction instead of being a surprise.

### The trap it was built around -- MEASURED, not reasoned

The obvious implementation is to ask `world_population_handoff.handoff_for_arrival` for every
reachable scene and print its `actor_count`. Measured on this clone, that seam answers
`kind='clear'`, `actor_count=0` **for scene 2**, because `lane_a_scene_census.skipped_scenes()`
records scene 2 as `reserved_by_a_runtime_branch` and its roster ships from the runtime's own
bg0002 arm (`runtime.py:8536`). Scene 2 is the FIRST map on the owner's list. A preflight built
the obvious way prints `0` for it and sends a tester hunting a bug that is not there.

Scene 2 is therefore asked of its own arm with the same arguments that call site passes
(`count_source=COUNT_SOURCE_FULL_ROSTER`, default `actor_count`) -- and because `runtime.py` is
chief's file and this lane cannot stop it changing, a test READS THAT CALL SITE'S SOURCE with
`ast` and goes red if the arguments drift. Both halves are pinned: that the seam really does say
clear/0, and that the tool does not repeat it.

### What it measured (the whole reachable world, this clone)

The production gate `warp_executor.warp_no_coords_live_target`, asked for all 330 scene ids in
`gm/scene_catalog.py`, answers **exactly thirteen**: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14,
130` -- the owner's list, independently derived. Anything outside it is REFUSED BY NAME, which
is a different outcome from an empty map and must not be graded as one.

Actors composed on arrival: scene 2 = 97 (runtime arm) - 3 = 62 - 4 = 109 - 5 = 87 - 6 = 66 -
7 = 56 - 8 = 69 - 9 = 57 - 10 = 94 - 11 = 51 - 14 = 81 - 130 = 41 - scene 1 = 0 on arrival,
108 after one step. `empty_by_design=1 empty_unexplained=none`.

### Design rules this module keeps, and the test that kills each

~~* **The count is read off `world_population_handoff.handoff_for_arrival`.**~~ **STRUCK the same
  round it was written** -- pf-adversary D1 measured that seam answering with a full roster for a
  scene the runtime DECLINES, because it never sees the composer's own admission check. See the
  correction below; the count now comes from calling the composer, the route the runtime takes.
* **`0` never stands in for "do not know."** `actor_count` is `None` whenever a number could not
  be derived. `_lane_count` returning `0` on a non-census handoff survived the first five
  mutations this lane ran and was only killed by a test added afterwards, driven against the one
  scene whose seam really answers `clear`.
* **Fail closed and NAMED.** Every failure returns a row carrying the exception type; a preflight
  that crashes on one map takes the other twelve with it.
* **The nonclaim rides the OUTPUT, not only the docstring.** The last line the tool prints says it
  predicts what the server composes and never what the client draws. A tester reads a console, not
  this repository.
* **The reachable set is asked of the production gate, never listed.** The day LANE-A opens a
  scene this covers it without an edit.

### nonclaim

1. No GM status is granted or used, no account is touched, no socket is opened, no frame is sent,
   nothing is wired into `runtime.py`, and no flag is flipped. The tool runs with
   `production_allowed` false everywhere.
2. **No milestone moves.** P-1, P-2, P-3, GM-A, GM-B are exactly where they were. This is a tool
   for reaching a testable state, not evidence that anything works.
3. It predicts the SERVER side only. Nothing here says the client renders any of these actors --
   that is `GT-192`'s client-observable layer and no number printed here substitutes for it.
4. `GT-192`'s own header is chief's (opened round `liq4ri`); this lane did not touch it. The debt
   it still carries -- no status tag, and step 3 still saying "pick e.g. scene 4/5/6/8/10" rather
   than the closed list `COO-DECISION 20260902_0544` ordered at 05:44 -- is reported in
   `pf_bridge/notes_to_chief/20260902_1526_LANE-GM-TO-CHIEF-*`, not fixed here.
5. Six of the thirteen scenes on the chain (`7 8 9 10 11 130`) print
   `LANE_A_CHOOSE_NPC_ROSTER_SKIPPED ... columbus_placement_index_collision_needs_runtime_scene_guard`
   at hook registration. The census still ships (the counts above stand); what is skipped is the
   ChooseNPC roster, i.e. CLICKING an NPC. That is chief's Columbus work in R304, reported not fixed.

### `pf-adversary` on this round -- **NOT APPROVED on the first design**, ten defects, all taken

The result came back BEFORE anything was undrafted, which is `COO-DECISION 20260902_1446` and is
the rule this lane's own failure the previous round caused to be written. Everything below was
measured by him with a control, most of it against the REAL dispatcher, not argued.

**What he could not break, stated first because it is the load-bearing half.** He built a control
that drives the real dispatcher (reusing `test_gm_warp_chain_census_shipped.py`'s harness), warps
to every reachable scene in one login, reads each count back OFF THE QUEUED BUFFER with
`wire_count_of`, and diffed it row by row against this tool: **thirteen scenes, zero
disagreements.** Scene 1's after-the-step number is right (driven twice, a 10-unit and a
9000-unit step; only the byte ORDER differs). The hostility splice cannot move scene 2's number.
The output is ASCII and cp874-safe and the `LANE_HOOK_*` noise goes to stderr, not stdout. It
grants nothing and sends nothing.

| # | What he measured | What this round did |
|---|---|---|
| **D1 (HIGH)** | The tool read two of the runtime's THREE census gates. The third -- `lane_a_scene_census.scene_is_open_to_players`, reading `login_entry_allowed` -- is the only one whose purpose is to say "this map is shut on purpose". With scene 10 shut he measured the tool printing **94 actors** while the real dispatcher shipped **nothing**. Scenes 17 and 126 are shut in the registry TODAY. The tool would have sent a tester into a deliberately closed map and, by its own NOTE line, told her to file it as the census bug. | **The count no longer comes from the seam at all.** It comes from CALLING THE COMPOSER, the runtime's own route, and is read back off the composed BYTES. A shut map gets its own answer word `shut_to_players` and its own summary bucket -- it is never `empty_unexplained`. |
| **D2 (HIGH)** | `actor_count` is the THIRD POSITIONAL parameter of `build_bg0002_population`. The AST guard read only keywords, so `legacy, anchor, 12, scene_id=...` shipped **12 actors** on the wire with both test files GREEN and the tool still saying 97 -- while the guard's own failure message names that exact drift. He also noted `count_source` is a LABEL the arm records, not a count selector, so the guard's one substantive assertion pinned a string with no effect on the number. | The guard now asserts `len(call.args) == 2` -- the position that carries the count. `count_source` stays pinned but is named in the test as the weaker check it is. |
| **D2b (HIGH)** | Adding an ALIASED second call site kept `len(calls) == 1`, because the guard counted only `ast.Attribute` calls. Wire shipped 7; everything green. | The guard counts the NAME in the source text first (exactly one occurrence), then walks both `ast.Attribute` and `ast.Name` calls. |
| **D3 (HIGH)** | `runtime.py:993` arms the census only when no lane/scenario object is active AND `second_password_mode == "required"`. Measured: with `bypass`, **every scene ships nothing**. The tool printed twelve nonzero predictions and said nothing about it, so the single most likely cause of all thirteen maps being empty was unnamed -- and its NOTE line actively instructed the tester to file a deliberate containment rule as a finding. | A `PRECONDITION` line LEADS the output, and a test reads `runtime.py`'s arming condition from source so it cannot drift. |
| **D4 (MED)** | `render()` threw the `note` field away, so a `/warp` REFUSED BY NAME, a shut map, and the real bug all printed the same line and were all swept into `empty_unexplained` -- while the module docstring insisted those must not be confused. `test_a_scene_warp_refuses_is_not_reported_as_an_empty_map` was green on a field the tool showed nobody. | Every row prints `why=<its own note>`. |
| **D5 (MED)** | A composer that RAISES was labelled "the composer declined". The runtime distinguishes them by effect: a decline latches `world_census_sent` for that map, a raise latches `world_census_refused`, which **silences every remaining map of the login**. The tool collapsed them and picked the harmless word. | Separate answers, and the raise row names the exception type and the latch it would cause. |
| **D6 (MED)** | `preflight_for(True)` printed Port Royal's NAME and then "the registry does not pin a spawn" -- rendered as an unexplained empty map -- while `preflight_for(1)` said 108. Two entry points, opposite verdicts, one scene. The test added mid-round PINNED the wrong answer. | `type(scene_id) is not int` is refused by name at the top; the bad test is replaced by one that requires the bool NOT to be answered as Port Royal. |
| **D7 (MED)** | `test_the_gate_this_module_asks_is_the_production_gate` re-typed the function's own comprehension and compared a value to itself. He replaced the whole function with a hardcoded thirteen-id tuple: **21 passed**. | The test now MOVES the gate and requires the answer to follow. |
| **D8 (MED)** | `main()` -- the only thing a human runs -- had no test; a junk argument died with a bare `int()` traceback and printed nothing; it returned 0 whether every scene resolved or none did. Two fail-closed branches had never executed, in a file that argues a branch no test kills is not a branch. | `main()` refuses by name, returns non-zero when any scene is empty for a reason it could not explain, and has four tests. Both branches now have one. |
| **D9 (LOW)** | `empty_by_design=1` read identically as "one scene" and "scene 1". | `chain_scenes=<count>` and bracketed id lists. |

**All four of his own mutants were re-run after the fixes and all four now die**: the positional
`actor_count`, the aliased second call site, the hardcoded reachable list, and (from the real
registry file, not an injection) scene 10 shut -> `source=shut_to_players`, `shut_on_purpose=[10]`,
`empty_unexplained=[]`.

**His closing question -- "when the preflight and the runtime disagree, what in the output tells
her?" -- is answered for the lane arm and OPEN for the other two.** The lane arm now takes the
runtime's own route, so there is no second opinion left to disagree with. Scene 1 (home arm) and
scene 2 (bg0002 arm) are still predicted through routes the runtime merely resembles, and nothing
in the output says so. What stands behind those two is
`test_gm_warp_chain_census_shipped.py`, which drives the real dispatcher -- a test, not a line on
her console. Named here rather than closed.

**One more defect the FULL SUITE found after his pass, and it is worth naming as loudly.** The
first scene-1 branch reached the count through `world_population_handoff.handoff_for_arrival` --
and `tests/test_world_population_bg0015.py::test_only_the_population_seam_imports_this_module` is
ANOTHER LANE'S GATE naming the exact files allowed to be call sites of that seam. This module is
not one of them, and it went red. The branch was rewritten to ask the home arm directly
(`world_population.build_world_population`) rather than the gate widened: going around another
lane's gate to make a diagnostic prettier is how a diagnostic starts altering dispatch, which is
the rule `gm/chat_command_action.py` carries in capitals for its own console line. Scene 1's
number is now the DEFAULT ceiling rung; the runtime's staircase argument can select another, and
this tool does not model that.

**Not measured, carried forward as his own suspicion:** `main()` uses the DEFAULT scene registry,
not a boot-loaded one. `preflight_for` accepts an injected registry (that is how D1's fix is
tested), but nothing yet reads the registry a scenario boot would install.

## Round `xodi87` (2026-09-02T17:xx+07:00) -- the preflight says which numbers it derived and which it copied, and the last map of the chain finally prints its number

Same file, no new module: `gm/warp_chain_preflight.py` + `tests/test_gm_warp_chain_preflight.py`.
Three items, all of them opened by the previous round's own written-down debt rather than by a new
letter.

**1. `actors_after_one_step` -- a number that was computed and shown to nobody.** The owner's chain
CLOSES on scene 1, and `COO-DECISION 20260902_0544` says that map is judged only after one step.
The count for that step has been in `ScenePreflight.actor_count` since the module shipped, and a
test named `test_it_still_says_what_she_gets_after_the_step` asserted it was there -- but `render`
printed `actors_on_arrival=0` for that row and dropped it. The console she actually reads carried
NO number for the last map of her own chain. That is pf-adversary D4 (a field computed with care
and never printed) repeating one field over, in a module already fixed for it once. Every row now
prints `actors_after_one_step=`; scene 1 prints `108`, every other row prints `n/a` -- never `0`,
because `0` reads as a bug and this tool has measured nothing about what a step does on a map whose
census already shipped on arrival.

**2. `route=` -- pf-adversary's closing question from round `0aij4z`, answered.** He asked: when
the preflight and the runtime disagree, what in the OUTPUT tells her which to doubt? Eleven rows
walk the runtime's own route (`composer.compose`, counted off the bytes). Scenes 1 and 2 have no
composer and are a RECONSTRUCTION of a call inside `runtime.py`. Both printed identically. Now
every row carries `route=production_composer` or `route=mirrored_runtime_arm`, a `ROUTE` legend
line prints once under `PRECONDITION`, and the summary ends with `mirrored_not_measured=[2,1]`.
The legend also names the boot flag this tool does not model: `--world-census-actors` selects
another rung, for scene 1 alone.

**3. The home arm is mirrored from the runtime's own expression, and it was not.** `runtime.py`
takes scene 1's count from `world_population.census_count_for_dispatch()` on the flagless boot
`GT-192` asks for. This module passed `effective_actor_count()` with a `count_source` hand-picked
beside it. **Measured before changing anything: the two build BYTE-IDENTICAL frames today (both
108 on the wire), so the printed number was never wrong.** The branch now copies the expression,
and scene 1's call site gained an AST gate of its own.

> 🔴 ~~What differed was the recorded reason -- `measured_client_ceiling` where the runtime records
> `full_census` -- exactly the misreport `census_count_for_dispatch`'s own docstring exists to
> prevent, and a difference that would only start moving bytes on the day a client ceiling is
> finally measured.~~ ~~Scene 1's call site also gained the AST gate scene 2 already had.~~
>
> **STRUCK THE SAME ROUND IT WAS WRITTEN, by pf-adversary, and both halves were false.**
> `build_world_population` **overwrites** whatever `count_source` a caller passes
> (`world_population.py`, the `count < CENSUS_COUNT and count == len(available)` branch): both
> spellings record `identity_resolved`, neither ever records `measured_client_ceiling` or
> `full_census`. Swept **every legal ceiling** (`None` plus 1..115, 116 builds of each spelling):
> the two agree on bytes, wire count and recorded reason at **every** value -- there is no day
> when it starts to matter -- and this module never reads `count_source` at all. **The change is a
> no-op.** It stays for the only reason that survives measurement: a mirror should copy the
> EXPRESSION its original evaluates, so the day chief's flagless rung changes, this branch changes
> with it instead of agreeing by coincidence. And the two gates are **not** the same strength:
> scene 2's pins the NUMBER (no positional count, no `actor_count` keyword, therefore the
> default); scene 1's can only pin the SHAPE of the branch the count comes from, and neither says
> anything about the anchor. The cause was reading `census_count_for_dispatch`'s docstring and not
> reading `build_world_population` twenty lines above the call being mirrored.

**Mutants run before the adversary pass, five on this module and three on `runtime.py`
(reverted, never committed) -- all eight die:** `_after_one_step` always `n/a`; `render` drops
`route=`; scene 1 claims `production_composer`; the old hand-picked `count_source` restored;
`_after_one_step` printing a number on every row; and in `runtime.py` a literal count at the home
call site, an aliased second call site, and the flagless branch no longer calling
`census_count_for_dispatch()`.

**Still not closed, carried forward:** the two mirrored rows are still reconstructions, and no
AST gate can turn a reconstruction into the real thing -- what stands behind them is
`test_gm_warp_chain_census_shipped.py` driving the real dispatcher, a test rather than a line on
her console. And `main()` still uses the DEFAULT scene registry, not a boot-loaded one.

### Round `xodi87` continued -- pf-adversary: **NOT APPROVED**, ten items, all ten accepted

He ran before the final push (`COO-DECISION 20260902_1446`), and he was right about the two things
that mattered most. Struck the false claim above rather than deleting it.

| # | What he measured | What the round did |
|---|---|---|
| **D2 (top)** | The whole stated rationale for the `count_source` change is false in three places (source comment, test docstring, this doc). `build_world_population` overwrites the caller's `count_source`; swept all 116 ceiling values, the two spellings never differ. The module does not even read the field. | Retraction written where each claim was. The change stays, relabelled as the no-op it is, with the only reason that survives: a mirror copies the expression. |
| **D1 (top)** | The new scene-1 AST gate walked ALL of `runtime.py` and asked only that two substrings appear *somewhere* among assignments binding the name. He inverted the two arms (flagless boot ships 20, tool still prints 108, tester files a false FAIL) and separately put a literal `count = 20` at the live site with a dead decoy function at the end of the file. **Both green.** | The gate is scoped to the ENCLOSING FUNCTION and now reads the conditional itself: the arm selected by `world_census_actor_count is None` must call `census_count_for_dispatch()`. Both his mutants now fail. |
| **D3** | `_framing_lines()` returned `len(render(()))`, so three assertions compared `render`'s output to its own. Control run: the same mutant (PRECONDITION printed three times) failed FOUR tests against the previous revision and zero against this one -- the round **weakened** the gate. | Framing lines are named by identity (`FRAMING_MARKERS`), each asserted to appear exactly once, and no line may be neither a scene row nor framing. His mutant now fails four tests. |
| **D6** | `route=production_composer` promises the number came off the queued bytes at the pinned spawn. Both promises could be broken with the file green and the console byte-identical (read the lane's label instead of the bytes; compose at the origin). The rows advertised as MEASURED had no gate, while the two reconstructed rows had two. | Two behavioural tests with a fake composer whose label (56) disagrees with its bytes (7), and one that records the anchor it was called at. Both mutants now fail. |
| **D8** | The round refused to print `0` in the new field and kept printing it one field to the left, including for a `/warp` REFUSED BY NAME -- a fabricated number for a map nobody can enter, which `ScenePreflight`'s own docstring forbids. | `actors_on_arrival=n/a` wherever nothing is known; `0` only for the two rows where it IS the prediction (held until you move, shut on purpose). |
| **D5** | `route=none` reaches the console and the legend defined only two values -- a mistyped scene number is how she meets it. | The legend names all three routes and points at `why=` for the four causes `none` covers. |
| **D7** | The runtime composes scene 1 at the position she STEPPED TO (`last_target_pos`); this tool composes at the pinned spawn, and the legend listed only the `--world-census-actors` caveat. Measured anchor-insensitive today (count identical at spawn, spawn+50, origin, and 99999) -- so latent, not live. | The legend now names BOTH caveats and says which one is measured-harmless today. No gate is claimed for either. |
| **D4** | "Scene 1's call site also gained the AST gate scene 2 already had" overstates it; the two are different shapes and the scene-1 one pins no number. | Struck above and corrected in the module docstring. |
| **D9** | Two new tripwires on chief's file could fire on a legitimate refactor and misname the cause. | Failure messages rewritten to say what actually broke and that this is a GM-lane diagnostic's dependency on his call site, not a rule about it. |
| **D10** | Dead branch in `_after_one_step`; three module lines never execute under the test file. | The branch is named as unreachable-today rather than deleted or left silent. |

**Attacks of his that failed, recorded because they are the half that carries weight:** the alias
and `getattr` defeats of the scene-1 gate both die; the `n/a` rule could not be made wrong for any
real row (`_after_one_step` keys on `source`, not on `on_arrival`, which he confirmed is the right
key); "byte-identical today" is TRUE and he reproduced it; no scene was found where a step changes
the census after the arrival dispatch; and the preflight-side pin is backstopped by a real
behavioural oracle. He also confirmed the round touched no file outside this lane's zone.

## Round `et2ux4` -- GT-193 came back [FAIL], and this door now withholds by default

`GT-193` was the first time anything this lane composed reached a real client's screen. It went
badly, and the round file `pf_bridge/rounds/GM_20260902_1824_et2ux4_*` carries the full account.
What is recorded here is the mechanism, because a future round reading only this file must not
re-open the door by accident.

**What the attended round measured** (results letter `20260902_1755_KA1A-R303-RESULTS-*`,
owner at the keyboard): `/speed 300` composed and sent
`LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL (74 bytes)` carrying `00 00 96 43` = 300.0 "followed by
trailing zero fields". The character showed HP 0, money 0 and died. Afterwards: 426 inbound
frames, **zero of them non-heartbeat** -- the revive buttons produced no server traffic at all.
The client locked itself out and the attended round lost it until a re-login. The run DB was
healthy the whole time (`speed_walk = 300.0`, hp 100/100), so nothing was persisted: the client
reacted to bytes this lane put on the wire.

**What "trailing zero fields" are, named from this clone's own composer.** `encode_block` always
emits both sections of the DBAttribute body. A door that sets one BasicAttr field and nothing else
therefore announces an ActorAttr section with a **zero mask and no fields**. The composer's first
return value (`pc`, 63 bytes) ends
`... 12 40 00 2a 00 00 96 43 32 00 00 00 00 00 00 00 00 05 01 0b 00`; the DBAttribute body itself
is 30 bytes and the FRAME the dispatcher counts -- the `(74 bytes)` in the tester's tally -- is the
second return value. (The first draft of this section called the 74 "the body"; pf-adversary
measured that it is not. Three different objects, now each named.) `cash` (offset `0x0A8`, mask
`1<<11`) is one of the fields the empty section carries, and money read 0 on screen.

**What was NOT proven, and is not claimed anywhere in the code:** which byte killed the character.
The tester's own nonclaim is explicit. The hold below is a correlation that earns a hold, never a
root cause.

**The mechanism.** `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` is an EMPTY SET on `main`.
`speed_wire.declared_empty_sections()` computes the shape's signature -- which DBAttribute sections
the door announces with nothing in them, today `("actor_attr",)` -- and `_speed_action` withholds
unless that exact signature is in the cleared set, or whenever the signature cannot be computed at
all. It fires **before** the DB write, so a held frame never leaves a moved row behind it, and it
returns the same `SPEED DENIED` LocalTalk notice every other refusal returns -- letter `0311`'s
nine refusal paths are now ten.

> ~~"withholds when a section is empty and the shape is not cleared ... a future door that fills the
> section opens this gate by itself"~~ -- **struck in the same round it was written.** pf-adversary
> (D6) measured what that meant: filling the section was an independent opening path that never
> consulted the clearance, so a lane adding an ActorAttr field would have shipped a new,
> never-measured ~90-byte shape to an attended tester, on the strength of a causal link the R303
> letter explicitly disclaims. The clearance is now keyed on the signature and is required on
> **every** send.

**How it opens.** One entry added to the set, with the measurement that earned it named in the
comment above: an attended round that sees a client accept a shape, or an RE result that says which
shape is safe. Not by a lane deciding it is probably fine, and not by changing the shape.
`tests/test_gm_speed_shape_hold.py` runs against the shipped default and is what turns red if
anyone clears a shape without evidence.

**What the hold does NOT prove.** Nobody has seen `SPEED DENIED` on a screen: the same R303 letter
records `SPEED DENIED count in this run = 0`, because the command succeeded that round and no
refusal path fired. So `/speed` does not now send *nothing* -- it sends a **different**, also
never-client-observed frame, on every invocation instead of none. That is a trade (one chat line
against a character, a client and a re-login), not a proof, and no test in this lane may be named
as if it were one.

**What GT-193's other half is, and whose:** on re-login the sheet read **400**, not 300, because
~~`speed_walk` has no login read~~ -- the client is painting `CLIENT_CONSTRUCTION_DEFAULTS`
(`persistence_attr_compose.py:289`). That is LANE-DB's CORE-REQUEST (letter `1035`, COO approved
`1143`), untouched by this lane.

🔴 **STRUCK, NOT DELETED, round `gj77z5`: LANE-DB LANDED IT.** PR #605 put the login read on `main`
(`session.py:192` -> `login_speed.resolve_for_character` -> `player_wire.py:266`). A re-login after
`/speed 300` now paints **300**, not 400. Measured this round with both `/speed` locks held: the
command sends **zero bytes**, and the **next login frame** carries `f32(300.0)` where it carried
`f32(400.0)` before. So the two locks shut this lane's own door while the login door beside it
carries the same field (BasicAttr `+0x54`, x=7) with the same number one re-login later -- and
`GT-193`'s recovery step is a re-login. Named for the COO in letter `20260903_0529`; **this lane did
not act on it alone**, because `COO 1847` ruled "the DB write continues as before" in as many words.

### Round `et2ux4` -- chief's two asks on `warp_chain_preflight` (letter `1712`)

(a) The `PRECONDITION` was stdout line 1 and the tester still met it at roughly line 29, because
importing the package writes 28 `LANE_HOOK_REGISTERED`/`LANE_A_CENSUS_SKIPPED` lines to stderr
first. It is now printed to stderr **above the package imports**, guarded on `__main__` so no
importer sees it, and duplicated rather than moved so a redirected `*>` capture is unchanged.
(b) The "a skipped scene is not an empty scene" warning lived in the module docstring, which a
tester does not open. It now rides the existing `NOTE` framing line, with the map number and its
actor count read off the row rather than typed in.

## Round `hj2cry` (2026-09-02T20:38+07:00) -- `/speed` stops sending, and the manifest step the plug-in build never had

### `SPEED DEFERRED`: the door is shut from a second, independent side

`COO-DECISION 20260902_1847` (`pf_bridge/notes_to_chief/20260902_1847_COO-DECISION-lane-gm-stop-
sending-speed-as-an-attr-frame-now.md`), after `GT-193` locked the owner's client out of an attended
round: **`/speed` may not put `LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL` on the wire until LANE-DB lands
the `speed_walk` login read on `main`.** The route refuses and prints one pure-ASCII line whose
first two words are `SPEED DEFERRED`. **The DB write continues as before** -- the decision is
explicit that only the outbound frame stops.

`speed_wire.SPEED_LOGIN_READ_LANDED` / `send_deferred()` is that gate, and it is deliberately NOT
the shape hold widened. The two answer different questions and neither implies the other:

| gate | question | owner |
|---|---|---|
| `SHAPES_CLEARED_BY_A_REAL_CLIENT` | has a real client been measured accepting **this shape**? | LANE-GM (an attended round or an RE result) |
| `SPEED_LOGIN_READ_LANDED` | does the number the client would paint **survive the next login**? | LANE-DB (`COO-DECISION 20260902_1846`) |

Both must open for a byte to leave, they are owned by different lanes, and each is pinned open and
shut by a test in both directions. Whichever lane moves first cannot cost an attended round alone.

**It is not auto-detected**, and that is the decision this round most wants read: a heuristic that
guesses "LANE-DB's login read looks landed" and guesses wrong reopens the exact door that locked a
real client. `COO 1847` forbids guessing in the same letter ("do not guess which field killed the
client and then fix your guess"), so it is a literal a round edits with its evidence named.

### What moved, and the reasoning that was struck to move it

~~"the shape hold fires **before** the DB write, so a held frame never leaves a moved row behind
it"~~ -- **struck**, one round after it was written, by `COO 1847`'s third item. Both gates now
stand **below** the write. The screen-disagrees-with-the-row state that paragraph feared is now
accepted deliberately: ~~`speed_walk` has no login read either way, so the row is what a later
login-read can honour~~, and the frame is what killed a client. It also keeps `GT-193` step 6 (diff
the row) gradeable at all. **(Struck round `gj77z5` -- the login read is on `main` since #605, so
that row is no longer inert; see the paragraph above.)**

The shape check is now measured off `stored` -- the store's own read-back, the very number the frame
beneath it would carry -- rather than off the typed value, so it no longer leans on the
"the signature cannot depend on the value" pin to be legitimate. That pin is kept anyway, because it
is what makes the signature a stable **key** for the clearance set.

### The one thing this lane decided rather than was told

`COO 1847` says "refuse and print", and its test requirement is "pin that **no bytes** go out on
this route". `COO-DECISION 0345` had ordered every `/speed` refusal to reach the screen through the
`SPEED DENIED` LocalTalk notice -- **and a notice is bytes**. The deferral path returns no action at
all, notice included, tagged `[ASSUMPTION OF LANE-GM, AWAITING COO]` in the source and asked back in
`pf_bridge/notes_to_chief/20260902_2038_LANE-GM-ASK-COO-speed-deferral-drops-the-on-screen-
notice.md`. The narrower reading is the one that cannot cost an attended round if it is wrong: the
GM loses one on-screen sentence, and the console still says `SPEED DEFERRED`.

The AST guards that forbid a silent refusal were **narrowed, not loosened**: a `_Verdict` built
outside `_speed_denied` is allowed to be exactly two things, and the action-less one must carry
`OUTCOME_SPEED_DEFERRED` **and** a `line_printed=` argument -- silent on the screen is only
acceptable while it is loud on the console. A third still turns red.

### `mt.exe`: every DLL this repo's build script produced was unloadable

`COO-DECISION 20260902_1948` item 2, from ka1-A's measurement in attended R304: `patches/gm_plugin/
build_vs2008.bat` never called `mt.exe`, so its DLL had no embedded `RT_MANIFEST` while importing
`MSVCR90.dll`. Windows answers `LoadLibraryW` with **14001** for that combination and nothing in the
plug-in runs -- button visible, click silent, **indistinguishable from the bug the plug-in exists to
fix**. The `GT-207` PASS was on a build a human patched by hand.

New `patches/gm_plugin/find_mt.bat` searches PATH, `%WindowsSdkDir%`, both `Microsoft SDKs\Windows`
trees and `%VCINSTALLDIR%bin`, and **fails loudly naming every place it looked** -- never quietly,
because a quiet skip ships the unloadable DLL. `build_vs2008.bat` embeds before every check (the
checks and the SHA256 must describe the image that gets installed), adds `check 0/4` that reads
`RT_MANIFEST #2` back **out of the built DLL** (`mt.exe` exiting 0 is not the claim that matters),
and deletes a stale `GameMaster.dll.manifest` first so an old one cannot be embedded into a new DLL
against the wrong CRT assembly. `install.bat` refuses to copy a DLL with no embedded manifest.

**NONCLAIM, and it is the important line of this section: none of those three scripts has ever been
run.** This clone has no cmd, no VC9, no `mt.exe` and no Windows. What is claimed is "the step
ka1-A measured as missing is now in the script", not "the build is green". `P-3` therefore does NOT
move to "waiting for Panya to tick": `COO 1948` sets that bar at *the script in the repo producing a
loadable file by itself*, and only the owner's machine can show that.

### Round `selrsl` (2026-09-02T22:2x+07:00) -- the manifest check stops accepting a manifest the loader never reads

`plugin_image_check` used to answer **"an RT_MANIFEST entry exists in the root resource
directory"**. `pf-adversary` reported in round `hj2cry` (D13) that this is not the question: a DLL's
activation context is built from resource **id 2** (`ISOLATIONAWARE_MANIFEST_RESOURCE_ID`) and from
nowhere else, so a manifest embedded at id 1 -- the EXE id, which is what
`mt.exe -outputresource:GameMaster.dll;1` writes -- reported `image_ok` and still answered
**14001** at load. That is the worst shape this module can produce: a green light on a file that
cannot run, pointing a tester at a bug in code that never executed.

Tightened under `COO-DECISION 20260902_2147` item 2. `_manifest_resource_ids` now descends the
RT_MANIFEST type entry into its id-level subdirectory and returns the ids; `has_embedded_manifest`
is `2 in ids`. `PeFacts.manifest_resource_ids` carries them so the two shapes say different things
on screen -- "no manifest, rebuild with revision 5" versus "a manifest at id 1, re-embed at `;#2`"
-- and the console line now reads `embedded_manifest=no manifest_ids=1`, which is enough to tell
them apart from a log alone, with no file in hand.

**Why this is not a new false red.** The one DLL anybody has measured LOADING on the owner's machine
(ka1-A, attended `GT-207`, build 1) was embedded with
`mt.exe -manifest GameMaster.dll.manifest -outputresource:GameMaster.dll;#2` -- id 2 -- and
`build_vs2008.bat` revision 5 both embeds at `;#2` and reads back at `;#2`. Every path anyone has
run stays green; only the hand-embed at the wrong id turns red, and it was already red at load.

**NONCLAIM, unchanged and important:** this reads the resource TREE, not the manifest TEXT. An id-2
entry whose XML names the wrong assembly version still reads as present here. Nobody has measured
that shape, so no verdict claims it. And nothing in this module has been run against a real
`GameMaster.dll` in this clone -- there is no Windows, no VC9 and no PE fixture here.

**The rule itself is unmeasured, and that is stated in the code, not only here.** Nobody in this
project has embedded a manifest at id 1 and watched a Windows loader decide. It ships as a BLOCKING
verdict rather than an advisory on a cost argument, not on proof: the remedy it prints (re-embed at
`;#2`) is correct for a DLL either way and costs one `mt.exe` run, while the false GREEN it replaces
already cost an attended round. **The negative control that would refute it**: build one DLL
embedded at `;#1`, load it on the owner's machine, and see whether `LoadLibraryW` succeeds. Put to
COO in `notes_to_chief/20260902_2252_LANE-GM-ASK-COO-id-2-*`.

**pf-adversary refused this diff twice over, and the second refusal was the important one.** The
first descent bounded its offsets with `_need`, which bounds the FILE. Given a type-24 entry
pointing into `.data`, where sixteen planted bytes parse as a directory with an id-2 entry, it
answered `embedded_manifest=yes manifest_ids=2` for an image carrying no manifest anywhere -- the
false green this round exists to delete, reintroduced by the deletion. Offsets are now bounded by
the resource data directory's own Size. Eleven mutants of the new code (type filter, both string
name filters, all three bounds, the id-2 test, the leaf-entry rule, the named-id message, and both
halves of the loud-root/quiet-child split) were applied by hand and every one of them turns a test
red.

~~**What still is not wired, said plainly:** no script RUNS this module. `build_vs2008.bat` only
echoes its command line, and the gates that actually block a build or an install are
`findstr /c:".rsrc"` -- which, in those scripts' own words, proves an image has A resource
directory, not a manifest at id 2. So the tightening is real for `GT-207`'s step 0, which a human
runs by hand, and not yet for the pipeline. Asked in the same letter.~~ -- **struck in round
`p7q74c`, not deleted: it stopped being true in `pf_bridge#909`** (round `b8xrod`), where
`install.bat` revision 3 started RUNNING this module and refusing on its verdict. It is still true
of `build_vs2008.bat`, which echoes the command line and gates on `.rsrc`.

### Round `p7q74c` (2026-09-03T03:3x+07:00) -- a refusal that can be reported instead of only obeyed

`COO-DECISION 20260903_0148` item 7 revises the same COO's `20260902_2342`: the id-2 rule keeps
blocking, but `install.bat` must take `PFGM_FORCE=1` and install anyway, printing the real verdict.
The reason is written into the batch: **this rule has never read a real DLL.** The one DLL this
project has watched load -- build 1 of `GT-207`, whose GM window opened on screen at 18:54 -- has
never been past this checker. A rule that refuses that file at two in the morning with no way past
blocks `P-3` by our own hand, and no lane can help until the next round.

**Why it is not fail-open, in the four properties a test now grades:**

- the variable has no default anywhere in either repository, and only the literal `1` counts, so the
  owner has to type it;
- it is reachable from the checker's refusal and from nothing else -- not the `[STOP]` guard about
  an existing `GameMaster.dll` (that one is about destroying the artifact this project has failed to
  obtain since 27 Aug, and stays unforceable), not the `.rsrc` `[FAIL]`, not any warn-and-copy
  branch;
- it prints `[FORCED] verdict=<real> rules=<the rules that failed>` in capitals, keeps the full
  report on disk, and repeats the line under the `[OK]`, because the `[OK]` and the SHA256 are what
  a person screenshots;
- `tests/test_gm_plugin_image_check.py` walks the batch as a block graph and requires EVERY edge
  from `:pfgm_refuse` that can reach `:do_copy` to carry `PFGM_FORCE` and `=="1"` -- an
  unconditional `goto`, a deleted `exit /b 1` that falls through, a jump guarded by some other
  variable, or a second escape edge each turn it red. The previous version of that test forbade one
  spelling of one jump; pf-adversary named that gap in round `kv2vjk` (D5) before this feature
  existed, and this is the shape it asked for.

The two tokens are read from the checker, never re-typed into the batch: `console_lines()` now
prints `GM_PLUGIN_IMAGE <label> failed_rules=<list>` directly under the verdict, listing EVERY rule
of `CONSOLE_RULES` the image breaks rather than only the one the verdict names (an image can break
two), `none` when the file passed, and `none_evaluated` for `missing` / `no_such_dir` /
`unreadable`, where no byte was read and naming a rule would claim a test that never ran. A checker
older than this round prints no such line; the batch says so in words instead of printing an empty
`rules=`.

**pf-adversary refused the first draft of this, and the refusal is the reason the paragraph above
is true.** Thirteen defects; the shape of the first three is one shape:

1. **The test graded the shape of a line, not the property.** It asserted the refusal block
   *contains the substring* `exit /b 1` and that an escaping line *contains* `PFGM_FORCE` and
   `=="1"`. Three mutants passed the whole 8,234-test suite with a refused DLL installing every
   time: `REM exit /b 1 -- removed` (the statement is gone, the substring is not, and control falls
   straight into `:pfgm_forced` below); `if **not** "%PFGM_FORCE_FLAG%"=="1" goto pfgm_forced` (one
   word, polarity inverted, both substrings still present); and `set "PFGM_FORCE_FLAG=1"` two lines
   above, which leaves the guard line byte-identical while nothing ties the flag to the environment
   at all. The tests now read the EXECUTABLE statements (`_batch_statements` drops comments and
   `echo`), require the last one to end the script, compare the guard whole, and pin the assignment
   chain from `%PFGM_FORCE%` line by line. Ten batch mutants tried afterwards, ten red.
2. **The only test of the new Python token lived in the class the gate skips.** On a gate-shaped
   checkout, nine of nine mutants of `failed_rules` passed -- including renaming the printed token,
   which silently turns every forced install into "this checker is too old" and sends the owner to
   report the wrong thing. The Python side is now graded by unguarded tests that run everywhere;
   sixteen mutants tried afterwards, sixteen red.
3. **Four scoping properties held by luck.** Making the `[STOP]` guard itself forceable, making the
   `.rsrc` `[FAIL]` forceable, routing `:pfgm_no_tool` into the forced banner, and deleting
   `set "PFGM_FORCED=1"` were all green. The check had scanned a 17-line window that began after
   the `if exist` line; it now forbids the variable in every statement above `:pfgm_image_check`
   and allows exactly one jump into the forced branch in the whole file.

Four defects were runtime rather than test-coverage, and each is fixed in the script:

- `%PFGM_OUT%` is a fixed path that every later run deletes -- including the next, successful one
  -- so the only durable trace of a forced install was console scrollback. The forced branch now
  APPENDS the report to `%TEMP%\pf_gm_forced_installs.log`, which nothing here deletes, and says to
  send that file instead.
- `PFGM_FORCED` was the one variable the script never cleared, and `setlocal` inherits the caller's
  environment: a person who typed `PFGM_FORCED` (one letter off, and `[FORCED]` is the word the
  script shouts a dozen times) made the next fully CHECKED install print "THAT [OK] MEANS COPIED,
  NOT CHECKED" with both evidence tokens empty. Cleared at the top now.
- The banner asserted "the verdict above is a finding about these bytes" over `verdict=unreadable`
  and `verdict=missing`, where the checker's own comment says no byte was read -- laundering a
  failure to open a file into a statement about its contents, in capitals. Those two now get their
  own wording, selected by the `failed_rules=none_evaluated` the checker already prints.
- `failed_rules=none` claimed "every rule ran and passed" for a /MT build, where `manifest_id2` is
  never asked. The line now carries `not_evaluated=` as a third fact.

**NONCLAIM.** Nothing here has been run on Windows, `PFGM_FORCE` has never been set by anyone, and
no DLL has been forced. `P-3` does not move. What is claimed is that the escape exists, is scoped,
and cannot be exercised silently -- and that claim is now measured by mutants rather than asserted
in a comment.

## Round `dotoho` (2026-09-03T07:1x+07:00) -- the runtime key that opens `/speed` for ONE value, without opening either lock on `main`

**What the round was asked to do.** COO-DECISION 2026-09-03T06:46+07:00
(`pf_bridge/notes_to_chief/20260903_0646_COO-DECISION-lane-gm-the-row-keeps-being-written-and-the-
trial-opens-at-runtime-not-on-main.md`), item 2, cutting a loop this lane had reported rather than
guessed at: `GT-218` -- the attended round whose entire purpose is to try ONE deliberately-safe
`/speed` value -- cannot boot until both of this door's locks are open, and `COO 2147` point 3
forbids opening either until that round has happened and has a result. Neither side could move
first. The COO's cut, in his own words: "ไม่มีล็อกไหนถูกเปิดบน `main` ทั้งสองคงค่าเดิม · ทางเปิดคือ
**เกต runtime** รูปเดียวกับ `PFGM_FORCE=1`".

**What shipped.** `PF_SPEED_TRIAL=<one value>` in the process environment admits `/speed <that one
value>` and nothing else.

- `gm/speed_wire.py` gains `SPEED_TRIAL_ENV`, `trial_opening()`, `trial_admits()` and
  `trial_console_field()`. Nothing in that section edits `SPEED_LOGIN_READ_LANDED` (still `False`)
  or `SHAPES_CLEARED_BY_A_REAL_CLIENT` (still empty), and a test asserts both are still shut IN THE
  SAME CALL that puts a frame on the route. The gate BYPASSES the locks for one value; it does not
  open them, and a future round that implements it by flipping a constant instead turns that test
  red.
- `gm/chat_command_action.py` reads the gate ONCE, above both holds, into a local
  (`trial_admitted`) that both gates then read. Two separate reads could see two different
  environments -- another thread, a test patching mid-call -- and produce the one combination
  neither gate was designed for.
- **The key WRAPS the two holds; it is not a second term inside their conditions.** The first draft
  of this round wrote `if speed_wire.send_deferred() and not trial_admitted:` and turned
  `tests/test_gm_speed_denied_nine_paths.py::_assert_the_deferral_branch_holds_one_reason` red --
  correctly. That pin is pf-adversary's (round `ha492g`, D6): he wrote `if
  speed_wire.send_deferred() or <anything>:` and measured 276 tests green while a silent refusal
  wore COO `1847`'s audit word. An AST cannot tell a term that widens a hold from one that narrows
  it, so the pin refuses both. Both holds therefore keep their exact conditions, audit words and
  console lines; the key decides only whether the route ARRIVES at them, from a guard that is
  exactly one `not` over one name -- and `tests/test_gm_speed_trial_gate.py` pins that shape too,
  from this side, so a future round cannot satisfy his file by deleting it.
- **The gate is compared against the ROW, not the typing**, and that distinction is measured rather
  than asserted: mutating the call site to `_trial_admits(value)` left every other test in the new
  file green, because in all of them the store echoes the typed number back. A store double whose
  read-back diverges now pins both directions -- a row holding the armed value goes out even when
  the GM typed something else, and a row holding something else is HELD even when the typing
  matches. Eleven mutants of the gate were tried in total; eleven died.
- The value compared is `stored`, the store's read-back, not the GM's typed text. `PF_SPEED_TRIAL`
  is rounded through the same f32 trip `persistence_typed_attrs.validate` rounds the row through,
  so arming `400.1` admits the row's `400.1000061035156` by construction rather than by luck.
- **The key opens NOTHING above itself.** It is read below the run-copy-DB gate, the identity read
  and the version gate, and three tests pin each: an armed key on the canonical database still
  withholds and writes no row, an armed key does not open a version gate forced shut, and an armed
  key does not invent a selected character. COO `0646` opened one door for one value; the guards
  above it exist for reasons that have nothing to do with `GT-193`, and no environment variable an
  owner sets in a hurry is a way around the canonical-database gate.
- **Fail-closed in the shape `PFGM_FORCE=1` uses.** Unset, empty, whitespace, `fast`, `nan`, `inf`,
  `1e400`, a non-string, a mapping whose `.get` raises, a value past `F32_MAX` -- every one of them
  is today's behaviour and a console word, never an open door for a value nobody chose. `-0.0` and
  `0.0` are compared as `repr()` rather than with `==`, so `PF_SPEED_TRIAL=0` does not admit
  `/speed -0`.
- **And it does not reopen the LOGIN door, which chief named before it could happen.**
  `login_speed.py`'s point 3 (`wire_trial_only`, written after pf-adversary caught chief's own
  first draft in round `4lf2hl`, D1) states the trap: implement this trial by making
  `send_deferred()` answer `False` and a login gated on `send_deferred()` alone sends whatever the
  ROW holds -- and `/speed` writes its row even when the frame is withheld. His worked example is
  the `GT-193` disaster verbatim: trial opens for `400`, tester types `/speed 300` (frame withheld,
  row written), the ticket's own recovery step is a re-login, `00 00 96 43` goes out. This lane did
  not take that shape: `send_deferred()` is untouched, so after a trial `/speed 450` the resolver
  still answers the constant, with reason `wire_deferred` -- never `wire_trial_only`, which is the
  belt for the shape this round did not build. Measured end to end here, with a companion test that
  proves the row really did move so the assertion is not vacuous.

**The console line, because the operator is the whole point.** `SPEED TRIAL OPEN account=...
command=speed env=PF_SPEED_TRIAL trial_opens_for=450.0 sending=450.0 identity=...`, printed BELOW
the compose so it can never claim bytes that a refused composer never produced. The `SPEED
DEFERRED` line gains a fourth field, `trial_opens_for=`, so an operator who typed the wrong number
learns the right one from the console instead of from the shell she armed it in. Both lines are
pure ASCII (the bridge console is cp874); neither echoes the environment's raw text nor the GM's
typed spelling -- `/speed 4.5e2` on a gate armed at `450` prints `sending=450.0`, and the string
`4.5e2` appears nowhere.

**NONCLAIM, and it is the important paragraph.** This is not evidence that any `/speed` value is
safe on a real client. `GT-193` [FAIL] remains the only client-observable measurement this door
has, and it ends in a dead character, a locked client and a lost attended round. The gate is a way
for the OWNER to try one value WHILE WATCHING, and it closes when her process dies. No milestone
moves, `P-1` does not move, and nothing here has been run against a real client.

**What the tester can do today that she could not yesterday.** Yesterday, trying a single `/speed`
value on a real client required a code change on `main` that would have opened the door for every
value at once, for everyone, permanently -- which is what `COO 2147` point 3 forbids. Today she
types `set PF_SPEED_TRIAL=450` in her own server window, and `/speed 450` sends while `/speed 451`
and every other value stay held by both locks.

## Round `g0nqnz` (2026-09-03T10:2x+07:00) -- the uniqueness claim fourteen modules repeated, made runnable

`NOW.md` P-2 forbids guessing a signed-negative identity "without closing uniqueness/registry".
`gm/name_color_gate.py` already carries `RE-195`'s bounded negative and its closing ask -- "a
coherent nonpositive identity mapping PLUS a typed/live gate proof". The typed/live half needs the
client image and belongs to the RE runner. The uniqueness half is a question about OUR tables, and
until this round the only answer was a COMMENT, hand-copied into fourteen scene modules almost word
for word: *"Never sent in the same generation as another scene's census ... so sharing the numeric
space is a collision in the abstract only."* A claim about data, repeated by hand, run by nobody.

**`gm/identity_registry_census.py` runs it.** It reads the placement tables this repository already
ships -- twelve `world_bgXXXX_identity` modules, `scene2_prison_exile_tables`, the frozen scene-1
rows behind `population.load_port_royal_placements`, and both live `field_mobs` rosters -- and
reports who claims which wire identity. It sends no byte, writes nothing, grants no GM status, and
chooses no identity value.

**What was already runnable, said first, because the first draft of this section implied nothing
was.** `field_mobs` exports `same_scene_identity_collisions` and `cross_scene_identity_collisions`
-- between MOB TABLES -- and all fourteen families already refuse duplicate placement indices at
import (`world_bgXXXX_identity._self_check`, `population.load_port_royal_placements`, five guards in
`field_mobs`). What had no runner: the twelve `world_bgXXXX_identity` census tables, the comparison
BETWEEN the census family and the mob family inside one scene, and the cross-scene ambiguity as data.

**What it measured, on the tables at `1864e4a`.**
* The identity offset is READ BACK from all sixteen sources and agrees everywhere; it is not a
  constant in the file, so the day one family renumbers, `measured_identity_offset` raises by name
  instead of a hardcoded number quietly disagreeing with the wire.
* **Within a scene there is nothing left to discover, and the module says so.** `actor_identity` is
  a property returning the placement index plus one constant in every family, so inside one scene an
  identity collision IS an index collision -- and duplicate indices are already refused at import,
  fourteen times over. pf-adversary (D1) measured that the "no identity names two placements" check
  is therefore unreachable, and that a mutant filing every dispute as benign survived the whole
  first draft. It is now labelled a TRIPWIRE for the day the formula grows a scene term, driven
  directly by a test rather than asserted empty against shipped data.
* **Across scenes uniqueness does not hold**: 113 identity values are handed out by more than one
  scene, and **28** of them are handed out by all fourteen. An identity is NOT a key on its own --
  `(scene_id, identity)` is. That is the runnable form of the defect `field_mobs.scene_for_scene_id`
  already documents in prose, from the round a player in Bg0002 landed a hit that debited a Port
  Royal monster.
* Every field-mob roster identity is also a census identity OF THE SAME SCENE, and the reason that
  matters is the opposite of what this section first said. `world_population.apply_identity_override`
  does **not** refuse a key its generation does not carry: it is
  `entries.append(override.get(identity, original))`, and that function's own docstring says a
  missing key "is not an error". So a roster identity outside the census is SILENTLY DROPPED -- the
  monster's bytes never leave, the client draws the census NPC in that slot, and nothing raises or
  logs. Worse than a refusal, which is why the containment is pinned, and pinned by recomputing it
  rather than reading the field back.
* **Scene 1's two families disagree about what four identities ARE**: the census says template 97
  `Mutant Green Eagle`, the roster says template 916 `Training Iron Man`, on the same placement.
  That is not reported as a defect -- the override exists precisely to replace those census entries
  with the roster's bytes, so one of the two reaches a client. It is pinned because a reader of a
  server log sees both names for one number, and because the day the disagreement SPREADS beyond
  scene 1 should be a red test rather than a shrug. And it is NOT an artefact of comparing two
  numbering spaces: both 97 and 916 are real `CONSTDATA_TH__MOBS.n_ID` rows, the census accessor
  prefers `n_id` precisely because `template_id` in the `world_bgXXXX` families is that scene
  table's own row index (810 rows expose both today and all 810 differ), and scene 2's twelve
  shared identities -- census read through `n_id`, roster through `template_id` -- agree exactly,
  which is what says the two accessors land in one space. Both halves are pinned.

**NONCLAIM, and it is the paragraph that matters.** P-2 did not move. `p2_color_wiring_verdict()`
still refuses, its three blockers are untouched, and a test pins that they are untouched. No
negative-identity scheme is proposed here; no `FontStyleID` appears in the executable source (the
test strips docstrings before it looks, and a second test proves the stripper strips). Closing a
precondition the order names is not permission to do the thing the order forbids.

**pf-adversary, round `g0nqnz`, and what it changed before this landed.** It wrote 22 mutants plus
three evasions and three real-data injections, and **nine mutants survived the first draft**. D1
(the unreachable check above) rewrote the module's central claim; D3 corrected the override sentence
in the opposite direction; D5 caught `test_a_family_that_renumbers_makes_the_offset_refuse` never
calling the function it was named for; D6 created a real file on disk at import time while the suite
stayed green, because the "writes nothing" guard banned the spelling `write(` and not `write_text(`
-- that guard is now an import-surface check plus a normalised token ban; D7 renamed the console
token and survived, because the only assertion compared the constant against itself; D8 showed one
test was a false-red generator for any future scene mined with a non-overlapping index range. All
nine are dead as of this commit, re-measured mutant by mutant. Two findings were accepted as stated
rather than fixed: the module's fifteen parent-package imports are a coupling outlier for this lane
(a census has to read the tables it censuses), and claim 5 survived the attack intact.

**What the tester can do today that she could not yesterday.** Yesterday, an attended tester who saw
a hit land on the wrong body, or a server log naming a monster she was not looking at, had no way to
ask what else in that scene answers to that number, or whether the two halves of the server agree
about what the number IS -- the answer lived in a comment in one module's docstring about one scene.
Today `describe_scene(scene_id, legacy=...)` answers it for any scene in one greppable ASCII line,
`GM_IDENTITY_CENSUS ... disagreeing=N ... unique_within_scene=yes|NO families_agree=yes|NO`, and
scene 1 answers `families_agree=NO disagreeing=4` today. `CORE-REQUEST-GM-050` asks chief for the
one call site in `runtime.py` that would print it at scene entry; until that lands she runs it
herself.
