# DEMO-FULLLOOP-001 — canonical database end-to-end client session runtime pass

Date: 2026-08-17
Scope: one controlled local session driven through the real GameClient against
the canonical database. Platform/lifecycle claim only; no protocol hypothesis,
no inventory mutation, no accepted ceiling movement.

## Result

Grade B pass for the end-to-end lifecycle claim: with the visible-console server
required by CONSOLE-001, the real client completes server select, character
select, `StartGameReq`, scene entry at Port Royal, and a clean two-sided
shutdown, leaving the canonical database logically consistent.

Controlled run `demo_canonical_20260817_041728` (2026-08-17 04:17-04:24 ICT):

1. **Clean predecessor stop.** The previous server (shim PID 14344 / server
   PID 2956) was stopped with one bounded `CTRL_C_EVENT`; helper exit 0, server
   exit 0, ports free at `04:17:33`.
2. **Server start.** `tools\run_foundation_visible.ps1` on the canonical
   database `state\pirateforce.sqlite3`
   (sha256 `7EC83821A3922F9909F8083D0586C2C71FCDB8554AA60AB7E0D48550BAC39EAA`)
   brought up visible shim PID 3496 / server PID 6736; listeners up within
   1 second. Capture root
   `GameClient\capture_demo_canonical_20260817_041728`.
3. **Client start.** `GameClient.local.bin` was started through
   `ProcessStartInfo` with `UseShellExecute=$false`.
4. **UI path.** Server list `Pirate Force Local` / `Channel 1` -> PVP/EXP
   confirmation dialog -> character select showing `Arena01` LV.1 at Port Royal
   with its floating nameboard -> enter game.
5. **Protocol path (server console evidence).**
   - `[MILESTONE] CHARACTER SELECT READY / PickActor state.`
   - `[G< #10] 22 bytes IDs=[(0, 17722, 'GSCN_LoginProtocol'), (15, 7815, 'StartGameReq')]`
   - `[G>] FOUNDATION_SELECTED_START_GAME (418 bytes; late=0.8 ms)` — the response
     carries the UTF-16 name `Arena01`
   - `[G>] V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE (73 bytes; late=1.3 ms)`
   - `[!!!] MILESTONE: StartGameReq selector=0 captured.`
   - `[G>] RUNTIME_RES_ACK_FIRST_REQ` and
     `[G>] V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE` after the first client
     `TeleportVital` request
6. **In-map observation.** The client rendered Port Royal with HP 100/100, LV.1,
   minimap, coordinates X:-9038 Y:-2866, the `Arena01` nameboard, and the chat
   line `[ระบบ] : Pirate Force local server online`. Client-side capture recorded
   `SESSION_START peer=127.0.0.1:60857` at `04:21:12.547` and one retained
   `TeleportVital` event at `04:22:11.797`.
7. **Clean shutdown.** Client exit through its own confirmation dialog, then one
   bounded `CTRL_C_EVENT` to the server console: helper exit 0, server exit 0,
   shim exit 0, listeners remaining 0, exactly one `[FOUNDATION] stopped` marker,
   mirrored stderr 0 bytes.

## Database post-state (canonical, read-only oracle)

Read back over a read-only connection after shutdown:

- `sessions` — exactly one row: `id=08509a0dc3f944ed94a797457ea5962e`,
  `account_id=1`, `selected_character_id=1`,
  `opened_at=2026-08-16T21:21:12.475251+00:00`,
  `closed_at=2026-08-16T21:23:18.557709+00:00`, `lease_generation=1`.
  The session was opened on scene entry and closed on client exit.
- `character_backpack_items` — unchanged at
  `[(id 1, template 2600001, qty 2, slot 0), (id 2, template 2400901, qty 1,
  slot 1), (id 4, template 2200002, qty 1, slot 3)]`.
- `pragma integrity_check` = `ok`; `pragma foreign_key_check` empty.

### Evidence correction

The collection job that ran at `04:24` queried `sessions.generation`, which does
not exist; the real column is `lease_generation`. That job therefore raised
`sqlite3.OperationalError` and **collected no database evidence at all**. The
post-state above was re-derived afterwards over an independent read-only
connection. Any earlier note claiming this database evidence came from the
`04:24` collection job is incorrect; the figures themselves are confirmed.

## Root cause of the earlier "cannot enter game" observation

An earlier attempt (`demo_fullloop_20260817_035212`) reached character select,
emitted `StartGameReq`, and then received nothing until `[*] login idle timeout`.
The cause was database selection, not UI and not any change made during this
milestone:

- That run used `item_move_hyp001_25690817_002012.sqlite3`, whose backpack is
  `[1@slot2, 2@slot1, 4@slot3]` — the HYP-PF-008 **post-move** state.
- `inventory.is_unmoved_baseline()` treats only the initial and merged snapshots
  as baseline.
- The uncommitted M3 work-in-progress guard in `session.select_and_start()`
  raises `PermissionError` for a non-baseline backpack unless the opt-in
  scenario is enabled, so no `StartGame` was composed.

That guard originates in inherited work-in-progress, not in the visible-console
milestone. Running against the canonical baseline database removed the symptom
entirely, which is what this report records.

**Follow-up (open):** the guard fails silently — no log line, empty stderr. A
rejection reason should be logged before this path is exercised again. Recorded
as a sub-item of M3.

## Nonclaims

This proves one controlled single-client session on this machine against this
canonical database. It is **not** proof of multi-client behaviour, reconnect
policy, inventory mutation, occupied-slot behaviour, combat, persistence beyond
the observed session row, or any original-server response policy. No hypothesis
ledger entry changed; `production_allowed` remains `false` everywhere.
