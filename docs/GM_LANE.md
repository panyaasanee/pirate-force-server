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
  `get_login_scene_override(token)` and send that scene_id instead of the
  default start scene when it is not `None`; (2) assemble that scene's
  census from `Data\Scene\Save\bgXXXX\bgXXXX.npc` placements (via
  `gamedata/pf_decode_lua_npc.py`, already used for `bg0001` by lane A/B)
  plus lane B's hostile roster where one exists for that scene (`bg0015`
  has one per the order). See `CORE-REQUEST-GM-015`.

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
  site (`get_login_scene_override(self.token)`) already routes through this
  function, so the new path activates at the existing wiring point with no
  core-file edit.
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

`lane_hooks/lane_gm_chat_command.py` registers for point
`vital_inbound_chat_local_talk`. That point was inert for one round and is
now live: chief wired it in round `lo7e03` (R214, `CORE-REQUEST-GM-028`) as
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
