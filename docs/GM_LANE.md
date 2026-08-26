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
| 0x9F2C | `Channel_GMGlobalMessageVital` | server->client | registered in RUNTIME_CLASSMAP; field layout not yet pinned by this lane |
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
- No command *execution* path (see `gm/commands.py` scope note above).
  `gm/teleport_wire.py` gives `warp` a real, tested byte builder for
  `ForcePos`/`CWarpResult`/`TeleportVital`, and `gm/dispatch.py` (this
  round) gives 0x51E9 an inbound authorization gate and a real capture
  sink, but sending a reply and applying any gameplay effect still need a
  runtime send path -- outside this lane's write zone -- so execution stays
  not-built until a `CORE-REQUEST-GM-<nnn>` wires one in and (separately)
  the wide-string field mapping is proven enough to bridge into
  `gm/commands.py`'s grammar.
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

None filed by this lane as of this round. Remaining semantic gaps (what the
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
