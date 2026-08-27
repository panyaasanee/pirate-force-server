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
| 0x51E9 | `GM_RunGMCommandVital` | client->server | **RE-088 PASS/DONE -- STRUCTURAL-LAYOUT-PINNED** (outer `0x00729E10` span_sha256 `541d82f5...c8554`, nested `0x00726C20` span_sha256 `aa3c7c8d...93559d`): one presence flag `u8tag(0x0B)`; when nonzero, exactly one nested body `u32tag(0x14) + u32tag(0x14) + u8tag(0x0B) + UNTAGGED_WSTRING16LE_LEN32LE + UNTAGGED_WSTRING16LE_LEN32LE`. RE-088 closes the earlier "two runtime-selected sub-paths" question this doc used to carry: the presence flag gates one nested serializer call, not a sub-opcode choosing between two shapes, and RE-088 found no field it could prove is a separate sub-opcode. **Field meaning is still NOT proven** -- the two wide strings are not confirmed to be a command name and its argument text, and the live chat-input trigger condition is RE-091 (open). Decoder: `gm/command_wire.py`. |
| 0x8C77 | `GM_RunGMCommandResultVital` | server->client | **proven**: single u8tag(0x0B) @+0x14, span_sha256 `ad65d125...633e9`. Meaning of the byte not proven (RE-088 explicitly declines to call it success/error). Decoder: `gm/command_wire.py`. |
| 0x162E | `CheatVital` | both | proven: single UNTAGGED_STRING8_LEN32LE @+0x14 (reference only, not reused as GM wire) |
| 0x9F2C | `Channel_GMGlobalMessageVital` | server->client (Global-scope `Channel_*` family) | **already proven elsewhere in this repo -- do not re-derive or re-codec in this lane's zone.** `reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md` (byte-exact static, 69 static guards + `tests/test_chat_channel_family_static.py`, 15 passed) proves `Channel_GMGlobalMessageVital` shares serializer `0x65AD40` with four other channels (LocalTalk/Party/Guild/ActorBoardcast) byte-for-byte identically: `tag 0x48 + u32 byte-length + UTF-16LE` wstring codec, field order `speaker@+0x34` then `body@+0x18`. This is a **different, more specific wire shape** than `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`'s coarser `UNTAGGED_WSTRING16LE_LEN32LE` label for the same offsets implies (no leading tag byte) -- the report's claim is corroborated against real captured GT-006 frames (three independent byte-for-byte hash cross-checks against pins produced by an unrelated code path), which the TSV row alone is not. `src/pirateforce_foundation/channel_message_hypothesis.py` already implements a tested encoder/decoder for all five shared-serializer channels including this one (`CHANNEL_MESSAGE_FIELD_ORDER`, `SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"] = 0x9F2C`). **This lane tried to build its own codec for this message in a since-retracted round (see "Attempted and retracted" below) before finding this.** `gm/say_wire.py` (say-wire round, below) now bridges a parsed `say` `GmCommand` to that existing encoder by import -- no second codec. |
| 0x0E80 | `ForcePos` | direction NOT_OBSERVED (0 captured frames either way, `PF_FIELD_VALIDATION.tsv`) | **RE-090 PASS/DONE**: vec3 only, three `f32tag(0x2A)` (X/Y/Z), span_sha256 `7c6f6cb7...860e0d`. Vital id is not a table row in `VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` (the client computes it at runtime from the name, it is not a stored constant); reproduced here from that file's own documented formula -- see "Vital id formula" below. Codec: `gm/teleport_wire.py`. |
| 0x1BA4 | `CWarpResult` | direction NOT_OBSERVED (0 captured frames either way) | **RE-090 PASS/DONE**: flat `qwordtag(0x32)` + vec3 (`f32tag(0x2A)` x3) + `u16tag(0x12)`, span_sha256 `5e3acf83...986c6db6a9`. The name `Result` is not evidence of direction. Codec: `gm/teleport_wire.py`. |
| 0x25A2 | `TeleportVital` | direction not confirmed, but NOT the same evidentiary state as the two rows above: 132 candidate frames per direction exist at status `A2_STATIC_OPEN` (candidate-matched, not parse-confirmed), unlike `ForcePos`/`CWarpResult`'s genuine zero | **RE-090 PASS/DONE**: `u8tag(0x0B)` field_0x18 -> presence-gated target object (stream order per RE-090's listing: `scene_id` u16tag(0x12), `scene_seq` qwordtag(0x32), then `field_0x10`/`field_0x11` u8 -- **not** ascending object-offset order, same pattern as the aux reorder below; `scene_id`/`scene_seq` are the same RE-077 crosswalk `player_wire.py`/`npc_wire.py` already use -- then vec3 f32tag(0x2A) x3) -> presence-gated auxiliary object (untagged wstring, then four more scalars, **wire order `+0x40` before `+0x38`** even though the object offset is lower -- RE-090 confirms this is real, not a transcription slip) -> `field_0x20` u8 -> `field_0x22` u16tag(0x0F). span_sha256 `fbe813db...df990487` (top), `ec9a5421...9a724df0b5ef` (target), `105bad91...6ccc049c93` (aux). Codec: `gm/teleport_wire.py`. The target field order is this lane's own reading of RE-090's prose listing, not independently re-verified against a real frame -- a follow-up round should run it against the 132 `A2_STATIC_OPEN` candidate frames before this is used against a real client (see the `TeleportTarget` docstring). |

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
  its override on the very next call, no restart needed. Neither file alone
  can grant anything: an override entry for a non-GM account is inert.
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
  `get_login_scene_override(token)` and send that scene_id instead of the
  default start scene when it is not `None`; (2) assemble that scene's
  census from `Data\Scene\Save\bgXXXX\bgXXXX.npc` placements (via
  `gamedata/pf_decode_lua_npc.py`, already used for `bg0001` by lane A/B)
  plus lane B's hostile roster where one exists for that scene (`bg0015`
  has one per the order). See `CORE-REQUEST-GM-015`.

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
  `is_gm_account()` is true, `make_gm_update_state_frame(legacy, 1, 0, 0, 0)`
  is called and the resulting frame is queued to that connection, no
  scenario flag. `is_gm_account()` failures are refused-by-name (login
  proceeds with no GM frame) so a config typo cannot take down the
  listener thread for every player -- see the comment at the call site.
  The four payload values (`1, 0, 0, 0`) remain an unproven placeholder
  tagged `[ASSUMED - awaiting RE]` -- `RE-089 GM-STATE-VISUAL-001` came back
  **DONE/BOUNDED-NEGATIVE** (see wire-facts table): it pins the propagation
  path but finds no render/UI consumer, so it answers CORE-REQUEST-GM-001
  without unblocking a semantic rename. What still needs to resolve real
  semantics is a capture/attended matrix (RE-089's own stated next step),
  not yet opened; wiring itself is done and unaffected.
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

## RE requests open (owned by static RE lane, filed via chief)

Two filed by this lane, both still open as of this round (this list had
drifted stale -- corrected here rather than silently, per this lane's own
rule against letting an inaccurate claim stand):

5. **`RE-104`** GM-EDITOR-WIDGET-OPEN-TRIGGER-001 -- what toggles the
   dedicated GM editor widget active/visible (filed 2026-08-27, follow-up to
   `RE-091` nonclaim (2)). Blocks a scripted procedure for `GT-103`'s
   attended capture matrix; does not block this round's login-scene-override
   work.
6. **`RE-105`** GM-UPDATE-STATE-VITAL-VERSION-001 -- **urgent, filed this
   round**. `GT-101` (attended, owner-observed) proved the `vital_version=1`
   this lane had shipped as `[ASSUMED - awaiting RE]` for
   `GM_UpdateGMStateVital` (`0x5A19`) is wrong: the client rejects it with a
   modal `網路 VitalData 版本不對 --- ErrorData=23065` (`23065` decimal =
   `0x5A19`), stops processing the connection, and closes the socket --
   killing the owner's session on the very account she booted with. `RE-105`
   asks the static RE lane to pin the version the client's `0x00729F00`
   handler actually accepts. **Until `RE-105` closes, no account this
   project's owner boots with may appear in `gm_accounts` while
   `runtime.py`'s `GM_UPDATE_STATE_AFTER_LOGIN` call site
   (`make_gm_update_state_frame(legacy, 1, 0, 0, 0)`, chief's write zone)
   still hardcodes `vital_version=1` -- see `CORE-REQUEST-GM-016`.**

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
