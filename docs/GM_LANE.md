# Lane GM -- GM / developer tooling

Opened by PANYA-ORDER (pf_bridge/notes_to_chief/20260826_1630_PANYA-ORDER-
open-Lane-GM-plus-attended-recon-GM-packets-already-in-client-registry.md).
Intent: GM tooling is a multiplier on the project's most expensive resource
(the owner's own attended time) -- warp straight to the scene under test,
toggle NPCs, grant items/level, spawn a monster, without walking the game
every time.

## The three rules that define this lane

1. Everything here must work without `production_allowed=true`.  What gates
   GM behavior is membership in the server-side `gm_accounts` allowlist
   (`gm/accounts.py`) -- default empty, client cannot add itself, ever.
2. GM is a tool to reach a state worth testing, never evidence that a
   feature works.  Warping to an island with GM and seeing the island is not
   a pass for that island's own milestone.  Every test entry and PR that
   uses GM must say which step it skipped.
3. This lane does not answer research questions by itself -- when a byte
   layout or semantic is unknown, it is asked of the RE lane
   (pf_bridge notes_to_chief, `RE-0xx`) and this lane keeps building with
   whatever is already proven, labeled `[SMMUT_LANE_GM_ROR_RE]` where it
   is not.

## Write zone

- `src/pirateforce_foundation/gm/` -- all new modules for this lane
- `tools/pf_mine_gm_scene_catalog.py` -- generator for `gm/scene_catalog.py`
- `tests/test_gm_*.py`
- `docs/GM_LANE.md` (this file)

`runtime.py` / `app.py` / `pf_login_game_server_v141.py` are chief's files;
wiring into them goes through a `CORE-REQUEST-0xx` letter, one per touch
point, never a direct edit from this lane.

## Status by ticket

| Ticket | What | State |
|---|---|---|
| GM-001 | GM state at login (`gm/accounts.py`, `gm/state_wire.py`) | Built. Field layout proven (span sha `03b18673...`); field semantics unconfirmed, awaiting RE-002. Wiring into runtime.py requested as CORE-REQUEST-007 (proposed, awaiting chief's number). |
| GM-002 | Raw capture of inbound `0x51E9` (`gm/command_capture.py`) | Built as a pure log-only capture (no interpretation). Attended chat-probe step queued in `GAME_TEST_QUEUE.md`. |
| GM-003 | Server-side GM command set (`warp`/`npc`/`item`/`lv`/`spawn`/`say`) | Not started this round. Blocked on GM-002's attended capture (to confirm which field of `GM_RunGMCommandVital` carries the command text) and on importing lane A's scene registry / lane B's mob roster rather than duplicating their tables. |
| GM-004 | GM scene-name catalog (`gm/scene_catalog.py`) | Built. Generated from `TEXTDATA_TH__SCENE_NAME_TIP.tsv` (sha `f9076cfc...`), 330 rows -- the opening letter's "331" counted the header row. |

## Open design question flagged by pf-adversary (round 1) -- for chief to answer in CORE-REQUEST-007

`accounts.load_gm_accounts` returns a `frozenset`, which implies "load once,
share." Nothing in this lane says *when* that load happens relative to a
live connection. If the wiring loads it once at server boot and a
connection object holds its own membership result for the life of the
session, then editing `gm_accounts` to revoke someone mid-session does
nothing until the process restarts. `gm/command_capture.py` was changed in
this round specifically so it can never be the thing that goes stale (it
takes the allowlist and recomputes membership on every call rather than
trusting a cached bool) -- but that only closes the capture path. The wiring
CORE-REQUEST-007 asks for still has to decide, and state, how often
`runtime.py` re-checks a connected account against `gm_accounts` after
login.

## Accepted low-severity findings (pf-adversary round 1, not fixed this round)

- `tools/pf_mine_gm_scene_catalog.py`'s only defense against a silently wrong
  source table is that scene ids 1-4 match four hand-verified names; the
  other 326 rows have no invariant beyond "3 exact columns" and "no duplicate
  n_ID". A same-length, same-file-hash mid-row corruption introduced before
  mining would pass `--check` (it re-derives from the same corrupted source)
  and ship a wrong GM-facing label for one scene. Severity is a display bug
  in a GM warp menu, not a security bypass, so this round leaves it as a
  known gap rather than building full per-row schema validation.

## Known-unknown fields (RE lane's job, not guessed here)

- `GM_UpdateGMStateVital` (`0x5A19`): three fields proven structurally
  (`u8@+0x14`, `u8@+0x15`, `u32@+0x18`); no field's semantic meaning
  (is_gm flag? GM level? something else) is confirmed by a client observation
  yet.
- `GM_RunGMCommandVital` (`0x51E9`): structural field layout exists in
  `PF_SERIALIZER_FIELDS.tsv` (mode byte, two u32s behind a nested pointer,
  a byte, and two length-prefixed wide strings); which field is the command
  text is unconfirmed.
