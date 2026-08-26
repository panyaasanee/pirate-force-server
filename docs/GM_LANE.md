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
| 0x51E9 | `GM_RunGMCommandVital` | client->server | **not proven** -- no row in PF_SERIALIZER_FIELDS yet, RE-open |
| 0x8C77 | `GM_RunGMCommandResultVital` | server->client | **not proven** -- RE-open |
| 0x162E | `CheatVital` | both | proven: single UNTAGGED_STRING8_LEN32LE @+0x14 (reference only, not reused as GM wire) |
| 0x9F2C | `Channel_GMGlobalMessageVital` | server->client | registered in RUNTIME_CLASSMAP; field layout not yet pinned by this lane |

## Modules delivered this round

- `gm/accounts.py` (GM-001) -- `is_gm_account` / `load_gm_accounts`, JSON
  config, default empty.
- `gm/state_wire.py` (GM-001) -- `make_gm_update_state_payload` /
  `make_gm_update_state_frame` for 0x5A19. The three field values are plain
  integer parameters, not named booleans: their meaning is unresolved,
  labelled `[สมมติของสาย GM - รอ RE]` in the module docstring, and an RE
  request is filed (CORE-REQUEST-GM-001) to pin them against client handler
  `0x00729F00`.
- `gm/command_capture.py` (GM-002) -- `capture_raw_gm_command`, a raw
  hex-dump sink for 0x51E9. Does not parse or interpret; the point is to
  have real bytes to read a layout off of once an attended session captures
  some.
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
  lands, via its own `CORE-REQUEST-GM-<nnn>` letter.

## What is intentionally NOT built yet, and why

- No wiring of `state_wire` into the actual login path -- that edit belongs
  to `runtime.py`/`app.py` (chief's territory). CORE-REQUEST-GM-001 asks for
  it explicitly: call `make_gm_update_state_frame` after a successful login
  for any account where `is_gm_account()` is true, and send the resulting
  frame to that connection.
- No command *execution* path (see `gm/commands.py` scope note above).
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

## RE requests open (owned by static RE lane, filed via chief)

1. `GM_RunGMCommandVital` serializer 0x00729E10 (W) and
   `GM_RunGMCommandResultVital` 0x00729790 (R) field layout.
2. `GM_UpdateGMStateVital` handler `0x00729F00`: which byte is which flag,
   what the u32 field means, what visibly changes on the client
   (`bm_gm.tga`, `GMModule_Client`).
3. `TeleportVital` / `ForcePos` / `CWarpResult` field layout.
4. Chat input -> 0x51E9 trigger condition (prefix? GM-state gate?), xref
   global id `0x01088F8C`.
